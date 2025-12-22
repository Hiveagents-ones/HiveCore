# -*- coding: utf-8 -*-
"""Sandbox orchestrator for dynamic sandbox type selection by AA."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    from .intent import IntentRequest
    from .scaffold import ScaffoldExecutor
    from .task_executor import SandboxTaskExecutor, SandboxTask


class SandboxTypeEnum(str, Enum):
    """Sandbox type enumeration matching agentscope-runtime."""

    BASE = "base"
    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    GUI = "gui"
    MOBILE = "mobile"


@dataclass
class SandboxCapability:
    """Capability description for a sandbox type."""

    sandbox_type: SandboxTypeEnum
    description: str
    keywords: list[str] = field(default_factory=list)
    priority: int = 0  # Higher priority = more preferred when multiple match


# Predefined sandbox capabilities
SANDBOX_CAPABILITIES: dict[SandboxTypeEnum, SandboxCapability] = {
    SandboxTypeEnum.BASE: SandboxCapability(
        sandbox_type=SandboxTypeEnum.BASE,
        description="Basic Python/Shell execution sandbox",
        keywords=[
            "python", "script", "数据分析", "计算", "算法",
            "后端", "api", "服务", "数据库", "backend",
        ],
        priority=1,
    ),
    SandboxTypeEnum.FILESYSTEM: SandboxCapability(
        sandbox_type=SandboxTypeEnum.FILESYSTEM,
        description="File system operations + code execution",
        keywords=[
            "代码", "文件", "生成", "创建", "编写", "开发",
            "前端", "后端", "全栈", "项目", "系统",
            "code", "file", "generate", "create", "develop",
            "frontend", "backend", "fullstack",
        ],
        priority=2,
    ),
    SandboxTypeEnum.BROWSER: SandboxCapability(
        sandbox_type=SandboxTypeEnum.BROWSER,
        description="Browser automation with Playwright",
        keywords=[
            "测试", "浏览器", "网页", "ui", "界面", "页面",
            "前端", "html", "css", "javascript", "react", "vue",
            "test", "browser", "web", "frontend", "website",
        ],
        priority=3,
    ),
    SandboxTypeEnum.GUI: SandboxCapability(
        sandbox_type=SandboxTypeEnum.GUI,
        description="Desktop GUI automation (Computer Use)",
        keywords=[
            "桌面", "应用程序", "软件", "desktop", "application",
            "computer use", "gui", "窗口",
        ],
        priority=4,
    ),
    SandboxTypeEnum.MOBILE: SandboxCapability(
        sandbox_type=SandboxTypeEnum.MOBILE,
        description="Mobile app testing",
        keywords=[
            "移动", "手机", "app", "ios", "android", "mobile",
        ],
        priority=5,
    ),
}


@dataclass
class SandboxDecision:
    """Decision about which sandbox types to use."""

    required_sandboxes: list[SandboxTypeEnum] = field(default_factory=list)
    primary_sandbox: SandboxTypeEnum | None = None
    reasoning: str = ""
    complexity_level: str = "simple"  # simple, medium, complex

    def __post_init__(self) -> None:
        if self.required_sandboxes and self.primary_sandbox is None:
            self.primary_sandbox = self.required_sandboxes[0]


@dataclass
class SandboxPool:
    """Pool of initialized sandboxes."""

    sandboxes: dict[SandboxTypeEnum, Any] = field(default_factory=dict)
    active: bool = False


class SandboxOrchestrator:
    """Orchestrator for dynamic sandbox selection and management.

    This class is responsible for:
    1. Analyzing user requirements to determine needed sandbox types
    2. Managing sandbox lifecycle (creation, pooling, cleanup)
    3. Providing sandboxes to agents based on their needs
    """

    def __init__(
        self,
        *,
        default_timeout: int = 300,
        base_url: str | None = None,
        enable_pooling: bool = True,
        enable_task_queue: bool = True,
        task_poll_interval: float = 2.0,
    ) -> None:
        """Initialize sandbox orchestrator.

        Args:
            default_timeout: Default timeout for sandboxes.
            base_url: Optional remote sandbox server URL.
            enable_pooling: Whether to enable sandbox pooling.
            enable_task_queue: Whether to enable async task queue for long commands.
            task_poll_interval: Polling interval for task status checks.
        """
        self._default_timeout = default_timeout
        self._base_url = base_url
        self._enable_pooling = enable_pooling
        self._enable_task_queue = enable_task_queue
        self._task_poll_interval = task_poll_interval
        self._pool = SandboxPool()
        self._initialized_types: set[SandboxTypeEnum] = set()
        self._scaffold_executor: "ScaffoldExecutor | None" = None
        self._task_executors: dict[SandboxTypeEnum, "SandboxTaskExecutor"] = {}

    def analyze_requirement(
        self,
        intent: "IntentRequest",
    ) -> SandboxDecision:
        """Analyze intent to determine required sandbox types.

        Args:
            intent: User intent request.

        Returns:
            SandboxDecision with recommended sandbox types.
        """
        utterance = intent.utterance.lower()
        matched_sandboxes: list[tuple[SandboxTypeEnum, int, int]] = []

        # Score each sandbox type based on keyword matching
        for sandbox_type, capability in SANDBOX_CAPABILITIES.items():
            score = 0
            for keyword in capability.keywords:
                if keyword.lower() in utterance:
                    score += 1

            if score > 0:
                matched_sandboxes.append(
                    (sandbox_type, score, capability.priority),
                )

        # Sort by score (desc) then priority (desc)
        matched_sandboxes.sort(key=lambda x: (x[1], x[2]), reverse=True)

        # Determine complexity level
        complexity = self._determine_complexity(utterance, matched_sandboxes)

        # Build sandbox list based on complexity
        required = self._build_sandbox_list(matched_sandboxes, complexity)

        if not required:
            # Default to BROWSER for simple web tasks
            required = [SandboxTypeEnum.BROWSER]

        decision = SandboxDecision(
            required_sandboxes=required,
            primary_sandbox=required[0] if required else None,
            reasoning=self._generate_reasoning(required, utterance),
            complexity_level=complexity,
        )

        logger.info(
            "Sandbox decision for '%s': %s (complexity: %s)",
            utterance[:50],
            [s.value for s in required],
            complexity,
        )

        return decision

    def _determine_complexity(
        self,
        utterance: str,
        matches: list[tuple[SandboxTypeEnum, int, int]],
    ) -> str:
        """Determine project complexity level."""
        # Complex indicators
        complex_keywords = [
            "系统", "管理", "平台", "完整", "全栈",
            "system", "management", "platform", "complete", "fullstack",
            "前端", "后端", "数据库", "frontend", "backend", "database",
        ]

        # Medium indicators
        medium_keywords = [
            "应用", "功能", "模块", "app", "feature", "module",
        ]

        complex_count = sum(1 for kw in complex_keywords if kw in utterance)
        medium_count = sum(1 for kw in medium_keywords if kw in utterance)

        # Multiple sandbox types needed = more complex
        unique_types = len(set(m[0] for m in matches))

        if complex_count >= 2 or unique_types >= 3:
            return "complex"
        elif medium_count >= 1 or unique_types >= 2 or complex_count >= 1:
            return "medium"
        return "simple"

    def _build_sandbox_list(
        self,
        matches: list[tuple[SandboxTypeEnum, int, int]],
        complexity: str,
    ) -> list[SandboxTypeEnum]:
        """Build list of required sandboxes based on matches and complexity."""
        if not matches:
            return []

        required: list[SandboxTypeEnum] = []
        seen_types: set[SandboxTypeEnum] = set()

        for sandbox_type, score, _ in matches:
            if sandbox_type not in seen_types:
                required.append(sandbox_type)
                seen_types.add(sandbox_type)

        # For complex projects, ensure we have both dev and test capabilities
        if complexity == "complex":
            if SandboxTypeEnum.FILESYSTEM not in seen_types:
                required.insert(0, SandboxTypeEnum.FILESYSTEM)
            if SandboxTypeEnum.BROWSER not in seen_types:
                required.append(SandboxTypeEnum.BROWSER)

        # For medium projects with frontend work, add browser for testing
        elif complexity == "medium":
            has_frontend = any(
                kw in str(matches)
                for kw in ["前端", "html", "css", "frontend", "web"]
            )
            if has_frontend and SandboxTypeEnum.BROWSER not in seen_types:
                required.append(SandboxTypeEnum.BROWSER)

        return required

    def _generate_reasoning(
        self,
        sandboxes: list[SandboxTypeEnum],
        utterance: str,
    ) -> str:
        """Generate human-readable reasoning for sandbox selection."""
        if not sandboxes:
            return "默认选择浏览器沙箱进行网页测试"

        parts = []
        for sandbox in sandboxes:
            cap = SANDBOX_CAPABILITIES.get(sandbox)
            if cap:
                parts.append(f"{sandbox.value}: {cap.description}")

        return f"根据需求 '{utterance[:30]}...' 选择: " + "; ".join(parts)

    def get_sandbox(
        self,
        sandbox_type: SandboxTypeEnum,
    ) -> Any:
        """Get or create a sandbox of the specified type.

        Args:
            sandbox_type: Type of sandbox to get.

        Returns:
            Initialized sandbox instance.
        """
        # Check pool first
        if self._enable_pooling and sandbox_type in self._pool.sandboxes:
            logger.debug("Returning pooled sandbox: %s", sandbox_type.value)
            return self._pool.sandboxes[sandbox_type]

        # Create new sandbox
        sandbox = self._create_sandbox(sandbox_type)

        if self._enable_pooling:
            self._pool.sandboxes[sandbox_type] = sandbox
            self._pool.active = True

        self._initialized_types.add(sandbox_type)
        return sandbox

    def _create_sandbox(self, sandbox_type: SandboxTypeEnum) -> Any:
        """Create a new sandbox of the specified type."""
        sandbox_class = self._get_sandbox_class(sandbox_type)

        kwargs: dict[str, Any] = {"timeout": self._default_timeout}
        if self._base_url:
            kwargs["base_url"] = self._base_url

        sandbox = sandbox_class(**kwargs)
        sandbox.__enter__()

        logger.info(
            "Created %s sandbox (id=%s)",
            sandbox_type.value,
            sandbox.sandbox_id,
        )
        return sandbox

    def _get_sandbox_class(self, sandbox_type: SandboxTypeEnum) -> type:
        """Get the sandbox class for a type."""
        try:
            if sandbox_type == SandboxTypeEnum.BASE:
                from agentscope_runtime.sandbox import BaseSandbox
                return BaseSandbox
            elif sandbox_type == SandboxTypeEnum.BROWSER:
                from agentscope_runtime.sandbox import BrowserSandbox
                return BrowserSandbox
            elif sandbox_type == SandboxTypeEnum.FILESYSTEM:
                from agentscope_runtime.sandbox import FilesystemSandbox
                return FilesystemSandbox
            elif sandbox_type == SandboxTypeEnum.GUI:
                from agentscope_runtime.sandbox import GuiSandbox
                return GuiSandbox
            else:
                # Fallback to base
                from agentscope_runtime.sandbox import BaseSandbox
                return BaseSandbox
        except ImportError as exc:
            raise ImportError(
                f"agentscope-runtime is required for {sandbox_type.value} sandbox. "
                "Install with: pip install agentscope-runtime"
            ) from exc

    def cleanup(self, sandbox_type: SandboxTypeEnum | None = None) -> None:
        """Cleanup sandboxes and task executors.

        Args:
            sandbox_type: If provided, only cleanup this type.
                         Otherwise cleanup all sandboxes.
        """
        if sandbox_type:
            # Cleanup task executor first
            if sandbox_type in self._task_executors:
                try:
                    self._task_executors[sandbox_type].stop()
                except Exception as exc:
                    logger.warning(
                        "Error stopping task executor for %s: %s",
                        sandbox_type,
                        exc,
                    )
                finally:
                    del self._task_executors[sandbox_type]

            if sandbox_type in self._pool.sandboxes:
                try:
                    self._pool.sandboxes[sandbox_type].__exit__(None, None, None)
                except Exception as exc:
                    logger.warning("Error cleaning up %s: %s", sandbox_type, exc)
                finally:
                    del self._pool.sandboxes[sandbox_type]
                    self._initialized_types.discard(sandbox_type)
        else:
            # Cleanup all task executors
            for stype, executor in list(self._task_executors.items()):
                try:
                    executor.stop()
                except Exception as exc:
                    logger.warning(
                        "Error stopping task executor for %s: %s",
                        stype,
                        exc,
                    )
            self._task_executors.clear()

            # Cleanup all sandboxes
            for stype, sandbox in list(self._pool.sandboxes.items()):
                try:
                    sandbox.__exit__(None, None, None)
                except Exception as exc:
                    logger.warning("Error cleaning up %s: %s", stype, exc)
            self._pool.sandboxes.clear()
            self._initialized_types.clear()
            self._pool.active = False

    def __enter__(self) -> "SandboxOrchestrator":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()

    @property
    def active_sandboxes(self) -> list[SandboxTypeEnum]:
        """Get list of active sandbox types."""
        return list(self._initialized_types)

    def get_sandbox_info(self) -> dict[str, Any]:
        """Get information about all active sandboxes."""
        info = {
            "active_types": [s.value for s in self._initialized_types],
            "pooling_enabled": self._enable_pooling,
            "sandboxes": {},
        }
        for stype, sandbox in self._pool.sandboxes.items():
            info["sandboxes"][stype.value] = {
                "sandbox_id": sandbox.sandbox_id,
                "type": stype.value,
            }
        return info

    # =========================================================================
    # Scaffold Execution Integration
    # =========================================================================

    def get_scaffold_executor(
        self,
        *,
        allow_high_risk: bool = False,
    ) -> "ScaffoldExecutor":
        """Get or create the scaffold executor.

        Args:
            allow_high_risk: Whether to allow high-risk commands.

        Returns:
            ScaffoldExecutor instance for executing shell commands.
        """
        if self._scaffold_executor is None:
            from .scaffold import ScaffoldExecutor

            self._scaffold_executor = ScaffoldExecutor(
                sandbox_orchestrator=self,
                default_working_dir="/workspace",
                allow_high_risk=allow_high_risk,
            )
            logger.info("Created scaffold executor")

        return self._scaffold_executor

    def execute_command(
        self,
        command: str,
        *,
        working_dir: str | None = None,
        env_vars: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> Any:
        """Execute a shell command in sandbox.

        This is the main method for executing LLM-generated commands.
        Commands are validated for security before execution.

        Args:
            command: Shell command to execute (decided by LLM).
            working_dir: Override working directory.
            env_vars: Environment variables to set.
            timeout: Timeout in seconds.

        Returns:
            ScaffoldResult from the execution.

        Example:
            >>> result = orchestrator.execute_command("npm create vite@latest my-app -- --template react-ts")
            >>> if result.success:
            ...     print(result.output)
        """
        executor = self.get_scaffold_executor()
        return executor.execute(
            command,
            working_dir=working_dir,
            env_vars=env_vars,
            timeout=timeout,
        )

    def execute_commands(
        self,
        commands: list[str],
        *,
        working_dir: str | None = None,
        env_vars: dict[str, str] | None = None,
        timeout: int = 300,
        stop_on_error: bool = True,
    ) -> list[Any]:
        """Execute multiple shell commands in sandbox.

        Args:
            commands: List of shell commands to execute.
            working_dir: Working directory.
            env_vars: Environment variables.
            timeout: Timeout per command.
            stop_on_error: Stop on first error.

        Returns:
            List of ScaffoldResult for each command.

        Example:
            >>> results = orchestrator.execute_commands([
            ...     "npm create vite@latest frontend -- --template vue-ts",
            ...     "cd frontend && npm install",
            ...     "cd frontend && npm run build",
            ... ])
        """
        executor = self.get_scaffold_executor()
        return executor.execute_many(
            commands,
            working_dir=working_dir,
            env_vars=env_vars,
            timeout=timeout,
            stop_on_error=stop_on_error,
        )

    def detect_project(
        self,
        working_dir: str | None = None,
    ) -> dict[str, Any]:
        """Detect project type from files in working directory.

        Provides context for LLM to understand the project.

        Args:
            working_dir: Directory to analyze.

        Returns:
            Dict with detected languages, frameworks, package managers.
        """
        executor = self.get_scaffold_executor()
        return executor.detect_project(working_dir)

    def get_project_context(
        self,
        working_dir: str | None = None,
    ) -> str:
        """Get project context formatted for LLM.

        This provides context to help LLM decide what commands to run.

        Args:
            working_dir: Directory to analyze.

        Returns:
            Formatted string with project context.
        """
        executor = self.get_scaffold_executor()
        return executor.get_context_for_llm(working_dir)

    # =========================================================================
    # Task Queue Integration for Long-Running Commands
    # =========================================================================

    def get_task_executor(
        self,
        sandbox_type: SandboxTypeEnum | None = None,
    ) -> "SandboxTaskExecutor":
        """Get or create task executor for a sandbox type.

        The task executor provides async task queue for long-running commands,
        preventing health check timeouts in the sandbox container.

        Args:
            sandbox_type: Sandbox type to get executor for.
                         Defaults to FILESYSTEM.

        Returns:
            SandboxTaskExecutor instance.
        """
        if not self._enable_task_queue:
            raise RuntimeError(
                "Task queue is disabled. "
                "Initialize with enable_task_queue=True to use this feature."
            )

        from .task_executor import SandboxTaskExecutor

        if sandbox_type is None:
            sandbox_type = SandboxTypeEnum.FILESYSTEM

        if sandbox_type not in self._task_executors:
            sandbox = self.get_sandbox(sandbox_type)
            executor = SandboxTaskExecutor(
                sandbox,
                poll_interval=self._task_poll_interval,
            )
            executor.start()
            self._task_executors[sandbox_type] = executor
            logger.info(
                "Created task executor for sandbox type: %s",
                sandbox_type.value,
            )

        return self._task_executors[sandbox_type]

    def submit_task(
        self,
        command: str,
        *,
        timeout: int = 300,
        depends_on: list[str] | None = None,
        working_dir: str = "/workspace",
        env_vars: dict[str, str] | None = None,
        sandbox_type: SandboxTypeEnum | None = None,
    ) -> str:
        """Submit a command as an async task.

        Use this for long-running commands (pip install, npm install, etc.)
        to avoid blocking the sandbox health check.

        Args:
            command: Shell command to execute.
            timeout: Maximum execution time in seconds.
            depends_on: List of task IDs this task depends on.
            working_dir: Working directory.
            env_vars: Environment variables.
            sandbox_type: Sandbox type to use.

        Returns:
            Task ID for tracking.

        Example:
            >>> task_id = orchestrator.submit_task("npm install", timeout=300)
            >>> task = orchestrator.wait_task(task_id)
            >>> print(task.status, task.output)
        """
        executor = self.get_task_executor(sandbox_type)
        return executor.submit(
            command,
            timeout=timeout,
            depends_on=depends_on,
            working_dir=working_dir,
            env_vars=env_vars,
        )

    def submit_task_chain(
        self,
        commands: list[str | dict[str, Any]],
        *,
        working_dir: str = "/workspace",
        stop_on_error: bool = True,
        sandbox_type: SandboxTypeEnum | None = None,
    ) -> list[str]:
        """Submit a chain of dependent commands as tasks.

        Each command will wait for the previous one to complete successfully
        before starting.

        Args:
            commands: List of commands or command configs.
            working_dir: Working directory for all commands.
            stop_on_error: Whether to stop chain on error.
            sandbox_type: Sandbox type to use.

        Returns:
            List of task IDs.

        Example:
            >>> task_ids = orchestrator.submit_task_chain([
            ...     "npm install",
            ...     {"command": "npm run build", "timeout": 120},
            ...     "npm run test",
            ... ])
            >>> results = orchestrator.wait_tasks(task_ids)
        """
        executor = self.get_task_executor(sandbox_type)
        return executor.submit_chain(
            commands,
            working_dir=working_dir,
            stop_on_error=stop_on_error,
        )

    def get_task(
        self,
        task_id: str,
        sandbox_type: SandboxTypeEnum | None = None,
    ) -> "SandboxTask | None":
        """Get task by ID.

        Args:
            task_id: Task identifier.
            sandbox_type: Sandbox type where task was submitted.

        Returns:
            SandboxTask or None if not found.
        """
        executor = self.get_task_executor(sandbox_type)
        return executor.get_task(task_id)

    def wait_task(
        self,
        task_id: str,
        *,
        timeout: float | None = None,
        sandbox_type: SandboxTypeEnum | None = None,
    ) -> "SandboxTask":
        """Wait for a task to complete.

        Args:
            task_id: Task identifier.
            timeout: Maximum wait time (None for indefinite).
            sandbox_type: Sandbox type where task was submitted.

        Returns:
            Completed SandboxTask.

        Raises:
            TimeoutError: If wait times out.
            KeyError: If task not found.
        """
        executor = self.get_task_executor(sandbox_type)
        return executor.wait(task_id, timeout=timeout)

    def wait_tasks(
        self,
        task_ids: list[str],
        *,
        timeout: float | None = None,
        sandbox_type: SandboxTypeEnum | None = None,
    ) -> list["SandboxTask"]:
        """Wait for multiple tasks to complete.

        Args:
            task_ids: List of task identifiers.
            timeout: Maximum total wait time.
            sandbox_type: Sandbox type where tasks were submitted.

        Returns:
            List of completed SandboxTasks.
        """
        executor = self.get_task_executor(sandbox_type)
        return executor.wait_all(task_ids, timeout=timeout)

    def execute_long_command(
        self,
        command: str,
        *,
        timeout: int = 300,
        working_dir: str = "/workspace",
        env_vars: dict[str, str] | None = None,
        sandbox_type: SandboxTypeEnum | None = None,
    ) -> "SandboxTask":
        """Execute a long-running command and wait for result.

        This is a convenience method that submits a task and waits for it.
        Use this for commands that may take a long time (pip install, etc.)

        Args:
            command: Shell command to execute.
            timeout: Maximum execution time in seconds.
            working_dir: Working directory.
            env_vars: Environment variables.
            sandbox_type: Sandbox type to use.

        Returns:
            Completed SandboxTask with output.

        Example:
            >>> result = orchestrator.execute_long_command(
            ...     "pip install -r requirements.txt",
            ...     timeout=300,
            ... )
            >>> if result.status == TaskStatus.SUCCESS:
            ...     print("Installation successful!")
        """
        task_id = self.submit_task(
            command,
            timeout=timeout,
            working_dir=working_dir,
            env_vars=env_vars,
            sandbox_type=sandbox_type,
        )
        return self.wait_task(task_id, timeout=timeout + 30, sandbox_type=sandbox_type)

    def execute_long_commands(
        self,
        commands: list[str | dict[str, Any]],
        *,
        working_dir: str = "/workspace",
        stop_on_error: bool = True,
        sandbox_type: SandboxTypeEnum | None = None,
        total_timeout: float | None = None,
    ) -> list["SandboxTask"]:
        """Execute multiple long-running commands sequentially.

        Commands are executed as a task chain, each waiting for the previous
        one to complete.

        Args:
            commands: List of commands or command configs.
            working_dir: Working directory.
            stop_on_error: Whether to stop on first error.
            sandbox_type: Sandbox type to use.
            total_timeout: Maximum total time for all commands.

        Returns:
            List of SandboxTasks with results.

        Example:
            >>> results = orchestrator.execute_long_commands([
            ...     "npm install",
            ...     "npm run build",
            ...     "npm run test",
            ... ])
            >>> for r in results:
            ...     print(f"{r.command}: {r.status.value}")
        """
        task_ids = self.submit_task_chain(
            commands,
            working_dir=working_dir,
            stop_on_error=stop_on_error,
            sandbox_type=sandbox_type,
        )
        return self.wait_tasks(
            task_ids,
            timeout=total_timeout,
            sandbox_type=sandbox_type,
        )
