# -*- coding: utf-8 -*-
"""End-to-end integration test for the full collaborative workflow.

This test validates the complete flow:
1. User request -> AA agent selection
2. Task graph construction with dependencies
3. Parallel collaborative execution
4. Agent-to-agent communication
5. Shared workspace and artifact delivery
"""
import asyncio
import pytest
from dataclasses import dataclass
from typing import Any

from agentscope.aa import (
    AgentCapabilities,
    AgentProfile,
    Requirement,
    StaticScore,
)
from agentscope.agent import AgentBase
from agentscope.message import Msg
from agentscope.ones import (
    AcceptanceCriteria,
    AssistantOrchestrator,
    CollaborativeExecutor,
    ExecutionLoop,
    IntentRequest,
    KPITracker,
    MemoryPool,
    MessageType,
    ProjectPool,
    ResourceLibrary,
    SharedWorkspace,
    SystemRegistry,
    TaskGraphBuilder,
)


@dataclass
class AgentExecutionLog:
    """Tracks what an agent did during execution."""
    agent_id: str
    role: str
    received_context: str
    output: str
    shared_artifacts: list[str]
    questions_asked: list[str]
    answers_received: list[str]


class _SmartMockAgent(AgentBase):
    """A mock agent that simulates realistic behavior.

    - Reads context from previous agents
    - Produces structured output
    - Can share artifacts
    - Can ask questions (marked in output)
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        behavior: dict[str, Any],
    ) -> None:
        super().__init__()
        self.id = agent_id
        self.name = agent_id
        self.role = role
        self.behavior = behavior
        self.execution_log = AgentExecutionLog(
            agent_id=agent_id,
            role=role,
            received_context="",
            output="",
            shared_artifacts=[],
            questions_asked=[],
            answers_received=[],
        )
        self.observed_messages: list[Msg] = []

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        if msg is None:
            return
        msgs = [msg] if isinstance(msg, Msg) else msg
        self.observed_messages.extend(msgs)

        # Check for answers to our questions
        for m in msgs:
            if m.metadata and m.metadata.get("msg_type") == MessageType.ANSWER.value:
                self.execution_log.answers_received.append(m.content)

    async def reply(self, msg: Msg | list[Msg] | None = None, **kwargs) -> Msg:
        # Record received context
        if msg:
            content = msg.content if isinstance(msg, Msg) else str(msg)
            self.execution_log.received_context = content

        # Generate output based on behavior config
        output_parts = [f"## {self.role} 执行报告\n"]

        # Check if we have context from other agents
        if "前序任务输出" in self.execution_log.received_context:
            output_parts.append("✓ 已接收前序任务上下文\n")

        if "共享工作区" in self.execution_log.received_context:
            output_parts.append("✓ 已读取共享工作区\n")

        # Produce role-specific output
        output_parts.append(f"\n### 任务输出\n{self.behavior.get('output', '任务完成')}\n")

        # Share artifacts if configured
        if "artifacts" in self.behavior:
            output_parts.append("\n### 共享产物")
            for artifact in self.behavior["artifacts"]:
                output_parts.append(f"\n[共享产物: {artifact['name']}]\n{artifact['content']}")
                self.execution_log.shared_artifacts.append(artifact["name"])

        # Ask questions if configured
        if "questions" in self.behavior:
            output_parts.append("\n### 需要协助")
            for q in self.behavior["questions"]:
                output_parts.append(f"\n[需要协助: @{q['target']} {q['question']}]")
                self.execution_log.questions_asked.append(q["question"])

        output = "\n".join(output_parts)
        self.execution_log.output = output

        # Simulate some work time
        delay = self.behavior.get("delay", 0.05)
        await asyncio.sleep(delay)

        return Msg(name=self.name, role="assistant", content=output)


def _create_agent_profile(agent_id: str, skills: set[str]) -> AgentProfile:
    """Create an agent profile for AA selection."""
    return AgentProfile(
        agent_id=agent_id,
        name=f"Agent-{agent_id}",
        static_score=StaticScore(performance=0.9, recognition=0.85, brand_certified=1.0),
        capabilities=AgentCapabilities(
            skills=skills,
            tools={"ai", "code"},
            domains={"web", "ai"},
            languages={"zh", "en"},
            regions={"cn"},
        ),
    )


class TestFullCollaborativeFlow:
    """End-to-end tests for the complete workflow."""

    @pytest.mark.asyncio
    async def test_ai_website_project_flow(self) -> None:
        """Test a realistic AI website building project.

        Scenario: User wants to build an AI-powered product showcase website

        Flow:
        1. 策略官 - 分解需求
        2. 产品官, 体验官 - 并行定义规格
        3. 前端官, 后端官 - 并行开发
        4. 质量官 - 最终验收
        """
        # === Phase 1: Setup agents with realistic behaviors ===

        strategy_agent = _SmartMockAgent(
            "strategy-1",
            "策略官",
            {
                "output": "需求分解完成:\n- 首页展示\n- 产品列表\n- AI 推荐模块",
                "artifacts": [
                    {"name": "任务分解", "content": "1. 首页 2. 产品页 3. AI模块"},
                    {"name": "优先级", "content": "P0: 首页, P1: 产品页, P2: AI"},
                ],
                "delay": 0.05,
            },
        )

        product_agent = _SmartMockAgent(
            "product-1",
            "产品官",
            {
                "output": "产品规格:\n- 支持 10 个产品\n- AI 推荐 Top 3",
                "artifacts": [
                    {"name": "产品规格", "content": "产品数: 10, AI推荐: 3"},
                ],
                "delay": 0.05,
            },
        )

        ux_agent = _SmartMockAgent(
            "ux-1",
            "体验官",
            {
                "output": "交互设计:\n- 卡片式布局\n- 悬浮预览",
                "artifacts": [
                    {"name": "设计规范", "content": "卡片尺寸: 300x400, 间距: 20px"},
                ],
                "delay": 0.05,
            },
        )

        frontend_agent = _SmartMockAgent(
            "frontend-1",
            "前端官",
            {
                "output": "前端实现:\n- React 组件\n- Tailwind 样式",
                "questions": [
                    {"target": "后端官", "question": "API 接口格式是什么?"},
                ],
                "delay": 0.08,
            },
        )

        backend_agent = _SmartMockAgent(
            "backend-1",
            "后端官",
            {
                "output": "后端实现:\n- FastAPI 服务\n- PostgreSQL 存储",
                "artifacts": [
                    {"name": "API文档", "content": "GET /products, POST /recommend"},
                ],
                "delay": 0.08,
            },
        )

        qa_agent = _SmartMockAgent(
            "qa-1",
            "质量官",
            {
                "output": "测试报告:\n- 功能测试: 通过\n- 性能测试: 通过\n- AI 准确率: 92%",
                "delay": 0.05,
            },
        )

        # === Phase 2: Setup AA system and register agents ===

        registry = SystemRegistry()
        orchestrator = AssistantOrchestrator(system_registry=registry)

        # Register agent profiles
        agents_config = [
            ("strategy-1", {"planning", "analysis", "strategy"}),
            ("product-1", {"requirements", "specs", "product"}),
            ("ux-1", {"design", "interaction", "ux"}),
            ("frontend-1", {"react", "css", "frontend"}),
            ("backend-1", {"python", "api", "backend"}),
            ("qa-1", {"testing", "quality", "qa"}),
        ]

        profiles = []
        for agent_id, skills in agents_config:
            profile = _create_agent_profile(agent_id, skills)
            profiles.append(profile)
        orchestrator.register_candidates(profiles)

        # Register runtime agents
        orchestrator._runtime_agents = {
            "strategy-1": strategy_agent,
            "product-1": product_agent,
            "ux-1": ux_agent,
            "frontend-1": frontend_agent,
            "backend-1": backend_agent,
            "qa-1": qa_agent,
        }

        # === Phase 3: Create intent and requirements ===

        intent = IntentRequest(
            user_id="user-1",
            utterance="我需要一个 AI 驱动的产品展示网站，支持智能推荐",
            project_id="proj-ai-site",
            artifact_type="web",
            requirements={
                "task-strategy": Requirement(skills={"planning", "strategy"}),
                "task-product": Requirement(skills={"requirements", "product"}),
                "task-ux": Requirement(skills={"design", "ux"}),
                "task-frontend": Requirement(skills={"react", "frontend"}),
                "task-backend": Requirement(skills={"python", "backend"}),
                "task-qa": Requirement(skills={"testing", "qa"}),
            },
        )

        acceptance = AcceptanceCriteria(
            description="AI 网站上线",
            metrics={"quality": 0.8, "completeness": 0.9},
        )

        # === Phase 4: Plan strategy via AA ===

        plan = orchestrator.plan_strategy(intent, acceptance)

        # Verify all roles got assigned
        assert len(plan.rankings) == 6
        assert all(
            plan.rankings[f"task-{role.lower()}"].profile.agent_id
            for role in ["strategy", "product", "ux", "frontend", "backend", "qa"]
        )

        # === Phase 5: Execute with CollaborativeExecutor ===

        executor = CollaborativeExecutor(
            agents={
                "strategy-1": strategy_agent,
                "product-1": product_agent,
                "ux-1": ux_agent,
                "frontend-1": frontend_agent,
                "backend-1": backend_agent,
                "qa-1": qa_agent,
            },
            agent_roles={
                "strategy-1": "策略官",
                "product-1": "产品官",
                "ux-1": "体验官",
                "frontend-1": "前端官",
                "backend-1": "后端官",
                "qa-1": "质量官",
            },
            timeout_seconds=30.0,
        )

        tasks = {
            "strategy-1": "分解需求: " + intent.utterance,
            "product-1": "定义产品规格和 MVP 范围",
            "ux-1": "设计交互流程和视觉规范",
            "frontend-1": "实现前端页面和组件",
            "backend-1": "实现后端 API 和数据存储",
            "qa-1": "执行测试并出具验收报告",
        }

        # Define dependencies (realistic project flow)
        dependencies = {
            "product-1": {"strategy-1"},  # 产品依赖策略
            "ux-1": {"strategy-1"},       # 体验依赖策略
            "frontend-1": {"product-1", "ux-1"},  # 前端依赖产品和体验
            "backend-1": {"product-1"},   # 后端依赖产品
            "qa-1": {"frontend-1", "backend-1"},  # QA 依赖前后端
        }

        import time
        start_time = time.time()
        states = await executor.execute_parallel(tasks, dependencies)
        elapsed = time.time() - start_time

        # === Phase 6: Verify results ===

        # All agents should complete
        assert all(s.status == "completed" for s in states.values()), \
            f"Some agents failed: {[(k, v.status) for k, v in states.items() if v.status != 'completed']}"

        # Verify shared artifacts were created
        workspace = executor.workspace
        assert len(workspace.artifacts) >= 3, \
            f"Expected at least 3 artifacts, got {len(workspace.artifacts)}"

        # Verify specific artifacts
        artifact_names = set(workspace.artifacts.keys())
        assert "任务分解" in artifact_names or "产品规格" in artifact_names

        # Verify parallel execution (should be faster than sequential)
        # 6 agents * 0.05s each = 0.3s sequential
        # With parallelism: ~3 levels * 0.08s = 0.24s
        print(f"\n执行时间: {elapsed:.3f}s")
        assert elapsed < 0.5, f"Execution too slow ({elapsed}s), parallelism may not be working"

        # Verify context was passed
        # QA agent should have received context about frontend and backend
        qa_context = qa_agent.execution_log.received_context
        assert "共享工作区" in qa_context or "产物" in qa_context or "任务" in qa_context

        # Verify message history
        assert len(workspace.message_history) >= 1

        # Print execution summary
        print("\n=== 执行摘要 ===")
        print(f"总耗时: {elapsed:.3f}s")
        print(f"共享产物: {list(workspace.artifacts.keys())}")
        print(f"消息记录: {len(workspace.message_history)} 条")

        for agent_id, state in states.items():
            log = orchestrator._runtime_agents[agent_id].execution_log
            print(f"\n{log.role} ({agent_id}):")
            print(f"  - 状态: {state.status}")
            print(f"  - 共享产物: {log.shared_artifacts}")
            if log.questions_asked:
                print(f"  - 提问: {log.questions_asked}")

    @pytest.mark.asyncio
    async def test_context_passing_between_agents(self) -> None:
        """Verify that agents receive context from their dependencies."""

        producer = _SmartMockAgent(
            "producer",
            "生产者",
            {
                "output": "生产数据: [1, 2, 3, 4, 5]",
                "artifacts": [
                    {"name": "数据集", "content": "[1, 2, 3, 4, 5]"},
                ],
            },
        )

        consumer = _SmartMockAgent(
            "consumer",
            "消费者",
            {
                "output": "处理完成: 数据已转换",
            },
        )

        executor = CollaborativeExecutor(
            agents={"producer": producer, "consumer": consumer},
            agent_roles={"producer": "生产者", "consumer": "消费者"},
        )

        # Pre-add some context to workspace
        executor.workspace.add_decision("使用 JSON 格式")

        tasks = {
            "producer": "生产数据",
            "consumer": "消费并处理数据",
        }

        dependencies = {
            "consumer": {"producer"},
        }

        states = await executor.execute_parallel(tasks, dependencies)

        # Consumer should have received workspace context
        consumer_context = consumer.execution_log.received_context
        assert "共享工作区" in consumer_context or "JSON" in consumer_context or "数据集" in consumer_context

        # Workspace should have the artifact
        assert "数据集" in executor.workspace.artifacts

    @pytest.mark.asyncio
    async def test_integration_with_execution_loop(self) -> None:
        """Test that ExecutionLoop works with the new context passing."""

        agent1 = _SmartMockAgent(
            "dev-1",
            "开发者",
            {"output": "代码完成"},
        )

        registry = SystemRegistry()
        orchestrator = AssistantOrchestrator(system_registry=registry)

        profile = _create_agent_profile("dev-1", {"python"})
        orchestrator.register_candidates([profile])
        orchestrator._runtime_agents["dev-1"] = agent1

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
            utterance="实现功能",
            requirements={
                "task-1": Requirement(skills={"python"}),
            },
        )

        acceptance = AcceptanceCriteria(
            description="完成",
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
        assert len(report.agent_outputs) >= 1

    @pytest.mark.asyncio
    async def test_error_handling_in_parallel_execution(self) -> None:
        """Test that errors in one agent don't crash the entire execution."""

        class _FailingAgent(AgentBase):
            def __init__(self, agent_id: str):
                super().__init__()
                self.id = agent_id
                self.name = agent_id

            async def observe(self, msg):
                pass

            async def reply(self, msg=None, **kwargs):
                raise RuntimeError("模拟失败")

        good_agent = _SmartMockAgent("good", "Good", {"output": "成功"})
        bad_agent = _FailingAgent("bad")

        executor = CollaborativeExecutor(
            agents={"good": good_agent, "bad": bad_agent},
            agent_roles={"good": "Good", "bad": "Bad"},
        )

        tasks = {"good": "任务1", "bad": "任务2"}

        # Should not raise, but bad agent should be marked as blocked
        states = await executor.execute_parallel(tasks)

        assert states["good"].status == "completed"
        assert states["bad"].status == "blocked"
        assert "模拟失败" in states["bad"].blocked_reason


class TestParallelPerformance:
    """Performance tests for parallel execution."""

    @pytest.mark.asyncio
    async def test_speedup_with_parallelism(self) -> None:
        """Verify that parallel execution is faster than sequential."""
        import time

        # Create 4 agents with 0.1s delay each
        agents = {}
        for i in range(4):
            agents[f"agent-{i}"] = _SmartMockAgent(
                f"agent-{i}",
                f"Role-{i}",
                {"output": f"Output {i}", "delay": 0.1},
            )

        executor = CollaborativeExecutor(
            agents=agents,
            agent_roles={k: f"Role-{i}" for i, k in enumerate(agents)},
        )

        tasks = {k: f"Task for {k}" for k in agents}

        # All independent - should run in parallel
        start = time.time()
        states = await executor.execute_parallel(tasks, {})
        elapsed = time.time() - start

        # Sequential would be 4 * 0.1 = 0.4s
        # Parallel should be ~0.1s (plus overhead)
        assert elapsed < 0.2, f"Parallel execution too slow: {elapsed}s"
        assert all(s.status == "completed" for s in states.values())

        print(f"\n并行执行 4 个任务 (每个 0.1s): {elapsed:.3f}s")
        print(f"加速比: {0.4 / elapsed:.2f}x")
