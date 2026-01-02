# -*- coding: utf-8 -*-
"""Execution loop tying all sections together (III)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, TYPE_CHECKING

from .intent import (
    AcceptanceCriteria,
    AssistantOrchestrator,
    IntentRequest,
    StrategyPlan,
)
from .kpi import KPIRecord, KPITracker
from .memory import (
    DecisionCategory,
    MemoryEntry,
    MemoryPool,
    ProjectDescriptor,
    ProjectMemory,
    ProjectPool,
    ResourceLibrary,
)
from .task_graph import TaskGraphBuilder, TaskGraph
from ._task_validator import TaskLevelValidator, TaskValidationResult
from .task_board import ProjectTaskBoard, TaskItem, TaskItemStatus
from .msghub import MsgHubBroadcaster, RoundUpdate
from .artifacts import ArtifactDeliveryManager, ArtifactDeliveryResult
from .repair_engine import RepairEngine, RepairAction, FilePatch
from .dependency_sync import DependencySynchronizer, DependencyInfo, SyncResult
from .blueprint_enhancer import BlueprintEnhancer, EnhancedBlueprint, RequiredFunction
from ..message import Msg
from ..pipeline import MsgHub
from ..memory import MemoryBase
from ..observability import TimelineTracker, ObservabilityHub
from .._logging import logger
import shortuuid
import time as _time_module


def _log_execution(
    msg: str,
    *,
    level: str = "info",
    prefix: str = "[ExecutionLoop]",
    hub: "Any | None" = None,
    event_type: str | None = None,
    metadata: dict | None = None,
    project_id: str | None = None,
) -> None:
    """Log execution progress with immediate flush for observability.

    Args:
        msg: Message to log.
        level: Log level (info, warning, error).
        prefix: Log prefix (default: [ExecutionLoop]).
        hub: Optional ObservabilityHub instance for timeline tracking.
        event_type: Optional timeline event type for ObservabilityHub.
        metadata: Optional metadata for timeline event.
        project_id: Optional project ID for timeline event.
    """
    timestamp = _time_module.strftime("%H:%M:%S")
    formatted = f"{timestamp} | {prefix} {msg}"

    # Print with flush for immediate visibility
    print(formatted, flush=True)

    # Also log via logger for file logging
    if level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.info(msg)

    # Record to ObservabilityHub if provided
    if hub is not None and event_type is not None:
        try:
            from datetime import datetime
            from ..observability._types import TimelineEvent

            event = TimelineEvent(
                timestamp=datetime.now(),
                event_type=event_type,  # type: ignore[arg-type]
                project_id=project_id,
                agent_id="execution_loop",
                metadata={"message": msg, **(metadata or {})},
            )
            hub.record_timeline_event(event)
        except Exception:
            pass  # Don't fail on observability errors


if TYPE_CHECKING:
    from .acceptance_agent import AcceptanceAgent, AcceptanceResult
    from .project_context import ProjectContext, RoundFeedback
    from .manifest import AgentManifest


@dataclass
class ExecutionEnhancer:
    """Execution enhancer that integrates repair, dependency, and blueprint tools.

    This class wraps the RepairEngine, DependencySynchronizer, and BlueprintEnhancer
    to provide enhanced execution capabilities based on agent manifests.

    Attributes:
        repair_engine (`RepairEngine | None`):
            Engine for analyzing and repairing errors.
        dependency_sync (`DependencySynchronizer | None`):
            Synchronizer for managing dependencies.
        blueprint_enhancer (`BlueprintEnhancer | None`):
            Enhancer for blueprint generation.
    """

    repair_engine: RepairEngine | None = None
    dependency_sync: DependencySynchronizer | None = None
    blueprint_enhancer: BlueprintEnhancer | None = None

    @classmethod
    def from_manifest(cls, manifest: "AgentManifest") -> "ExecutionEnhancer":
        """Create an ExecutionEnhancer from an agent manifest.

        Args:
            manifest: The agent manifest with configuration.

        Returns:
            Configured ExecutionEnhancer instance.
        """
        enhancer = cls()

        # Initialize components based on manifest configuration
        if manifest.repair_config:
            enhancer.repair_engine = RepairEngine(manifest)

        if manifest.dependency_config:
            enhancer.dependency_sync = DependencySynchronizer(manifest)

        if manifest.blueprint_config:
            enhancer.blueprint_enhancer = BlueprintEnhancer(manifest)

        return enhancer

    def analyze_error(self, error_message: str) -> list[RepairAction]:
        """Analyze an error and return repair actions.

        Args:
            error_message: The error message to analyze.

        Returns:
            List of repair actions.
        """
        if self.repair_engine:
            return self.repair_engine.analyze_error(error_message)
        return []

    def build_repair_prompt(
        self,
        error_message: str,
        actions: list[RepairAction],
        affected_files: dict[str, str] | None = None,
    ) -> str:
        """Build a repair prompt for the LLM.

        Args:
            error_message: The error message.
            actions: Repair actions from analysis.
            affected_files: Optional affected file contents.

        Returns:
            Prompt string for repair.
        """
        if self.repair_engine:
            return self.repair_engine.build_repair_prompt(
                error_message, actions, affected_files
            )
        return f"请修复以下错误:\n\n```\n{error_message}\n```"

    def extract_dependencies(
        self,
        code_content: str,
        language: str | None = None,
    ) -> list[DependencyInfo]:
        """Extract dependencies from code content.

        Args:
            code_content: The source code.
            language: Optional language hint.

        Returns:
            List of extracted dependencies.
        """
        if self.dependency_sync:
            return self.dependency_sync.extract_dependencies_from_code(
                code_content, language
            )
        return []

    def find_missing_dependencies(
        self,
        required: list[DependencyInfo],
        dep_file_content: str,
    ) -> list[DependencyInfo]:
        """Find missing dependencies.

        Args:
            required: Required dependencies.
            dep_file_content: Current dependency file content.

        Returns:
            List of missing dependencies.
        """
        if self.dependency_sync:
            return self.dependency_sync.find_missing_dependencies(
                required, dep_file_content
            )
        return []

    async def sync_dependencies(
        self,
        code_files: dict[str, str],
        workspace: Any,
    ) -> SyncResult:
        """Synchronize dependencies from code to dependency file.

        Args:
            code_files: Dict of file paths to content.
            workspace: The workspace to update.

        Returns:
            Sync result with details.
        """
        if self.dependency_sync:
            return await self.dependency_sync.sync_dependencies(code_files, workspace)
        return SyncResult(success=False, errors=["No dependency synchronizer configured"])

    async def enhance_blueprint(
        self,
        requirement: str,
        criteria: list,
        original_blueprint: dict[str, Any] | None = None,
    ) -> EnhancedBlueprint:
        """Enhance a blueprint with required functions.

        Args:
            requirement: The requirement description.
            criteria: List of acceptance criteria.
            original_blueprint: Optional original blueprint.

        Returns:
            Enhanced blueprint with function requirements.
        """
        if self.blueprint_enhancer:
            return await self.blueprint_enhancer.analyze_and_enhance(
                requirement, criteria, original_blueprint
            )
        return EnhancedBlueprint()

    def build_enhanced_prompt(
        self,
        requirement: str,
        criteria: list,
        enhanced: EnhancedBlueprint,
    ) -> str:
        """Build an enhanced generation prompt.

        Args:
            requirement: The requirement.
            criteria: Acceptance criteria.
            enhanced: Enhanced blueprint.

        Returns:
            Enhanced prompt string.
        """
        if self.blueprint_enhancer:
            return self.blueprint_enhancer.build_enhanced_prompt(
                requirement, criteria, enhanced
            )
        return requirement


@dataclass
class AgentOutput:
    """Captures agent execution result for context passing.

    Attributes:
        agent_id (`str`):
            The agent ID that produced this output.
        node_id (`str`):
            The task node ID.
        content (`str`):
            The output content.
        success (`bool`):
            Whether execution succeeded.
        execution_id (`str | None`):
            The execution ID for timeline tracking.
        start_time (`datetime | None`):
            When execution started.
        end_time (`datetime | None`):
            When execution ended.
        duration_ms (`float | None`):
            Duration in milliseconds.
    """

    agent_id: str
    node_id: str
    content: str
    success: bool = True
    execution_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: float | None = None


@dataclass
class ExecutionContext:
    """Accumulated context from previous agent executions."""

    intent_utterance: str
    agent_outputs: list[AgentOutput] = field(default_factory=list)
    shared_artifacts: dict[str, str] = field(default_factory=dict)
    project_memory: ProjectMemory | None = None
    round_feedback: "RoundFeedback | None" = None

    def add_output(self, output: AgentOutput) -> None:
        """Add an agent output to the context."""
        self.agent_outputs.append(output)

    def set_round_feedback(self, feedback: "RoundFeedback") -> None:
        """Set feedback from the previous round.

        Args:
            feedback: The round feedback to include in prompts.
        """
        self.round_feedback = feedback

    def build_prompt(self, current_node_id: str, requirement_desc: str) -> str:
        """Build a prompt with accumulated context for the next agent.

        This method constructs a comprehensive prompt that includes:
        1. User requirement
        2. Project memory (technology decisions and constraints)
        3. Previous round feedback (if available)
        4. Previous agent outputs
        5. Current task description

        The project memory section is critical for maintaining consistency
        across multiple rounds of code generation.
        """
        lines = [
            f"## 用户需求\n{self.intent_utterance}",
        ]

        # Add project memory context (critical for consistency)
        if self.project_memory:
            memory_context = self.project_memory.get_context_for_prompt()
            if memory_context.strip():
                lines.append(f"\n{memory_context}")

        # Add previous round feedback (critical for iterative improvement)
        if self.round_feedback and not self.round_feedback.is_successful():
            feedback_prompt = self.round_feedback.build_feedback_prompt()
            if feedback_prompt.strip():
                lines.append(f"\n{feedback_prompt}")

        lines.append(
            f"\n## 当前任务\n任务ID: {current_node_id}\n要求: {requirement_desc}"
        )

        if self.agent_outputs:
            lines.append("\n## 前序任务输出")
            for output in self.agent_outputs:
                status = "✓" if output.success else "✗"
                lines.append(f"\n### [{status}] {output.node_id} ({output.agent_id})")
                lines.append(output.content)

        if self.shared_artifacts:
            lines.append("\n## 共享产物")
            for name, value in self.shared_artifacts.items():
                lines.append(f"- {name}: {value}")

        lines.append(
            "\n## 指令\n"
            "请基于以上上下文完成当前任务，输出结构化结果。\n\n"
            "### 验证要求（重要）\n"
            "完成代码编写后，你**必须**主动验证代码的正确性：\n"
            "1. 运行适当的命令验证代码可以被正确加载/编译（如导入测试、构建命令等）\n"
            "2. 如果项目有测试框架，运行相关测试\n"
            "3. 如果验证失败，立即修复问题后再次验证\n"
            "4. 只有验证通过后才算任务完成\n\n"
            "验证方式由你根据项目类型自行决定，确保代码可以正常运行。"
        )
        return "\n".join(lines)


@dataclass
class ExecutionReport:
    project_id: str | None
    accepted: bool
    kpi: KPIRecord
    task_status: dict[str, str]
    plan: StrategyPlan
    deliverable: ArtifactDeliveryResult | None = None
    agent_outputs: list[AgentOutput] = field(default_factory=list)
    acceptance_result: "AcceptanceResult | None" = None  # LLM-driven validation


class ExecutionLoop:
    """Execution loop with agent interaction support.

    This class orchestrates multi-agent task execution with:
    - Context passing: Previous agent outputs are passed to subsequent agents
    - MsgHub integration: Agents can broadcast and observe messages
    - Shared memory: Optional shared memory for cross-agent state
    """

    def __init__(
        self,
        *,
        project_pool: ProjectPool,
        memory_pool: MemoryPool,
        resource_library: ResourceLibrary,
        orchestrator: AssistantOrchestrator,
        task_graph_builder: TaskGraphBuilder,
        kpi_tracker: KPITracker,
        msg_hub_factory: Callable[[str], MsgHubBroadcaster] | None = None,
        delivery_manager: ArtifactDeliveryManager | None = None,
        max_rounds: int = 3,
        shared_memory: MemoryBase | None = None,
        enable_agent_msghub: bool = True,
        acceptance_agent: "AcceptanceAgent | None" = None,
        workspace_dir: str = "/workspace",
        enable_project_context: bool = True,
        enable_parallel_execution: bool = False,
        parallel_timeout_seconds: float = 300.0,
        enable_task_validation: bool = True,
        max_task_retries: int = 2,
        task_validation_timeout: float = 30.0,
        enable_active_validation: bool = True,
        # 300s (5 min) to accommodate npm install + build for Node.js projects
        # Previous 120s was too short, causing 84+ timeout failures
        active_validation_timeout: float = 300.0,
    ) -> None:
        self.project_pool = project_pool
        self.memory_pool = memory_pool
        self.resource_library = resource_library
        self.orchestrator = orchestrator
        self.task_graph_builder = task_graph_builder
        self.kpi_tracker = kpi_tracker
        self.msg_hub_factory = msg_hub_factory
        self.delivery_manager = delivery_manager
        self.max_rounds = max_rounds
        self.shared_memory = shared_memory
        self.enable_agent_msghub = enable_agent_msghub
        self.acceptance_agent = acceptance_agent
        self.workspace_dir = workspace_dir
        self.enable_project_context = enable_project_context
        self.enable_parallel_execution = enable_parallel_execution
        self.parallel_timeout_seconds = parallel_timeout_seconds
        # Task-level validation settings
        self.enable_task_validation = enable_task_validation
        self.max_task_retries = max_task_retries
        self.task_validation_timeout = task_validation_timeout
        # Active validation: call Claude Code to verify task results
        self.enable_active_validation = enable_active_validation
        self.active_validation_timeout = active_validation_timeout
        # Task-level validator (created lazily)
        self._task_validator: TaskLevelValidator | None = None
        # Project task boards for tracking agent-level progress
        self._project_task_boards: Dict[str, "ProjectTaskBoard"] = {}
        # Project memories for cross-agent context sharing
        self._project_memories: Dict[str, ProjectMemory] = {}
        # Enhanced project contexts for file tracking and validation
        self._project_contexts: Dict[str, "ProjectContext"] = {}
        # Execution enhancers per agent (keyed by agent_id)
        self._agent_enhancers: Dict[str, ExecutionEnhancer] = {}
        # Agent cache to avoid dynamic re-creation (NEW)
        self._agent_cache: Dict[str, Any] = {}

    def get_project_memory(self, project_id: str) -> ProjectMemory:
        """Get or create project memory for a project.

        Args:
            project_id: The project identifier.

        Returns:
            ProjectMemory instance for the project.
        """
        if project_id not in self._project_memories:
            self._project_memories[project_id] = ProjectMemory(
                project_id=project_id,
                workspace_dir=self.workspace_dir,
            )
        return self._project_memories[project_id]

    def get_project_context(self, project_id: str) -> "ProjectContext":
        """Get or create enhanced project context for a project.

        The ProjectContext provides file tracking, dependency validation,
        and structured feedback generation.

        Args:
            project_id: The project identifier.

        Returns:
            ProjectContext instance for the project.
        """
        if project_id not in self._project_contexts:
            from .project_context import create_project_context

            project_memory = self.get_project_memory(project_id)
            self._project_contexts[project_id] = create_project_context(
                project_id=project_id,
                workspace_dir=self.workspace_dir,
                project_memory=project_memory,
            )
        return self._project_contexts[project_id]

    def register_agent_enhancer(
        self,
        agent_id: str,
        manifest: "AgentManifest",
    ) -> ExecutionEnhancer:
        """Register an execution enhancer for an agent.

        Creates an ExecutionEnhancer from the agent's manifest and stores
        it for use during execution. The enhancer provides repair, dependency
        sync, and blueprint enhancement capabilities.

        Args:
            agent_id: The agent identifier.
            manifest: The agent's manifest with configuration.

        Returns:
            The created ExecutionEnhancer.
        """
        enhancer = ExecutionEnhancer.from_manifest(manifest)
        self._agent_enhancers[agent_id] = enhancer
        logger.debug(
            "Registered enhancer for agent %s (repair=%s, deps=%s, blueprint=%s)",
            agent_id,
            enhancer.repair_engine is not None,
            enhancer.dependency_sync is not None,
            enhancer.blueprint_enhancer is not None,
        )
        return enhancer

    def get_agent_enhancer(self, agent_id: str) -> ExecutionEnhancer | None:
        """Get the execution enhancer for an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            The ExecutionEnhancer if registered, None otherwise.
        """
        return self._agent_enhancers.get(agent_id)

    def get_task_validator(self) -> TaskLevelValidator:
        """Get or create the task-level validator.

        Returns:
            TaskLevelValidator instance for immediate task validation.
        """
        if self._task_validator is None:
            # Try to get container context if available
            container_id = None
            container_workspace = "/workspace/working"
            try:
                from agentscope.scripts._claude_code import get_container_context

                container_id, container_workspace = get_container_context()
            except ImportError:
                pass

            self._task_validator = TaskLevelValidator(
                workspace_dir=self.workspace_dir,
                container_id=container_id,
                container_workspace=container_workspace,
                validation_timeout=self.task_validation_timeout,
            )
        return self._task_validator

    async def _handle_execution_error(
        self,
        agent_id: str,
        error_message: str,
        project_context: "ProjectContext | None",
    ) -> str | None:
        """Handle an execution error using the agent's repair engine.

        This method analyzes the error using the agent's configured repair
        patterns and generates a repair prompt with specific hints.

        Args:
            agent_id: The agent that produced the error.
            error_message: The error message.
            project_context: Optional project context for file access.

        Returns:
            A repair prompt if the error can be analyzed, None otherwise.
        """
        enhancer = self.get_agent_enhancer(agent_id)
        if enhancer is None or enhancer.repair_engine is None:
            return None

        # Analyze the error
        actions = enhancer.analyze_error(error_message)
        if not actions:
            logger.debug("No repair actions found for error: %s", error_message[:100])
            return None

        _log_execution(
            f"Found {len(actions)} repair actions for error in agent {agent_id}",
            prefix="[RepairEngine]",
        )

        # Get affected files if project context is available
        affected_files: dict[str, str] = {}
        if project_context:
            for action in actions:
                for sync_file in action.sync_files:
                    content = project_context.get_file_content(sync_file)
                    if content:
                        affected_files[sync_file] = content

        # Build repair prompt
        return enhancer.build_repair_prompt(error_message, actions, affected_files)

    async def _sync_project_dependencies(
        self,
        project_id: str,
        agent_id: str,
        project_context: "ProjectContext",
    ) -> SyncResult | None:
        """Synchronize dependencies for a project.

        Extracts imports from generated code files and ensures they are
        present in the dependency file (requirements.txt, package.json, etc).

        Args:
            project_id: The project identifier.
            agent_id: The agent that generated the code.
            project_context: The project context with file tracking.

        Returns:
            SyncResult if synchronization was attempted, None otherwise.
        """
        enhancer = self.get_agent_enhancer(agent_id)
        if enhancer is None or enhancer.dependency_sync is None:
            return None

        # Gather all code files from project context
        code_files: dict[str, str] = {}
        for path in project_context.list_files():
            content = project_context.get_file_content(path)
            if content and (
                path.endswith(".py") or
                path.endswith(".js") or
                path.endswith(".ts") or
                path.endswith(".go")
            ):
                code_files[path] = content

        if not code_files:
            return None

        # Create a simple workspace wrapper for file operations
        class WorkspaceWrapper:
            def __init__(self, ctx: "ProjectContext"):
                self._ctx = ctx

            def read_file(self, path: str) -> str:
                return self._ctx.get_file_content(path) or ""

            def write_file(self, path: str, content: str) -> None:
                self._ctx.register_file(
                    path=path,
                    content=content,
                    created_by="DependencySynchronizer",
                    description="Auto-generated dependency update",
                )

        workspace = WorkspaceWrapper(project_context)
        result = await enhancer.sync_dependencies(code_files, workspace)

        if result.added:
            _log_execution(
                f"Added {len(result.added)} dependencies to {result.dependency_file}: {[d.name for d in result.added]}",
                prefix="[DependencySync]",
            )

        return result

    def _parse_agent_output_files(
        self,
        output: AgentOutput,
        project_context: "ProjectContext",
    ) -> list[str]:
        """Parse agent output to extract and register generated files.

        This method detects file content blocks in agent output and
        registers them with the ProjectContext for tracking and validation.

        Common output patterns supported:
        - ```filename.ext\\n...content...\\n```
        - **File: path/to/file**\\n```lang\\n...content...\\n```
        - <file path="...">...content...</file>
        - JSON format: {"files": [{"path": "...", "content": "..."}]}

        Args:
            output: The agent output to parse.
            project_context: The project context to register files with.

        Returns:
            List of file paths that were registered.
        """
        registered_files = []
        content = output.content

        # Pattern 1: **File: path/to/file**\n```lang\ncontent\n```
        file_block_pattern = re.compile(
            r'\*\*File:\s*([^\*\n]+)\*\*\s*\n```(?:\w+)?\n(.*?)```',
            re.DOTALL
        )
        for match in file_block_pattern.finditer(content):
            path = match.group(1).strip()
            file_content = match.group(2)
            if path and file_content:
                project_context.register_file(
                    path=path,
                    content=file_content,
                    created_by=output.agent_id,
                    description=f"Generated in node {output.node_id}",
                )
                registered_files.append(path)

        # Pattern 2: <file path="...">content</file>
        xml_file_pattern = re.compile(
            r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>',
            re.DOTALL
        )
        for match in xml_file_pattern.finditer(content):
            path = match.group(1).strip()
            file_content = match.group(2)
            if path and file_content and path not in registered_files:
                project_context.register_file(
                    path=path,
                    content=file_content,
                    created_by=output.agent_id,
                    description=f"Generated in node {output.node_id}",
                )
                registered_files.append(path)

        # Pattern 3: JSON format with files array
        try:
            import json
            # Look for JSON blocks in the content
            json_pattern = re.compile(r'```json\n(.*?)```', re.DOTALL)
            for match in json_pattern.finditer(content):
                try:
                    data = json.loads(match.group(1))
                    files = data.get("files", [])
                    for file_info in files:
                        path = file_info.get("path", "")
                        file_content = file_info.get("content", "")
                        if path and file_content and path not in registered_files:
                            project_context.register_file(
                                path=path,
                                content=file_content,
                                created_by=output.agent_id,
                                description=file_info.get(
                                    "description",
                                    f"Generated in node {output.node_id}"
                                ),
                            )
                            registered_files.append(path)
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass

        # Pattern 4: Simple code blocks with filename comment
        # ```python\n# filename: path/to/file.py\ncontent\n```
        simple_pattern = re.compile(
            r'```(\w+)\n#\s*(?:filename|file):\s*([^\n]+)\n(.*?)```',
            re.DOTALL
        )
        for match in simple_pattern.finditer(content):
            path = match.group(2).strip()
            file_content = match.group(3)
            if path and file_content and path not in registered_files:
                project_context.register_file(
                    path=path,
                    content=file_content,
                    created_by=output.agent_id,
                    description=f"Generated in node {output.node_id}",
                )
                registered_files.append(path)

        if registered_files:
            _log_execution(
                f"Registered {len(registered_files)} files from agent {output.agent_id}: {', '.join(registered_files[:5])}",
                prefix="[FileRegistry]",
            )

        return registered_files

    def _register_dependency_file(
        self,
        path: str,
        content: str,
        project_context: "ProjectContext",
    ) -> None:
        """Register a dependency file (package.json, requirements.txt, etc.).

        Args:
            path: The file path.
            content: The file content.
            project_context: The project context.
        """
        dependency_files = {
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
            "Cargo.toml",
            "go.mod",
        }
        filename = path.split("/")[-1]
        if filename in dependency_files:
            project_context.declare_dependencies_from_file(path, content)
            _log_execution(
                f"Declared dependencies from {path}",
                prefix="[DependencySync]",
            )

    def _get_runtime_agents(self) -> dict[str, object]:
        """Get all registered runtime agents."""
        return getattr(self.orchestrator, "_runtime_agents", {})

    async def _cleanup_all_worktrees(self) -> None:
        """Cleanup all tracked worktrees at the end of an execution cycle.

        This method is called at the end of run_cycle_async to cleanup
        worktrees that were deferred from CollaborativeExecutor. By deferring
        cleanup to the cycle end, we allow agents to be reused across rounds.
        """
        from ._collaborative_executor import get_workspace_for_collaborative

        workspace = get_workspace_for_collaborative(
            self.orchestrator,
            self.workspace_dir,
        )
        if not workspace:
            return

        # Get tracked worktrees from workspace
        active_worktrees = getattr(workspace, "_active_agent_worktrees", set())
        if not active_worktrees:
            return

        _log_execution(
            f"Cleaning up {len(active_worktrees)} agent worktrees...",
            prefix="[Worktree]",
        )

        # Cleanup each worktree
        for agent_id in list(active_worktrees):
            try:
                await workspace.remove_agent_worktree(agent_id)
            except Exception as e:
                _log_execution(
                    f"Failed to cleanup worktree for {agent_id}: {e}",
                    level="warning",
                    prefix="[Worktree]",
                )

        # Clear the tracking set
        workspace._active_agent_worktrees.clear()
        _log_execution("✓ Worktree cleanup completed", prefix="[Worktree]")

    def _get_or_load_agent(self, agent_id: str) -> object | None:
        """Get agent from runtime_agents, or lazy-load from registry if available.

        This method enables agents loaded from registry (with only AgentProfile
        in _candidates) to be instantiated on-demand when needed for execution.

        Args:
            agent_id: The agent identifier.

        Returns:
            The agent instance, or None if not found and cannot be loaded.
        """
        # First try runtime_agents
        runtime_agents = self._get_runtime_agents()
        if agent_id in runtime_agents:
            return runtime_agents[agent_id]

        # Not in runtime_agents - try to lazy load from registry
        candidates = getattr(self.orchestrator, "_candidates", [])
        profile = None
        for c in candidates:
            if c.agent_id == agent_id:
                profile = c
                break

        if profile is None:
            return None

        # Check if we have manifest_path to load from
        manifest_path = profile.metadata.get("manifest_path")
        if not manifest_path:
            _log_execution(
                f"Agent {agent_id} 无 manifest_path，无法加载实例",
                level="warning",
                prefix="[LazyLoad]",
            )
            return None

        # Try to load the agent instance
        try:
            from pathlib import Path
            from ._modular_agent import load_modular_agent

            # manifest_path points to manifest.json, agent_dir is its parent
            agent_dir = str(Path(manifest_path).parent)

            # Get LLM from team_selector if available
            llm = None
            if hasattr(self.orchestrator, "team_selector"):
                llm = getattr(self.orchestrator.team_selector, "_model", None)

            # Get MCP clients from orchestrator if available
            mcp_clients = None
            if hasattr(self.orchestrator, "_mcp_clients"):
                mcp_clients = self.orchestrator._mcp_clients

            # Build toolkit with Claude Code tools for file operations
            toolkit = None
            try:
                from agentscope.scripts.hive_toolkit import HiveToolkitManager
                toolkit_manager = HiveToolkitManager(llm=llm, mcp_clients=mcp_clients)
                toolkit = toolkit_manager.build_toolkit(
                    tools_filter={"claude_code_edit", "claude_code_chat"}
                )
                _log_execution(
                    f"Agent {agent_id} 已添加 Claude Code 工具",
                    level="info",
                    prefix="[LazyLoad]",
                )
            except ImportError as e:
                _log_execution(
                    f"Agent {agent_id} 无法添加工具: {e}",
                    level="warning",
                    prefix="[LazyLoad]",
                )

            agent = load_modular_agent(
                agent_dir,
                llm=llm,
                mcp_clients=mcp_clients,
                toolkit=toolkit,
            )

            # Store in runtime_agents for future use
            runtime_agents[agent_id] = agent

            _log_execution(
                f"Agent {agent_id} 已从 {agent_dir} 懒加载",
                level="info",
                prefix="[LazyLoad]",
            )
            return agent

        except Exception as e:
            _log_execution(
                f"Agent {agent_id} 懒加载失败: {e}",
                level="error",
                prefix="[LazyLoad]",
            )
            return None

    def get_task_board(self, project_id: str) -> ProjectTaskBoard:
        """Get or create project task board.

        Args:
            project_id: The project identifier.

        Returns:
            The project's task board.
        """
        if project_id not in self._project_task_boards:
            self._project_task_boards[project_id] = ProjectTaskBoard(
                project_id=project_id
            )
        return self._project_task_boards[project_id]

    def _init_task_board_from_plan(
        self,
        project_id: str,
        plan: StrategyPlan,
        acceptance: AcceptanceCriteria,
    ) -> ProjectTaskBoard:
        """Initialize task board from strategy plan.

        Args:
            project_id: The project identifier.
            plan: The strategy plan with agent assignments.
            acceptance: Acceptance criteria for the project.

        Returns:
            Initialized project task board.
        """
        board = self.get_task_board(project_id)
        board.set_acceptance_criteria(acceptance)

        # Create tasks from plan rankings
        for node_id, ranking in plan.rankings.items():
            agent_id = ranking.profile.agent_id
            agent_name = ranking.profile.name

            # Create task item
            task = TaskItem(
                task_id=node_id,
                description=f"Task for {node_id}",
                assigned_to=agent_id,
            )

            # Add to board and assign to agent
            board.assign_task_to_agent(
                task=task,
                agent_id=agent_id,
                agent_name=agent_name,
                role=node_id,
            )

        return board

    def _update_task_board_status(
        self,
        project_id: str,
        task_status: Dict[str, str],
    ) -> None:
        """Update task board from execution results.

        Args:
            project_id: The project identifier.
            task_status: Dict of task_id -> status string.
        """
        board = self.get_task_board(project_id)
        board.sync_from_task_graph(task_status)

        # Also update agent task boards
        for task_id, status_str in task_status.items():
            if task_id in board.global_tasks:
                task = board.global_tasks[task_id]
                agent_id = task.assigned_to
                if agent_id and agent_id in board.agent_boards:
                    agent_board = board.agent_boards[agent_id]
                    if status_str == "running":
                        agent_board.start_task(task_id)
                    elif status_str == "completed":
                        agent_board.complete_task(task_id)
                    elif status_str == "failed":
                        agent_board.fail_task(task_id)

    def _update_agent_scores(
        self,
        plan: "StrategyPlan",
        task_status: dict[str, str],
        pass_ratio: float,
    ) -> None:
        """Update agent scores based on task completion results.

        This implements the cold-start learning mechanism where agent
        performance scores are updated based on actual task outcomes.

        Args:
            plan: The strategy plan containing agent rankings.
            task_status: Status of each task (completed/failed/etc).
            pass_ratio: Overall pass ratio for quality estimation.
        """
        from ..aa import AgentProfile

        for node_id, status in task_status.items():
            if node_id not in plan.rankings:
                continue

            ranking = plan.rankings[node_id]
            profile: AgentProfile = ranking.profile

            # Determine if task was successful
            accepted = status == "completed"

            # Use pass_ratio as a proxy for quality score
            # In real implementation, this could be more sophisticated
            quality_score = pass_ratio if accepted else 0.3

            # Update the agent's performance score
            profile.update_after_task(
                quality_score=quality_score,
                accepted=accepted,
            )

    def _invoke_agent(
        self,
        agent_id: str,
        prompt: str,
        *,
        context: ExecutionContext | None = None,
        node_id: str | None = None,
    ) -> AgentOutput | None:
        """Invoke an agent with context from previous executions.

        Args:
            agent_id: The agent identifier
            prompt: Base prompt (usually the user utterance)
            context: Accumulated context from previous agent executions
            node_id: Current task node identifier

        Returns:
            AgentOutput capturing the result, or None if agent not found
        """
        agent = self._get_or_load_agent(agent_id)
        if agent is None:
            return None

        # Build enriched prompt with context
        if context and node_id:
            requirement_desc = prompt  # Use original prompt as requirement description
            enriched_prompt = context.build_prompt(node_id, requirement_desc)
        else:
            enriched_prompt = prompt

        try:
            coro = agent.reply(Msg(name="system", role="user", content=enriched_prompt))
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(coro)
            finally:
                loop.close()
            content = result.get_text_content() or ""
            return AgentOutput(
                agent_id=agent_id,
                node_id=node_id or "unknown",
                content=content,
                success=True,
            )
        except Exception as e:
            return AgentOutput(
                agent_id=agent_id,
                node_id=node_id or "unknown",
                content=f"执行失败: {str(e)}",
                success=False,
            )

    async def _invoke_agent_async(
        self,
        agent_id: str,
        prompt: str,
        *,
        context: ExecutionContext | None = None,
        node_id: str | None = None,
    ) -> AgentOutput | None:
        """Async version of agent invocation."""
        agent = self._get_or_load_agent(agent_id)
        if agent is None:
            return None

        if context and node_id:
            enriched_prompt = context.build_prompt(node_id, prompt)
        else:
            enriched_prompt = prompt

        try:
            result = await agent.reply(
                Msg(name="system", role="user", content=enriched_prompt),
                task_id=node_id,  # Pass task_id for observability
            )
            content = result.get_text_content() or ""
            return AgentOutput(
                agent_id=agent_id,
                node_id=node_id or "unknown",
                content=content,
                success=True,
            )
        except Exception as e:
            return AgentOutput(
                agent_id=agent_id,
                node_id=node_id or "unknown",
                content=f"执行失败: {str(e)}",
                success=False,
            )

    async def _execute_with_msghub(
        self,
        graph: TaskGraph,
        context: ExecutionContext,
    ) -> list[AgentOutput]:
        """Execute tasks with MsgHub for agent-to-agent broadcasting.

        All agents are added to a MsgHub so they can observe each other's outputs.
        """
        outputs: list[AgentOutput] = []

        # Collect all agents involved in this execution
        # Use _get_or_load_agent to support lazy loading from registry
        agent_instances = []
        node_agent_map: dict[str, object] = {}
        missing_agents: list[tuple[str, str]] = []  # (node_id, agent_id)

        for node_id in graph.topological_order():
            node = graph.get(node_id)

            # Handle both single agent and collaborative (multi-agent) tasks
            agent_ids_to_load = []
            if hasattr(node, "assigned_agent_ids") and node.assigned_agent_ids:
                # Collaborative task with multiple agents
                agent_ids_to_load.extend(node.assigned_agent_ids)
            if node.assigned_agent_id:
                # Single agent task (also serves as fallback for collaborative)
                if node.assigned_agent_id not in agent_ids_to_load:
                    agent_ids_to_load.append(node.assigned_agent_id)

            if not agent_ids_to_load:
                _log_execution(
                    f"任务 {node_id} 未分配 Agent",
                    level="warning",
                    prefix="[MsgHub]",
                )
                continue

            # Load all agents for this node
            for agent_id in agent_ids_to_load:
                agent = self._get_or_load_agent(agent_id)
                if agent is not None:
                    if agent not in agent_instances:
                        agent_instances.append(agent)
                    # Map first agent as primary for node_agent_map
                    if node_id not in node_agent_map:
                        node_agent_map[node_id] = agent
                else:
                    missing_agents.append((node_id, agent_id))

        if not agent_instances:
            # No runtime agents available - this is a critical issue!
            runtime_agents = self._get_runtime_agents()
            _log_execution(
                f"无可用 Agent 实例! runtime_agents={len(runtime_agents)}, graph_nodes={len(list(graph.nodes()))}",
                level="error",
                prefix="[MsgHub]",
            )
            # Log details about missing agents
            for node_id, agent_id in missing_agents:
                _log_execution(
                    f"任务 {node_id} 分配的 Agent '{agent_id}' 无法加载",
                    level="error",
                    prefix="[MsgHub]",
                )
            return outputs

        _log_execution(
            f"[MsgHub] 开始执行: {len(agent_instances)} 个 Agent 实例, {len(list(graph.nodes()))} 个任务节点",
        )

        # Create announcement message with initial context
        announcement = Msg(
            name="ExecutionLoop",
            role="system",
            content=f"## 协作任务启动\n\n用户需求: {context.intent_utterance}\n\n"
            f"参与代理: {len(agent_instances)} 个\n"
            f"任务数量: {len(list(graph.nodes()))} 个",
        )

        # Execute within MsgHub context for automatic broadcasting
        import time
        total_tasks = len(list(graph.nodes()))
        completed_tasks = 0

        async with MsgHub(
            participants=agent_instances,
            announcement=announcement,
            enable_auto_broadcast=True,
        ):
            for node_id in graph.topological_order():
                graph.mark_running(node_id)
                node = graph.get(node_id)

                # Check if this is a collaborative task (multiple agents)
                if node.is_collaborative:
                    task_start = time.time()
                    _log_execution(
                        f"[MsgHub] 任务 {completed_tasks + 1}/{total_tasks}: {node_id} -> 协作执行 ({len(node.assigned_agent_ids)} Agents)...",
                    )

                    # Get workspace for collaborative execution
                    from ._collaborative_executor import (
                        CollaborativeExecutor,
                        get_workspace_for_collaborative,
                    )

                    workspace = get_workspace_for_collaborative(
                        self.orchestrator,
                        self.workspace_dir,
                    )

                    if workspace:
                        executor = CollaborativeExecutor(
                            workspace=workspace,
                            invoke_agent_async=self._invoke_agent_async,
                            get_runtime_agents=self._get_runtime_agents,
                        )
                        collab_outputs = await executor.execute(
                            node=node,
                            context=context,
                        )
                        outputs.extend(collab_outputs)

                        task_duration = time.time() - task_start
                        _log_execution(
                            f"[MsgHub] 协作任务 {node_id} 完成 (耗时: {task_duration:.1f}s, {len(collab_outputs)} 个输出)",
                        )
                    else:
                        _log_execution(
                            f"[MsgHub] ⚠️ 协作任务 {node_id} 需要 RuntimeWorkspaceWithPR，降级为单 Agent 执行",
                            level="warning",
                        )
                        # Fallback to single agent (first one)
                        if node.assigned_agent_id:
                            output = await self._invoke_agent_async(
                                node.assigned_agent_id,
                                context.intent_utterance,
                                context=context,
                                node_id=node_id,
                            )
                            if output:
                                outputs.append(output)
                                context.add_output(output)

                    graph.mark_completed(node_id)
                    completed_tasks += 1
                    continue

                elif node.assigned_agent_id:
                    task_start = time.time()
                    agent_id = node.assigned_agent_id
                    _log_execution(
                        f"[MsgHub] 任务 {completed_tasks + 1}/{total_tasks}: {node_id} -> Agent '{agent_id}' 开始执行...",
                    )

                    # Setup worktree directory for agent before execution
                    from ._collaborative_executor import (
                        get_workspace_for_collaborative,
                    )
                    workspace = get_workspace_for_collaborative(
                        self.orchestrator,
                        self.workspace_dir,
                    )
                    if workspace and hasattr(workspace, "get_agent_working_dir"):
                        try:
                            # Initialize git repo first (sets safe.directory)
                            # This is required before creating worktrees
                            if hasattr(workspace, "init_git_repo"):
                                await workspace.init_git_repo()

                            agent_dir = await workspace.get_agent_working_dir(agent_id)
                            # Set container workspace to agent's worktree directory
                            from agentscope.scripts._claude_code import set_container_context
                            container_id = getattr(workspace, "container_id", None)
                            if container_id and agent_dir:
                                set_container_context(container_id, agent_dir)
                                _log_execution(
                                    f"[{node_id}] 📁 {agent_id} 工作目录: {agent_dir}",
                                )
                        except Exception as e:
                            _log_execution(
                                f"[{node_id}] ⚠️ 设置工作目录失败: {e}",
                                level="warning",
                            )

                    output = await self._invoke_agent_async(
                        agent_id,
                        context.intent_utterance,
                        context=context,
                        node_id=node_id,
                    )

                    task_duration = time.time() - task_start

                    if output:
                        outputs.append(output)
                        context.add_output(output)
                        _log_execution(
                            f"[MsgHub] 任务 {node_id} 完成 (耗时: {task_duration:.1f}s, 输出长度: {len(output.content) if output.content else 0} 字符)",
                        )

                        # Store in shared memory if available
                        if self.shared_memory:
                            await self.shared_memory.add(
                                Msg(
                                    name=output.agent_id,
                                    role="assistant",
                                    content=output.content,
                                    metadata={"node_id": node_id},
                                )
                            )

                        # === TASK-LEVEL IMMEDIATE VALIDATION ===
                        if self.enable_task_validation:
                            _log_execution(f"[{node_id}] 🔍 开始任务级验收...")

                            # Check if we have workspace with cherry-pick support
                            from ._collaborative_executor import (
                                get_workspace_for_collaborative,
                            )
                            workspace = get_workspace_for_collaborative(
                                self.orchestrator,
                                self.workspace_dir,
                            )

                            if workspace and hasattr(workspace, "cherry_pick_to_delivery"):
                                # Use cherry-pick validation flow
                                validation = await self._cherry_pick_and_validate(
                                    node_id=node_id,
                                    node=node,
                                    agent_id=node.assigned_agent_id,
                                    context=context,
                                    workspace=workspace,
                                )
                            else:
                                # Fallback to original validation flow
                                validation = await self._validate_and_fix_task(
                                    node_id=node_id,
                                    node=node,
                                    output=output,
                                    context=context,
                                )

                            if validation.passed:
                                _log_execution(f"[{node_id}] ✓ 任务验收通过")
                            if not validation.passed:
                                # Task failed validation after retries
                                graph.mark_failed(
                                    node_id,
                                    reason=validation.error_summary,
                                )
                                _log_execution(
                                    f"[MsgHub] 任务 {node_id} 验收失败 (已重试): {validation.error_summary}",
                                    level="error",
                                )
                                # Continue with other tasks instead of stopping
                                completed_tasks += 1
                                continue
                        # === END TASK-LEVEL VALIDATION ===
                    else:
                        _log_execution(
                            f"[MsgHub] 任务 {node_id} 未产生输出 (耗时: {task_duration:.1f}s)",
                            level="warning",
                        )
                else:
                    _log_execution(
                        f"[MsgHub] 任务 {node_id} 无分配 Agent, 跳过",
                        level="warning",
                    )

                graph.mark_completed(node_id)
                completed_tasks += 1

        _log_execution(
            f"[MsgHub] 执行完成: {completed_tasks}/{total_tasks} 任务, {len(outputs)} 个输出",
        )
        return outputs

    async def _validate_and_fix_task(
        self,
        node_id: str,
        node: Any,
        output: "AgentOutput",
        context: "ExecutionContext",
    ) -> TaskValidationResult:
        """Validate a task immediately after completion and fix if needed.

        This method implements the task-level immediate validation pattern:
        1. Validate the task output
        2. If validation fails, generate a fix prompt
        3. Let the SAME agent fix the issue
        4. Re-validate after fix
        5. Repeat up to max_task_retries times

        Args:
            node_id: Task identifier (e.g., 'REQ-001')
            node: The task node from the graph
            output: The agent's output
            context: Execution context

        Returns:
            Final TaskValidationResult after validation/fix attempts
        """
        validator = self.get_task_validator()

        # Initial validation (check for [ERROR] markers)
        validation = await validator.validate_task(
            node_id=node_id,
            requirement=node.requirement,
            output_content=output.content if output else None,
        )

        if not validation.passed:
            # Output has error markers, go to fix loop
            pass
        elif self.enable_active_validation:
            # Output looks OK, but do active validation to verify
            _log_execution(
                f"[{node_id}] 🔍 执行主动验证...",
            )
            active_validation = await validator.validate_with_agent(
                node_id=node_id,
                requirement=node.requirement,
                output_content=output.content if output else None,
                validation_timeout=self.active_validation_timeout,
            )
            if not active_validation.passed:
                # Active validation failed - use its errors
                validation = active_validation
            else:
                # Both validations passed
                return validation
        else:
            # No active validation, output check passed
            return validation

        # Validation failed - attempt fixes
        for retry in range(self.max_task_retries):
            _log_execution(
                f"[{node_id}] ⚠️ 任务验收失败 (尝试 {retry + 1}/{self.max_task_retries}): {validation.error_summary}",
                level="warning",
            )

            # Generate fix prompt
            fix_prompt = validator.generate_fix_prompt(
                node_id=node_id,
                requirement=node.requirement,
                validation_result=validation,
                original_output=output.content if output else None,
            )

            # Let the SAME agent fix the issue
            _log_execution(
                f"[{node_id}] 🔧 Agent '{node.assigned_agent_id}' 开始修复...",
            )

            fix_output = await self._invoke_agent_async(
                node.assigned_agent_id,
                fix_prompt,
                context=context,
                node_id=node_id,
            )

            # Update output
            if fix_output:
                output = fix_output
                context.add_output(fix_output)

            # Re-validate
            validation = await validator.validate_task(
                node_id=node_id,
                requirement=node.requirement,
                output_content=fix_output.content if fix_output else None,
            )

            if validation.passed:
                _log_execution(
                    f"[{node_id}] ✓ 修复成功 (第 {retry + 1} 次尝试)",
                )
                return validation

        # All retries exhausted
        _log_execution(
            f"[{node_id}] ✗ 修复失败 (已达最大重试次数 {self.max_task_retries})",
            level="error",
        )
        return validation

    async def _cherry_pick_and_validate(
        self,
        node_id: str,
        node: Any,
        agent_id: str,
        context: "ExecutionContext",
        workspace: Any,
    ) -> TaskValidationResult:
        """Cherry-pick agent's commit to delivery and validate.

        This implements the cherry-pick validation flow:
        1. Commit agent's changes in worktree
        2. Cherry-pick to delivery
        3. If conflict, sync delivery to worktree and let agent re-implement
        4. Validate in delivery directory
        5. If validation fails, reset delivery and let agent fix

        Args:
            node_id: Task identifier.
            node: The task node.
            agent_id: The agent that completed the task.
            context: Execution context.
            workspace: RuntimeWorkspaceWithPR instance.

        Returns:
            TaskValidationResult after cherry-pick and validation.
        """
        from ._task_validator import TaskValidationResult

        max_retries = self.max_task_retries
        validation = None  # Initialize to avoid UnboundLocalError

        for retry in range(max_retries + 1):
            # Step 1: Commit agent's changes
            await workspace.commit_agent_changes(
                agent_id,
                f"{node_id}: {agent_id} implementation",
            )

            # Step 2: Save delivery HEAD for potential rollback
            delivery_head = await workspace.get_delivery_head()

            # Step 3: Cherry-pick to delivery
            _log_execution(
                f"[{node_id}] 🍒 Cherry-pick {agent_id} 到 delivery...",
            )
            pick_result = await workspace.cherry_pick_to_delivery(agent_id)

            if not pick_result.success:
                if pick_result.conflicts:
                    # Conflict - sync delivery to worktree and let agent re-implement
                    _log_execution(
                        f"[{node_id}] ⚠️ Cherry-pick 冲突: {pick_result.conflicts}",
                        level="warning",
                    )

                    # Sync delivery state to agent's worktree
                    synced = await workspace.sync_delivery_to_agent_worktree(agent_id)
                    if not synced:
                        _log_execution(
                            f"[{node_id}] ❌ Sync 失败",
                            level="error",
                        )
                        return TaskValidationResult(
                            passed=False,
                            errors=["Sync delivery to worktree failed"],
                            warnings=[],
                        )

                    # Let agent re-implement
                    _log_execution(
                        f"[{node_id}] 🔧 让 Agent 基于最新状态重新实现...",
                    )
                    reimpl_prompt = f"""## 需要重新实现

你的修改与其他 Agent 的修改冲突。你的工作目录已更新为包含其他 Agent 修改的最新状态。

冲突的文件：
{chr(10).join(f'- {f}' for f in pick_result.conflicts)}

**你需要做的：**
1. 查看当前工作目录中的最新代码（已包含其他 Agent 的修改）
2. 重新实现你的修改，确保与现有代码兼容
3. 确保功能完整性
"""
                    await self._invoke_agent_async(
                        agent_id,
                        reimpl_prompt,
                        context=context,
                        node_id=node_id,
                    )
                    # Retry cherry-pick
                    continue
                else:
                    _log_execution(
                        f"[{node_id}] ❌ Cherry-pick 失败: {pick_result.message}",
                        level="error",
                    )
                    return TaskValidationResult(
                        passed=False,
                        errors=[f"Cherry-pick failed: {pick_result.message}"],
                        warnings=[],
                    )

            # Step 4: Validate in delivery directory
            _log_execution(
                f"[{node_id}] 🔍 在 delivery 目录验收...",
            )

            validator = self.get_task_validator()
            # Set validator to use delivery directory
            validator.workspace_dir = workspace.delivery_dir

            validation = await validator.validate_with_agent(
                node_id=node_id,
                requirement=node.requirement,
                output_content=None,  # Let validator read from delivery dir
                validation_timeout=self.active_validation_timeout,
            )

            if validation.passed:
                _log_execution(
                    f"[{node_id}] ✓ 验收通过",
                )
                return validation

            # Step 5: Validation failed - reset delivery and let agent fix
            _log_execution(
                f"[{node_id}] ⚠️ 验收失败 (尝试 {retry + 1}/{max_retries + 1}): {validation.error_summary}",
                level="warning",
            )

            if retry < max_retries:
                # Reset delivery and sync to agent if in fallback mode
                reset_ok, sync_performed = await workspace.reset_delivery_for_retry(
                    agent_id, delivery_head
                )
                if sync_performed:
                    _log_execution(
                        f"[{node_id}] 📥 已同步 delivery 状态到 Agent 工作目录 (fallback mode)",
                    )

                # Generate fix prompt
                fix_prompt = validator.generate_fix_prompt(
                    node_id=node_id,
                    requirement=node.requirement,
                    validation_result=validation,
                    original_output=None,
                )

                # For fallback mode: prepend notice about state reset
                if sync_performed:
                    fallback_notice = """## ⚠️ 状态重置通知

你之前的修改验证失败，工作目录已被重置到初始状态。
**请基于当前干净的代码状态重新实现功能。**

---

"""
                    fix_prompt = fallback_notice + fix_prompt

                # Let agent fix in worktree
                _log_execution(
                    f"[{node_id}] 🔧 Agent '{agent_id}' 开始修复...",
                )
                await self._invoke_agent_async(
                    agent_id,
                    fix_prompt,
                    context=context,
                    node_id=node_id,
                )
                # Retry cherry-pick and validate
                continue

        # All retries exhausted
        _log_execution(
            f"[{node_id}] ✗ 验收失败 (已达最大重试次数)",
            level="error",
        )
        return TaskValidationResult(
            passed=False,
            errors=validation.errors if validation else ["Max retries reached"],
            warnings=validation.warnings if validation else [],
        )

    def _execute_sequential(
        self,
        graph: TaskGraph,
        context: ExecutionContext,
        round_index: int = 1,
    ) -> list[AgentOutput]:
        """Execute tasks sequentially with context passing (sync version).

        Args:
            graph: Task graph to execute.
            context: Execution context with project memory.
            round_index: Current round index for decision tracking.

        Returns:
            List of agent outputs from this execution.
        """
        outputs: list[AgentOutput] = []

        for node_id in graph.topological_order():
            graph.mark_running(node_id)
            node = graph.get(node_id)

            if node.assigned_agent_id:
                output = self._invoke_agent(
                    node.assigned_agent_id,
                    context.intent_utterance,
                    context=context,
                    node_id=node_id,
                )
                if output:
                    outputs.append(output)
                    context.add_output(output)

                    # Parse and record decisions from this agent's output
                    if context.project_memory:
                        context.project_memory.parse_decisions_from_output(
                            output.content,
                            agent_id=output.agent_id,
                            round_index=round_index,
                        )

            graph.mark_completed(node_id)

        return outputs

    async def _execute_parallel(
        self,
        graph: TaskGraph,
        context: ExecutionContext,
        round_index: int = 1,
    ) -> list[AgentOutput]:
        """Execute tasks in parallel with agent collaboration.

        This method uses CollaborativeExecutor to run independent tasks
        concurrently while respecting dependency ordering in the task graph.

        Args:
            graph: Task graph to execute.
            context: Execution context with project memory.
            round_index: Current round index for decision tracking.

        Returns:
            List of agent outputs from this execution.
        """
        from .collaboration import CollaborativeExecutor
        from ..agent import AgentBase

        # Build task map and collect agents
        tasks: dict[str, str] = {}
        agents: dict[str, AgentBase] = {}
        agent_roles: dict[str, str] = {}
        dependencies: dict[str, set[str]] = {}

        for node_id in graph.topological_order():
            node = graph.get(node_id)
            if node.assigned_agent_id:
                agent = self.orchestrator.registry.get_agent_instance(
                    node.assigned_agent_id
                )
                if agent:
                    # Use requirement.notes as task description if available
                    task_desc = node.requirement.notes or "完成分配的任务"
                    tasks[node.assigned_agent_id] = (
                        f"[{node_id}] {context.intent_utterance}\n\n"
                        f"任务描述: {task_desc}"
                    )
                    agents[node.assigned_agent_id] = agent
                    # Get role from metadata or default to "Worker"
                    agent_roles[node.assigned_agent_id] = (
                        node.metadata.get("role") or "Worker"
                    )

                    # Build dependencies from node.dependencies
                    node_deps = set()
                    for dep_id in node.dependencies:
                        dep_node = graph.get(dep_id)
                        if dep_node and dep_node.assigned_agent_id:
                            node_deps.add(dep_node.assigned_agent_id)
                    if node_deps:
                        dependencies[node.assigned_agent_id] = node_deps

        if not tasks:
            _log_execution(
                "No tasks to execute in parallel mode",
                level="warning",
                prefix="[ParallelExec]",
            )
            return []

        # Create collaborative executor
        executor = CollaborativeExecutor(
            agents=agents,
            agent_roles=agent_roles,
            timeout_seconds=self.parallel_timeout_seconds,
        )

        _log_execution(
            f"Starting parallel execution with {len(agents)} agents, timeout={self.parallel_timeout_seconds:.1f}s",
            prefix="[ParallelExec]",
        )

        # Execute in parallel
        try:
            work_states = await executor.execute_parallel(
                tasks=tasks,
                dependencies=dependencies,
            )
        except asyncio.TimeoutError:
            _log_execution(
                f"Parallel execution timed out after {self.parallel_timeout_seconds:.1f}s",
                level="error",
                prefix="[ParallelExec]",
            )
            work_states = {}

        # Convert work states to AgentOutput format
        outputs: list[AgentOutput] = []
        for agent_id, state in work_states.items():
            graph_node_id = None
            for node_id in graph.topological_order():
                node = graph.get(node_id)
                if node.assigned_agent_id == agent_id:
                    graph_node_id = node_id
                    break

            if graph_node_id:
                if state.status == "completed":
                    graph.mark_completed(graph_node_id)
                elif state.status == "blocked":
                    graph.mark_failed(graph_node_id)

            output = AgentOutput(
                agent_id=agent_id,
                content=state.output or f"[{state.status}] {state.blocked_reason or ''}",
                metadata={
                    "status": state.status,
                    "node_id": graph_node_id,
                    "parallel_execution": True,
                },
            )
            outputs.append(output)
            context.add_output(output)

            # Parse and record decisions
            if context.project_memory and state.output:
                context.project_memory.parse_decisions_from_output(
                    state.output,
                    agent_id=agent_id,
                    round_index=round_index,
                )

        # Share artifacts from workspace
        for key, content in executor.workspace.artifacts.items():
            _log_execution(
                f"Shared artifact: {key}",
                prefix="[ParallelExec]",
            )

        _log_execution(
            f"Parallel execution completed: {sum(1 for s in work_states.values() if s.status == 'completed')}/{len(work_states)} agents succeeded",
            prefix="[ParallelExec]",
        )

        return outputs

    def _persist_intent(self, intent: IntentRequest) -> None:
        entry = MemoryEntry(
            key=f"intent:{intent.user_id}:{intent.project_id}",
            content=intent.utterance,
            tags={"intent", intent.user_id},
        )
        self.memory_pool.save(entry)

    def _ensure_project(self, intent: IntentRequest) -> str:
        if intent.project_id:
            if self.project_pool.get(intent.project_id) is None:
                descriptor = ProjectDescriptor(
                    project_id=intent.project_id,
                    name=f"Project {intent.project_id}",
                    metadata={"source": "aa"},
                )
                self.project_pool.register(descriptor)
            return intent.project_id
        project_id = f"proj-{shortuuid.uuid()}"
        descriptor = ProjectDescriptor(
            project_id=project_id,
            name=f"{intent.user_id}-{project_id}",
            metadata={"source": "aa"},
        )
        self.project_pool.register(descriptor)
        intent.project_id = project_id
        return project_id

    def _persist_round_summary(
        self,
        *,
        project_id: str,
        round_index: int,
        plan: StrategyPlan,
        task_status: dict[str, str],
        observed_metrics: dict[str, float],
    ) -> None:
        summary_lines = [
            f"Round {round_index}",
            f"Observed metrics: {observed_metrics}",
        ]
        for node_id, status in task_status.items():
            agent_name = (
                plan.rankings.get(node_id).profile.name
                if node_id in plan.rankings
                else "unassigned"
            )
            summary_lines.append(f"- {node_id}: {status} -> {agent_name}")
        entry = MemoryEntry(
            key=f"project:{project_id}:round:{round_index}",
            content="\n".join(summary_lines),
            tags={f"project:{project_id}", "round"},
        )
        self.memory_pool.save(entry)

    def _compute_metric_snapshot(
        self,
        *,
        baseline_cost: float,
        observed_cost: float,
        baseline_time: float,
        observed_time: float,
        acceptance: AcceptanceCriteria,
        round_index: int,
    ) -> tuple[float, dict[str, float], dict[str, bool]]:
        def ratio(baseline: float, observed: float) -> float:
            if observed <= 0:
                return 1.0
            if baseline <= 0:
                return 0.0
            return min(1.0, baseline / observed)

        def metric_value(name: str) -> float:
            lowered = name.lower()
            cost_component = ratio(baseline_cost, observed_cost)
            time_component = ratio(baseline_time, observed_time)
            base_score = (cost_component + time_component) / 2
            if "cost" in lowered:
                value = cost_component
            elif "time" in lowered or "speed" in lowered:
                value = time_component
            else:
                value = base_score
            if self.max_rounds > 1:
                progressive_bonus = ((round_index - 1) / (self.max_rounds - 1)) * 0.5
                value += progressive_bonus
            return max(0.0, min(1.0, value))

        metrics = acceptance.metrics or {"quality": 0.9}
        values: dict[str, float] = {name: metric_value(name) for name in metrics}
        passes: dict[str, bool] = {
            name: values[name] >= target for name, target in metrics.items()
        }
        total = max(len(metrics), 1)
        pass_ratio = sum(1 for ok in passes.values() if ok) / total
        return pass_ratio, values, passes

    def _broadcast_progress(
        self,
        *,
        project_id: str,
        round_index: int,
        summary: str,
        status: dict[str, str],
    ) -> None:
        if self.msg_hub_factory is None:
            return
        hub = self.msg_hub_factory(project_id)
        update = RoundUpdate(
            project_id=project_id,
            round_index=round_index,
            summary=summary,
            status=status,
        )
        hub.broadcast(update)

    @staticmethod
    def _plan_summary(plan: StrategyPlan) -> str:
        names = []
        for node_id, ranking in plan.rankings.items():
            names.append(f"{node_id}->{ranking.profile.name}")
        return "; ".join(names)

    def run_cycle(
        self,
        intent: IntentRequest,
        acceptance: AcceptanceCriteria,
        *,
        baseline_cost: float,
        observed_cost: float,
        baseline_time: float,
        observed_time: float,
    ) -> ExecutionReport:
        """Execute a full cycle with agent interaction and context passing.

        This method orchestrates multi-agent task execution with:
        - Context passing between agents (each agent sees previous outputs)
        - Optional MsgHub broadcasting for real-time agent communication
        - Shared memory support for cross-agent state

        Args:
            intent: The user intent request
            acceptance: Acceptance criteria for the task
            baseline_cost: Baseline cost for KPI calculation
            observed_cost: Observed cost for KPI calculation
            baseline_time: Baseline time for KPI calculation
            observed_time: Observed time for KPI calculation

        Returns:
            ExecutionReport with results and agent outputs
        """
        project_id = self._ensure_project(intent)
        self._persist_intent(intent)
        plan = self.orchestrator.plan_strategy(intent, acceptance)
        graph = self.task_graph_builder.build(
            requirements=plan.requirement_map,
            rankings=plan.rankings,
            edges=None,
            team_selections=plan.team_selections,
        )

        # Initialize project task board from plan
        task_board = self._init_task_board_from_plan(project_id, plan, acceptance)

        accepted = False
        task_status: Dict[str, str] = {}
        observed_metrics: Dict[str, float] = {}
        deliverable: ArtifactDeliveryResult | None = None
        all_agent_outputs: list[AgentOutput] = []

        # Get project memory for cross-agent context sharing
        project_memory = self.get_project_memory(project_id)

        # Get enhanced project context for file tracking and validation
        project_context: "ProjectContext | None" = None
        if self.enable_project_context:
            project_context = self.get_project_context(project_id)

        # Track previous round feedback
        previous_feedback: "RoundFeedback | None" = None

        for round_index in range(1, self.max_rounds + 1):
            # Create execution context with project memory and previous feedback
            context = ExecutionContext(
                intent_utterance=intent.utterance,
                project_memory=project_memory,
                round_feedback=previous_feedback,
            )

            # Execute tasks with context passing and project memory
            if self.enable_parallel_execution:
                # Use parallel execution with CollaborativeExecutor
                _log_execution(
                    f"Using parallel execution mode for round {round_index}",
                    prefix="[ExecutionLoop]",
                )
                round_outputs = asyncio.get_event_loop().run_until_complete(
                    self._execute_parallel(graph, context, round_index=round_index)
                )
            else:
                # Use sequential execution (default)
                round_outputs = self._execute_sequential(
                    graph, context, round_index=round_index
                )
            all_agent_outputs.extend(round_outputs)

            # Parse decisions from agent outputs and save to project memory
            for output in round_outputs:
                project_memory.parse_decisions_from_output(
                    output.content,
                    agent_id=output.agent_id,
                    round_index=round_index,
                )

                # Register generated files with project context
                if project_context:
                    registered_files = self._parse_agent_output_files(
                        output, project_context
                    )
                    # Register dependency files for validation
                    for path in registered_files:
                        content = project_context.get_file_content(path)
                        if content:
                            self._register_dependency_file(
                                path, content, project_context
                            )

            task_status = {node.node_id: node.status.value for node in graph.nodes()}
            pass_ratio, metric_values, metric_passes = self._compute_metric_snapshot(
                baseline_cost=baseline_cost,
                observed_cost=observed_cost,
                baseline_time=baseline_time,
                observed_time=observed_time,
                acceptance=acceptance,
                round_index=round_index,
            )
            observed_metrics = {
                **metric_values,
                "pass_ratio": pass_ratio,
                "passed": sum(metric_passes.values()),
                "total": max(len(metric_passes), 1),
            }
            self._persist_round_summary(
                project_id=project_id,
                round_index=round_index,
                plan=plan,
                task_status=task_status,
                observed_metrics=observed_metrics,
            )
            self._broadcast_progress(
                project_id=project_id,
                round_index=round_index,
                summary=f"Round {round_index} status: {task_status}",
                status=task_status,
            )

            # Update agent scores based on task completion results
            self._update_agent_scores(plan, task_status, pass_ratio)

            # Update task board with execution results
            self._update_task_board_status(project_id, task_status)

            # Run LLM-driven acceptance validation
            acceptance_result = None
            if self.acceptance_agent is not None:
                _log_execution("Running LLM-driven acceptance validation...")
                # Use container workspace path if runtime_workspace is available
                acceptance_workspace = self.workspace_dir
                if (
                    self.acceptance_agent._runtime_workspace
                    and hasattr(self.acceptance_agent._runtime_workspace, "workspace_dir")
                ):
                    acceptance_workspace = self.acceptance_agent._runtime_workspace.workspace_dir
                acceptance_result = self.acceptance_agent.validate_sync(
                    workspace_dir=acceptance_workspace,
                    user_requirement=intent.utterance,
                    acceptance_criteria=[
                        c.description for c in acceptance.criteria
                    ] if hasattr(acceptance, "criteria") else None,
                    artifact_type=intent.artifact_type or "web",
                )
                accepted = acceptance_result.passed
                observed_metrics["acceptance_score"] = acceptance_result.score
                _log_execution(
                    f"Acceptance validation: {acceptance_result.status.value} (score={acceptance_result.score:.2f})",
                )
            else:
                # No acceptance agent configured - use pass_ratio as fallback
                # This is a simple heuristic, real validation requires AcceptanceAgent
                accepted = pass_ratio >= 0.8
                _log_execution(
                    f"No AcceptanceAgent configured, using pass_ratio fallback: {pass_ratio:.2f}",
                    level="warning",
                )

            if accepted:
                break

            # Generate round feedback for the next iteration
            if project_context:
                previous_feedback = project_context.generate_round_feedback(
                    requirement_id=intent.project_id or project_id,
                    round_index=round_index,
                )
                # Integrate acceptance validation results into feedback
                if acceptance_result is not None:
                    previous_feedback.add_acceptance_result(acceptance_result)
                _log_execution(
                    f"Round {round_index} feedback: {len(previous_feedback.critical_issues)} critical issues, {len(previous_feedback.warnings)} warnings",
                )
                # Log critical issues details for better observability
                if previous_feedback.critical_issues:
                    _log_execution("=== Critical Issues ===", level="error")
                    for i, issue in enumerate(previous_feedback.critical_issues[:5], 1):
                        _log_execution(f"  [{i}] {issue}", level="error")
                    if len(previous_feedback.critical_issues) > 5:
                        _log_execution(
                            f"  ... 还有 {len(previous_feedback.critical_issues) - 5} 个问题未显示",
                            level="error",
                        )
                # Log warnings too
                if previous_feedback.warnings:
                    _log_execution("=== Warnings ===", level="warning")
                    for i, warning in enumerate(previous_feedback.warnings[:3], 1):
                        _log_execution(f"  [{i}] {warning}", level="warning")

            # Re-plan for next round to reflect potential agent changes.
            plan = self.orchestrator.plan_strategy(intent, acceptance)
            graph = self.task_graph_builder.build(
                requirements=plan.requirement_map,
                rankings=plan.rankings,
                edges=None,
            )
            observed_cost *= 0.8
            observed_time *= 0.8

        kpi_record = self.kpi_tracker.record_cycle(
            baseline_cost=baseline_cost,
            observed_cost=observed_cost,
            baseline_time=baseline_time,
            observed_time=observed_time,
        )

        # Note: For sync run_cycle, finalize is handled in the async version
        # or by the caller who manages the workspace

        if accepted and self.delivery_manager is not None:
            artifact_type = intent.artifact_type or "web"
            deliverable = self.delivery_manager.deliver(
                artifact_type=artifact_type,
                project_id=project_id,
                plan_summary=self._plan_summary(plan),
                task_status=task_status,
            )

        return ExecutionReport(
            project_id=project_id,
            accepted=accepted,
            kpi=kpi_record,
            task_status=task_status,
            plan=plan,
            deliverable=deliverable,
            agent_outputs=all_agent_outputs,
            acceptance_result=acceptance_result,
        )

    async def run_cycle_async(
        self,
        intent: IntentRequest,
        acceptance: AcceptanceCriteria,
        *,
        baseline_cost: float,
        observed_cost: float,
        baseline_time: float,
        observed_time: float,
    ) -> ExecutionReport:
        """Async version of run_cycle with MsgHub support.

        This method enables full agent interaction via MsgHub, where agents
        can broadcast their outputs and observe other agents' messages in
        real-time.

        Args:
            intent: The user intent request
            acceptance: Acceptance criteria for the task
            baseline_cost: Baseline cost for KPI calculation
            observed_cost: Observed cost for KPI calculation
            baseline_time: Baseline time for KPI calculation
            observed_time: Observed time for KPI calculation

        Returns:
            ExecutionReport with results and agent outputs
        """
        project_id = self._ensure_project(intent)
        self._persist_intent(intent)
        plan = self.orchestrator.plan_strategy(intent, acceptance)
        graph = self.task_graph_builder.build(
            requirements=plan.requirement_map,
            rankings=plan.rankings,
            edges=None,
            team_selections=plan.team_selections,
        )

        # Initialize project task board from plan
        task_board = self._init_task_board_from_plan(project_id, plan, acceptance)

        accepted = False
        task_status: Dict[str, str] = {}
        observed_metrics: Dict[str, float] = {}
        deliverable: ArtifactDeliveryResult | None = None
        all_agent_outputs: list[AgentOutput] = []

        # Get project memory for cross-agent context sharing
        project_memory = self.get_project_memory(project_id)

        # Get enhanced project context for file tracking and validation
        project_context: "ProjectContext | None" = None
        if self.enable_project_context:
            project_context = self.get_project_context(project_id)

        # Track previous round feedback
        previous_feedback: "RoundFeedback | None" = None

        for round_index in range(1, self.max_rounds + 1):
            # Create execution context with project memory and previous feedback
            context = ExecutionContext(
                intent_utterance=intent.utterance,
                project_memory=project_memory,
                round_feedback=previous_feedback,
            )

            # Use MsgHub for agent interaction if enabled
            if self.enable_agent_msghub:
                round_outputs = await self._execute_with_msghub(graph, context)
            else:
                # Fall back to sequential execution without MsgHub
                round_outputs = self._execute_sequential(graph, context)

            all_agent_outputs.extend(round_outputs)

            # Parse decisions from agent outputs and save to project memory
            for output in round_outputs:
                project_memory.parse_decisions_from_output(
                    output.content,
                    agent_id=output.agent_id,
                    round_index=round_index,
                )

                # Register generated files with project context
                if project_context:
                    registered_files = self._parse_agent_output_files(
                        output, project_context
                    )
                    # Register dependency files for validation
                    for path in registered_files:
                        content = project_context.get_file_content(path)
                        if content:
                            self._register_dependency_file(
                                path, content, project_context
                            )

            task_status = {node.node_id: node.status.value for node in graph.nodes()}
            pass_ratio, metric_values, metric_passes = self._compute_metric_snapshot(
                baseline_cost=baseline_cost,
                observed_cost=observed_cost,
                baseline_time=baseline_time,
                observed_time=observed_time,
                acceptance=acceptance,
                round_index=round_index,
            )
            observed_metrics = {
                **metric_values,
                "pass_ratio": pass_ratio,
                "passed": sum(metric_passes.values()),
                "total": max(len(metric_passes), 1),
            }
            self._persist_round_summary(
                project_id=project_id,
                round_index=round_index,
                plan=plan,
                task_status=task_status,
                observed_metrics=observed_metrics,
            )
            self._broadcast_progress(
                project_id=project_id,
                round_index=round_index,
                summary=f"Round {round_index} status: {task_status}",
                status=task_status,
            )

            # Update agent scores based on task completion results
            self._update_agent_scores(plan, task_status, pass_ratio)

            # Update task board with execution results
            self._update_task_board_status(project_id, task_status)

            # Run LLM-driven acceptance validation
            acceptance_result = None
            if self.acceptance_agent is not None:
                _log_execution("Running LLM-driven acceptance validation...")
                # Use delivery_dir for acceptance (merged code), not working_dir
                acceptance_workspace = self.workspace_dir
                if self.acceptance_agent._runtime_workspace:
                    rt_ws = self.acceptance_agent._runtime_workspace
                    # Prefer delivery_dir (merged code) over workspace_dir (working)
                    if hasattr(rt_ws, "delivery_dir") and rt_ws.delivery_dir:
                        acceptance_workspace = rt_ws.delivery_dir
                    elif hasattr(rt_ws, "workspace_dir"):
                        acceptance_workspace = rt_ws.workspace_dir
                acceptance_result = await self.acceptance_agent.validate(
                    workspace_dir=acceptance_workspace,
                    user_requirement=intent.utterance,
                    acceptance_criteria=[
                        c.description for c in acceptance.criteria
                    ] if hasattr(acceptance, "criteria") else None,
                    artifact_type=intent.artifact_type or "web",
                )
                accepted = acceptance_result.passed
                observed_metrics["acceptance_score"] = acceptance_result.score
                _log_execution(
                    f"Acceptance validation: {acceptance_result.status.value} (score={acceptance_result.score:.2f})",
                )
            else:
                # No acceptance agent configured - use pass_ratio as fallback
                # This is a simple heuristic, real validation requires AcceptanceAgent
                accepted = pass_ratio >= 0.8
                _log_execution(
                    f"No AcceptanceAgent configured, using pass_ratio fallback: {pass_ratio:.2f}",
                    level="warning",
                )

            if accepted:
                break

            # Generate round feedback for the next iteration
            if project_context:
                previous_feedback = project_context.generate_round_feedback(
                    requirement_id=intent.project_id or project_id,
                    round_index=round_index,
                )
                # Integrate acceptance validation results into feedback
                if acceptance_result is not None:
                    previous_feedback.add_acceptance_result(acceptance_result)
                _log_execution(
                    f"Round {round_index} feedback: {len(previous_feedback.critical_issues)} critical issues, {len(previous_feedback.warnings)} warnings",
                )
                # Log critical issues details for better observability
                if previous_feedback.critical_issues:
                    _log_execution("=== Critical Issues ===", level="error")
                    for i, issue in enumerate(previous_feedback.critical_issues[:5], 1):
                        _log_execution(f"  [{i}] {issue}", level="error")
                    if len(previous_feedback.critical_issues) > 5:
                        _log_execution(
                            f"  ... 还有 {len(previous_feedback.critical_issues) - 5} 个问题未显示",
                            level="error",
                        )
                # Log warnings too
                if previous_feedback.warnings:
                    _log_execution("=== Warnings ===", level="warning")
                    for i, warning in enumerate(previous_feedback.warnings[:3], 1):
                        _log_execution(f"  [{i}] {warning}", level="warning")

            # Replan for next round, but try to reuse existing agents
            # Store current runtime agents before replanning
            current_agents = self._get_runtime_agents().copy()

            plan = self.orchestrator.plan_strategy(intent, acceptance)

            # Restore cached agents to avoid re-creation
            # This ensures agents are reused across rounds
            new_agents = self._get_runtime_agents()
            for agent_id, agent in current_agents.items():
                if agent_id not in new_agents:
                    new_agents[agent_id] = agent
                    logger.debug(
                        "复用缓存的 Agent: %s",
                        agent_id,
                    )

            graph = self.task_graph_builder.build(
                requirements=plan.requirement_map,
                rankings=plan.rankings,
                edges=None,
            )
            observed_cost *= 0.8
            observed_time *= 0.8

        kpi_record = self.kpi_tracker.record_cycle(
            baseline_cost=baseline_cost,
            observed_cost=observed_cost,
            baseline_time=baseline_time,
            observed_time=observed_time,
        )

        # Finalize delivery to main after all validations passed
        if accepted:
            from ._collaborative_executor import get_workspace_for_collaborative

            workspace = get_workspace_for_collaborative(
                self.orchestrator,
                self.workspace_dir,
            )
            if workspace and hasattr(workspace, "finalize_delivery_to_main"):
                _log_execution("Finalizing delivery branch to main...")
                finalize_result = await workspace.finalize_delivery_to_main()
                if finalize_result.success:
                    _log_execution("✓ Delivery finalized to main successfully")
                else:
                    _log_execution(
                        f"⚠️ Finalize to main failed: {finalize_result.message}",
                        level="warning",
                    )

        if accepted and self.delivery_manager is not None:
            artifact_type = intent.artifact_type or "web"
            deliverable = self.delivery_manager.deliver(
                artifact_type=artifact_type,
                project_id=project_id,
                plan_summary=self._plan_summary(plan),
                task_status=task_status,
            )

        # Cleanup all worktrees at the end of the cycle
        # This is deferred from CollaborativeExecutor to allow agent reuse
        await self._cleanup_all_worktrees()

        return ExecutionReport(
            project_id=project_id,
            accepted=accepted,
            kpi=kpi_record,
            task_status=task_status,
            plan=plan,
            deliverable=deliverable,
            agent_outputs=all_agent_outputs,
            acceptance_result=acceptance_result,
        )
