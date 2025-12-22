# -*- coding: utf-8 -*-
"""Parallel collaborative execution with agent-to-agent communication.

This module implements a collaborative execution model where:
1. Agents work in parallel on their assigned tasks
2. Agents can request assistance from other agents when blocked
3. Communication happens through a shared message hub
4. A coordinator manages the collaboration protocol
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Any

from ..message import Msg
from ..agent import AgentBase
from ..pipeline import MsgHub


class MessageType(str, Enum):
    """Types of collaboration messages."""

    TASK_START = "task_start"  # Agent starts working on a task
    TASK_PROGRESS = "task_progress"  # Progress update
    TASK_COMPLETE = "task_complete"  # Task completed successfully
    TASK_BLOCKED = "task_blocked"  # Agent is blocked, needs help
    ASSIST_REQUEST = "assist_request"  # Request for assistance
    ASSIST_RESPONSE = "assist_response"  # Response to assistance request
    QUESTION = "question"  # Question to other agents
    ANSWER = "answer"  # Answer to a question
    ARTIFACT_SHARE = "artifact_share"  # Sharing an artifact/deliverable


@dataclass
class CollaborationMessage:
    """A structured message for agent-to-agent communication."""

    msg_type: MessageType
    sender_id: str
    sender_role: str
    content: str
    target_role: str | None = None  # None means broadcast to all
    target_agent_id: str | None = None  # Specific agent target
    artifact_key: str | None = None  # For artifact sharing
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_msg(self) -> Msg:
        """Convert to AgentScope Msg format."""
        return Msg(
            name=self.sender_id,
            role="assistant",
            content=self._format_content(),
            metadata={
                "msg_type": self.msg_type.value,
                "sender_role": self.sender_role,
                "target_role": self.target_role,
                "target_agent_id": self.target_agent_id,
                "artifact_key": self.artifact_key,
                "timestamp": self.timestamp.isoformat(),
                **self.metadata,
            },
        )

    def _format_content(self) -> str:
        """Format message content for display."""
        prefix = f"[{self.msg_type.value}] "
        if self.target_role:
            prefix += f"@{self.target_role}: "
        elif self.target_agent_id:
            prefix += f"@{self.target_agent_id}: "
        return prefix + self.content


@dataclass
class AgentWorkState:
    """Tracks the working state of an agent."""

    agent_id: str
    role: str
    status: str = "idle"  # idle, working, blocked, completed
    current_task: str | None = None
    output: str | None = None
    blocked_reason: str | None = None
    pending_questions: list[CollaborationMessage] = field(default_factory=list)
    received_answers: list[CollaborationMessage] = field(default_factory=list)


@dataclass
class SharedWorkspace:
    """Shared workspace for agent collaboration."""

    artifacts: dict[str, str] = field(default_factory=dict)  # key -> content
    decisions: list[str] = field(default_factory=list)
    open_questions: list[CollaborationMessage] = field(default_factory=list)
    message_history: list[CollaborationMessage] = field(default_factory=list)

    def add_artifact(self, key: str, content: str, sender_id: str) -> None:
        """Add or update an artifact."""
        self.artifacts[key] = content
        self.message_history.append(
            CollaborationMessage(
                msg_type=MessageType.ARTIFACT_SHARE,
                sender_id=sender_id,
                sender_role="",
                content=f"共享产物 [{key}]",
                artifact_key=key,
            )
        )

    def add_decision(self, decision: str) -> None:
        """Record a decision made during collaboration."""
        self.decisions.append(decision)

    def get_context_summary(self) -> str:
        """Get a summary of current workspace state."""
        lines = ["## 共享工作区状态"]

        if self.artifacts:
            lines.append("\n### 已共享产物")
            for key in self.artifacts:
                lines.append(f"- {key}")

        if self.decisions:
            lines.append("\n### 已达成决策")
            for d in self.decisions[-5:]:  # Last 5 decisions
                lines.append(f"- {d}")

        if self.open_questions:
            lines.append("\n### 待解决问题")
            for q in self.open_questions[-3:]:  # Last 3 open questions
                lines.append(f"- [{q.sender_role}] {q.content}")

        return "\n".join(lines)


class CollaborativeAgent(AgentBase):
    """Wrapper that adds collaboration capabilities to any agent."""

    def __init__(
        self,
        wrapped_agent: AgentBase,
        agent_id: str,
        role: str,
        workspace: SharedWorkspace,
        on_message: Callable[[CollaborationMessage], None] | None = None,
    ) -> None:
        super().__init__()
        self.wrapped = wrapped_agent
        self.id = agent_id
        self.name = agent_id
        self.role = role
        self.workspace = workspace
        self.on_message = on_message
        self.state = AgentWorkState(agent_id=agent_id, role=role)
        self._inbox: asyncio.Queue[CollaborationMessage] = asyncio.Queue()
        self._collaboration_enabled = True

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        """Receive and process collaboration messages."""
        if msg is None:
            return

        msgs = [msg] if isinstance(msg, Msg) else msg
        for m in msgs:
            # Check if this is a collaboration message
            if m.metadata and "msg_type" in m.metadata:
                collab_msg = self._parse_collaboration_msg(m)
                if collab_msg and self._should_process(collab_msg):
                    await self._inbox.put(collab_msg)

        # Also forward to wrapped agent
        await self.wrapped.observe(msg)

    def _parse_collaboration_msg(self, msg: Msg) -> CollaborationMessage | None:
        """Parse a Msg into CollaborationMessage."""
        try:
            return CollaborationMessage(
                msg_type=MessageType(msg.metadata.get("msg_type")),
                sender_id=msg.name,
                sender_role=msg.metadata.get("sender_role", ""),
                content=msg.content,
                target_role=msg.metadata.get("target_role"),
                target_agent_id=msg.metadata.get("target_agent_id"),
                artifact_key=msg.metadata.get("artifact_key"),
            )
        except (ValueError, KeyError):
            return None

    def _should_process(self, msg: CollaborationMessage) -> bool:
        """Check if this agent should process the message."""
        # Don't process own messages
        if msg.sender_id == self.id:
            return False

        # Process if targeted at this agent
        if msg.target_agent_id == self.id:
            return True

        # Process if targeted at this role
        if msg.target_role == self.role:
            return True

        # Process broadcasts (no specific target)
        if msg.target_role is None and msg.target_agent_id is None:
            return True

        # Process questions that might be relevant
        if msg.msg_type == MessageType.QUESTION:
            return True

        return False

    async def reply(self, msg: Msg | list[Msg] | None = None, **kwargs: Any) -> Msg:
        """Execute task with collaboration support."""
        self.state.status = "working"

        # Build context with workspace info
        context = self._build_collaborative_context(msg)

        # Check inbox for relevant messages before starting
        await self._process_inbox()

        # Execute via wrapped agent
        try:
            result = await self.wrapped.reply(
                Msg(name="system", role="user", content=context), **kwargs
            )
            self.state.status = "completed"
            self.state.output = result.get_text_content()

            # Parse and share artifacts from output
            self._parse_and_share_artifacts(self.state.output or "")

            # Broadcast completion
            await self._broadcast_completion()

            return result

        except Exception as e:
            self.state.status = "blocked"
            self.state.blocked_reason = str(e)
            raise

    def _parse_and_share_artifacts(self, output: str) -> None:
        """Parse output for [共享产物: name] markers and add to workspace."""
        import re

        # Pattern: [共享产物: name]\ncontent (until next [共享产物 or section header)
        # More permissive pattern that captures content including [ characters
        pattern = r'\[共享产物:\s*([^\]]+)\]\s*\n(.*?)(?=\n\[共享产物:|\n\[需要协助:|\n###|\n##|\Z)'
        matches = re.findall(pattern, output, re.DOTALL)

        for name, content in matches:
            name = name.strip()
            content = content.strip()
            if name and content:
                self.workspace.add_artifact(name, content, self.id)

    def _build_collaborative_context(self, msg: Msg | list[Msg] | None) -> str:
        """Build context including workspace state and pending messages."""
        lines = []

        # Original task
        if msg:
            content = msg.content if isinstance(msg, Msg) else str(msg)
            lines.append(f"## 你的任务\n{content}")

        # Workspace context
        workspace_summary = self.workspace.get_context_summary()
        if workspace_summary:
            lines.append(f"\n{workspace_summary}")

        # Relevant artifacts
        if self.workspace.artifacts:
            lines.append("\n## 可用产物详情")
            for key, content in list(self.workspace.artifacts.items())[:5]:
                lines.append(f"\n### {key}\n{content[:500]}...")

        # Received answers to questions
        if self.state.received_answers:
            lines.append("\n## 收到的回复")
            for ans in self.state.received_answers[-3:]:
                lines.append(f"- [{ans.sender_role}]: {ans.content}")

        lines.append(
            "\n## 协作指令\n"
            "- 如果需要其他角色帮助，在输出中标注: [需要协助: @角色名 问题描述]\n"
            "- 如果产出了可共享的产物，标注: [共享产物: 产物名称]\n"
            "- 完成任务后给出明确的结论"
        )

        return "\n".join(lines)

    async def _process_inbox(self) -> None:
        """Process pending messages in inbox."""
        processed = []
        while not self._inbox.empty():
            try:
                msg = self._inbox.get_nowait()
                processed.append(msg)

                if msg.msg_type == MessageType.ANSWER:
                    self.state.received_answers.append(msg)
                elif msg.msg_type == MessageType.ARTIFACT_SHARE:
                    # Artifact already in workspace
                    pass

            except asyncio.QueueEmpty:
                break

    async def _broadcast_completion(self) -> None:
        """Broadcast task completion."""
        if self.on_message:
            msg = CollaborationMessage(
                msg_type=MessageType.TASK_COMPLETE,
                sender_id=self.id,
                sender_role=self.role,
                content=f"任务完成: {self.state.output[:200] if self.state.output else '无输出'}...",
            )
            self.on_message(msg)

    async def request_assistance(
        self,
        question: str,
        target_role: str | None = None,
    ) -> None:
        """Request assistance from other agents."""
        msg = CollaborationMessage(
            msg_type=MessageType.ASSIST_REQUEST,
            sender_id=self.id,
            sender_role=self.role,
            content=question,
            target_role=target_role,
        )
        self.state.pending_questions.append(msg)
        if self.on_message:
            self.on_message(msg)

    def share_artifact(self, key: str, content: str) -> None:
        """Share an artifact with other agents."""
        self.workspace.add_artifact(key, content, self.id)


class CollaborativeExecutor:
    """Executes tasks with parallel agent collaboration.

    This executor:
    1. Groups tasks by dependency level
    2. Executes independent tasks in parallel
    3. Enables agent communication via MsgHub
    4. Handles assistance requests between agents
    """

    def __init__(
        self,
        agents: dict[str, AgentBase],
        agent_roles: dict[str, str],
        timeout_seconds: float = 300.0,
    ) -> None:
        """Initialize the collaborative executor.

        Args:
            agents: Map of agent_id -> AgentBase
            agent_roles: Map of agent_id -> role name
            timeout_seconds: Maximum execution time
        """
        self.agents = agents
        self.agent_roles = agent_roles
        self.timeout = timeout_seconds
        self.workspace = SharedWorkspace()
        self._collaborative_agents: dict[str, CollaborativeAgent] = {}
        self._message_queue: asyncio.Queue[CollaborationMessage] = asyncio.Queue()

    def _wrap_agents(self) -> list[CollaborativeAgent]:
        """Wrap all agents with collaboration capabilities."""
        wrapped = []
        for agent_id, agent in self.agents.items():
            role = self.agent_roles.get(agent_id, "Unknown")
            collab_agent = CollaborativeAgent(
                wrapped_agent=agent,
                agent_id=agent_id,
                role=role,
                workspace=self.workspace,
                on_message=lambda m: self._message_queue.put_nowait(m),
            )
            self._collaborative_agents[agent_id] = collab_agent
            wrapped.append(collab_agent)
        return wrapped

    async def execute_parallel(
        self,
        tasks: dict[str, str],  # agent_id -> task description
        dependencies: dict[str, set[str]] | None = None,  # agent_id -> depends on
    ) -> dict[str, AgentWorkState]:
        """Execute tasks in parallel with collaboration.

        Args:
            tasks: Map of agent_id -> task description
            dependencies: Optional dependency graph

        Returns:
            Map of agent_id -> final work state
        """
        dependencies = dependencies or {}
        wrapped_agents = self._wrap_agents()

        # Group tasks by dependency level
        levels = self._compute_execution_levels(tasks.keys(), dependencies)

        # Create announcement
        task_list = "\n".join(f"- {aid}: {desc[:50]}..." for aid, desc in tasks.items())
        announcement = Msg(
            name="Coordinator",
            role="system",
            content=f"## 协作任务启动\n\n参与者: {len(tasks)} 个\n\n任务列表:\n{task_list}",
        )

        # Execute within MsgHub for automatic broadcasting
        async with MsgHub(
            participants=wrapped_agents,
            announcement=announcement,
            enable_auto_broadcast=True,
        ):
            # Process message routing in background
            router_task = asyncio.create_task(self._route_messages())

            try:
                # Execute each level in parallel
                for level_agents in levels:
                    level_tasks = []
                    for agent_id in level_agents:
                        if agent_id in tasks:
                            agent = self._collaborative_agents[agent_id]
                            task_desc = tasks[agent_id]
                            level_tasks.append(
                                self._execute_agent_task(agent, task_desc)
                            )

                    if level_tasks:
                        # Execute this level in parallel with timeout
                        await asyncio.wait_for(
                            asyncio.gather(*level_tasks, return_exceptions=True),
                            timeout=self.timeout,
                        )

            finally:
                router_task.cancel()
                try:
                    await router_task
                except asyncio.CancelledError:
                    pass

        # Collect final states
        return {
            agent_id: agent.state
            for agent_id, agent in self._collaborative_agents.items()
        }

    def _compute_execution_levels(
        self,
        agent_ids: set[str] | list[str],
        dependencies: dict[str, set[str]],
    ) -> list[list[str]]:
        """Compute execution levels based on dependencies.

        Returns a list of lists, where each inner list contains agents
        that can execute in parallel.
        """
        agent_ids = set(agent_ids)
        remaining = set(agent_ids)
        completed: set[str] = set()
        levels: list[list[str]] = []

        while remaining:
            # Find agents with no pending dependencies
            ready = []
            for agent_id in remaining:
                deps = dependencies.get(agent_id, set())
                if deps.issubset(completed):
                    ready.append(agent_id)

            if not ready:
                # No progress possible, add remaining as final level
                levels.append(list(remaining))
                break

            levels.append(ready)
            for agent_id in ready:
                remaining.discard(agent_id)
                completed.add(agent_id)

        return levels

    async def _execute_agent_task(
        self,
        agent: CollaborativeAgent,
        task_desc: str,
    ) -> None:
        """Execute a single agent's task."""
        agent.state.current_task = task_desc
        agent.state.status = "working"

        try:
            msg = Msg(name="Coordinator", role="user", content=task_desc)
            await agent.reply(msg)
        except Exception as e:
            agent.state.status = "blocked"
            agent.state.blocked_reason = str(e)

    async def _route_messages(self) -> None:
        """Route collaboration messages between agents."""
        while True:
            try:
                msg = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )

                # Record in workspace
                self.workspace.message_history.append(msg)

                # Route to appropriate agents
                for agent_id, agent in self._collaborative_agents.items():
                    if agent._should_process(msg):
                        await agent._inbox.put(msg)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
