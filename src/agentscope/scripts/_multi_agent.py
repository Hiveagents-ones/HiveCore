# -*- coding: utf-8 -*-
"""Multi-Agent parallel workspace management module.

This module provides:
- MultiAgentWorkspace: Manage multiple agent working directories in parallel
- AgentTask: Task definition for each agent
- ParallelExecutionResult: Result of parallel execution
- smart_merge: LLM-powered intelligent merge for conflicts
- sort_tasks_by_dependency: Sort tasks by requirement dependencies

Architecture:
    /workspace/
    ├── delivery/           # Delivery directory (main branch)
    ├── agents/             # Agent working directories
    │   ├── agent-001/
    │   ├── agent-002/
    │   └── ...

Usage:
    ws = RuntimeWorkspaceWithPR(...)
    await ws.start()

    multi_ws = MultiAgentWorkspace(ws, max_agents=4)
    await multi_ws.init_agent_dirs(3)

    tasks = [
        AgentTask(agent_id="agent-001", requirement={"category": "backend"}, ...),
        AgentTask(agent_id="agent-002", requirement={"category": "frontend"}, ...),
    ]

    result = await multi_ws.parallel_execute(tasks, execute_func)
    if result.success:
        merge_result = await multi_ws.merge_all_to_delivery(result.completed_tasks)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Awaitable

if TYPE_CHECKING:
    from ._runtime_workspace import RuntimeWorkspaceWithPR, MergeResult


@dataclass
class AgentTask:
    """Agent task definition.

    Attributes:
        agent_id (`str`):
            Unique identifier for the agent (e.g., "agent-001").
        requirement (`dict[str, Any]`):
            Requirement details including 'category', 'description', etc.
        working_dir (`str`):
            Working directory path for this agent.
        status (`str`):
            Task status: 'pending', 'running', 'completed', 'failed'.
        result (`dict[str, Any] | None`):
            Execution result after task completion.
    """

    agent_id: str
    requirement: dict[str, Any]
    working_dir: str
    status: str = "pending"  # pending, running, completed, failed
    result: dict[str, Any] | None = None


@dataclass
class ParallelExecutionResult:
    """Result of parallel execution.

    Attributes:
        success (`bool`):
            Whether all tasks completed successfully.
        completed_tasks (`list[AgentTask]`):
            List of successfully completed tasks.
        failed_tasks (`list[AgentTask]`):
            List of failed tasks.
        merge_conflicts (`list[str]`):
            List of file paths with merge conflicts.
        message (`str`):
            Human-readable description of the execution result.
    """

    success: bool
    completed_tasks: list[AgentTask]
    failed_tasks: list[AgentTask]
    merge_conflicts: list[str] = field(default_factory=list)
    message: str = ""


class MultiAgentWorkspace:
    """Multi-Agent parallel workspace manager.

    Supports multiple agents working simultaneously in different directories,
    with final merge to unified delivery directory.

    Directory structure:
        /workspace/
        ├── delivery/           # Delivery directory (main branch)
        ├── agents/             # Agent working directories
        │   ├── agent-001/
        │   ├── agent-002/
        │   └── ...
    """

    def __init__(
        self,
        base_workspace: "RuntimeWorkspaceWithPR",
        max_agents: int = 4,
    ):
        """Initialize multi-agent workspace.

        Args:
            base_workspace (`RuntimeWorkspaceWithPR`):
                Base runtime workspace instance.
            max_agents (`int`):
                Maximum number of parallel agents.
        """
        self.base_workspace = base_workspace
        self.max_agents = max_agents

        # Use paths from base workspace
        base_dir = base_workspace.base_workspace_dir
        self.delivery_dir = f"{base_dir}/delivery"
        self.agents_base_dir = f"{base_dir}/agents"

        # Track agent directories: agent_id -> dir_path
        self.agent_dirs: dict[str, str] = {}

        # Semaphore for limiting concurrent agents
        self._semaphore: asyncio.Semaphore | None = None

    async def init_agent_dirs(self, num_agents: int) -> list[str]:
        """Initialize agent working directories.

        Creates agent directories by copying from delivery directory.

        Args:
            num_agents (`int`):
                Number of agent directories to create.

        Returns:
            `list[str]`:
                List of created agent directory paths.

        Raises:
            ValueError: If num_agents exceeds max_agents.
            RuntimeError: If base workspace is not initialized.
        """
        from ._observability import get_logger

        logger = get_logger()

        if num_agents > self.max_agents:
            raise ValueError(
                f"Requested {num_agents} agents exceeds max_agents={self.max_agents}"
            )

        if not self.base_workspace.is_initialized:
            raise RuntimeError("Base workspace not initialized. Call start() first.")

        logger.info(f"[MultiAgent] Initializing {num_agents} agent directories")

        # Create agents base directory
        await self.base_workspace.exec(f"mkdir -p {self.agents_base_dir}")

        created_dirs: list[str] = []
        self.agent_dirs.clear()

        for i in range(num_agents):
            agent_id = f"agent-{i + 1:03d}"
            agent_dir = f"{self.agents_base_dir}/{agent_id}"

            # Create agent directory
            await self.base_workspace.exec(f"mkdir -p {agent_dir}")

            # Sync from delivery to agent directory
            # rsync -a: archive mode (preserves permissions, timestamps, etc.)
            sync_result = await self.base_workspace.exec(
                f"rsync -a {self.delivery_dir}/ {agent_dir}/ 2>/dev/null || "
                f"cp -a {self.delivery_dir}/. {agent_dir}/ 2>/dev/null || true"
            )

            if sync_result.get("error") and "rsync" not in sync_result["error"]:
                logger.warn(f"[MultiAgent] Sync warning for {agent_id}: {sync_result['error']}")

            self.agent_dirs[agent_id] = agent_dir
            created_dirs.append(agent_dir)

            logger.debug(f"[MultiAgent] Created {agent_id} at {agent_dir}")

        # Initialize semaphore for concurrent execution
        self._semaphore = asyncio.Semaphore(self.max_agents)

        logger.info(f"[MultiAgent] Initialized {len(created_dirs)} agent directories")
        return created_dirs

    async def parallel_execute(
        self,
        tasks: list[AgentTask],
        execute_func: Callable[[AgentTask], Awaitable[dict[str, Any]]],
        *,
        verbose: bool = False,
    ) -> ParallelExecutionResult:
        """Execute multiple agent tasks in parallel.

        Uses asyncio.gather for true parallel execution with semaphore
        to limit maximum concurrent agents.

        Args:
            tasks (`list[AgentTask]`):
                List of agent tasks to execute.
            execute_func (`Callable[[AgentTask], Awaitable[dict[str, Any]]]`):
                Async function that executes a single task and returns result.
            verbose (`bool`):
                Whether to print debug information.

        Returns:
            `ParallelExecutionResult`:
                Result containing completed and failed tasks.
        """
        from ._observability import get_logger

        logger = get_logger()

        if not tasks:
            return ParallelExecutionResult(
                success=True,
                completed_tasks=[],
                failed_tasks=[],
                message="No tasks to execute",
            )

        logger.info(f"[MultiAgent] Starting parallel execution of {len(tasks)} tasks")

        # Ensure semaphore is initialized
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_agents)

        async def execute_with_semaphore(task: AgentTask) -> AgentTask:
            """Execute a task with semaphore control."""
            async with self._semaphore:  # type: ignore[union-attr]
                task.status = "running"
                if verbose:
                    logger.debug(f"[MultiAgent] Starting task {task.agent_id}")

                try:
                    result = await execute_func(task)
                    task.result = result
                    task.status = "completed"
                    if verbose:
                        logger.debug(f"[MultiAgent] Completed task {task.agent_id}")
                except Exception as exc:
                    task.result = {"error": str(exc)}
                    task.status = "failed"
                    logger.warn(f"[MultiAgent] Task {task.agent_id} failed: {exc}")

                return task

        # Execute all tasks in parallel
        completed_tasks_raw = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=False,
        )

        # Separate completed and failed tasks
        completed_tasks: list[AgentTask] = []
        failed_tasks: list[AgentTask] = []

        for task in completed_tasks_raw:
            if task.status == "completed":
                completed_tasks.append(task)
            else:
                failed_tasks.append(task)

        success = len(failed_tasks) == 0
        message = (
            f"Completed {len(completed_tasks)}/{len(tasks)} tasks"
            if success
            else f"Failed {len(failed_tasks)}/{len(tasks)} tasks"
        )

        logger.info(f"[MultiAgent] Parallel execution finished: {message}")

        return ParallelExecutionResult(
            success=success,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            message=message,
        )

    async def merge_all_to_delivery(
        self,
        completed_tasks: list[AgentTask],
        *,
        resolve_conflicts: bool = True,
        llm: Any = None,
        verbose: bool = False,
    ) -> "MergeResult":
        """Merge all completed agent work to delivery directory.

        Merges in dependency order (database -> backend -> frontend -> other).
        Optionally uses LLM to resolve conflicts.

        Args:
            completed_tasks (`list[AgentTask]`):
                List of completed tasks to merge.
            resolve_conflicts (`bool`):
                Whether to attempt LLM-powered conflict resolution.
            llm (`Any`):
                LLM instance for smart merge (required if resolve_conflicts=True).
            verbose (`bool`):
                Whether to print debug information.

        Returns:
            `MergeResult`:
                Merge result with success status, conflicts, and message.
        """
        from ._observability import get_logger
        from ._runtime_workspace import MergeResult

        logger = get_logger()

        if not completed_tasks:
            return MergeResult(
                success=True,
                conflicts=[],
                message="No tasks to merge",
            )

        logger.info(f"[MultiAgent] Merging {len(completed_tasks)} tasks to delivery")

        # Sort tasks by dependency order
        sorted_tasks = sort_tasks_by_dependency(completed_tasks)

        all_conflicts: list[str] = []
        merged_count = 0

        for task in sorted_tasks:
            agent_dir = task.working_dir
            if not agent_dir:
                agent_dir = self.agent_dirs.get(task.agent_id, "")

            if not agent_dir:
                logger.warn(f"[MultiAgent] No working dir for {task.agent_id}, skipping")
                continue

            if verbose:
                logger.debug(f"[MultiAgent] Merging {task.agent_id} from {agent_dir}")

            # Detect conflicts before merge
            conflicts = await self._detect_merge_conflicts(agent_dir)

            if conflicts:
                if resolve_conflicts and llm is not None:
                    # Try to resolve conflicts with LLM
                    resolved, unresolved = await self._resolve_conflicts_with_llm(
                        agent_dir, conflicts, llm, verbose
                    )
                    if unresolved:
                        all_conflicts.extend(unresolved)
                        logger.warn(
                            f"[MultiAgent] {len(unresolved)} unresolved conflicts "
                            f"for {task.agent_id}"
                        )
                else:
                    all_conflicts.extend(conflicts)
                    logger.warn(
                        f"[MultiAgent] {len(conflicts)} conflicts for {task.agent_id}"
                    )

            # Perform merge (rsync agent_dir -> delivery)
            # Use --ignore-existing for conflicted files if not resolved
            if all_conflicts:
                # Only merge non-conflicting files
                exclude_args = " ".join(
                    f"--exclude='{Path(c).name}'" for c in all_conflicts
                )
                merge_cmd = (
                    f"rsync -a {exclude_args} {agent_dir}/ {self.delivery_dir}/"
                )
            else:
                merge_cmd = f"rsync -a {agent_dir}/ {self.delivery_dir}/"

            merge_result = await self.base_workspace.exec(merge_cmd)

            if merge_result.get("success"):
                merged_count += 1
            else:
                logger.warn(
                    f"[MultiAgent] Merge failed for {task.agent_id}: "
                    f"{merge_result.get('error')}"
                )

        # Build result message
        if all_conflicts:
            message = (
                f"Merged {merged_count}/{len(sorted_tasks)} tasks with "
                f"{len(all_conflicts)} conflict(s)"
            )
            success = False
        else:
            message = f"Successfully merged {merged_count}/{len(sorted_tasks)} tasks"
            success = merged_count == len(sorted_tasks)

        logger.info(f"[MultiAgent] Merge complete: {message}")

        return MergeResult(
            success=success,
            conflicts=all_conflicts,
            message=message,
        )

    async def _detect_merge_conflicts(self, agent_dir: str) -> list[str]:
        """Detect potential merge conflicts between agent directory and delivery.

        Args:
            agent_dir (`str`):
                Agent working directory path.

        Returns:
            `list[str]`:
                List of file paths with potential conflicts.
        """
        # Find files that exist in both directories and differ
        diff_result = await self.base_workspace.exec(
            f"diff -rq {self.delivery_dir} {agent_dir} 2>/dev/null || true"
        )

        conflicts: list[str] = []
        if diff_result.get("output"):
            for line in diff_result["output"].strip().split("\n"):
                if line.strip():
                    # Parse diff output: "Files X and Y differ"
                    if " differ" in line:
                        # Extract file path relative to delivery
                        parts = line.split(" and ")
                        if len(parts) >= 2:
                            # Get path from delivery side
                            delivery_path = parts[0].replace("Files ", "").strip()
                            if delivery_path.startswith(self.delivery_dir):
                                rel_path = delivery_path[len(self.delivery_dir) + 1:]
                                conflicts.append(rel_path)

        return conflicts

    async def _resolve_conflicts_with_llm(
        self,
        agent_dir: str,
        conflicts: list[str],
        llm: Any,
        verbose: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Attempt to resolve conflicts using LLM.

        Args:
            agent_dir (`str`):
                Agent working directory path.
            conflicts (`list[str]`):
                List of conflicting file paths.
            llm (`Any`):
                LLM instance for smart merge.
            verbose (`bool`):
                Whether to print debug information.

        Returns:
            `tuple[list[str], list[str]]`:
                (resolved_files, unresolved_files)
        """
        from ._observability import get_logger

        logger = get_logger()

        resolved: list[str] = []
        unresolved: list[str] = []

        for conflict_path in conflicts:
            delivery_file = f"{self.delivery_dir}/{conflict_path}"
            agent_file = f"{agent_dir}/{conflict_path}"

            # Read both versions
            delivery_result = await self.base_workspace.exec(f"cat {delivery_file}")
            agent_result = await self.base_workspace.exec(f"cat {agent_file}")

            if not delivery_result.get("success") or not agent_result.get("success"):
                unresolved.append(conflict_path)
                continue

            delivery_content = delivery_result.get("output", "")
            agent_content = agent_result.get("output", "")

            # Try smart merge
            merged_content, success = await smart_merge(
                base_content=delivery_content,
                head_content=agent_content,
                file_path=conflict_path,
                llm=llm,
            )

            if success:
                # Write merged content to delivery
                # Use temp file approach for safety
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", delete=False
                ) as tmp_file:
                    tmp_file.write(merged_content)
                    tmp_path = tmp_file.name

                try:
                    # Copy to container
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "cp", tmp_path,
                        f"{self.base_workspace.container_id}:{delivery_file}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, stderr = await proc.communicate()

                    if proc.returncode == 0:
                        resolved.append(conflict_path)
                        if verbose:
                            logger.debug(f"[MultiAgent] Resolved conflict: {conflict_path}")
                    else:
                        unresolved.append(conflict_path)
                        logger.warn(
                            f"[MultiAgent] Failed to write merged file: {conflict_path}"
                        )
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            else:
                unresolved.append(conflict_path)
                if verbose:
                    logger.debug(f"[MultiAgent] Could not resolve: {conflict_path}")

        return resolved, unresolved


async def smart_merge(
    base_content: str,
    head_content: str,
    file_path: str,
    llm: Any,
) -> tuple[str, bool]:
    """Use LLM to intelligently merge conflicting file versions.

    Args:
        base_content (`str`):
            Base version content (delivery).
        head_content (`str`):
            Head version content (agent working directory).
        file_path (`str`):
            File path for context.
        llm (`Any`):
            LLM instance.

    Returns:
        `tuple[str, bool]`:
            (merged_content, success)
    """
    from ._llm_utils import call_llm_raw

    # Truncate content if too long
    max_chars = 3000
    base_truncated = base_content[:max_chars]
    head_truncated = head_content[:max_chars]

    if len(base_content) > max_chars:
        base_truncated += "\n... (truncated)"
    if len(head_content) > max_chars:
        head_truncated += "\n... (truncated)"

    prompt = f"""You are a code merge assistant. The file `{file_path}` has two versions that need to be merged.

## Main Branch Version (delivery)
```
{base_truncated}
```

## Working Branch Version (agent)
```
{head_truncated}
```

Please merge these two versions, preserving functionality from both sides.
Rules:
1. Keep all unique functionality from both versions
2. Resolve any direct conflicts by preferring the working branch (agent) version
3. Maintain code consistency and formatting
4. Only output the merged code, no explanations

Merged code:"""

    messages = [{"role": "user", "content": prompt}]

    try:
        merged = await call_llm_raw(
            llm,
            messages,
            temperature=0.3,
            retries=2,
            label="smart_merge",
            verbose=False,
        )

        # Clean up response - remove markdown code blocks if present
        merged = merged.strip()
        if merged.startswith("```"):
            lines = merged.split("\n")
            # Remove first line (```lang) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            merged = "\n".join(lines)

        # Basic validation: merged content should not be empty
        if not merged.strip():
            return "", False

        return merged, True

    except Exception as exc:
        from ._observability import get_logger
        get_logger().warn(f"[smart_merge] Failed for {file_path}: {exc}")
        return "", False


def sort_tasks_by_dependency(tasks: list[AgentTask]) -> list[AgentTask]:
    """Sort tasks by requirement dependency order.

    Dependency order:
    - database tasks first (priority 0)
    - backend tasks second (priority 1)
    - frontend tasks third (priority 2)
    - other tasks last (priority 3)

    Args:
        tasks (`list[AgentTask]`):
            List of tasks to sort.

    Returns:
        `list[AgentTask]`:
            Sorted list of tasks.
    """
    priority_map = {
        "database": 0,
        "db": 0,
        "data": 0,
        "backend": 1,
        "api": 1,
        "server": 1,
        "frontend": 2,
        "ui": 2,
        "web": 2,
        "other": 3,
    }

    def get_priority(task: AgentTask) -> int:
        """Get priority for a task based on its requirement category."""
        requirement = task.requirement or {}
        category = requirement.get("category", "other")

        if isinstance(category, str):
            category = category.lower()
            return priority_map.get(category, 3)

        return 3

    return sorted(tasks, key=get_priority)


__all__ = [
    "MultiAgentWorkspace",
    "AgentTask",
    "ParallelExecutionResult",
    "smart_merge",
    "sort_tasks_by_dependency",
]
