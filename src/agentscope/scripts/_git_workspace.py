# -*- coding: utf-8 -*-
"""Git-based workspace management for isolated requirement execution.

This module provides Git integration for HiveCore execution:
- Branch isolation: Each requirement gets its own branch
- Change validation: Detect actual vs claimed changes
- Destruction prevention: Detect suspicious file deletions/truncations
- Merge strategy: Combine requirement branches with conflict handling
- Rollback support: Easy recovery from failed implementations

Usage:
    git_ws = GitWorkspace(workspace_dir)
    git_ws.init()

    for req in requirements:
        git_ws.create_branch(req["id"])
        # ... agent implementation ...
        git_ws.commit_requirement(req["id"])
        git_ws.switch_to_main()

    # Merge all
    for req in requirements:
        git_ws.merge_requirement(req["id"])
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ChangeStats:
    """Statistics about file changes."""

    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.modified or self.deleted)

    @property
    def total_files(self) -> int:
        """Total number of changed files."""
        return len(self.added) + len(self.modified) + len(self.deleted)


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool
    conflicts: list[str] = field(default_factory=list)
    merged_files: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ValidationResult:
    """Result of change validation."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class GitWorkspace:
    """Git-based workspace management for isolated requirement execution.

    Provides branch-per-requirement isolation with merge capabilities.
    """

    def __init__(
        self,
        workspace: Path,
        main_branch: str = "main",
        auto_init: bool = False,
    ):
        """Initialize GitWorkspace.

        Args:
            workspace: Path to the workspace directory.
            main_branch: Name of the main branch.
            auto_init: Whether to automatically initialize git repo.
        """
        # Use absolute path to ensure GIT_DIR env var works correctly
        self.workspace = Path(workspace).resolve()
        self.main_branch = main_branch
        self._initialized = False

        if auto_init and not self._is_git_repo():
            self.init()

    def _is_git_repo(self) -> bool:
        """Check if workspace is already a git repository."""
        return (self.workspace / ".git").exists()

    def _run(
        self,
        cmd: str,
        check: bool = True,
        capture: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a git command in the workspace.

        Args:
            cmd: Git command to run (without 'git' prefix).
            check: Whether to raise on non-zero exit.
            capture: Whether to capture output.

        Returns:
            CompletedProcess with stdout/stderr.

        Note:
            Uses GIT_DIR and GIT_WORK_TREE env vars to ensure Git
            operations are isolated to this workspace, even when
            workspace is inside a parent Git repository.
        """
        full_cmd = f"git {cmd}"

        # Set environment to isolate from parent repos
        env = dict(os.environ)
        git_dir = self.workspace / ".git"
        env["GIT_DIR"] = str(git_dir)
        env["GIT_WORK_TREE"] = str(self.workspace)

        result = subprocess.run(
            full_cmd,
            shell=True,
            cwd=self.workspace,
            capture_output=capture,
            text=True,
            env=env,
        )
        if check and result.returncode != 0:
            # Ignore certain non-error cases
            if "nothing to commit" in result.stdout + result.stderr:
                return result
            if "Already on" in result.stdout + result.stderr:
                return result
            raise subprocess.CalledProcessError(
                result.returncode,
                full_cmd,
                result.stdout,
                result.stderr,
            )
        return result

    def _run_init(self, cmd: str) -> subprocess.CompletedProcess:
        """Run git command during init (before .git exists).

        Unlike _run(), this doesn't set GIT_DIR env var since
        .git directory doesn't exist yet.
        """
        full_cmd = f"git {cmd}"
        return subprocess.run(
            full_cmd,
            shell=True,
            cwd=self.workspace,
            capture_output=True,
            text=True,
        )

    def _make_git_dir_writable(self) -> None:
        """Make .git directory writable by all users.

        This is needed for container execution where a non-root user
        (e.g., node with uid=1000) needs to write to .git directory
        that was created by the host user.
        """
        import os
        import stat

        git_dir = self.workspace / ".git"
        if not git_dir.exists():
            return

        # Make .git and all subdirectories/files writable by all users
        for root, dirs, files in os.walk(git_dir):
            root_path = Path(root)
            # Make directories accessible
            for d in dirs:
                dir_path = root_path / d
                try:
                    # Add write permission for all users
                    current_mode = dir_path.stat().st_mode
                    dir_path.chmod(current_mode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
                except OSError:
                    pass
            # Make files writable
            for f in files:
                file_path = root_path / f
                try:
                    current_mode = file_path.stat().st_mode
                    file_path.chmod(current_mode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
                except OSError:
                    pass
        # Make .git directory itself writable
        try:
            current_mode = git_dir.stat().st_mode
            git_dir.chmod(current_mode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
        except OSError:
            pass

    def init(self) -> bool:
        """Initialize git repository with initial commit.

        Returns:
            True if initialization succeeded.
        """
        if self._is_git_repo():
            self._initialized = True
            return True

        try:
            # Use _run_init for commands before .git exists
            self._run_init("init")
            self._run("config user.email 'hivecore@local'")
            self._run("config user.name 'HiveCore'")

            # Create .gitignore
            gitignore = self.workspace / ".gitignore"
            gitignore.write_text(
                "node_modules/\n"
                "__pycache__/\n"
                "*.pyc\n"
                ".venv/\n"
                "venv/\n"
                ".env\n"
                "*.log\n"
                ".DS_Store\n",
                encoding="utf-8",
            )

            self._run("add -A")
            self._run("commit -m 'Initial scaffolding' --allow-empty")

            # Rename to main if needed
            result = self._run("branch --show-current", check=False)
            current = result.stdout.strip()
            if current and current != self.main_branch:
                self._run(f"branch -m {current} {self.main_branch}")

            # Make .git directory writable by all users (for container execution)
            # This is needed when the workspace is mounted into a container
            # where a non-root user needs to write to .git
            self._make_git_dir_writable()

            self._initialized = True
            return True
        except subprocess.CalledProcessError as e:
            from ._observability import get_logger
            get_logger().warn(f"[GitWorkspace] Init failed: {e.stderr}")
            return False

    def create_branch(self, rid: str) -> str:
        """Create and checkout a branch for a requirement.

        Args:
            rid: Requirement ID (e.g., "REQ-001").

        Returns:
            Branch name.
        """
        branch = self._branch_name(rid)

        # Check if branch exists
        result = self._run(f"branch --list {branch}", check=False)
        if branch in result.stdout:
            # Branch exists, just checkout
            self._run(f"checkout {branch}")
        else:
            # Create new branch from main
            self._run(f"checkout -b {branch} {self.main_branch}")

        return branch

    def _branch_name(self, rid: str) -> str:
        """Generate branch name from requirement ID."""
        return f"req/{rid.lower().replace(' ', '-')}"

    def get_current_branch(self) -> str:
        """Get current branch name."""
        result = self._run("branch --show-current")
        return result.stdout.strip()

    def get_changes(self) -> ChangeStats:
        """Get actual changes in working directory.

        Returns:
            ChangeStats with added/modified/deleted files.
        """
        stats = ChangeStats()

        # Get status of all files (staged and unstaged)
        result = self._run("status --porcelain", check=False)

        for line in result.stdout.split("\n"):
            # Skip empty lines (but preserve leading spaces in non-empty lines)
            if not line.strip():
                continue

            # Git status --porcelain format: XY PATH
            # X = index status, Y = worktree status
            # Ensure line has at least 3 characters (XY + space)
            if len(line) < 3:
                continue

            status = line[:2]
            filepath = line[3:].strip()

            # Handle renamed files
            if " -> " in filepath:
                filepath = filepath.split(" -> ")[1]

            # Remove quotes if present
            filepath = filepath.strip('"')

            if status in ("A ", "??"," A"):
                stats.added.append(filepath)
            elif status in ("M ", " M", "MM"):
                stats.modified.append(filepath)
            elif status in ("D ", " D"):
                stats.deleted.append(filepath)

        return stats

    def get_diff_stats(self) -> list[dict[str, Any]]:
        """Get detailed diff statistics for each file.

        Returns:
            List of dicts with file path and line changes.
        """
        result = self._run("diff HEAD --numstat", check=False)
        stats = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) >= 3:
                added, deleted, path = parts[0], parts[1], parts[2]

                # Handle binary files
                if added == "-" or deleted == "-":
                    stats.append({
                        "path": path,
                        "added": 0,
                        "deleted": 0,
                        "binary": True,
                    })
                else:
                    stats.append({
                        "path": path,
                        "added": int(added),
                        "deleted": int(deleted),
                        "binary": False,
                    })

        return stats

    def validate_changes(
        self,
        max_deletion_ratio: float = 0.8,
        min_file_size: int = 10,
    ) -> ValidationResult:
        """Validate changes for suspicious patterns.

        Args:
            max_deletion_ratio: Max ratio of deleted to total lines.
            min_file_size: Minimum file size in bytes to be considered valid.

        Returns:
            ValidationResult with violations and warnings.
        """
        result = ValidationResult(is_valid=True)
        diff_stats = self.get_diff_stats()

        for stat in diff_stats:
            path = stat["path"]
            added = stat.get("added", 0)
            deleted = stat.get("deleted", 0)

            if stat.get("binary"):
                continue

            total = added + deleted
            if total == 0:
                continue

            # Check for suspicious deletions
            if deleted > 50 and added < 5:
                deletion_ratio = deleted / total
                if deletion_ratio > max_deletion_ratio:
                    result.violations.append(
                        f"Suspicious deletion in {path}: +{added}/-{deleted}"
                    )
                    result.is_valid = False

            # Check for files being emptied
            full_path = self.workspace / path
            if full_path.exists():
                size = full_path.stat().st_size
                if size < min_file_size and deleted > 20:
                    result.violations.append(
                        f"File nearly emptied: {path} ({size} bytes, -{deleted} lines)"
                    )
                    result.is_valid = False

        # Check for important files being deleted
        changes = self.get_changes()
        important_patterns = [
            "package.json",
            "requirements.txt",
            "tsconfig.json",
            "vite.config",
            "docker-compose",
            "Dockerfile",
        ]

        for deleted_file in changes.deleted:
            for pattern in important_patterns:
                if pattern in deleted_file:
                    result.warnings.append(
                        f"Important file deleted: {deleted_file}"
                    )

        return result

    def commit_requirement(
        self,
        rid: str,
        message: str | None = None,
        force: bool = False,
    ) -> bool:
        """Commit changes for a requirement.

        Args:
            rid: Requirement ID.
            message: Commit message (auto-generated if None).
            force: Whether to commit even with violations.

        Returns:
            True if commit succeeded.
        """
        changes = self.get_changes()

        if not changes.has_changes:
            from ._observability import get_logger
            get_logger().debug(f"[GitWorkspace] No changes to commit for {rid}")
            return False

        # Validate changes unless forced
        if not force:
            validation = self.validate_changes()
            if not validation.is_valid:
                from ._observability import get_logger
                logger = get_logger()
                for v in validation.violations:
                    logger.warn(f"[GitWorkspace] {v}")
                return False

        # Stage and commit
        self._run("add -A")

        msg = message or f"Implement {rid}"
        # Escape single quotes in message
        msg = msg.replace("'", "'\"'\"'")
        self._run(f"commit -m '{msg}'")

        return True

    def rollback_changes(self) -> None:
        """Discard all uncommitted changes."""
        self._run("checkout -- .", check=False)
        self._run("clean -fd", check=False)

    def switch_to_main(self) -> None:
        """Switch back to main branch."""
        self._run(f"checkout {self.main_branch}")

    def merge_requirement(
        self,
        rid: str,
        strategy: str = "recursive",
        abort_on_conflict: bool = False,
    ) -> MergeResult:
        """Merge requirement branch into main.

        Args:
            rid: Requirement ID.
            strategy: Git merge strategy.
            abort_on_conflict: Whether to abort merge on conflict.

        Returns:
            MergeResult with success status and any conflicts.
        """
        branch = self._branch_name(rid)
        result = MergeResult(success=False)

        # Ensure we're on main
        self.switch_to_main()

        try:
            merge_result = self._run(
                f"merge {branch} --no-edit -s {strategy}",
                check=False,
            )

            if merge_result.returncode == 0:
                result.success = True
                # Get merged files
                log_result = self._run(
                    f"diff --name-only HEAD~1..HEAD",
                    check=False,
                )
                result.merged_files = [
                    f for f in log_result.stdout.strip().split("\n") if f
                ]
            else:
                # Check for conflicts
                conflict_result = self._run(
                    "diff --name-only --diff-filter=U",
                    check=False,
                )
                conflicts = [
                    f for f in conflict_result.stdout.strip().split("\n") if f
                ]

                if conflicts:
                    result.conflicts = conflicts
                    if abort_on_conflict:
                        self._run("merge --abort", check=False)
                    else:
                        # Mark conflicts for manual resolution
                        result.error = "Merge conflicts detected"
                else:
                    result.error = merge_result.stderr

        except subprocess.CalledProcessError as e:
            result.error = str(e)

        return result

    def resolve_conflicts_theirs(self) -> None:
        """Resolve all conflicts by accepting incoming changes."""
        self._run("checkout --theirs .", check=False)
        self._run("add -A")
        self._run("commit -m 'Resolve conflicts: accept incoming'", check=False)

    def resolve_conflicts_ours(self) -> None:
        """Resolve all conflicts by keeping current changes."""
        self._run("checkout --ours .", check=False)
        self._run("add -A")
        self._run("commit -m 'Resolve conflicts: keep current'", check=False)

    def get_file_at_commit(
        self,
        filepath: str,
        commit: str = "HEAD~1",
    ) -> str | None:
        """Get file content at a specific commit.

        Args:
            filepath: Relative path to file.
            commit: Commit reference.

        Returns:
            File content or None if not found.
        """
        try:
            result = self._run(f"show {commit}:{filepath}", check=False)
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return None

    def restore_file(self, filepath: str, commit: str = "HEAD~1") -> bool:
        """Restore a file from a previous commit.

        Args:
            filepath: Relative path to file.
            commit: Commit to restore from.

        Returns:
            True if restore succeeded.
        """
        try:
            self._run(f"checkout {commit} -- {filepath}")
            return True
        except subprocess.CalledProcessError:
            return False

    def get_branch_list(self) -> list[str]:
        """Get list of all branches."""
        result = self._run("branch --list", check=False)
        branches = []
        for line in result.stdout.strip().split("\n"):
            if line:
                # Remove leading * and whitespace
                branch = line.lstrip("* ").strip()
                if branch:
                    branches.append(branch)
        return branches

    def delete_branch(self, rid: str, force: bool = False) -> bool:
        """Delete a requirement branch.

        Args:
            rid: Requirement ID.
            force: Whether to force delete.

        Returns:
            True if deletion succeeded.
        """
        branch = self._branch_name(rid)
        flag = "-D" if force else "-d"

        try:
            self._run(f"branch {flag} {branch}")
            return True
        except subprocess.CalledProcessError:
            return False

    def get_log(self, count: int = 10) -> list[dict[str, str]]:
        """Get recent commit log.

        Args:
            count: Number of commits to retrieve.

        Returns:
            List of commit dicts with hash, message, author, date.
        """
        result = self._run(
            f"log --oneline -n {count} --format='%h|%s|%an|%ad'",
            check=False,
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) >= 2:
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2] if len(parts) > 2 else "",
                    "date": parts[3] if len(parts) > 3 else "",
                })

        return commits

    def cleanup(self) -> None:
        """Clean up merged requirement branches."""
        branches = self.get_branch_list()
        for branch in branches:
            if branch.startswith("req/") and branch != self.get_current_branch():
                self.delete_branch(branch.replace("req/", ""), force=True)
