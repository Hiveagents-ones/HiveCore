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
    TeamSelector,
    TeamSelection,
    CollaborationMode,
)
from ..agent import spawn_metaso_agent
from ._system import SystemRegistry, UserProfile
from .._logging import logger

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
    """Strategy plan with agent assignments.

    Supports both single-agent (backward compatible) and multi-agent team assignments.
    When team_selections is populated, TaskGraphBuilder uses team composition for
    collaborative task execution.

    Attributes:
        requirement_map: Map of node_id to Requirement.
        rankings: Map of node_id to CandidateRanking (primary agent, backward compatible).
        decision: Map of node_id to SelectionDecision.
        acceptance: Acceptance criteria for the plan.
        team_selections: Map of node_id to TeamSelection (multi-agent teams).
        sandbox_decision: Optional sandbox configuration.
        created_at: Timestamp when plan was created.
    """

    requirement_map: dict[str, Requirement]
    rankings: dict[str, CandidateRanking]
    decision: dict[str, SelectionDecision]
    acceptance: AcceptanceCriteria
    team_selections: dict[str, TeamSelection] = field(default_factory=dict)
    sandbox_decision: "SandboxDecision | None" = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AssistantOrchestrator:
    """AA facade bridging user intent, candidate pools, and acceptance.

    Supports both single-agent (backward compatible) and multi-agent team selection.
    When enable_multi_agent is True, uses TeamSelector for role-based team composition.

    Attributes:
        registry: System registry for user/agent management.
        selector: Single-agent selector (backward compatible).
        team_selector: Multi-agent team selector.
        enable_multi_agent: Whether to enable multi-agent team selection.
    """

    def __init__(
        self,
        *,
        system_registry: SystemRegistry,
        scoring_config: AAScoringConfig | None = None,
        spawn_factory: Callable[[Requirement, str], tuple[AgentProfile, object]]
        | None = None,
        enable_multi_agent: bool = True,
        model_config_name: str | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            system_registry: System registry for user/agent management.
            scoring_config: Scoring configuration for agent selection.
            spawn_factory: Factory for spawning new agents.
            enable_multi_agent: Whether to enable multi-agent team selection.
            model_config_name: Model config name for LLM team analysis.
                If None, falls back to single-agent selection.
        """
        self.registry = system_registry
        self.selector = AssistantAgentSelector(config=scoring_config)
        self.team_selector = TeamSelector(
            config=scoring_config,
            enable_multi_agent=enable_multi_agent,
            model_config_name=model_config_name,
        )
        self.enable_multi_agent = enable_multi_agent
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

    def load_from_registry(self, registry_path: str | None = None) -> int:
        """Load previously registered agents from the registry.

        This should be called on startup to restore agents created in
        previous sessions. The agents are loaded from their manifest files
        and added to the candidate pool.

        Args:
            registry_path: Optional path to registry.json. If None, uses default.

        Returns:
            Number of agents loaded.
        """
        try:
            from ..aa._agent_registry import (
                get_global_registry,
                load_all_agent_profiles,
            )

            registry = get_global_registry(registry_path)
            profiles = load_all_agent_profiles(registry)

            for profile in profiles:
                self.register_candidates([profile])

            logger.info(
                "[Orchestrator] Loaded %d agents from registry",
                len(profiles),
            )
            return len(profiles)

        except Exception as e:
            logger.warning("[Orchestrator] Failed to load from registry: %s", e)
            return 0

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
                # Directly use the spawned agent instead of re-running selection
                # because the spawned agent's capabilities are derived from
                # the requirement, ensuring a perfect match
                from ..aa import CandidateRanking, RequirementFitBreakdown
                perfect_fit = RequirementFitBreakdown(
                    score=1.0,
                    matched={},
                    missing={},
                    partial_matches={},
                    rationales=["Spawned agent with matching capabilities"],
                )
                spawned_ranking = CandidateRanking(
                    profile=spawned,
                    s_base=0.5,  # Default score for spawned agent
                    requirement_fit=perfect_fit,
                    combined_score=1.0,
                    cold_start_slot_reserved=True,
                    risk_notes=["Dynamically spawned agent"],
                )
                from ..aa import SelectionDecision, SelectionRound
                decision = SelectionDecision(
                    selected=spawned_ranking,
                    ranked_candidates=[spawned_ranking],
                    decision_source="spawn",
                    batch_index=0,
                    audit_round=SelectionRound(
                        batch_index=0,
                        requirement=requirement,
                        candidates=[spawned_ranking],
                        decision_source="spawn",
                        selected_agent_id=spawned.agent_id,
                    ),
                )
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

    def _spawn_agent_with_spec(
        self,
        requirement: Requirement,
        utterance: str,
        agent_spec: Any,
    ) -> AgentProfile | None:
        """Spawn a new agent using LLM-generated spec.

        Args:
            requirement: The requirement for the agent.
            utterance: User utterance for context.
            agent_spec: AgentSpec from LLM analysis with agent identity.

        Returns:
            AgentProfile of spawned agent, or None if spawn failed.
        """
        if self.spawn_factory is None:
            return None

        # Call spawn_factory with agent_spec passed via requirement metadata
        # The spawn_factory should check for agent_spec in requirement
        try:
            from ..ones._modular_agent import spawn_modular_agent

            # Get LLM and MCP clients from existing runtime agents if available
            llm = None
            mcp_clients = None
            for agent in self._runtime_agents.values():
                if hasattr(agent, "llm") and agent.llm:
                    llm = agent.llm
                if hasattr(agent, "_mcp_clients") and agent._mcp_clients:
                    mcp_clients = agent._mcp_clients
                if llm and mcp_clients:
                    break

            # Fallback: get LLM from team_selector if not found in runtime agents
            # This is critical because load_from_registry only loads profiles,
            # not agent instances, so _runtime_agents may be empty initially
            if llm is None and hasattr(self, "team_selector"):
                llm = getattr(self.team_selector, "_model", None)

            # Get persist directory from workspace if available
            # Use local_mirror_dir (host path) instead of base_workspace_dir (container path)
            persist_dir = None
            if hasattr(self, "_workspace") and self._workspace:
                from pathlib import Path
                # Prefer local_mirror_dir (host path) over base_workspace_dir (container path)
                ws_dir = getattr(self._workspace, "local_mirror_dir", None)
                if not ws_dir:
                    ws_dir = getattr(self._workspace, "base_workspace_dir", None)
                if ws_dir:
                    # If ws_dir looks like a container path (starts with /workspace),
                    # fall back to deliverables/agents
                    ws_path = Path(ws_dir)
                    if str(ws_path).startswith("/workspace"):
                        persist_dir = "deliverables/agents"
                    else:
                        persist_dir = str(ws_path.parent / "agents")

            profile, agent_instance = spawn_modular_agent(
                requirement=requirement,
                utterance=utterance,
                llm=llm,
                mcp_clients=mcp_clients,
                with_file_tools=True,
                agent_spec=agent_spec,
                persist_to=persist_dir,
            )

            if profile.agent_id in self._runtime_agents:
                return profile

            self._runtime_agents[profile.agent_id] = agent_instance
            self.register_candidates([profile])
            return profile

        except Exception as e:
            logger.warning("Failed to spawn agent with spec: %s", e)
            return None

    def plan_strategy(
        self,
        intent: IntentRequest,
        acceptance: AcceptanceCriteria,
    ) -> StrategyPlan:
        """Create a strategy plan by selecting agents for each requirement.

        When enable_multi_agent is True, uses TeamSelector with LLM analysis
        to dynamically decide team composition for each requirement.

        Args:
            intent: The user intent with requirements.
            acceptance: Acceptance criteria for the plan.

        Returns:
            StrategyPlan with agent assignments and team selections.
        """
        rankings: dict[str, CandidateRanking] = {}
        decisions: dict[str, SelectionDecision] = {}
        team_selections: dict[str, TeamSelection] = {}

        for node_id, requirement in intent.requirements.items():
            # Single-agent selection (backward compatible)
            decision = self._select(requirement, intent.utterance)
            decisions[node_id] = decision
            if decision.selected:
                rankings[node_id] = decision.selected

            # Multi-agent team selection (LLM-driven)
            if self.enable_multi_agent and self._candidates:
                team_selection = self.team_selector.select_team(
                    requirement_id=node_id,
                    requirement=requirement,
                    candidates=self._candidates,
                )

                # Spawn new agents from LLM-generated specs
                analysis = team_selection.llm_analysis
                if analysis and analysis.new_agent_specs and self.spawn_factory:
                    for agent_spec in analysis.new_agent_specs:
                        if not agent_spec.agent_id:
                            continue
                        # Check if agent already exists
                        if agent_spec.agent_id in self._runtime_agents:
                            continue
                        # Spawn new agent with LLM-generated spec
                        spawned = self._spawn_agent_with_spec(
                            requirement, intent.utterance, agent_spec
                        )
                        if spawned:
                            logger.info(
                                "[Orchestrator] Spawned new agent from LLM spec: %s (%s)",
                                agent_spec.name,
                                agent_spec.agent_id,
                            )
                            # Re-run team selection with new agent
                            team_selection = self.team_selector.select_team(
                                requirement_id=node_id,
                                requirement=requirement,
                                candidates=self._candidates,
                            )

                if team_selection.assignments:
                    team_selections[node_id] = team_selection
                    # Log team selection result
                    if analysis:
                        logger.info(
                            "[Orchestrator] Team for %s: complexity=%s, %d agents (%s) - %s",
                            node_id,
                            analysis.complexity,
                            len(team_selection.assignments),
                            ", ".join(
                                f"{a.role.value}:{a.agent.agent_id}"
                                for a in team_selection.assignments
                            ),
                            analysis.reasoning[:100] if analysis.reasoning else "",
                        )

        return StrategyPlan(
            requirement_map=intent.requirements,
            rankings=rankings,
            decision=decisions,
            acceptance=acceptance,
            team_selections=team_selections,
            sandbox_decision=intent.sandbox_decision,
        )

    def route_user(self, profile: UserProfile) -> None:
        """Route user to an AA instance."""
        if not self.registry.aa_binding(profile.user_id):
            aa_id = f"aa-{profile.user_id}"
            self.registry.register_user(profile, aa_id)

    def set_team_selector_model(self, model: object) -> None:
        """Set the LLM model for team selector analysis.

        Args:
            model (`object`):
                The LLM model instance for team analysis.
        """
        self.team_selector._model = model

