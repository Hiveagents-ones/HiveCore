# -*- coding: utf-8 -*-
"""Integration style tests for the One·s modules."""
from agentscope.aa import AgentCapabilities, AgentProfile, StaticScore, RoleRequirement
from agentscope.agent import AgentBase
from agentscope.message import Msg
from agentscope.pipeline import MsgHub
from agentscope.ones import (
    AcceptanceCriteria,
    AgentScopeMsgHubBroadcaster,
    AssistantOrchestrator,
    DeliveryStack,
    ExecutionLoop,
    ExperienceLayer,
    IntentLayer,
    IntentRequest,
    KPITracker,
    MemoryPool,
    ProjectMsgHubRegistry,
    ProjectDescriptor,
    ProjectPool,
    ResourceLibrary,
    SlaLayer,
    SupervisionLayer,
    SystemMission,
    SystemProfile,
    SystemRegistry,
    TaskGraphBuilder,
    UserProfile,
    build_summary,
    OpenQuestionTracker,
    CollaborationLayer,
    ArtifactDeliveryManager,
    WebDeployAdapter,
    InMemoryMsgHub,
    RoundUpdate,
)


def _mock_agent(agent_id: str) -> AgentProfile:
    return AgentProfile(
        agent_id=agent_id,
        name=agent_id,
        role="Dev",
        static_score=StaticScore(performance=0.9, brand=0.8, recognition=0.85),
        capabilities=AgentCapabilities(
            skills={"python", "rag"},
            tools={"docker"},
            domains={"infra"},
            languages={"zh"},
            regions={"cn"},
            compliance_tags={"standard"},
            certifications={"iso"},
        ),
    )


def test_end_to_end_cycle() -> None:
    mission = SystemMission(
        name="One·s",
        value_proposition="所求即所得",
        goal_statement="Build self-driven AI delivery",
    )
    profile = SystemProfile(
        project_name="One·s",
        mission=mission,
        aa_description="AA orchestrates intent + acceptance",
    )
    registry = SystemRegistry()
    orchestrator = AssistantOrchestrator(system_registry=registry)
    orchestrator.register_candidates("Dev", [_mock_agent("dev-1")])

    intent = IntentRequest(
        user_id="u-1",
        utterance="需要部署一个RAG服务",
        project_id="proj-1",
        role_requirements={
            "task-1": RoleRequirement(role="Dev", skills={"python", "rag"}, tools={"docker"}),
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
    delivery_stack = DeliveryStack(
        intent=IntentLayer(),
        sla=SlaLayer(),
        supervision=SupervisionLayer(),
        collaboration=CollaborationLayer(),
        experience=ExperienceLayer(),
    )
    assert delivery_stack.execute("hello") == "hello"
    kpi_tracker = KPITracker(target_reduction=0.5)
    executor = ExecutionLoop(
        project_pool=project_pool,
        memory_pool=memory_pool,
        resource_library=resource_library,
        orchestrator=orchestrator,
        task_graph_builder=TaskGraphBuilder(),
        kpi_tracker=kpi_tracker,
    )

    registry.register_user(UserProfile(user_id="u-1"), "aa-u-1")
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

    question_tracker = OpenQuestionTracker()
    summary = build_summary(profile, kpi_tracker, question_tracker)
    assert summary.overview.startswith("Project One·s")
    assert summary.unresolved_questions == 0


def test_round_persistence_and_replan(tmp_path) -> None:
    registry = SystemRegistry()
    orchestrator = AssistantOrchestrator(system_registry=registry)
    orchestrator.register_candidates(
        "Dev",
        [
            AgentProfile(
                agent_id="dev-round",
                name="dev-round",
                role="Dev",
                static_score=StaticScore(performance=0.8, brand=0.7, recognition=0.75),
                capabilities=AgentCapabilities(skills={"python"}, tools={"docker"}),
            ),
        ],
    )

    intent = IntentRequest(
        user_id="u-round",
        utterance="需要多轮次交付",
        role_requirements={
            "task-1": RoleRequirement(role="Dev", skills={"python"}, tools={"docker"}),
        },
    )
    acceptance = AcceptanceCriteria(description="Quality", metrics={"quality": 0.8})

    project_pool = ProjectPool()
    memory_pool = MemoryPool()
    resource_library = ResourceLibrary()
    hub = InMemoryMsgHub()
    delivery_manager = ArtifactDeliveryManager([WebDeployAdapter(base_domain="example.com")])
    executor = ExecutionLoop(
        project_pool=project_pool,
        memory_pool=memory_pool,
        resource_library=resource_library,
        orchestrator=orchestrator,
        task_graph_builder=TaskGraphBuilder(),
        kpi_tracker=KPITracker(target_reduction=0.9),
        max_rounds=2,
        msg_hub_factory=lambda _: hub,
        delivery_manager=delivery_manager,
    )

    report = executor.run_cycle(
        intent,
        acceptance,
        baseline_cost=100,
        observed_cost=400,
        baseline_time=80,
        observed_time=200,
    )

    assert report.accepted is True
    project_id = report.project_id
    assert project_id is not None
    round_entries = memory_pool.query_by_tag(f"project:{project_id}")
    assert len(round_entries) == 2
    assert len(hub.updates) == 2
    assert report.deliverable is not None
    assert report.deliverable.artifact_type == "web"


class _RecorderAgent(AgentBase):
    """Minimal agent to capture MsgHub broadcasts."""

    def __init__(self, agent_id: str) -> None:
        super().__init__()
        self.id = agent_id
        self.name = agent_id
        self.observed_messages: list[Msg] = []

    async def observe(self, msg: Msg | list[Msg] | None) -> None:  # type: ignore[override]
        if msg is None:
            return
        if isinstance(msg, list):
            self.observed_messages.extend(msg)
        else:
            self.observed_messages.append(msg)

    async def reply(self, *args, **kwargs) -> Msg:  # type: ignore[override]
        return Msg(name=self.name, role="assistant", content="noop")


def test_agentscope_msghub_broadcaster_relays_updates() -> None:
    observers = [_RecorderAgent("dash-1"), _RecorderAgent("dash-2")]
    hub = MsgHub(participants=observers, enable_auto_broadcast=False)
    broadcaster = AgentScopeMsgHubBroadcaster(hub=hub, sender_name="hivecore")
    update = RoundUpdate(
        project_id="proj-test",
        round_index=1,
        summary="Round 1 status: {'task-1': 'completed'}",
        status={"task-1": "completed"},
    )

    broadcaster.broadcast(update)

    for agent in observers:
        assert len(agent.observed_messages) == 1
        delivered = agent.observed_messages[0]
        assert delivered.metadata["project_id"] == "proj-test"
        assert delivered.metadata["round_index"] == 1


def test_project_msghub_registry_provides_defaults() -> None:
    registry = ProjectMsgHubRegistry()
    default_hub = registry("proj-a")
    assert isinstance(default_hub, InMemoryMsgHub)
    # same project returns cached instance
    assert registry("proj-a") is default_hub

    custom = InMemoryMsgHub()
    registry.bind("proj-b", custom)
    assert registry("proj-b") is custom
