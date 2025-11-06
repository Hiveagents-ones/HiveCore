# -*- coding: utf-8 -*-
"""Intent recognition + strategy planning (Section II.3)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from ..aa import (
    AAScoringConfig,
    AgentProfile,
    AssistantAgentSelector,
    CandidateRanking,
    RoleRequirement,
    SelectionDecision,
)
from ._system import SystemRegistry, UserProfile


@dataclass
class IntentRequest:
    user_id: str
    utterance: str
    project_id: str | None = None
    notes: str | None = None
    role_requirements: dict[str, RoleRequirement] = field(default_factory=dict)


@dataclass
class AcceptanceCriteria:
    """Machine interpretable SLA definition."""

    description: str
    metrics: dict[str, float]
    sla_version: str = "v1"


@dataclass
class StrategyPlan:
    requirement_map: dict[str, RoleRequirement]
    rankings: dict[str, CandidateRanking]
    decision: dict[str, SelectionDecision]
    acceptance: AcceptanceCriteria
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AssistantOrchestrator:
    """AA facade bridging user intent, candidate pools, and acceptance."""

    def __init__(
        self,
        *,
        system_registry: SystemRegistry,
        scoring_config: AAScoringConfig | None = None,
    ) -> None:
        self.registry = system_registry
        self.selector = AssistantAgentSelector(config=scoring_config)
        self._candidate_pools: dict[str, list[AgentProfile]] = {}

    def register_candidates(self, role: str, candidates: Iterable[AgentProfile]) -> None:
        self._candidate_pools.setdefault(role, [])
        self._candidate_pools[role].extend(candidates)

    def _select_for_role(
        self,
        role: str,
        requirement: RoleRequirement,
    ) -> SelectionDecision:
        candidates = self._candidate_pools.get(role, [])
        return self.selector.select(role=role, requirement=requirement, candidates=candidates)

    def plan_strategy(
        self,
        intent: IntentRequest,
        acceptance: AcceptanceCriteria,
    ) -> StrategyPlan:
        rankings: dict[str, CandidateRanking] = {}
        decisions: dict[str, SelectionDecision] = {}
        for node_id, requirement in intent.role_requirements.items():
            decision = self._select_for_role(requirement.role, requirement)
            decisions[node_id] = decision
            if decision.selected:
                rankings[node_id] = decision.selected
        return StrategyPlan(
            requirement_map=intent.role_requirements,
            rankings=rankings,
            decision=decisions,
            acceptance=acceptance,
        )

    def route_user(self, profile: UserProfile) -> None:
        if not self.registry.aa_binding(profile.user_id):
            aa_id = f"aa-{profile.user_id}"
            self.registry.register_user(profile, aa_id)

    def evaluate_acceptance(
        self,
        plan: StrategyPlan,
        observed_metrics: dict[str, float],
    ) -> bool:
        for metric, target in plan.acceptance.metrics.items():
            if observed_metrics.get(metric, 0.0) < target:
                return False
        return True
