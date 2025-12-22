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
from .task_board import ProjectTaskBoard, TaskItem, TaskItemStatus
from .msghub import MsgHubBroadcaster, RoundUpdate
from .artifacts import ArtifactDeliveryManager, ArtifactDeliveryResult
from ..message import Msg
from ..pipeline import MsgHub
from ..memory import MemoryBase
from .._logging import logger
import shortuuid

if TYPE_CHECKING:
    from .acceptance_agent import AcceptanceAgent, AcceptanceResult
    from .project_context import ProjectContext, RoundFeedback


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

        lines.append("\n## 指令\n请基于以上上下文完成当前任务，输出结构化结果。")
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
        # Project task boards for tracking agent-level progress
        self._project_task_boards: Dict[str, "ProjectTaskBoard"] = {}
        # Project memories for cross-agent context sharing
        self._project_memories: Dict[str, ProjectMemory] = {}
        # Enhanced project contexts for file tracking and validation
        self._project_contexts: Dict[str, "ProjectContext"] = {}

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
            logger.info(
                "Registered %d files from agent %s: %s",
                len(registered_files),
                output.agent_id,
                ", ".join(registered_files[:5]),  # Log first 5
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
            logger.info("Declared dependencies from %s", path)

    def _get_runtime_agents(self) -> dict[str, object]:
        """Get all registered runtime agents."""
        return getattr(self.orchestrator, "_runtime_agents", {})

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
        agent = self._get_runtime_agents().get(agent_id)
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
        agent = self._get_runtime_agents().get(agent_id)
        if agent is None:
            return None

        if context and node_id:
            enriched_prompt = context.build_prompt(node_id, prompt)
        else:
            enriched_prompt = prompt

        try:
            result = await agent.reply(
                Msg(name="system", role="user", content=enriched_prompt)
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
        runtime_agents = self._get_runtime_agents()

        # Collect all agents involved in this execution
        agent_instances = []
        node_agent_map: dict[str, object] = {}
        for node_id in graph.topological_order():
            node = graph.get(node_id)
            if node.assigned_agent_id and node.assigned_agent_id in runtime_agents:
                agent = runtime_agents[node.assigned_agent_id]
                if agent not in agent_instances:
                    agent_instances.append(agent)
                node_agent_map[node_id] = agent

        if not agent_instances:
            # No runtime agents, fall back to simple execution
            return outputs

        # Create announcement message with initial context
        announcement = Msg(
            name="ExecutionLoop",
            role="system",
            content=f"## 协作任务启动\n\n用户需求: {context.intent_utterance}\n\n"
            f"参与代理: {len(agent_instances)} 个\n"
            f"任务数量: {len(list(graph.nodes()))} 个",
        )

        # Execute within MsgHub context for automatic broadcasting
        async with MsgHub(
            participants=agent_instances,
            announcement=announcement,
            enable_auto_broadcast=True,
        ):
            for node_id in graph.topological_order():
                graph.mark_running(node_id)
                node = graph.get(node_id)

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

                graph.mark_completed(node_id)

        return outputs

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
                logger.info("Running LLM-driven acceptance validation...")
                acceptance_result = self.acceptance_agent.validate_sync(
                    workspace_dir=self.workspace_dir,
                    user_requirement=intent.utterance,
                    acceptance_criteria=[
                        c.description for c in acceptance.criteria
                    ] if hasattr(acceptance, "criteria") else None,
                    artifact_type=intent.artifact_type or "web",
                )
                accepted = acceptance_result.passed
                observed_metrics["acceptance_score"] = acceptance_result.score
                logger.info(
                    "Acceptance validation: %s (score=%.2f)",
                    acceptance_result.status.value,
                    acceptance_result.score,
                )
            else:
                # No acceptance agent configured - use pass_ratio as fallback
                # This is a simple heuristic, real validation requires AcceptanceAgent
                accepted = pass_ratio >= 0.8
                logger.warning(
                    "No AcceptanceAgent configured, using pass_ratio fallback: %.2f",
                    pass_ratio,
                )

            if accepted:
                break

            # Generate round feedback for the next iteration
            if project_context:
                previous_feedback = project_context.generate_round_feedback(
                    requirement_id=intent.project_id or project_id,
                    round_index=round_index,
                )
                logger.info(
                    "Round %d feedback: %d critical issues, %d warnings",
                    round_index,
                    len(previous_feedback.critical_issues),
                    len(previous_feedback.warnings),
                )

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
                logger.info("Running LLM-driven acceptance validation...")
                acceptance_result = await self.acceptance_agent.validate(
                    workspace_dir=self.workspace_dir,
                    user_requirement=intent.utterance,
                    acceptance_criteria=[
                        c.description for c in acceptance.criteria
                    ] if hasattr(acceptance, "criteria") else None,
                    artifact_type=intent.artifact_type or "web",
                )
                accepted = acceptance_result.passed
                observed_metrics["acceptance_score"] = acceptance_result.score
                logger.info(
                    "Acceptance validation: %s (score=%.2f)",
                    acceptance_result.status.value,
                    acceptance_result.score,
                )
            else:
                # No acceptance agent configured - use pass_ratio as fallback
                # This is a simple heuristic, real validation requires AcceptanceAgent
                accepted = pass_ratio >= 0.8
                logger.warning(
                    "No AcceptanceAgent configured, using pass_ratio fallback: %.2f",
                    pass_ratio,
                )

            if accepted:
                break

            # Generate round feedback for the next iteration
            if project_context:
                previous_feedback = project_context.generate_round_feedback(
                    requirement_id=intent.project_id or project_id,
                    round_index=round_index,
                )
                logger.info(
                    "Round %d feedback: %d critical issues, %d warnings",
                    round_index,
                    len(previous_feedback.critical_issues),
                    len(previous_feedback.warnings),
                )

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
