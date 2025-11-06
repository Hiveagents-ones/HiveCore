# -*- coding: utf-8 -*-
"""Unit tests for the AA selection module."""
from datetime import datetime, timedelta, timezone

import pytest

from agentscope.aa import (
    AAScoringConfig,
    AssistantAgentSelector,
    AgentCapabilities,
    AgentProfile,
    FaultLedger,
    FaultRecord,
    RequirementHardConstraints,
    RoleRequirement,
    StaticScore,
)


NOW = datetime.now(timezone.utc)


def _profile(
    agent_id: str,
    performance: float,
    recognition: float,
    skills: set[str],
    tools: set[str],
    *,
    is_cold_start: bool = False,
    fault_records: list[FaultRecord] | None = None,
    recent_success_at: datetime | None = None,
) -> AgentProfile:
    ledger = FaultLedger(records=fault_records or [])
    return AgentProfile(
        agent_id=agent_id,
        name=agent_id,
        role="Dev",
        static_score=StaticScore(
            performance=performance,
            brand=0.5,
            recognition=recognition,
        ),
        capabilities=AgentCapabilities(
            skills=skills,
            tools=tools,
            domains={"infra"},
            languages={"zh"},
            regions={"cn"},
            compliance_tags={"standard"},
            certifications={"iso"},
        ),
        fault_ledger=ledger,
        recent_success_at=recent_success_at or NOW,
        is_cold_start=is_cold_start,
    )


def test_requirement_fit_can_out_rank_s_base() -> None:
    config = AAScoringConfig(top_n=2, requirement_weight=0.6)
    selector = AssistantAgentSelector(config=config)

    requirement = RoleRequirement(
        role="Dev",
        skills={"python", "rag"},
        tools={"docker"},
    )

    strong_base = _profile(
        agent_id="base",
        performance=0.95,
        recognition=0.9,
        skills={"cpp"},
        tools={"docker"},
    )
    perfect_match = _profile(
        agent_id="match",
        performance=0.88,
        recognition=0.85,
        skills={"python", "rag"},
        tools={"docker"},
    )

    decision = selector.select(
        role="Dev",
        requirement=requirement,
        candidates=[strong_base, perfect_match],
    )

    assert decision.selected is not None
    assert decision.selected.profile.agent_id == "match"
    assert decision.selected.requirement_fit.score > 0.5


def test_hard_constraints_filtering() -> None:
    selector = AssistantAgentSelector()
    requirement = RoleRequirement(
        role="Dev",
        skills={"python"},
        hard_constraints=RequirementHardConstraints(required_tools={"k8s"}),
    )

    ok = _profile(
        agent_id="ok",
        performance=0.8,
        recognition=0.8,
        skills={"python"},
        tools={"k8s"},
    )
    reject = _profile(
        agent_id="reject",
        performance=0.95,
        recognition=0.95,
        skills={"python"},
        tools={"docker"},
    )

    decision = selector.select(
        role="Dev",
        requirement=requirement,
        candidates=[ok, reject],
    )

    ids = [candidate.profile.agent_id for candidate in decision.ranked_candidates]
    assert ids == ["ok"], "Agent lacking hard requirements must be dropped"


def test_tie_break_prefers_lower_fault_volume() -> None:
    config = AAScoringConfig(top_n=2, requirement_weight=0.2)
    selector = AssistantAgentSelector(config=config)

    good_record = _profile(
        agent_id="clean",
        performance=0.9,
        recognition=0.9,
        skills={"python"},
        tools={"docker"},
        fault_records=[],
    )
    penalized = _profile(
        agent_id="faulty",
        performance=0.9,
        recognition=0.9,
        skills={"python"},
        tools={"docker"},
        fault_records=[
            FaultRecord(
                severity="critical",
                occurred_at=NOW - timedelta(days=1),
                cooling_days=30,
            ),
        ],
    )

    decision = selector.select(
        role="Dev",
        requirement=RoleRequirement(role="Dev", skills={"python"}),
        candidates=[penalized, good_record],
    )

    assert decision.ranked_candidates[0].profile.agent_id == "clean"


def test_cold_start_quota_enforced() -> None:
    config = AAScoringConfig(
        top_n=3,
        cold_start_quota=1,
        cold_start_bonus=0.2,
        cold_start_overflow_penalty=0.3,
    )
    selector = AssistantAgentSelector(config=config)
    requirement = RoleRequirement(role="Dev")

    veteran = _profile(
        agent_id="vet",
        performance=0.88,
        recognition=0.88,
        skills={"python"},
        tools={"docker"},
    )
    cold_1 = _profile(
        agent_id="cold-1",
        performance=0.87,
        recognition=0.87,
        skills={"python"},
        tools={"docker"},
        is_cold_start=True,
    )
    cold_2 = _profile(
        agent_id="cold-2",
        performance=0.87,
        recognition=0.87,
        skills={"python"},
        tools={"docker"},
        is_cold_start=True,
    )

    decision = selector.select(
        role="Dev",
        requirement=requirement,
        candidates=[cold_1, cold_2, veteran],
    )

    ordered = [candidate.profile.agent_id for candidate in decision.ranked_candidates]
    assert ordered[0] in {"vet", "cold-1"}
    assert ordered[-1] == "cold-2", "Overflow cold-start agent should be penalized"


def test_audit_log_tracks_rounds() -> None:
    selector = AssistantAgentSelector()
    requirement = RoleRequirement(role="Dev")
    agent = _profile(
        agent_id="solo",
        performance=0.9,
        recognition=0.9,
        skills={"python"},
        tools={"docker"},
    )

    selector.select(role="Dev", requirement=requirement, candidates=[agent])
    selector.select(role="Dev", requirement=requirement, candidates=[agent], batch_index=1)

    rounds = selector.last_rounds()
    assert len(rounds) == 2
    assert rounds[-1].batch_index == 1
    assert rounds[-1].candidates == []
