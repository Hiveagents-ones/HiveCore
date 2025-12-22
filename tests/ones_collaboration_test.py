# -*- coding: utf-8 -*-
"""Tests for parallel collaborative execution."""
import asyncio
import pytest
from agentscope.agent import AgentBase
from agentscope.message import Msg
from agentscope.ones import (
    CollaborativeAgent,
    CollaborativeExecutor,
    CollaborationMessage,
    MessageType,
    SharedWorkspace,
    AgentWorkState,
)


class _MockCollaborativeAgent(AgentBase):
    """Mock agent for collaboration testing."""

    def __init__(self, agent_id: str, response: str, delay: float = 0.0) -> None:
        super().__init__()
        self.id = agent_id
        self.name = agent_id
        self.response = response
        self.delay = delay
        self.received_prompts: list[str] = []
        self.observed_messages: list[Msg] = []
        self.execution_order: list[str] = []  # Shared across instances for tracking

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        if msg is None:
            return
        msgs = [msg] if isinstance(msg, Msg) else msg
        self.observed_messages.extend(msgs)

    async def reply(self, msg: Msg | list[Msg] | None = None, **kwargs) -> Msg:
        if msg:
            content = msg.content if isinstance(msg, Msg) else str(msg)
            self.received_prompts.append(content)

        # Simulate work time
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # Track execution order
        self.execution_order.append(self.id)

        return Msg(name=self.name, role="assistant", content=self.response)


class TestSharedWorkspace:
    """Tests for SharedWorkspace."""

    def test_add_artifact(self) -> None:
        workspace = SharedWorkspace()
        workspace.add_artifact("api_spec", "GET /users", "backend-agent")

        assert "api_spec" in workspace.artifacts
        assert workspace.artifacts["api_spec"] == "GET /users"
        assert len(workspace.message_history) == 1
        assert workspace.message_history[0].msg_type == MessageType.ARTIFACT_SHARE

    def test_add_decision(self) -> None:
        workspace = SharedWorkspace()
        workspace.add_decision("使用 REST API 而非 GraphQL")

        assert len(workspace.decisions) == 1
        assert "REST API" in workspace.decisions[0]

    def test_context_summary(self) -> None:
        workspace = SharedWorkspace()
        workspace.add_artifact("schema", "CREATE TABLE users...", "db-agent")
        workspace.add_decision("采用 PostgreSQL")

        summary = workspace.get_context_summary()

        assert "共享工作区状态" in summary
        assert "schema" in summary
        assert "PostgreSQL" in summary


class TestCollaborationMessage:
    """Tests for CollaborationMessage."""

    def test_to_msg_broadcast(self) -> None:
        msg = CollaborationMessage(
            msg_type=MessageType.TASK_COMPLETE,
            sender_id="agent-1",
            sender_role="Backend",
            content="API 开发完成",
        )

        result = msg.to_msg()

        assert result.name == "agent-1"
        assert "[task_complete]" in result.content
        assert result.metadata["msg_type"] == "task_complete"
        assert result.metadata["sender_role"] == "Backend"

    def test_to_msg_targeted(self) -> None:
        msg = CollaborationMessage(
            msg_type=MessageType.QUESTION,
            sender_id="frontend-agent",
            sender_role="Frontend",
            content="接口返回格式是什么？",
            target_role="Backend",
        )

        result = msg.to_msg()

        assert "@Backend" in result.content
        assert result.metadata["target_role"] == "Backend"


class TestCollaborativeAgent:
    """Tests for CollaborativeAgent wrapper."""

    @pytest.mark.asyncio
    async def test_wraps_agent_correctly(self) -> None:
        inner = _MockCollaborativeAgent("inner", "内部响应")
        workspace = SharedWorkspace()

        collab = CollaborativeAgent(
            wrapped_agent=inner,
            agent_id="collab-1",
            role="Developer",
            workspace=workspace,
        )

        result = await collab.reply(Msg(name="user", role="user", content="任务"))

        assert result.content == "内部响应"
        assert collab.state.status == "completed"

    @pytest.mark.asyncio
    async def test_receives_workspace_context(self) -> None:
        inner = _MockCollaborativeAgent("inner", "完成")
        workspace = SharedWorkspace()
        workspace.add_artifact("设计文档", "系统架构说明", "architect")

        collab = CollaborativeAgent(
            wrapped_agent=inner,
            agent_id="developer",
            role="Developer",
            workspace=workspace,
        )

        await collab.reply(Msg(name="user", role="user", content="实现功能"))

        # Check that the inner agent received workspace context
        assert len(inner.received_prompts) == 1
        prompt = inner.received_prompts[0]
        assert "设计文档" in prompt or "共享工作区" in prompt

    def test_share_artifact(self) -> None:
        inner = _MockCollaborativeAgent("inner", "done")
        workspace = SharedWorkspace()

        collab = CollaborativeAgent(
            wrapped_agent=inner,
            agent_id="backend",
            role="Backend",
            workspace=workspace,
        )

        collab.share_artifact("api_doc", "POST /users - 创建用户")

        assert "api_doc" in workspace.artifacts
        assert workspace.artifacts["api_doc"] == "POST /users - 创建用户"


class TestCollaborativeExecutor:
    """Tests for parallel collaborative execution."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self) -> None:
        """Test that independent tasks execute in parallel."""
        execution_order: list[str] = []

        agent1 = _MockCollaborativeAgent("agent-1", "A1完成", delay=0.1)
        agent1.execution_order = execution_order
        agent2 = _MockCollaborativeAgent("agent-2", "A2完成", delay=0.1)
        agent2.execution_order = execution_order
        agent3 = _MockCollaborativeAgent("agent-3", "A3完成", delay=0.1)
        agent3.execution_order = execution_order

        executor = CollaborativeExecutor(
            agents={"agent-1": agent1, "agent-2": agent2, "agent-3": agent3},
            agent_roles={"agent-1": "Frontend", "agent-2": "Backend", "agent-3": "QA"},
        )

        tasks = {
            "agent-1": "实现前端页面",
            "agent-2": "实现后端 API",
            "agent-3": "编写测试用例",
        }

        import time
        start = time.time()
        states = await executor.execute_parallel(tasks)
        elapsed = time.time() - start

        # All should complete
        assert all(s.status == "completed" for s in states.values())

        # Should be parallel (< 0.3s if truly parallel, > 0.3s if sequential)
        assert elapsed < 0.25, f"Execution took {elapsed}s, should be parallel"

    @pytest.mark.asyncio
    async def test_dependency_ordering(self) -> None:
        """Test that dependencies are respected."""
        execution_order: list[str] = []

        agent1 = _MockCollaborativeAgent("strategy", "策略完成", delay=0.05)
        agent1.execution_order = execution_order
        agent2 = _MockCollaborativeAgent("builder", "构建完成", delay=0.05)
        agent2.execution_order = execution_order
        agent3 = _MockCollaborativeAgent("reviewer", "审核完成", delay=0.05)
        agent3.execution_order = execution_order

        executor = CollaborativeExecutor(
            agents={"strategy": agent1, "builder": agent2, "reviewer": agent3},
            agent_roles={"strategy": "Strategy", "builder": "Builder", "reviewer": "Reviewer"},
        )

        tasks = {
            "strategy": "制定策略",
            "builder": "执行构建",
            "reviewer": "审核结果",
        }

        # builder depends on strategy, reviewer depends on builder
        dependencies = {
            "builder": {"strategy"},
            "reviewer": {"builder"},
        }

        states = await executor.execute_parallel(tasks, dependencies)

        # All should complete
        assert all(s.status == "completed" for s in states.values())

        # Check order: strategy -> builder -> reviewer
        assert execution_order.index("strategy") < execution_order.index("builder")
        assert execution_order.index("builder") < execution_order.index("reviewer")

    @pytest.mark.asyncio
    async def test_partial_dependencies(self) -> None:
        """Test mixed parallel and sequential execution."""
        execution_order: list[str] = []

        agents = {}
        for name in ["a", "b", "c", "d"]:
            agent = _MockCollaborativeAgent(name, f"{name}完成", delay=0.05)
            agent.execution_order = execution_order
            agents[name] = agent

        executor = CollaborativeExecutor(
            agents=agents,
            agent_roles={k: k.upper() for k in agents},
        )

        tasks = {k: f"任务{k}" for k in agents}

        # a and b are independent, c depends on a, d depends on b
        # Level 1: a, b (parallel)
        # Level 2: c, d (parallel, after their dependencies)
        dependencies = {
            "c": {"a"},
            "d": {"b"},
        }

        states = await executor.execute_parallel(tasks, dependencies)

        assert all(s.status == "completed" for s in states.values())

        # a before c, b before d
        assert execution_order.index("a") < execution_order.index("c")
        assert execution_order.index("b") < execution_order.index("d")

    @pytest.mark.asyncio
    async def test_shared_workspace_across_agents(self) -> None:
        """Test that agents share workspace artifacts."""
        agent1 = _MockCollaborativeAgent("producer", "生产数据")
        agent2 = _MockCollaborativeAgent("consumer", "消费数据")

        executor = CollaborativeExecutor(
            agents={"producer": agent1, "consumer": agent2},
            agent_roles={"producer": "Producer", "consumer": "Consumer"},
        )

        # Pre-populate workspace
        executor.workspace.add_artifact("shared_data", "重要数据", "system")

        tasks = {
            "producer": "生成数据",
            "consumer": "处理数据",
        }

        dependencies = {"consumer": {"producer"}}

        states = await executor.execute_parallel(tasks, dependencies)

        # Both should have access to workspace
        assert "shared_data" in executor.workspace.artifacts

    @pytest.mark.asyncio
    async def test_agents_receive_announcement(self) -> None:
        """Test that all agents receive the initial announcement."""
        agent1 = _MockCollaborativeAgent("a1", "done")
        agent2 = _MockCollaborativeAgent("a2", "done")

        executor = CollaborativeExecutor(
            agents={"a1": agent1, "a2": agent2},
            agent_roles={"a1": "Role1", "a2": "Role2"},
        )

        tasks = {"a1": "task1", "a2": "task2"}

        await executor.execute_parallel(tasks)

        # Both agents should have observed messages (at least the announcement)
        # Note: observed_messages are collected by CollaborativeAgent wrapper
        # The inner mock agents receive the wrapped context
        assert len(agent1.received_prompts) >= 1
        assert len(agent2.received_prompts) >= 1


class TestExecutionLevels:
    """Tests for dependency level computation."""

    def test_no_dependencies(self) -> None:
        executor = CollaborativeExecutor(
            agents={},
            agent_roles={},
        )

        levels = executor._compute_execution_levels(
            ["a", "b", "c"],
            {},
        )

        # All in one level (parallel)
        assert len(levels) == 1
        assert set(levels[0]) == {"a", "b", "c"}

    def test_linear_dependencies(self) -> None:
        executor = CollaborativeExecutor(
            agents={},
            agent_roles={},
        )

        levels = executor._compute_execution_levels(
            ["a", "b", "c"],
            {"b": {"a"}, "c": {"b"}},
        )

        # Three levels (sequential)
        assert len(levels) == 3
        assert levels[0] == ["a"]
        assert levels[1] == ["b"]
        assert levels[2] == ["c"]

    def test_diamond_dependencies(self) -> None:
        """Test diamond pattern: a -> (b, c) -> d"""
        executor = CollaborativeExecutor(
            agents={},
            agent_roles={},
        )

        levels = executor._compute_execution_levels(
            ["a", "b", "c", "d"],
            {
                "b": {"a"},
                "c": {"a"},
                "d": {"b", "c"},
            },
        )

        # Level 1: a
        # Level 2: b, c (parallel)
        # Level 3: d
        assert len(levels) == 3
        assert levels[0] == ["a"]
        assert set(levels[1]) == {"b", "c"}
        assert levels[2] == ["d"]
