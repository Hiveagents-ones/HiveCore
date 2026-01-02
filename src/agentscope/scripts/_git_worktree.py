# -*- coding: utf-8 -*-
"""Git worktree support for multi-agent collaboration.

This module provides git worktree operations for isolating agent work:
- Each agent gets a separate worktree (branch) with full codebase copy
- PRs are merged by size (largest first)
- Conflicts are resolved via git's native markers
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol


@dataclass
class MergeResult:
    """Result of a merge operation from working to delivery directory.

    Attributes:
        success (`bool`):
            Whether the merge completed without conflicts.
        conflicts (`list[str]`):
            List of file paths with merge conflicts (if any).
        message (`str`):
            Human-readable description of the merge result.
    """

    success: bool
    conflicts: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class AgentPRStats:
    """Statistics for an agent's PR (diff against main).

    Attributes:
        agent_id (`str`):
            The agent identifier.
        additions (`int`):
            Number of lines added.
        deletions (`int`):
            Number of lines deleted.
        files_changed (`int`):
            Number of files changed.
        total_changes (`int`):
            Total lines changed (additions + deletions).
    """

    agent_id: str
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0

    @property
    def total_changes(self) -> int:
        """Total lines changed."""
        return self.additions + self.deletions


class WorkspaceProtocol(Protocol):
    """Protocol for workspace with container execution support."""

    container_id: str | None
    delivery_dir: str
    working_dir: str

    async def exec(self, cmd: str) -> dict[str, Any]:
        """Execute command in container."""
        ...


class GitWorktreeMixin:
    """Mixin providing git worktree operations for multi-agent collaboration.

    This mixin adds git worktree support to any workspace class that:
    - Has container_id, delivery_dir, working_dir attributes
    - Has an exec() method for running commands in container
    """

    # These will be provided by the class this mixin is used with
    container_id: str | None
    delivery_dir: str
    working_dir: str

    async def exec(self, cmd: str) -> dict[str, Any]:
        """Execute command in container (to be implemented by host class)."""
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Git Worktree methods for multi-agent collaboration
    # -------------------------------------------------------------------------

    async def init_git_repo(self) -> bool:
        """Initialize git repository in delivery directory.

        This sets up the delivery directory as a git repo with an initial commit.
        Required before using git worktree features.
        Idempotent: skips if already initialized.

        Returns:
            `bool`: True if successful (or already initialized).
        """
        if not self.container_id:
            return False

        from ._observability import get_logger

        logger = get_logger()

        try:
            # Check if git is available
            git_check = await self.exec("which git")
            if not git_check["success"]:
                logger.warn("[RuntimeWorkspace] Git not available in container")
                return False

            # Add safe.directory to avoid ownership issues in container
            # Use '*' to trust all directories (safe in container context)
            await self.exec(
                "git config --global --add safe.directory '*'"
            )

            # Check if already initialized (has .git directory IN delivery_dir)
            # IMPORTANT: Must check that .git is directly inside delivery_dir,
            # not in a parent directory. git rev-parse --git-dir returns the
            # path to .git which could be in a parent (e.g., /workspace/.git).
            git_status = await self.exec(
                f"test -d {self.delivery_dir}/.git && echo 'local_git_exists'"
            )
            if git_status.get("success") and "local_git_exists" in git_status.get("output", ""):
                # Already initialized, but ensure git config is set
                logger.info("[RuntimeWorkspace] Git repo already initialized, ensuring config")
                await self.exec(
                    f"cd {self.delivery_dir} && git config user.name 'Agent'"
                )
                await self.exec(
                    f"cd {self.delivery_dir} && git config user.email 'agent@local'"
                )
                # Ensure .git directory ownership is correct for node user
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )
                return True

            # Check if there's a git repo in a parent directory (this would cause issues)
            parent_git_check = await self.exec(
                f"cd {self.delivery_dir} && git rev-parse --git-dir 2>/dev/null"
            )
            if parent_git_check.get("success"):
                parent_git_dir = parent_git_check.get("output", "").strip()
                if parent_git_dir and not parent_git_dir.startswith(self.delivery_dir):
                    logger.warn(
                        f"[RuntimeWorkspace] Found git repo in parent directory: {parent_git_dir}. "
                        f"This may cause worktree issues. Creating new repo in {self.delivery_dir}"
                    )

            # Initialize git repo in delivery directory
            await self.exec(f"cd {self.delivery_dir} && git init")
            await self.exec(
                f"cd {self.delivery_dir} && git config user.name 'Agent'"
            )
            await self.exec(
                f"cd {self.delivery_dir} && git config user.email 'agent@local'"
            )

            # Create .gitignore if it doesn't exist (idempotent)
            gitignore_path = f"{self.delivery_dir}/.gitignore"
            gitignore_check = await self.exec(f"test -f {gitignore_path} && echo exists")
            if not gitignore_check.get("success") or "exists" not in gitignore_check.get("output", ""):
                gitignore_content = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# Database
*.db
*.sqlite3

# Environment
.env
.env.local
venv/
.venv/

# Node
node_modules/

# IDE
.idea/
.vscode/
*.swp

# Logs
*.log

# Build
dist/
build/
*.egg-info/
"""
                # Write .gitignore using heredoc
                await self.exec(
                    f"cat > {gitignore_path} << 'GITIGNORE_EOF'\n{gitignore_content}GITIGNORE_EOF"
                )
                logger.info("[RuntimeWorkspace] Created .gitignore in delivery")

            # Initial commit (allow empty if no files)
            await self.exec(
                f"cd {self.delivery_dir} && git add -A && "
                f"git commit -m 'initial' --allow-empty"
            )

            # Fix ownership of .git directory for node user
            # This is critical because docker exec runs as root by default,
            # but Claude Code tools run as node user inside the container
            await self.exec(
                f"chown -R node:node {self.delivery_dir}/.git"
            )

            logger.info("[RuntimeWorkspace] Git repo initialized in delivery")
            return True

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Git init failed: {exc}")
            return False

    async def create_agent_worktree(self, agent_id: str) -> bool:
        """Create a git worktree for an agent.

        Creates a new branch and worktree for the agent to work in.
        The worktree is a full copy of the codebase on a separate branch.

        Args:
            agent_id (`str`):
                The agent identifier (used as branch name).

        Returns:
            `bool`: True if successful (or if worktree already exists).
        """
        if not self.container_id:
            return False

        from ._observability import get_logger

        logger = get_logger()

        agent_dir = f"{self.working_dir}/{agent_id}"

        try:
            # Check if directory already exists (worktree was previously created)
            check_result = await self.exec(f"test -d {agent_dir} && echo exists")
            if check_result.get("success") and "exists" in check_result.get("output", ""):
                logger.info(f"[RuntimeWorkspace] Worktree already exists for {agent_id}")
                return True

            # Create worktree with new branch
            result = await self.exec(
                f"cd {self.delivery_dir} && "
                f"git worktree add {agent_dir} -b {agent_id}"
            )

            if not result["success"]:
                # Branch might already exist, try without -b
                result = await self.exec(
                    f"cd {self.delivery_dir} && "
                    f"git worktree add {agent_dir} {agent_id}"
                )

            if result["success"]:
                # Fix ownership: worktree created by root, but node user needs write access
                await self.exec(f"chown -R node:node {agent_dir}")
                # Also fix .git/worktrees directory in main repo
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git/worktrees 2>/dev/null || true"
                )
                logger.info(f"[RuntimeWorkspace] Created worktree for {agent_id}")
                return True
            else:
                logger.warn(
                    f"[RuntimeWorkspace] Failed to create worktree: {result['error']}"
                )
                return False

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Worktree creation failed: {exc}")
            return False

    async def get_agent_working_dir(self, agent_id: str) -> str:
        """Get the working directory path for an agent.

        Ensures the worktree is created before returning the path.
        Falls back to creating a plain directory if worktree creation fails.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `str`: Full path to agent's working directory.
        """
        from ._observability import get_logger

        logger = get_logger()
        agent_dir = f"{self.working_dir}/{agent_id}"

        # Ensure tracking sets exist
        if not hasattr(self, "_agent_worktrees"):
            self._agent_worktrees: set[str] = set()
        if not hasattr(self, "_fallback_agents"):
            self._fallback_agents: set[str] = set()

        # Check if agent workspace already exists
        if agent_id not in self._agent_worktrees and agent_id not in self._fallback_agents:
            # Try to create worktree
            success = await self.create_agent_worktree(agent_id)
            if success:
                self._agent_worktrees.add(agent_id)
            else:
                # Fallback: create plain directory without git (will commit via delivery)
                logger.warn(
                    f"[RuntimeWorkspace] Worktree failed, using fallback mode for {agent_id}"
                )
                if self.container_id:
                    await self.exec(f"mkdir -p {agent_dir}")
                    # Use rsync to copy files, excluding .git directory
                    await self.exec(
                        f"rsync -a {self.delivery_dir}/ {agent_dir}/ "
                        f"--exclude=.git 2>/dev/null || "
                        f"cp -r {self.delivery_dir}/* {agent_dir}/ 2>/dev/null || true"
                    )
                    # Mark as fallback mode (no independent git repo)
                    self._fallback_agents.add(agent_id)
                    logger.info(
                        f"[RuntimeWorkspace] Fallback directory created for {agent_id} "
                        f"(commits will go directly to delivery)"
                    )

        return agent_dir

    async def commit_agent_changes(
        self,
        agent_id: str,
        message: str,
    ) -> bool:
        """Commit all changes in an agent's worktree or fallback directory.

        For worktree mode: commits directly in agent's worktree.
        For fallback mode: syncs files to delivery and commits there.

        Args:
            agent_id (`str`):
                The agent identifier.
            message (`str`):
                Commit message.

        Returns:
            `bool`: True if successful (or no changes to commit).
        """
        if not self.container_id:
            return False

        from ._observability import get_logger

        logger = get_logger()

        agent_dir = f"{self.working_dir}/{agent_id}"

        # Check if using fallback mode
        is_fallback = hasattr(self, "_fallback_agents") and agent_id in self._fallback_agents

        try:
            if is_fallback:
                # Fallback mode: sync files back to delivery and commit there
                logger.info(
                    f"[RuntimeWorkspace] Syncing {agent_id} changes to delivery (fallback mode)"
                )
                # Sync agent directory to delivery, excluding .git
                sync_result = await self.exec(
                    f"rsync -a {agent_dir}/ {self.delivery_dir}/ "
                    f"--exclude=.git 2>/dev/null || "
                    f"cp -r {agent_dir}/* {self.delivery_dir}/ 2>/dev/null || true"
                )

                # Stage and commit in delivery directory
                await self.exec(f"cd {self.delivery_dir} && git add -A")
                result = await self.exec(
                    f"cd {self.delivery_dir} && git commit -m '{message}' --allow-empty"
                )

                # Fix .git ownership after commit (new objects created as root)
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )

                if result["success"] or "nothing to commit" in result.get("output", ""):
                    logger.info(
                        f"[RuntimeWorkspace] Committed {agent_id} changes to delivery (fallback mode)"
                    )
                    return True
                else:
                    logger.warn(f"[RuntimeWorkspace] Commit failed: {result.get('error', '')}")
                    return False
            else:
                # Worktree mode: commit directly in agent directory
                await self.exec(f"cd {agent_dir} && git add -A")
                result = await self.exec(
                    f"cd {agent_dir} && git commit -m '{message}' --allow-empty"
                )

                # Fix .git ownership after commit (new objects created as root)
                await self.exec(
                    f"chown -R node:node {agent_dir}/.git 2>/dev/null || true"
                )
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )

                if result["success"] or "nothing to commit" in result.get("output", ""):
                    logger.info(f"[RuntimeWorkspace] Committed changes for {agent_id}")
                    return True
                else:
                    logger.warn(f"[RuntimeWorkspace] Commit failed: {result.get('error', '')}")
                    return False

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Commit failed: {exc}")
            return False

    async def get_agent_pr_stats(self, agent_id: str) -> AgentPRStats:
        """Get PR statistics for an agent (diff against main).

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `AgentPRStats`: Statistics about the agent's changes.
        """
        if not self.container_id:
            return AgentPRStats(agent_id=agent_id)

        agent_dir = f"{self.working_dir}/{agent_id}"

        try:
            # Get diff stats
            result = await self.exec(
                f"cd {agent_dir} && git diff --stat main 2>/dev/null || "
                f"git diff --stat HEAD~1 2>/dev/null || echo ''"
            )

            output = result["output"].strip()
            if not output:
                return AgentPRStats(agent_id=agent_id)

            # Parse last line: "X files changed, Y insertions(+), Z deletions(-)"
            lines = output.split("\n")
            last_line = lines[-1] if lines else ""

            additions = 0
            deletions = 0
            files_changed = 0

            import re

            # Match patterns
            files_match = re.search(r"(\d+) files? changed", last_line)
            add_match = re.search(r"(\d+) insertions?\(\+\)", last_line)
            del_match = re.search(r"(\d+) deletions?\(-\)", last_line)

            if files_match:
                files_changed = int(files_match.group(1))
            if add_match:
                additions = int(add_match.group(1))
            if del_match:
                deletions = int(del_match.group(1))

            return AgentPRStats(
                agent_id=agent_id,
                additions=additions,
                deletions=deletions,
                files_changed=files_changed,
            )

        except Exception:
            return AgentPRStats(agent_id=agent_id)

    async def get_agent_pr_diff(self, agent_id: str) -> str:
        """Get the full diff for an agent's changes.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `str`: Git diff output.
        """
        if not self.container_id:
            return ""

        agent_dir = f"{self.working_dir}/{agent_id}"

        result = await self.exec(
            f"cd {agent_dir} && git diff main 2>/dev/null || "
            f"git diff HEAD~1 2>/dev/null || echo ''"
        )

        return result["output"]

    async def merge_agent_to_main(self, agent_id: str) -> MergeResult:
        """Merge an agent's branch to main.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `MergeResult`: Result of the merge operation.
        """
        if not self.container_id:
            return MergeResult(
                success=False,
                message="Container not started",
            )

        from ._observability import get_logger

        logger = get_logger()

        try:
            # Merge agent branch to main
            result = await self.exec(
                f"cd {self.delivery_dir} && git merge {agent_id} "
                f"-m 'Merge {agent_id}'"
            )

            if result["success"]:
                # Fix .git ownership after merge
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )
                logger.info(f"[RuntimeWorkspace] Merged {agent_id} to main")
                return MergeResult(
                    success=True,
                    message=f"Successfully merged {agent_id}",
                )
            else:
                # Check for conflicts
                if "CONFLICT" in result["output"] or "CONFLICT" in result["error"]:
                    # Get conflict files
                    conflict_result = await self.exec(
                        f"cd {self.delivery_dir} && "
                        f"git diff --name-only --diff-filter=U"
                    )
                    conflicts = [
                        f.strip()
                        for f in conflict_result["output"].split("\n")
                        if f.strip()
                    ]

                    # Abort the merge
                    await self.exec(f"cd {self.delivery_dir} && git merge --abort")

                    return MergeResult(
                        success=False,
                        conflicts=conflicts,
                        message=f"Merge conflict in {len(conflicts)} file(s)",
                    )
                else:
                    return MergeResult(
                        success=False,
                        message=f"Merge failed: {result['error']}",
                    )

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Merge failed: {exc}")
            return MergeResult(
                success=False,
                message=f"Merge failed: {exc}",
            )

    async def update_agent_from_main(self, agent_id: str) -> MergeResult:
        """Update agent's branch by merging main into it.

        This may produce conflicts that the agent needs to resolve.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `MergeResult`: Result with conflicts list if any.
        """
        if not self.container_id:
            return MergeResult(
                success=False,
                message="Container not started",
            )

        from ._observability import get_logger

        logger = get_logger()

        agent_dir = f"{self.working_dir}/{agent_id}"

        try:
            # Merge main into agent branch
            result = await self.exec(
                f"cd {agent_dir} && git merge main -m 'Merge main into {agent_id}'"
            )

            if result["success"]:
                # Fix .git ownership after merge
                await self.exec(
                    f"chown -R node:node {agent_dir}/.git 2>/dev/null || true"
                )
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )
                logger.info(f"[RuntimeWorkspace] Updated {agent_id} from main")
                return MergeResult(
                    success=True,
                    message=f"Successfully updated {agent_id}",
                )
            else:
                # Check for conflicts
                if "CONFLICT" in result["output"] or "CONFLICT" in result["error"]:
                    # Get conflict files
                    conflict_result = await self.exec(
                        f"cd {agent_dir} && git diff --name-only --diff-filter=U"
                    )
                    conflicts = [
                        f.strip()
                        for f in conflict_result["output"].split("\n")
                        if f.strip()
                    ]

                    logger.warn(
                        f"[RuntimeWorkspace] Conflicts in {agent_id}: {conflicts}"
                    )

                    return MergeResult(
                        success=False,
                        conflicts=conflicts,
                        message=f"Conflicts in {len(conflicts)} file(s). "
                        f"Please resolve <<<<<<< ======= >>>>>>> markers.",
                    )
                else:
                    return MergeResult(
                        success=False,
                        message=f"Update failed: {result['error']}",
                    )

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Update failed: {exc}")
            return MergeResult(
                success=False,
                message=f"Update failed: {exc}",
            )

    async def get_conflict_details(self, agent_id: str) -> dict[str, str]:
        """Get details of conflicts in agent's working directory.

        Returns the content of files with conflict markers.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `dict[str, str]`: Map of filename to file content with conflict markers.
        """
        if not self.container_id:
            return {}

        agent_dir = f"{self.working_dir}/{agent_id}"

        # Find files with conflict markers
        result = await self.exec(
            f"cd {agent_dir} && grep -rl '<<<<<<< ' . 2>/dev/null || echo ''"
        )

        conflict_files = [
            f.strip().lstrip("./")
            for f in result["output"].split("\n")
            if f.strip()
        ]

        details = {}
        for filename in conflict_files:
            content_result = await self.exec(f"cat {agent_dir}/{filename}")
            if content_result["success"]:
                details[filename] = content_result["output"]

        return details

    async def mark_conflicts_resolved(self, agent_id: str) -> bool:
        """Mark conflicts as resolved after agent fixes them.

        This stages the resolved files and commits.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `bool`: True if successful.
        """
        if not self.container_id:
            return False

        from ._observability import get_logger

        logger = get_logger()

        agent_dir = f"{self.working_dir}/{agent_id}"

        try:
            # Stage resolved files
            await self.exec(f"cd {agent_dir} && git add -A")

            # Check if there are still conflict markers
            check_result = await self.exec(
                f"cd {agent_dir} && grep -rl '<<<<<<< ' . 2>/dev/null || echo ''"
            )

            if check_result["output"].strip():
                logger.warn(
                    f"[RuntimeWorkspace] Conflict markers still present in {agent_id}"
                )
                return False

            # Commit the merge
            result = await self.exec(
                f"cd {agent_dir} && git commit -m 'Resolve merge conflicts' "
                f"--allow-empty"
            )

            # Fix .git ownership after commit
            await self.exec(
                f"chown -R node:node {agent_dir}/.git 2>/dev/null || true"
            )
            await self.exec(
                f"chown -R node:node {self.delivery_dir}/.git"
            )

            if result["success"] or "nothing to commit" in result["output"]:
                logger.info(f"[RuntimeWorkspace] Conflicts resolved for {agent_id}")
                return True
            else:
                logger.warn(f"[RuntimeWorkspace] Commit failed: {result['error']}")
                return False

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Conflict resolution failed: {exc}")
            return False

    async def remove_agent_worktree(self, agent_id: str) -> bool:
        """Remove an agent's worktree.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `bool`: True if successful.
        """
        if not self.container_id:
            return False

        from ._observability import get_logger

        logger = get_logger()

        agent_dir = f"{self.working_dir}/{agent_id}"

        try:
            result = await self.exec(
                f"cd {self.delivery_dir} && git worktree remove {agent_dir} --force"
            )

            # Also delete the branch
            await self.exec(
                f"cd {self.delivery_dir} && git branch -D {agent_id} 2>/dev/null || true"
            )

            if result["success"]:
                logger.info(f"[RuntimeWorkspace] Removed worktree for {agent_id}")
                return True
            else:
                # Worktree might not exist, that's OK
                return True

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Worktree removal failed: {exc}")
            return False

    async def list_agent_worktrees(self) -> list[str]:
        """List all agent worktrees.

        Returns:
            `list[str]`: List of agent IDs with active worktrees.
        """
        if not self.container_id:
            return []

        result = await self.exec(
            f"cd {self.delivery_dir} && git worktree list --porcelain"
        )

        if not result["success"]:
            return []

        # Parse worktree list
        agents = []
        lines = result["output"].split("\n")
        for line in lines:
            if line.startswith("branch refs/heads/"):
                branch = line.replace("branch refs/heads/", "").strip()
                if branch != "main" and branch != "master":
                    agents.append(branch)

        return agents

    # -------------------------------------------------------------------------
    # Cherry-pick based validation flow
    # -------------------------------------------------------------------------

    async def get_agent_last_commit(self, agent_id: str) -> str | None:
        """Get the last commit hash from an agent's worktree.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `str | None`: Commit hash or None if not found.
        """
        if not self.container_id:
            return None

        agent_dir = f"{self.working_dir}/{agent_id}"

        result = await self.exec(
            f"cd {agent_dir} && git rev-parse HEAD 2>/dev/null"
        )

        if result["success"]:
            return result["output"].strip()
        return None

    async def get_delivery_head(self) -> str | None:
        """Get the current HEAD commit of delivery branch.

        Returns:
            `str | None`: Commit hash or None if not found.
        """
        if not self.container_id:
            return None

        result = await self.exec(
            f"cd {self.delivery_dir} && git rev-parse HEAD 2>/dev/null"
        )

        if result["success"]:
            return result["output"].strip()
        return None

    async def _clean_delivery_before_cherry_pick(self, logger: Any) -> None:
        """Clean delivery branch state before cherry-pick.

        This handles cases where previous operations left the delivery branch
        in a dirty state (uncommitted changes, failed cherry-pick, etc.).

        The cleaning process:
        1. Abort any in-progress cherry-pick
        2. Check for uncommitted changes
        3. If changes exist, either commit them or reset to clean state

        Args:
            logger: Logger instance for output.
        """
        # Step 1: Abort any in-progress cherry-pick or merge
        await self.exec(
            f"cd {self.delivery_dir} && git cherry-pick --abort 2>/dev/null || true"
        )
        await self.exec(
            f"cd {self.delivery_dir} && git merge --abort 2>/dev/null || true"
        )

        # Step 2: Check if delivery has uncommitted changes
        status_result = await self.exec(
            f"cd {self.delivery_dir} && git status --porcelain"
        )

        if status_result.get("success") and status_result.get("output", "").strip():
            # There are uncommitted changes
            dirty_files = status_result["output"].strip()
            logger.warn(
                f"[RuntimeWorkspace] Delivery has uncommitted changes:\n{dirty_files[:500]}"
            )

            # Step 3: Try to commit changes first (preserve work if possible)
            commit_result = await self.exec(
                f"cd {self.delivery_dir} && git add -A && "
                f"git commit -m 'Auto-commit: preserve uncommitted changes before cherry-pick' "
                f"--allow-empty 2>/dev/null"
            )

            if commit_result.get("success"):
                logger.info(
                    "[RuntimeWorkspace] Auto-committed uncommitted changes in delivery"
                )
            else:
                # Commit failed - force reset to clean state
                logger.warn(
                    "[RuntimeWorkspace] Could not commit changes, resetting delivery to HEAD"
                )
                await self.exec(
                    f"cd {self.delivery_dir} && git reset --hard HEAD"
                )
                await self.exec(
                    f"cd {self.delivery_dir} && git clean -fd"
                )

        # Fix ownership after cleanup
        await self.exec(
            f"chown -R node:node {self.delivery_dir}/.git"
        )

    async def cherry_pick_to_delivery(
        self,
        agent_id: str,
        commit_hash: str | None = None,
    ) -> MergeResult:
        """Merge an agent's branch to delivery branch.

        IMPORTANT: This now uses 'git merge' instead of 'git cherry-pick' to
        ensure ALL commits from the agent's branch are merged, not just the
        last one. The old cherry-pick approach only picked the HEAD commit,
        which caused code loss when agents made multiple commits.

        This is used for the merge validation flow:
        1. Agent completes task in worktree (may create multiple commits)
        2. Merge agent's branch to delivery (gets ALL commits)
        3. Validate in delivery directory
        4. If validation fails, reset delivery and let agent fix

        For fallback mode agents (no worktree), changes are already committed
        to delivery, so this returns success immediately.

        Args:
            agent_id (`str`):
                The agent identifier.
            commit_hash (`str | None`):
                Specific commit to merge. If None, uses agent's branch HEAD.
                When provided, only cherry-picks that specific commit.

        Returns:
            `MergeResult`: Result with success status and conflicts if any.
        """
        if not self.container_id:
            return MergeResult(
                success=False,
                message="Container not started",
            )

        from ._observability import get_logger

        logger = get_logger()

        # Check if using fallback mode - changes already committed to delivery
        is_fallback = hasattr(self, "_fallback_agents") and agent_id in self._fallback_agents
        if is_fallback:
            logger.info(
                f"[RuntimeWorkspace] Skipping merge for {agent_id} "
                f"(fallback mode - already committed to delivery)"
            )
            return MergeResult(
                success=True,
                message=f"Fallback mode: {agent_id} changes already in delivery",
            )

        try:
            # CRITICAL: Clean delivery branch before merge
            # This handles cases where previous merges failed and left dirty state
            await self._clean_delivery_before_cherry_pick(logger)

            # If specific commit provided, use cherry-pick for that commit only
            if commit_hash:
                return await self._cherry_pick_single_commit(agent_id, commit_hash, logger)

            # Otherwise, use git merge to get ALL commits from agent's branch
            # This is the key fix: merge the entire branch, not just HEAD commit
            agent_branch = agent_id  # Branch name is same as agent_id

            # First, check if the branch exists
            branch_check = await self.exec(
                f"cd {self.delivery_dir} && git rev-parse --verify {agent_branch} 2>/dev/null"
            )
            if not branch_check["success"]:
                return MergeResult(
                    success=False,
                    message=f"Branch {agent_branch} not found",
                )

            # Get commit count for logging
            commit_count_result = await self.exec(
                f"cd {self.delivery_dir} && "
                f"git log master..{agent_branch} --oneline 2>/dev/null | wc -l"
            )
            commit_count = commit_count_result.get("output", "?").strip()

            logger.info(
                f"[RuntimeWorkspace] Merging {agent_id} branch "
                f"({commit_count} commits) to delivery"
            )

            # Merge the agent's branch to delivery
            # Use --no-ff to always create a merge commit for better history
            result = await self.exec(
                f"cd {self.delivery_dir} && "
                f"git merge {agent_branch} --no-edit -m '{agent_id} implementation'"
            )

            if result["success"]:
                # Fix .git ownership after merge
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )
                logger.info(
                    f"[RuntimeWorkspace] Merged {agent_id} "
                    f"({commit_count} commits) to delivery"
                )
                return MergeResult(
                    success=True,
                    message=f"Successfully merged {agent_id} ({commit_count} commits)",
                )

            error_output = result.get("error", "") + result.get("output", "")

            # Check for "Already up to date" (no changes to merge)
            if "already up to date" in error_output.lower():
                logger.info(
                    f"[RuntimeWorkspace] Branch {agent_id} already up to date"
                )
                return MergeResult(
                    success=True,
                    message=f"Branch {agent_id} already up to date",
                )

            # Check for conflicts
            if "CONFLICT" in error_output or "Automatic merge failed" in error_output:
                # Get conflict files
                conflict_result = await self.exec(
                    f"cd {self.delivery_dir} && "
                    f"git diff --name-only --diff-filter=U"
                )
                conflicts = [
                    f.strip()
                    for f in conflict_result["output"].split("\n")
                    if f.strip()
                ]

                # Abort the merge
                await self.exec(
                    f"cd {self.delivery_dir} && git merge --abort"
                )

                logger.warn(
                    f"[RuntimeWorkspace] Merge conflict for {agent_id}: "
                    f"{conflicts}"
                )

                return MergeResult(
                    success=False,
                    conflicts=conflicts,
                    message=f"Merge conflict in {len(conflicts)} file(s)",
                )

            # Other error
            return MergeResult(
                success=False,
                message=f"Merge failed: {result['error']}",
            )

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Merge failed: {exc}")
            return MergeResult(
                success=False,
                message=f"Merge failed: {exc}",
            )

    async def _cherry_pick_single_commit(
        self,
        agent_id: str,
        commit_hash: str,
        logger: Any,
    ) -> MergeResult:
        """Cherry-pick a single specific commit (used for retry scenarios).

        Args:
            agent_id: The agent identifier.
            commit_hash: The specific commit to cherry-pick.
            logger: Logger instance.

        Returns:
            MergeResult with success status.
        """
        result = await self.exec(
            f"cd {self.delivery_dir} && git cherry-pick {commit_hash}"
        )

        if result["success"]:
            await self.exec(
                f"chown -R node:node {self.delivery_dir}/.git"
            )
            logger.info(
                f"[RuntimeWorkspace] Cherry-picked {agent_id} "
                f"({commit_hash[:8]}) to delivery"
            )
            return MergeResult(
                success=True,
                message=f"Successfully cherry-picked {agent_id}",
            )

        error_output = result.get("error", "") + result.get("output", "")

        # Check for empty cherry-pick
        if "empty" in error_output.lower() or "nothing to commit" in error_output.lower():
            await self.exec(
                f"cd {self.delivery_dir} && git cherry-pick --skip 2>/dev/null || true"
            )
            logger.info(
                f"[RuntimeWorkspace] Skipped empty cherry-pick for {agent_id}"
            )
            return MergeResult(
                success=True,
                message=f"Skipped empty cherry-pick for {agent_id}",
            )

        # Check for conflicts
        if "CONFLICT" in error_output:
            conflict_result = await self.exec(
                f"cd {self.delivery_dir} && "
                f"git diff --name-only --diff-filter=U"
            )
            conflicts = [
                f.strip()
                for f in conflict_result["output"].split("\n")
                if f.strip()
            ]

            await self.exec(
                f"cd {self.delivery_dir} && git cherry-pick --abort"
            )

            logger.warn(
                f"[RuntimeWorkspace] Cherry-pick conflict for {agent_id}: "
                f"{conflicts}"
            )

            return MergeResult(
                success=False,
                conflicts=conflicts,
                message=f"Cherry-pick conflict in {len(conflicts)} file(s)",
            )

        return MergeResult(
            success=False,
            message=f"Cherry-pick failed: {result['error']}",
        )

    async def cherry_pick_with_retry(
        self,
        agent_id: str,
        commit_hash: str | None = None,
        max_retries: int = 3,
        on_conflict_callback: (
            Callable[[str, list[str]], Awaitable[bool]] | None
        ) = None,
    ) -> CherryPickResult:
        """Cherry-pick with conflict resolution retry.

        This method wraps cherry_pick_to_delivery with automatic retry logic
        for handling conflicts. When a conflict occurs:

        1. Sync delivery state to agent worktree (so agent sees latest state)
        2. Call on_conflict_callback to let agent resolve the conflict
        3. Agent makes a new commit with resolved changes
        4. Retry the cherry-pick with the new commit

        For generated files (.pyc, .db, __pycache__, etc.), conflicts are
        automatically resolved using --theirs strategy.

        Args:
            agent_id (`str`):
                The agent identifier.
            commit_hash (`str | None`):
                Specific commit to cherry-pick. If None, uses agent's HEAD.
            max_retries (`int`):
                Maximum number of retry attempts. Default is 3.
            on_conflict_callback (`Callable[[str, list[str]], Awaitable[bool]] | None`):
                Async callback invoked when code conflicts occur.
                Receives (agent_id, list_of_conflicting_files).
                Should return True if agent successfully resolved conflicts
                and made a new commit, False otherwise.
                If None, conflicts will cause immediate failure.

        Returns:
            `CherryPickResult`: Result with success status, conflicts, and
            delivery commit hash if successful.
        """
        from ._observability import get_logger

        logger = get_logger()

        # Generated file patterns that can be auto-resolved
        auto_resolve_patterns = (
            ".pyc",
            ".pyo",
            ".db",
            ".sqlite",
            ".sqlite3",
            "__pycache__",
            ".egg-info",
            ".eggs",
            "dist/",
            "build/",
            ".tox",
            ".coverage",
            "htmlcov/",
            ".pytest_cache",
            ".mypy_cache",
            "node_modules/",
            ".next/",
            ".nuxt/",
        )

        attempt = 0
        last_conflicts: list[str] = []
        current_commit = commit_hash

        while attempt < max_retries:
            attempt += 1
            logger.info(
                f"[RuntimeWorkspace] Cherry-pick attempt {attempt}/{max_retries} "
                f"for {agent_id}"
            )

            # Get current commit if not specified
            if not current_commit:
                current_commit = await self.get_agent_last_commit(agent_id)
                if not current_commit:
                    return CherryPickResult(
                        success=False,
                        validated=False,
                        message=f"No commit found for agent {agent_id}",
                    )

            # Try cherry-pick
            result = await self.cherry_pick_to_delivery(
                agent_id=agent_id,
                commit_hash=current_commit,
            )

            if result.success:
                # Cherry-pick succeeded
                delivery_commit = await self.get_delivery_head()
                logger.info(
                    f"[RuntimeWorkspace] Cherry-pick succeeded for {agent_id} "
                    f"on attempt {attempt}"
                )
                return CherryPickResult(
                    success=True,
                    validated=False,  # Validation happens separately
                    message=result.message,
                    delivery_commit=delivery_commit,
                )

            # Cherry-pick failed
            if not result.conflicts:
                # Non-conflict failure (e.g., no commit found)
                return CherryPickResult(
                    success=False,
                    validated=False,
                    message=result.message,
                )

            # Handle conflicts
            last_conflicts = result.conflicts
            logger.info(
                f"[RuntimeWorkspace] Cherry-pick conflict for {agent_id}: "
                f"{last_conflicts}"
            )

            # Separate auto-resolvable from code conflicts
            auto_resolvable = []
            code_conflicts = []

            for conflict_file in last_conflicts:
                if any(
                    pattern in conflict_file for pattern in auto_resolve_patterns
                ):
                    auto_resolvable.append(conflict_file)
                else:
                    code_conflicts.append(conflict_file)

            # If all conflicts are auto-resolvable, try to resolve them
            if auto_resolvable and not code_conflicts:
                logger.info(
                    f"[RuntimeWorkspace] Auto-resolving {len(auto_resolvable)} "
                    f"generated file conflicts"
                )
                # These files should be regenerated, use theirs (agent's version)
                # But since we already aborted, we need to retry and handle inline
                # For now, just proceed to callback or fail
                # TODO: Implement inline auto-resolution

            # Need agent to resolve code conflicts
            if code_conflicts or (auto_resolvable and not on_conflict_callback):
                if not on_conflict_callback:
                    # No callback provided, can't resolve
                    return CherryPickResult(
                        success=False,
                        validated=False,
                        conflicts=last_conflicts,
                        message=(
                            f"Cherry-pick conflict in {len(last_conflicts)} file(s), "
                            f"no conflict callback provided"
                        ),
                    )

                # Sync delivery state to agent so they have latest code
                logger.info(
                    f"[RuntimeWorkspace] Syncing delivery to {agent_id} for "
                    f"conflict resolution"
                )
                sync_success = await self.sync_delivery_to_agent_worktree(agent_id)
                if not sync_success:
                    return CherryPickResult(
                        success=False,
                        validated=False,
                        conflicts=last_conflicts,
                        message="Failed to sync delivery state to agent worktree",
                    )

                # Call the conflict resolution callback
                logger.info(
                    f"[RuntimeWorkspace] Invoking conflict callback for {agent_id}"
                )
                callback_success = await on_conflict_callback(
                    agent_id, last_conflicts
                )

                if not callback_success:
                    logger.warn(
                        f"[RuntimeWorkspace] Conflict callback failed for {agent_id}"
                    )
                    return CherryPickResult(
                        success=False,
                        validated=False,
                        conflicts=last_conflicts,
                        message="Agent failed to resolve conflicts",
                    )

                # Agent should have made a new commit, get it for next attempt
                current_commit = await self.get_agent_last_commit(agent_id)
                if not current_commit:
                    return CherryPickResult(
                        success=False,
                        validated=False,
                        conflicts=last_conflicts,
                        message=(
                            "Agent resolved conflicts but no new commit found"
                        ),
                    )

                logger.info(
                    f"[RuntimeWorkspace] Agent {agent_id} made new commit "
                    f"{current_commit[:8]}, retrying cherry-pick"
                )
                # Continue to next iteration

        # Exhausted all retries
        return CherryPickResult(
            success=False,
            validated=False,
            conflicts=last_conflicts,
            message=(
                f"Cherry-pick failed after {max_retries} attempts, "
                f"last conflicts: {last_conflicts}"
            ),
        )

    async def reset_delivery(self, to_commit: str | None = None) -> bool:
        """Reset delivery branch to a specific commit.

        Used when validation fails after cherry-pick.

        Args:
            to_commit (`str | None`):
                Commit to reset to. If None, resets to HEAD~1.

        Returns:
            `bool`: True if successful.
        """
        if not self.container_id:
            return False

        from ._observability import get_logger

        logger = get_logger()

        try:
            if to_commit:
                reset_target = to_commit
            else:
                reset_target = "HEAD~1"

            result = await self.exec(
                f"cd {self.delivery_dir} && git reset --hard {reset_target}"
            )

            if result["success"]:
                # Fix .git ownership after reset
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )
                logger.info(
                    f"[RuntimeWorkspace] Reset delivery to {reset_target}"
                )
                return True
            else:
                logger.warn(
                    f"[RuntimeWorkspace] Reset failed: {result['error']}"
                )
                return False

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Reset failed: {exc}")
            return False

    async def reset_delivery_for_retry(
        self,
        agent_id: str,
        to_commit: str | None = None,
    ) -> tuple[bool, bool]:
        """Reset delivery and sync to agent's working directory if in fallback mode.

        This method handles the validation-failure-retry scenario:
        - Worktree mode: Only reset delivery, agent keeps their branch state
        - Fallback mode: Reset delivery AND sync to agent's working directory

        The distinction is critical because:
        - Worktree agents can incrementally fix on their own branch
        - Fallback agents need the reset state to avoid re-applying old changes

        Args:
            agent_id (`str`):
                The agent identifier.
            to_commit (`str | None`):
                Commit to reset to. If None, resets to HEAD~1.

        Returns:
            `tuple[bool, bool]`: (reset_success, sync_performed)
        """
        from ._observability import get_logger

        logger = get_logger()

        # Step 1: Reset delivery
        reset_success = await self.reset_delivery(to_commit)
        if not reset_success:
            return False, False

        # Step 2: Check if fallback mode - only sync in fallback mode
        is_fallback = (
            hasattr(self, "_fallback_agents") and agent_id in self._fallback_agents
        )

        if is_fallback:
            # Fallback mode: sync delivery state back to agent's working directory
            # This is essential because:
            # - Agent's working directory still has the old (failed) modifications
            # - Without sync, next commit would rsync old changes back to delivery
            logger.info(
                f"[RuntimeWorkspace] Syncing reset state to {agent_id} (fallback mode)"
            )
            sync_success = await self.sync_delivery_to_agent_worktree(agent_id)
            if not sync_success:
                logger.warn(
                    f"[RuntimeWorkspace] Failed to sync delivery to {agent_id}"
                )
                return True, False  # Reset succeeded but sync failed
            return True, True
        else:
            # Worktree mode: agent keeps their branch state
            # They will create a new commit on their branch and re-cherry-pick
            logger.debug(
                f"[RuntimeWorkspace] Skipping sync for {agent_id} (worktree mode)"
            )
            return True, False

    async def sync_delivery_to_agent_worktree(self, agent_id: str) -> bool:
        """Sync delivery directory content to an agent's worktree.

        Used when cherry-pick has conflicts - sync delivery state to agent
        so they can re-implement based on the latest state.

        This does NOT change git history - it only syncs file content.
        The agent should then make a new commit with their fixed changes.

        Args:
            agent_id (`str`):
                The agent identifier.

        Returns:
            `bool`: True if successful.
        """
        if not self.container_id:
            return False

        from ._observability import get_logger

        logger = get_logger()

        agent_dir = f"{self.working_dir}/{agent_id}"

        try:
            # Use rsync to sync file content (excluding .git)
            # NOTE: Do NOT use --delete flag!
            # --delete would wipe agent's work and cause infinite conflict loop:
            #   1. Sync (--delete) overwrites agent dir with delivery content
            #   2. Agent recreates files (e.g., requirements.txt)
            #   3. Cherry-pick conflicts (delivery already has same files)
            #   4. Loop back to step 1...
            #
            # Without --delete: delivery files are merged into agent dir,
            # preserving agent's unique files. Agent can then modify
            # the conflicting files based on delivery's version.
            result = await self.exec(
                f"rsync -a "
                f"--exclude='.git' "
                f"{self.delivery_dir}/ {agent_dir}/"
            )

            if result["success"]:
                logger.info(
                    f"[RuntimeWorkspace] Synced delivery to {agent_id} worktree"
                )
                return True
            else:
                logger.warn(
                    f"[RuntimeWorkspace] Sync failed: {result['error']}"
                )
                return False

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Sync failed: {exc}")
            return False

    async def finalize_delivery_to_main(self) -> MergeResult:
        """Finalize delivery branch by fast-forward merging to main.

        Called after all tasks pass validation in delivery.
        This makes main point to the same commit as delivery.

        Returns:
            `MergeResult`: Result of the operation.
        """
        if not self.container_id:
            return MergeResult(
                success=False,
                message="Container not started",
            )

        from ._observability import get_logger

        logger = get_logger()

        try:
            # Get current delivery HEAD
            delivery_head = await self.get_delivery_head()

            # Update main to point to delivery HEAD
            # We use reset instead of merge to ensure fast-forward
            result = await self.exec(
                f"cd {self.delivery_dir} && "
                f"git checkout main && "
                f"git reset --hard {delivery_head} && "
                f"git checkout -"  # Go back to previous branch
            )

            if result["success"]:
                # Fix .git ownership after finalize
                await self.exec(
                    f"chown -R node:node {self.delivery_dir}/.git"
                )
                logger.info(
                    "[RuntimeWorkspace] Finalized delivery to main"
                )
                return MergeResult(
                    success=True,
                    message="Successfully finalized delivery to main",
                )
            else:
                return MergeResult(
                    success=False,
                    message=f"Finalize failed: {result['error']}",
                )

        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Finalize failed: {exc}")
            return MergeResult(
                success=False,
                message=f"Finalize failed: {exc}",
            )


@dataclass
class CherryPickResult:
    """Result of cherry-pick validation flow.

    Attributes:
        success (`bool`):
            Whether the cherry-pick and validation succeeded.
        validated (`bool`):
            Whether validation was performed (vs failed at cherry-pick).
        conflicts (`list[str]`):
            List of conflicting files if cherry-pick failed.
        validation_errors (`list[str]`):
            List of validation errors if validation failed.
        message (`str`):
            Human-readable description of the result.
        delivery_commit (`str | None`):
            The commit hash in delivery after cherry-pick (if successful).
    """

    success: bool
    validated: bool = False
    conflicts: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    message: str = ""
    delivery_commit: str | None = None


__all__ = [
    "MergeResult",
    "AgentPRStats",
    "CherryPickResult",
    "GitWorktreeMixin",
]
