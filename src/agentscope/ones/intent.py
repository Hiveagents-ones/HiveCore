# -*- coding: utf-8 -*-
"""Intent recognition + strategy planning (Section II.3)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable, TYPE_CHECKING

from ..aa import (
    AAScoringConfig,
    AgentProfile,
    AssistantAgentSelector,
    CandidateRanking,
    Requirement,
    RoleRequirement,  # Alias for backward compatibility
    SelectionDecision,
)
from ..agent import spawn_metaso_agent
from ._system import SystemRegistry, UserProfile

if TYPE_CHECKING:
    from .sandbox_orchestrator import SandboxDecision


@dataclass
class IntentRequest:
    """User intent with capability requirements."""

    user_id: str
    utterance: str
    project_id: str | None = None
    notes: str | None = None
    artifact_type: str | None = None
    requirements: dict[str, Requirement] = field(default_factory=dict)
    sandbox_decision: "SandboxDecision | None" = None


@dataclass
class AcceptanceCriteria:
    """Machine interpretable SLA definition."""

    description: str
    metrics: dict[str, float]
    sla_version: str = "v1"


@dataclass
class StrategyPlan:
    """Strategy plan with agent assignments."""

    requirement_map: dict[str, Requirement]
    rankings: dict[str, CandidateRanking]
    decision: dict[str, SelectionDecision]
    acceptance: AcceptanceCriteria
    sandbox_decision: "SandboxDecision | None" = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AssistantOrchestrator:
    """AA facade bridging user intent, candidate pools, and acceptance.

    Agent selection is based purely on capabilities matching, not roles.
    """

    def __init__(
        self,
        *,
        system_registry: SystemRegistry,
        scoring_config: AAScoringConfig | None = None,
        spawn_factory: Callable[[Requirement, str], tuple[AgentProfile, object]]
        | None = None,
    ) -> None:
        self.registry = system_registry
        self.selector = AssistantAgentSelector(config=scoring_config)
        self._candidates: list[AgentProfile] = []
        self._runtime_agents: dict[str, object] = {}
        self.spawn_factory = spawn_factory or (
            lambda requirement, utterance: spawn_metaso_agent(requirement, utterance)
        )

    def register_candidates(self, candidates: Iterable[AgentProfile]) -> None:
        """Register agent candidates to the pool."""
        for candidate in candidates:
            if candidate.agent_id not in {c.agent_id for c in self._candidates}:
                self._candidates.append(candidate)

    def _select(
        self,
        requirement: Requirement,
        utterance: str,
    ) -> SelectionDecision:
        """Select best agent based on capabilities matching."""
        def _run_select() -> SelectionDecision:
            return self.selector.select(
                requirement=requirement,
                candidates=self._candidates,
            )

        decision = _run_select()
        if decision.selected is None:
            spawned = self._spawn_agent(requirement, utterance)
            if spawned is not None:
                decision = _run_select()
        return decision

    def _spawn_agent(
        self,
        requirement: Requirement,
        utterance: str,
    ) -> AgentProfile | None:
        """Spawn a new agent when no suitable candidate exists."""
        if self.spawn_factory is None:
            return None
        profile, agent_instance = self.spawn_factory(requirement, utterance)
        if profile.agent_id in self._runtime_agents:
            return profile
        self._runtime_agents[profile.agent_id] = agent_instance
        self.register_candidates([profile])
        return profile

    def plan_strategy(
        self,
        intent: IntentRequest,
        acceptance: AcceptanceCriteria,
    ) -> StrategyPlan:
        """Create a strategy plan by selecting agents for each requirement."""
        rankings: dict[str, CandidateRanking] = {}
        decisions: dict[str, SelectionDecision] = {}
        for node_id, requirement in intent.requirements.items():
            decision = self._select(requirement, intent.utterance)
            decisions[node_id] = decision
            if decision.selected:
                rankings[node_id] = decision.selected
        return StrategyPlan(
            requirement_map=intent.requirements,
            rankings=rankings,
            decision=decisions,
            acceptance=acceptance,
            sandbox_decision=intent.sandbox_decision,
        )

    def route_user(self, profile: UserProfile) -> None:
        """Route user to an AA instance."""
        if not self.registry.aa_binding(profile.user_id):
            aa_id = f"aa-{profile.user_id}"
            self.registry.register_user(profile, aa_id)

