# -*- coding: utf-8 -*-
"""Scenario test: AI建站多岗位挑选流程。"""
from agentscope.aa import (
    AgentCapabilities,
    AgentProfile,
    StaticScore,
    RoleRequirement,
    AAScoringConfig,
)
from agentscope.ones import AssistantOrchestrator, AcceptanceCriteria, IntentRequest
from agentscope.ones._system import SystemRegistry


def _candidate(
    agent_id: str,
    role: str,
    performance: float,
    recognition: float,
    *,
    skills: set[str],
    tools: set[str],
    domains: set[str],
) -> AgentProfile:
    return AgentProfile(
        agent_id=agent_id,
        name=agent_id,
        role=role,
        static_score=StaticScore(performance=performance, brand=0.8, recognition=recognition),
        capabilities=AgentCapabilities(
            skills=skills,
            tools=tools,
            domains=domains,
            languages={"zh"},
            regions={"cn"},
        ),
    )


def test_ai_site_role_selection_prefers_best_fit() -> None:
    registry = SystemRegistry()
    orchestrator = AssistantOrchestrator(
        system_registry=registry,
        scoring_config=AAScoringConfig(requirement_weight=0.5),
    )

    orchestrator.register_candidates(
        "Product",
        [
            _candidate(
                "prod-vision",
                "Product",
                0.9,
                0.92,
                skills={"ai_builder", "sla", "ux"},
                tools={"figjam", "notion"},
                domains={"website"},
            ),
            _candidate(
                "prod-generic",
                "Product",
                0.95,
                0.85,
                skills={"roadmap"},
                tools={"excel"},
                domains={"generic"},
            ),
        ],
    )

    orchestrator.register_candidates(
        "Frontend",
        [
            _candidate(
                "fe-pro",
                "Frontend",
                0.9,
                0.9,
                skills={"react", "tailwind", "ai_widget"},
                tools={"storybook", "docker"},
                domains={"website"},
            ),
            _candidate(
                "fe-basic",
                "Frontend",
                0.92,
                0.88,
                skills={"vue"},
                tools={"webpack"},
                domains={"landing"},
            ),
        ],
    )

    orchestrator.register_candidates(
        "Backend",
        [
            _candidate(
                "be-ai",
                "Backend",
                0.88,
                0.87,
                skills={"fastapi", "rag", "cache"},
                tools={"redis", "pg"},
                domains={"website"},
            ),
            _candidate(
                "be-basic",
                "Backend",
                0.93,
                0.82,
                skills={"django"},
                tools={"mysql"},
                domains={"generic"},
            ),
        ],
    )

    requirements = {
        "product": RoleRequirement(
            role="Product",
            skills={"ai_builder", "sla"},
            tools={"figjam"},
            domains={"website"},
        ),
        "frontend": RoleRequirement(
            role="Frontend",
            skills={"react", "ai_widget"},
            tools={"storybook"},
            domains={"website"},
        ),
        "backend": RoleRequirement(
            role="Backend",
            skills={"fastapi", "rag"},
            tools={"redis"},
            domains={"website"},
        ),
    }

    intent = IntentRequest(
        user_id="client-1",
        utterance="我要一个AI建站官网",
        project_id="ai-site",
        role_requirements=requirements,
    )
    acceptance = AcceptanceCriteria(description="AI site MVP", metrics={"quality": 0.8})

    plan = orchestrator.plan_strategy(intent, acceptance)

    assert plan.decision["product"].selected.profile.agent_id == "prod-vision"
    assert plan.decision["frontend"].selected.profile.agent_id == "fe-pro"
    assert plan.decision["backend"].selected.profile.agent_id == "be-ai"
