# -*- coding: utf-8 -*-
"""Task executor for long-running sandbox commands.

This module provides asynchronous task execution for sandbox commands,
solving the issue where long-running commands (pip install, npm install, etc.)
block the uvicorn worker and cause health check failures.

Key features:
1. Background execution of long-running commands
2. Task state management with proper lifecycle
3. Dependency handling between tasks
4. Timeout control and automatic cleanup
5. Multi-tenant safe with per-sandbox task queues
"""
from __future__ import annotations

import shlex
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from threading import Thread, Lock, Event
from typing import Any, Callable, TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    pass


class TaskStatus(str, Enum):
    """Status of a sandbox task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Priority levels for tasks."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class SandboxTask:
    """A task to be executed in sandbox.

    Attributes:
        id: Unique task identifier.
        command: Shell command to execute.
        timeout: Maximum execution time in seconds.
        status: Current task status.
        output: Command stdout output.
        error: Error message if failed.
        exit_code: Command exit code.
        depends_on: List of task IDs this task depends on.
        priority: Task priority level.
        created_at: Task creation timestamp.
        started_at: Task start timestamp.
        completed_at: Task completion timestamp.
        working_dir: Working directory for command.
        env_vars: Environment variables for command.
        callback: Optional callback when task completes.
        metadata: Additional task metadata.
    """

    id: str
    command: str
    timeout: int = 300
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    error: str | None = None
    exit_code: int | None = None
    depends_on: list[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    working_dir: str = "/workspace"
    env_vars: dict[str, str] = field(default_factory=dict)
    callback: Callable[["SandboxTask"], None] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        """Get task duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or time.time()
        return end_time - self.started_at

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
            TaskStatus.CANCELLED,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "command": self.command,
            "timeout": self.timeout,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "depends_on": self.depends_on,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "working_dir": self.working_dir,
            "duration": self.duration,
            "metadata": self.metadata,
        }


# Threshold for determining if a command is "long-running"
LONG_COMMAND_PATTERNS: list[str] = [
    "pip install",
    "pip3 install",
    "npm install",
    "npm ci",
    "yarn install",
    "yarn add",
    "pnpm install",
    "pnpm add",
    "cargo build",
    "cargo install",
    "go build",
    "go install",
    "mvn install",
    "gradle build",
    "npm run build",
    "yarn build",
    "pnpm build",
    "npm run dev",
    "npm run start",
    "npm test",
    "pytest",
    "python -m pytest",
    "make",
    "cmake",
    "docker build",
    "docker-compose up",
    "uvicorn",
    "gunicorn",
    "flask run",
    "python manage.py runserver",
    "npm run serve",
]


def is_long_running_command(command: str) -> bool:
    """Check if a command is likely to be long-running.

    Args:
        command: Shell command to check.

    Returns:
        True if command matches long-running patterns.
    """
    command_lower = command.lower()
    return any(pattern in command_lower for pattern in LONG_COMMAND_PATTERNS)


class SandboxTaskExecutor:
    """Executor for sandbox tasks with background execution support.

    This class manages task execution in a sandbox, providing:
    1. Sequential task execution with dependency handling
    2. Background execution for long-running commands
    3. Health check friendly (doesn't block uvicorn worker)
    4. Proper timeout and cleanup handling

    Example:
        >>> executor = SandboxTaskExecutor(sandbox)
        >>> task1 = executor.submit("npm install", timeout=300)
        >>> task2 = executor.submit("npm run build", depends_on=[task1])
        >>> result = executor.wait(task2)
        >>> print(result.status, result.output)
    """

    def __init__(
        self,
        sandbox: Any,
        *,
        max_concurrent: int = 1,
        poll_interval: float = 2.0,
        cleanup_completed: bool = True,
        cleanup_after_seconds: int = 3600,
    ) -> None:
        """Initialize task executor.

        Args:
            sandbox: Sandbox instance for command execution.
            max_concurrent: Maximum concurrent tasks (default 1 for safety).
            poll_interval: Interval for polling task status.
            cleanup_completed: Whether to auto-cleanup completed tasks.
            cleanup_after_seconds: Time after which to cleanup completed tasks.
        """
        self._sandbox = sandbox
        self._max_concurrent = max_concurrent
        self._poll_interval = poll_interval
        self._cleanup_completed = cleanup_completed
        self._cleanup_after_seconds = cleanup_after_seconds

        self._tasks: dict[str, SandboxTask] = {}
        self._queue: Queue[str] = Queue()
        self._lock = Lock()
        self._stop_event = Event()
        self._running = False

        # Start executor thread
        self._executor_thread: Thread | None = None

    def start(self) -> None:
        """Start the executor thread."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._executor_thread = Thread(
            target=self._execute_loop,
            daemon=True,
            name=f"SandboxTaskExecutor-{id(self)}",
        )
        self._executor_thread.start()
        logger.info("SandboxTaskExecutor started")

    def stop(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Stop the executor thread.

        Args:
            wait: Whether to wait for thread to finish.
            timeout: Maximum time to wait.
        """
        self._running = False
        self._stop_event.set()

        if wait and self._executor_thread and self._executor_thread.is_alive():
            self._executor_thread.join(timeout=timeout)
            if self._executor_thread.is_alive():
                logger.warning("Executor thread did not stop within timeout")

        logger.info("SandboxTaskExecutor stopped")

    def __enter__(self) -> "SandboxTaskExecutor":
        """Enter context manager."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.stop()

    def submit(
        self,
        command: str,
        *,
        timeout: int = 300,
        depends_on: list[str] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        working_dir: str = "/workspace",
        env_vars: dict[str, str] | None = None,
        callback: Callable[[SandboxTask], None] | None = None,
        metadata: dict[str, Any] | None = None,
        auto_start: bool = True,
    ) -> str:
        """Submit a task for execution.

        Args:
            command: Shell command to execute.
            timeout: Maximum execution time in seconds.
            depends_on: List of task IDs this task depends on.
            priority: Task priority level.
            working_dir: Working directory.
            env_vars: Environment variables.
            callback: Callback when task completes.
            metadata: Additional metadata.
            auto_start: Auto-start executor if not running.

        Returns:
            Task ID for tracking.
        """
        task_id = str(uuid.uuid4())[:8]

        task = SandboxTask(
            id=task_id,
            command=command,
            timeout=timeout,
            depends_on=depends_on or [],
            priority=priority,
            working_dir=working_dir,
            env_vars=env_vars or {},
            callback=callback,
            metadata=metadata or {},
        )

        with self._lock:
            self._tasks[task_id] = task

        self._queue.put(task_id)

        logger.debug(
            "Task submitted: %s - %s",
            task_id,
            command[:50] + ("..." if len(command) > 50 else ""),
        )

        # Auto-start if needed
        if auto_start and not self._running:
            self.start()

        return task_id

    def submit_chain(
        self,
        commands: list[str | dict[str, Any]],
        *,
        working_dir: str = "/workspace",
        stop_on_error: bool = True,
    ) -> list[str]:
        """Submit a chain of dependent commands.

        Args:
            commands: List of commands or command configs.
            working_dir: Working directory for all commands.
            stop_on_error: Whether to stop chain on error.

        Returns:
            List of task IDs.

        Example:
            >>> task_ids = executor.submit_chain([
            ...     "npm install",
            ...     {"command": "npm run build", "timeout": 120},
            ...     "npm run test",
            ... ])
        """
        task_ids: list[str] = []
        prev_task_id: str | None = None

        for cmd in commands:
            if isinstance(cmd, str):
                cmd_config = {"command": cmd}
            else:
                cmd_config = cmd

            command = cmd_config.pop("command")
            timeout = cmd_config.pop("timeout", 300)

            # Chain dependency
            depends_on = []
            if prev_task_id and stop_on_error:
                depends_on = [prev_task_id]

            task_id = self.submit(
                command,
                timeout=timeout,
                depends_on=depends_on,
                working_dir=working_dir,
                **cmd_config,
            )

            task_ids.append(task_id)
            prev_task_id = task_id

        return task_ids

    def get_task(self, task_id: str) -> SandboxTask | None:
        """Get task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            SandboxTask or None if not found.
        """
        return self._tasks.get(task_id)

    def get_status(self, task_id: str) -> TaskStatus | None:
        """Get task status.

        Args:
            task_id: Task identifier.

        Returns:
            TaskStatus or None if not found.
        """
        task = self._tasks.get(task_id)
        return task.status if task else None

    def wait(
        self,
        task_id: str,
        *,
        timeout: float | None = None,
        poll_interval: float = 1.0,
    ) -> SandboxTask:
        """Wait for a task to complete.

        Args:
            task_id: Task identifier.
            timeout: Maximum wait time (None for indefinite).
            poll_interval: Polling interval in seconds.

        Returns:
            Completed SandboxTask.

        Raises:
            TimeoutError: If wait times out.
            KeyError: If task not found.
        """
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task not found: {task_id}")

        start_time = time.time()

        while not task.is_terminal:
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Wait timeout for task {task_id}")
            time.sleep(poll_interval)
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task disappeared: {task_id}")

        return task

    def wait_all(
        self,
        task_ids: list[str],
        *,
        timeout: float | None = None,
        poll_interval: float = 1.0,
    ) -> list[SandboxTask]:
        """Wait for multiple tasks to complete.

        Args:
            task_ids: List of task identifiers.
            timeout: Maximum total wait time.
            poll_interval: Polling interval.

        Returns:
            List of completed SandboxTasks.
        """
        results: list[SandboxTask] = []
        start_time = time.time()

        for task_id in task_ids:
            remaining_timeout = None
            if timeout:
                elapsed = time.time() - start_time
                remaining_timeout = max(0, timeout - elapsed)

            task = self.wait(
                task_id,
                timeout=remaining_timeout,
                poll_interval=poll_interval,
            )
            results.append(task)

        return results

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task.

        Args:
            task_id: Task identifier.

        Returns:
            True if cancelled, False if not found or already running.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            if task.status != TaskStatus.PENDING:
                logger.warning(
                    "Cannot cancel task %s in status %s",
                    task_id,
                    task.status.value,
                )
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            task.error = "Cancelled by user"

        logger.info("Task cancelled: %s", task_id)
        return True

    def list_tasks(
        self,
        status: TaskStatus | None = None,
    ) -> list[SandboxTask]:
        """List tasks, optionally filtered by status.

        Args:
            status: Filter by status.

        Returns:
            List of matching tasks.
        """
        with self._lock:
            tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def _execute_loop(self) -> None:
        """Main execution loop running in background thread."""
        logger.debug("Executor loop started")

        while self._running and not self._stop_event.is_set():
            try:
                # Get next task from queue
                try:
                    task_id = self._queue.get(timeout=1.0)
                except Empty:
                    # Cleanup old completed tasks
                    if self._cleanup_completed:
                        self._cleanup_old_tasks()
                    continue

                task = self._tasks.get(task_id)
                if task is None or task.status == TaskStatus.CANCELLED:
                    continue

                # Check dependencies
                if not self._check_dependencies(task):
                    continue

                # Execute the task
                self._execute_task(task)

            except Exception as exc:
                logger.error("Error in executor loop: %s", exc)

        logger.debug("Executor loop stopped")

    def _check_dependencies(self, task: SandboxTask) -> bool:
        """Check if task dependencies are satisfied.

        Args:
            task: Task to check.

        Returns:
            True if dependencies satisfied, False otherwise.
        """
        for dep_id in task.depends_on:
            dep_task = self._tasks.get(dep_id)

            if dep_task is None:
                # Dependency not found, fail the task
                task.status = TaskStatus.FAILED
                task.error = f"Dependency not found: {dep_id}"
                task.completed_at = time.time()
                logger.error("Task %s failed: dependency %s not found", task.id, dep_id)
                return False

            if dep_task.status == TaskStatus.SUCCESS:
                continue

            if dep_task.is_terminal:
                # Dependency failed/cancelled, fail this task too
                task.status = TaskStatus.FAILED
                task.error = f"Dependency {dep_id} failed with status: {dep_task.status.value}"
                task.completed_at = time.time()
                logger.error(
                    "Task %s failed: dependency %s in status %s",
                    task.id,
                    dep_id,
                    dep_task.status.value,
                )
                return False

            # Dependency not yet complete, re-queue this task
            self._queue.put(task.id)
            time.sleep(0.5)  # Small delay to avoid busy-waiting
            return False

        return True

    def _execute_task(self, task: SandboxTask) -> None:
        """Execute a single task.

        Uses background execution for long-running commands to avoid
        blocking the uvicorn worker.

        Args:
            task: Task to execute.
        """
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        logger.info(
            "Executing task %s: %s",
            task.id,
            task.command[:50] + ("..." if len(task.command) > 50 else ""),
        )

        # Build full command with working directory and env vars
        env_prefix = ""
        if task.env_vars:
            env_parts = [f"{k}={shlex.quote(v)}" for k, v in task.env_vars.items()]
            env_prefix = " ".join(env_parts) + " "

        full_cmd = f"cd {shlex.quote(task.working_dir)} && {env_prefix}{task.command}"

        # Determine if this is a long-running command
        if is_long_running_command(task.command):
            self._execute_background(task, full_cmd)
        else:
            self._execute_direct(task, full_cmd)

        # Invoke callback if set
        if task.callback:
            try:
                task.callback(task)
            except Exception as exc:
                logger.warning("Task callback error: %s", exc)

    def _execute_direct(self, task: SandboxTask, full_cmd: str) -> None:
        """Execute command directly (for short commands).

        Args:
            task: Task being executed.
            full_cmd: Full command with cd and env.
        """
        try:
            result = self._sandbox.run_shell_command(
                command=full_cmd,
                timeout=task.timeout,
            )

            self._parse_result(task, result)

        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = time.time()
            logger.error("Task %s failed with exception: %s", task.id, exc)

    def _execute_background(self, task: SandboxTask, full_cmd: str) -> None:
        """Execute command in background (for long-running commands).

        This method:
        1. Starts the command in background with nohup
        2. Polls for completion without blocking
        3. Handles timeout properly

        Args:
            task: Task being executed.
            full_cmd: Full command with cd and env.
        """
        log_file = f"/tmp/task_{task.id}.log"
        pid_file = f"/tmp/task_{task.id}.pid"
        exit_file = f"/tmp/task_{task.id}.exit"

        try:
            # 1. Start command in background
            # Use a wrapper script to capture exit code
            bg_cmd = (
                f"nohup sh -c '{full_cmd}; echo $? > {exit_file}' "
                f"> {log_file} 2>&1 & echo $! > {pid_file}"
            )

            start_result = self._sandbox.run_shell_command(
                command=bg_cmd,
                timeout=30,  # Starting should be quick
            )

            # 2. Get PID
            pid_result = self._sandbox.run_shell_command(
                command=f"cat {pid_file} 2>/dev/null",
                timeout=10,
            )
            pid = self._extract_output(pid_result).strip()

            if not pid:
                task.status = TaskStatus.FAILED
                task.error = "Failed to get process ID"
                task.completed_at = time.time()
                return

            logger.debug("Task %s started with PID %s", task.id, pid)

            # 3. Poll for completion
            start_time = time.time()
            while time.time() - start_time < task.timeout:
                if self._stop_event.is_set():
                    # Executor stopping, kill the process
                    self._sandbox.run_shell_command(
                        command=f"kill -9 {pid} 2>/dev/null || true",
                        timeout=10,
                    )
                    task.status = TaskStatus.CANCELLED
                    task.error = "Executor stopped"
                    task.completed_at = time.time()
                    return

                # Check if process is still running
                status_result = self._sandbox.run_shell_command(
                    command=f"ps -p {pid} > /dev/null 2>&1 && echo running || echo done",
                    timeout=10,
                )
                status_text = self._extract_output(status_result).strip()

                if "done" in status_text:
                    break

                time.sleep(self._poll_interval)
            else:
                # Timeout - kill the process
                self._sandbox.run_shell_command(
                    command=f"kill -9 {pid} 2>/dev/null || true",
                    timeout=10,
                )
                task.status = TaskStatus.TIMEOUT
                task.error = f"Command timed out after {task.timeout}s"
                task.completed_at = time.time()

                # Get partial output
                try:
                    output_result = self._sandbox.run_shell_command(
                        command=f"cat {log_file} 2>/dev/null | tail -1000",
                        timeout=30,
                    )
                    task.output = self._extract_output(output_result)
                except Exception:
                    pass

                logger.warning("Task %s timed out", task.id)
                self._cleanup_task_files(task.id)
                return

            # 4. Get exit code
            exit_result = self._sandbox.run_shell_command(
                command=f"cat {exit_file} 2>/dev/null || echo 1",
                timeout=10,
            )
            exit_code_str = self._extract_output(exit_result).strip()
            try:
                task.exit_code = int(exit_code_str)
            except ValueError:
                task.exit_code = 1

            # 5. Get output
            output_result = self._sandbox.run_shell_command(
                command=f"cat {log_file} 2>/dev/null",
                timeout=60,
            )
            task.output = self._extract_output(output_result)

            # 6. Set final status
            if task.exit_code == 0:
                task.status = TaskStatus.SUCCESS
            else:
                task.status = TaskStatus.FAILED
                task.error = f"Command exited with code {task.exit_code}"

            task.completed_at = time.time()
            logger.info(
                "Task %s completed with status %s (exit=%s, %.2fs)",
                task.id,
                task.status.value,
                task.exit_code,
                task.duration,
            )

        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = time.time()
            logger.error("Task %s failed with exception: %s", task.id, exc)

        finally:
            # Cleanup temp files
            self._cleanup_task_files(task.id)

    def _parse_result(self, task: SandboxTask, result: Any) -> None:
        """Parse sandbox result and update task.

        Args:
            task: Task to update.
            result: Result from sandbox.run_shell_command.
        """
        task.completed_at = time.time()

        if isinstance(result, dict):
            # Handle dict result format
            task.output = result.get("stdout", "") or result.get("output", "")
            task.exit_code = result.get("exit_code", 0) or result.get("returncode", 0)

            stderr = result.get("stderr", "")
            if stderr:
                task.output = (
                    task.output + "\n[stderr]\n" + stderr
                    if task.output
                    else stderr
                )

            # Check for isError flag
            if result.get("isError"):
                task.exit_code = task.exit_code or 1

            # Extract content from MCP-style response
            content = result.get("content", [])
            if content and isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        desc = item.get("description", "")
                        if desc == "returncode":
                            try:
                                task.exit_code = int(text)
                            except ValueError:
                                pass
                        else:
                            parts.append(text)
                if parts:
                    task.output = "\n".join(parts)

        elif isinstance(result, str):
            task.output = result
            task.exit_code = 0
        else:
            task.output = str(result)
            task.exit_code = 0

        # Determine success/failure
        if task.exit_code == 0:
            task.status = TaskStatus.SUCCESS
        else:
            task.status = TaskStatus.FAILED
            task.error = f"Command exited with code {task.exit_code}"

        logger.debug(
            "Task %s completed: status=%s, exit_code=%s",
            task.id,
            task.status.value,
            task.exit_code,
        )

    def _extract_output(self, result: Any) -> str:
        """Extract output string from sandbox result.

        Args:
            result: Result from sandbox.

        Returns:
            Output string.
        """
        if isinstance(result, dict):
            # Check for content array (MCP-style)
            content = result.get("content", [])
            if content and isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        desc = item.get("description", "")
                        if desc not in ("returncode", "stderr"):
                            parts.append(item.get("text", ""))
                if parts:
                    return "\n".join(parts)

            return result.get("stdout", "") or result.get("output", "") or ""

        return str(result) if result else ""

    def _cleanup_task_files(self, task_id: str) -> None:
        """Cleanup temporary files for a task.

        Args:
            task_id: Task identifier.
        """
        try:
            self._sandbox.run_shell_command(
                command=(
                    f"rm -f /tmp/task_{task_id}.log "
                    f"/tmp/task_{task_id}.pid "
                    f"/tmp/task_{task_id}.exit 2>/dev/null || true"
                ),
                timeout=10,
            )
        except Exception as exc:
            logger.debug("Error cleaning up task files: %s", exc)

    def _cleanup_old_tasks(self) -> None:
        """Cleanup old completed tasks from memory."""
        current_time = time.time()
        to_remove: list[str] = []

        with self._lock:
            for task_id, task in self._tasks.items():
                if task.is_terminal and task.completed_at:
                    age = current_time - task.completed_at
                    if age > self._cleanup_after_seconds:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self._tasks[task_id]

        if to_remove:
            logger.debug("Cleaned up %d old tasks", len(to_remove))


class MultiTenantTaskManager:
    """Manager for per-tenant task executors.

    This class provides isolated task execution for multi-tenant scenarios,
    where each tenant/sandbox gets its own task queue.
    """

    def __init__(
        self,
        *,
        max_concurrent_per_tenant: int = 1,
        poll_interval: float = 2.0,
    ) -> None:
        """Initialize multi-tenant task manager.

        Args:
            max_concurrent_per_tenant: Max concurrent tasks per tenant.
            poll_interval: Polling interval for task status.
        """
        self._max_concurrent = max_concurrent_per_tenant
        self._poll_interval = poll_interval
        self._executors: dict[str, SandboxTaskExecutor] = {}
        self._lock = Lock()

    def get_executor(
        self,
        tenant_id: str,
        sandbox: Any,
    ) -> SandboxTaskExecutor:
        """Get or create executor for a tenant.

        Args:
            tenant_id: Tenant identifier.
            sandbox: Sandbox instance for the tenant.

        Returns:
            SandboxTaskExecutor for the tenant.
        """
        with self._lock:
            if tenant_id not in self._executors:
                executor = SandboxTaskExecutor(
                    sandbox,
                    max_concurrent=self._max_concurrent,
                    poll_interval=self._poll_interval,
                )
                executor.start()
                self._executors[tenant_id] = executor
                logger.info("Created task executor for tenant: %s", tenant_id)

            return self._executors[tenant_id]

    def remove_executor(self, tenant_id: str) -> None:
        """Remove and stop executor for a tenant.

        Args:
            tenant_id: Tenant identifier.
        """
        with self._lock:
            if tenant_id in self._executors:
                executor = self._executors.pop(tenant_id)
                executor.stop()
                logger.info("Removed task executor for tenant: %s", tenant_id)

    def cleanup(self) -> None:
        """Stop all executors."""
        with self._lock:
            for tenant_id, executor in list(self._executors.items()):
                executor.stop()
            self._executors.clear()

        logger.info("All task executors stopped")

    def __enter__(self) -> "MultiTenantTaskManager":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.cleanup()
