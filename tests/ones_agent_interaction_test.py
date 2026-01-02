# -*- coding: utf-8 -*-
"""Tests for agent interaction in the execution loop."""
import asyncio
import pytest
from agentscope.aa import AgentCapabilities, AgentProfile, StaticScore, Requirement
from agentscope.agent import AgentBase
from agentscope.message import Msg
from agentscope.ones import (
    AcceptanceCriteria,
    AgentOutput,
    AssistantOrchestrator,
    ExecutionContext,
    ExecutionLoop,
    IntentRequest,
    KPITracker,
    MemoryPool,
    ProjectPool,
    ResourceLibrary,
    SystemRegistry,
    TaskGraphBuilder,
)


class _MockInteractiveAgent(AgentBase):
    """Mock agent that records received prompts and returns structured responses."""

    def __init__(self, agent_id: str, response_prefix: str = "") -> None:
        super().__init__()
        self.id = agent_id
        self.name = agent_id
        self.response_prefix = response_prefix
        self.received_prompts: list[str] = []
        self.observed_messages: list[Msg] = []

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        """Record observed messages from MsgHub broadcasts."""
        if msg is None:
            return
        if isinstance(msg, list):
            self.observed_messages.extend(msg)
        else:
            self.observed_messages.append(msg)

    async def reply(self, msg: Msg | list[Msg] | None = None, **kwargs) -> Msg:
        """Record the prompt and return a structured response."""
        if msg:
            content = msg.content if isinstance(msg, Msg) else str(msg)
            self.received_prompts.append(content)
        response = f"{self.response_prefix}处理完成: {self.name} 已执行任务"
        return Msg(name=self.name, role="assistant", content=response)


def _create_mock_profile(agent_id: str, skills: set[str] | None = None) -> AgentProfile:
    """Create a mock agent profile."""
    return AgentProfile(
        agent_id=agent_id,
        name=agent_id,
        static_score=StaticScore(performance=0.9, recognition=0.85, brand_certified=1.0),
        capabilities=AgentCapabilities(
            skills=skills or {"python", "rag"},
            tools={"docker"},
            domains={"infra"},
            languages={"zh"},
            regions={"cn"},
        ),
    )


def _create_executor_with_agents(
    agents: dict[str, _MockInteractiveAgent],
    requirements: dict[str, Requirement],
) -> ExecutionLoop:
    """Create an ExecutionLoop with mock agents registered."""
    registry = SystemRegistry()
    orchestrator = AssistantOrchestrator(system_registry=registry)

    # Register agent profiles
    profiles = []
    for agent_id, agent in agents.items():
        profile = _create_mock_profile(agent_id)
        profiles.append(profile)
        orchestrator._runtime_agents[agent_id] = agent
    orchestrator.register_candidates(profiles)

    return ExecutionLoop(
        project_pool=ProjectPool(),
        memory_pool=MemoryPool(),
        resource_library=ResourceLibrary(),
        orchestrator=orchestrator,
        task_graph_builder=TaskGraphBuilder(),
        kpi_tracker=KPITracker(target_reduction=0.5),
    )


class TestExecutionContext:
    """Tests for ExecutionContext class."""

    def test_add_output(self) -> None:
        """Test adding agent outputs to context."""
        context = ExecutionContext(intent_utterance="测试需求")
        output = AgentOutput(
            agent_id="agent-1",
            node_id="task-1",
            content="任务完成",
            success=True,
        )
        context.add_output(output)

        assert len(context.agent_outputs) == 1
        assert context.agent_outputs[0].agent_id == "agent-1"

    def test_build_prompt_with_no_prior_outputs(self) -> None:
        """Test prompt building when there are no prior outputs."""
        context = ExecutionContext(intent_utterance="部署RAG服务")
        prompt = context.build_prompt("task-1", "配置Docker环境")

        assert "部署RAG服务" in prompt
        assert "task-1" in prompt
        assert "配置Docker环境" in prompt
        assert "前序任务输出" not in prompt

    def test_build_prompt_with_prior_outputs(self) -> None:
        """Test prompt building with accumulated prior outputs."""
        context = ExecutionContext(intent_utterance="部署RAG服务")
        context.add_output(AgentOutput(
            agent_id="strategy-agent",
            node_id="task-1",
            content="策略分析: 需要3个微服务",
            success=True,
        ))
        context.add_output(AgentOutput(
            agent_id="product-agent",
            node_id="task-2",
            content="产品规格: 支持10并发",
            success=True,
        ))

        prompt = context.build_prompt("task-3", "实现后端服务")

        assert "部署RAG服务" in prompt
        assert "前序任务输出" in prompt
        assert "策略分析: 需要3个微服务" in prompt
        assert "产品规格: 支持10并发" in prompt
        assert "task-3" in prompt
        assert "[✓]" in prompt  # Success marker

    def test_build_prompt_with_failed_output(self) -> None:
        """Test prompt includes failure markers for failed tasks."""
        context = ExecutionContext(intent_utterance="测试")
        context.add_output(AgentOutput(
            agent_id="agent-1",
            node_id="task-1",
            content="执行失败: 网络错误",
            success=False,
        ))

        prompt = context.build_prompt("task-2", "重试任务")

        assert "[✗]" in prompt  # Failure marker
        assert "执行失败: 网络错误" in prompt


class TestAgentContextPassing:
    """Tests for context passing between agents."""

    def test_sequential_context_passing(self) -> None:
        """Test that agents receive context from previous agents."""
        agent1 = _MockInteractiveAgent("agent-1", "第一步: ")
        agent2 = _MockInteractiveAgent("agent-2", "第二步: ")

        requirements = {
            "task-1": Requirement(skills={"python"}),
            "task-2": Requirement(skills={"python"}),
        }

        # Create orchestrator and register agents
        registry = SystemRegistry()
        orchestrator = AssistantOrchestrator(system_registry=registry)

        profile1 = _create_mock_profile("agent-1")
        profile2 = _create_mock_profile("agent-2")
        orchestrator.register_candidates([profile1, profile2])
        orchestrator._runtime_agents["agent-1"] = agent1
        orchestrator._runtime_agents["agent-2"] = agent2

        executor = ExecutionLoop(
            project_pool=ProjectPool(),
            memory_pool=MemoryPool(),
            resource_library=ResourceLibrary(),
            orchestrator=orchestrator,
            task_graph_builder=TaskGraphBuilder(),
            kpi_tracker=KPITracker(target_reduction=0.5),
        )

        intent = IntentRequest(
            user_id="u-1",
            utterance="需要部署服务",
            requirements=requirements,
        )
        acceptance = AcceptanceCriteria(
            description="Quality >= 0.8",
            metrics={"quality": 0.8},
        )

        report = executor.run_cycle(
            intent,
            acceptance,
            baseline_cost=100,
            observed_cost=20,
            baseline_time=100,
            observed_time=30,
        )

        # Verify execution completed
        assert report.accepted is True

        # Verify agent outputs are captured
        assert len(report.agent_outputs) >= 1

    def test_agent_receives_enriched_prompt(self) -> None:
        """Test that second agent receives context from first agent."""
        agent1 = _MockInteractiveAgent("agent-1", "策略: ")
        agent2 = _MockInteractiveAgent("agent-2", "实现: ")

        registry = SystemRegistry()
        orchestrator = AssistantOrchestrator(system_registry=registry)

        # Register both agents
        profile1 = _create_mock_profile("agent-1")
        orchestrator.register_candidates([profile1])
        orchestrator._runtime_agents["agent-1"] = agent1
        orchestrator._runtime_agents["agent-2"] = agent2

        executor = ExecutionLoop(
            project_pool=ProjectPool(),
            memory_pool=MemoryPool(),
            resource_library=ResourceLibrary(),
            orchestrator=orchestrator,
            task_graph_builder=TaskGraphBuilder(),
            kpi_tracker=KPITracker(target_reduction=0.5),
        )

        # Create context and execute first agent
        context = ExecutionContext(intent_utterance="部署服务")
        output1 = executor._invoke_agent(
            "agent-1",
            "部署服务",
            context=context,
            node_id="task-1",
        )

        assert output1 is not None
        context.add_output(output1)

        # Execute second agent - should receive context from first
        output2 = executor._invoke_agent(
            "agent-2",
            "部署服务",
            context=context,
            node_id="task-2",
        )

        assert output2 is not None

        # Verify second agent received enriched prompt
        assert len(agent2.received_prompts) == 1
        received_prompt = agent2.received_prompts[0]
        assert "部署服务" in received_prompt
        assert "前序任务输出" in received_prompt
        assert "task-1" in received_prompt


class TestMsgHubIntegration:
    """Tests for MsgHub integration with agent execution."""

    @pytest.mark.asyncio
    async def test_agents_observe_broadcasts(self) -> None:
        """Test that agents can observe each other's messages via MsgHub."""
        agent1 = _MockInteractiveAgent("agent-1", "A1: ")
        agent2 = _MockInteractiveAgent("agent-2", "A2: ")

        registry = SystemRegistry()
        orchestrator = AssistantOrchestrator(system_registry=registry)

        # Register agents with different skills so both get selected
        profile1 = _create_mock_profile("agent-1", skills={"strategy", "planning"})
        profile2 = _create_mock_profile("agent-2", skills={"builder", "automation"})
        orchestrator.register_candidates([profile1, profile2])
        orchestrator._runtime_agents["agent-1"] = agent1
        orchestrator._runtime_agents["agent-2"] = agent2

        executor = ExecutionLoop(
            project_pool=ProjectPool(),
            memory_pool=MemoryPool(),
            resource_library=ResourceLibrary(),
            orchestrator=orchestrator,
            task_graph_builder=TaskGraphBuilder(),
            kpi_tracker=KPITracker(target_reduction=0.5),
            enable_agent_msghub=True,
        )

        intent = IntentRequest(
            user_id="u-1",
            utterance="协作任务",
            requirements={
                "task-1": Requirement(skills={"strategy"}),
                "task-2": Requirement(skills={"builder"}),
            },
        )
        acceptance = AcceptanceCriteria(
            description="Quality >= 0.8",
            metrics={"quality": 0.8},
        )

        report = await executor.run_cycle_async(
            intent,
            acceptance,
            baseline_cost=100,
            observed_cost=20,
            baseline_time=100,
            observed_time=30,
        )

        assert report.accepted is True
        # Both agents should have been executed and received the announcement
        assert len(report.agent_outputs) == 2
        # At least one agent should have observed messages (the announcement)
        total_observed = len(agent1.observed_messages) + len(agent2.observed_messages)
        assert total_observed >= 1  # At minimum, agents receive the announcement


class TestAgentOutputCapture:
    """Tests for capturing and returning agent outputs."""

    def test_execution_report_includes_outputs(self) -> None:
        """Test that ExecutionReport contains all agent outputs."""
        agent = _MockInteractiveAgent("dev-agent", "完成: ")

        registry = SystemRegistry()
        orchestrator = AssistantOrchestrator(system_registry=registry)

        profile = _create_mock_profile("dev-agent")
        orchestrator.register_candidates([profile])
        orchestrator._runtime_agents["dev-agent"] = agent

        executor = ExecutionLoop(
            project_pool=ProjectPool(),
            memory_pool=MemoryPool(),
            resource_library=ResourceLibrary(),
            orchestrator=orchestrator,
            task_graph_builder=TaskGraphBuilder(),
            kpi_tracker=KPITracker(target_reduction=0.5),
        )

        intent = IntentRequest(
            user_id="u-1",
            utterance="单任务测试",
            requirements={
                "task-1": Requirement(skills={"python"}),
            },
        )
        acceptance = AcceptanceCriteria(
            description="Quality",
            metrics={"quality": 0.8},
        )

        report = executor.run_cycle(
            intent,
            acceptance,
            baseline_cost=100,
            observed_cost=20,
            baseline_time=100,
            observed_time=30,
        )

        assert report.accepted is True
        assert len(report.agent_outputs) == 1
        assert report.agent_outputs[0].agent_id == "dev-agent"
        assert report.agent_outputs[0].success is True
        assert "完成:" in report.agent_outputs[0].content


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing code."""

    def test_existing_tests_still_pass(self) -> None:
        """Verify that the original test case still works."""
        from agentscope.ones import ProjectDescriptor

        registry = SystemRegistry()
        orchestrator = AssistantOrchestrator(system_registry=registry)
        orchestrator.register_candidates([_create_mock_profile("dev-1")])

        intent = IntentRequest(
            user_id="u-1",
            utterance="需要部署一个RAG服务",
            project_id="proj-1",
            requirements={
                "task-1": Requirement(skills={"python", "rag"}, tools={"docker"}),
            },
        )
        acceptance = AcceptanceCriteria(
            description="Quality >= 0.8",
            metrics={"quality": 0.8},
        )

        project_pool = ProjectPool()
        project_pool.register(ProjectDescriptor(project_id="proj-1", name="RAG"))
        memory_pool = MemoryPool()
        resource_library = ResourceLibrary()
        kpi_tracker = KPITracker(target_reduction=0.5)

        executor = ExecutionLoop(
            project_pool=project_pool,
            memory_pool=memory_pool,
            resource_library=resource_library,
            orchestrator=orchestrator,
            task_graph_builder=TaskGraphBuilder(),
            kpi_tracker=kpi_tracker,
        )

        report = executor.run_cycle(
            intent,
            acceptance,
            baseline_cost=100,
            observed_cost=20,
            baseline_time=100,
            observed_time=30,
        )

        assert report.accepted is True
        assert all(status == "completed" for status in report.task_status.values())
        assert "task-1" in report.plan.decision
