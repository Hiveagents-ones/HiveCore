# -*- coding: utf-8 -*-
"""Selection logic for AA (AssistantAgent) orchestration."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable, Sequence

from .._logging import logger
from ._types import (
    AAScoringConfig,
    AgentCapabilities,
    AgentProfile,
    CandidateRanking,
    RequirementFitBreakdown,
    RequirementHardConstraints,
    RoleRequirement,
    SelectionAuditLog,
    SelectionDecision,
    SelectionRound,
)


class RequirementFitScorer:
    """Compute requirement fit score and explanation."""

    tracked_fields = (
        "skills",
        "tools",
        "domains",
        "languages",
        "regions",
        "compliance_tags",
    )

    def __init__(self, config: AAScoringConfig) -> None:
        self.config = config

    def _resolve_weights(self, requirement: RoleRequirement) -> dict[str, float]:
        weights = self.config.default_requirement_weights.copy()
        weights.update(requirement.weight_overrides)
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("Requirement weight sum must be positive")
        return {k: v / total for k, v in weights.items()}

    def score(
        self,
        requirement: RoleRequirement,
        capabilities: AgentCapabilities,
    ) -> RequirementFitBreakdown:
        weights = self._resolve_weights(requirement)
        matched: dict[str, set[str]] = {}
        missing: dict[str, set[str]] = {}
        partial: dict[str, float] = {}
        rationales: list[str] = []
        total_score = 0.0

        for field in self.tracked_fields:
            req_values: set[str] = getattr(requirement, field)
            if not req_values:
                continue
            cap_values: set[str] = getattr(capabilities, field)
            hit = req_values & cap_values
            miss = req_values - cap_values
            coverage = len(hit) / len(req_values) if req_values else 0.0
            matched[field] = hit
            missing[field] = miss
            partial[field] = coverage
            weight = weights.get(field, 0.0)
            total_score += weight * coverage

            rationales.append(
                (
                    f"{field}: matched {len(hit)}/{len(req_values)} requirements"
                    f" (weight={weight:.2f})."
                ),
            )

        total_score = max(0.0, min(1.0, total_score))

        if requirement.domains and capabilities.similar_cases:
            rationales.append(
                "Similar cases: "
                + ", ".join(capabilities.similar_cases[:3]),
            )

        return RequirementFitBreakdown(
            score=total_score,
            matched=matched,
            missing=missing,
            partial_matches=partial,
            rationales=rationales,
        )


class AssistantAgentSelector:
    """Implements the AA selection policy described in the spec."""

    def __init__(self, config: AAScoringConfig | None = None) -> None:
        self.config = config or AAScoringConfig()
        self.fit_scorer = RequirementFitScorer(self.config)
        self.audit_log = SelectionAuditLog()

    def _filter_candidates(
        self,
        role: str,
        requirement: RoleRequirement,
        candidates: Sequence[AgentProfile],
    ) -> list[AgentProfile]:
        hard_filter: RequirementHardConstraints = requirement.hard_constraints
        filtered: list[AgentProfile] = []
        for profile in candidates:
            if profile.role != role:
                continue
            if not hard_filter.satisfied_by(profile.capabilities):
                continue
            filtered.append(profile)
        return filtered

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    def _rank_by_s_base(
        self,
        profiles: list[AgentProfile],
        now: datetime | None = None,
    ) -> list[AgentProfile]:
        now = now or self._utcnow()
        scored = []
        for profile in profiles:
            s_base = profile.compute_s_base(self.config.severity_weights, now)
            scored.append((s_base, profile))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [profile for _, profile in scored]

    def _slice_batch(
        self,
        ranked: list[AgentProfile],
        batch_index: int,
    ) -> list[AgentProfile]:
        top_n = self.config.top_n
        start = batch_index * top_n
        end = start + top_n
        return ranked[start:end]

    def _compose_candidate_ranking(
        self,
        profile: AgentProfile,
        requirement: RoleRequirement,
        now: datetime,
        cold_start_quota_state: dict[str, int],
    ) -> CandidateRanking:
        requirement_fit = self.fit_scorer.score(requirement, profile.capabilities)
        s_base = profile.s_base if profile.s_base is not None else profile.compute_s_base(
            self.config.severity_weights,
            now,
        )
        combined = s_base + (requirement_fit.score * self.config.requirement_weight)
        reserved_cold_slot = False

        if profile.is_cold_start:
            if cold_start_quota_state["used"] < self.config.cold_start_quota:
                combined += self.config.cold_start_bonus
                reserved_cold_slot = True
                cold_start_quota_state["used"] += 1
            else:
                combined -= self.config.cold_start_overflow_penalty

        risk_notes: list[str] = []
        for field, missing_values in requirement_fit.missing.items():
            if missing_values:
                risk_notes.append(
                    f"{field} gap: {', '.join(sorted(missing_values))}",
                )
        if profile.is_cold_start:
            risk_notes.append("Cold start traffic limited")

        return CandidateRanking(
            profile=profile,
            s_base=s_base,
            requirement_fit=requirement_fit,
            combined_score=combined,
            cold_start_slot_reserved=reserved_cold_slot,
            risk_notes=risk_notes,
        )

    def _sorted_rankings(
        self,
        rankings: list[CandidateRanking],
        now: datetime,
    ) -> list[CandidateRanking]:
        def sort_key(item: CandidateRanking) -> tuple:
            profile = item.profile
            active_faults = len(profile.fault_ledger.active_records(now))
            recent_ts = (
                profile.recent_success_at.timestamp()
                if profile.recent_success_at
                else 0.0
            )
            return (
                -item.combined_score,
                -item.requirement_fit.score,
                active_faults,
                -profile.static_score.performance,
                -profile.static_score.brand,
                -profile.static_score.recognition,
                -recent_ts,
            )

        return sorted(rankings, key=sort_key)

    def select(
        self,
        role: str,
        requirement: RoleRequirement,
        candidates: Sequence[AgentProfile],
        batch_index: int = 0,
        user_selected_agent_id: str | None = None,
    ) -> SelectionDecision:
        if batch_index < 0:
            raise ValueError("batch_index must be non-negative")

        now = self._utcnow()
        filtered = self._filter_candidates(role, requirement, candidates)
        if not filtered:
            logger.warning("No candidates available for role %s", role)
            empty_round = SelectionRound(
                role=role,
                batch_index=batch_index,
                requirement=requirement,
                candidates=[],
                decision_source="system",
                selected_agent_id=None,
            )
            self.audit_log.append(empty_round)
            return SelectionDecision(
                selected=None,
                ranked_candidates=[],
                decision_source="system",
                batch_index=batch_index,
                audit_round=empty_round,
            )

        ranked_by_base = self._rank_by_s_base(filtered, now)
        batch = self._slice_batch(ranked_by_base, batch_index)
        if not batch:
            logger.info(
                "Batch index %s exceeds candidate list for role %s",
                batch_index,
                role,
            )
            empty_round = SelectionRound(
                role=role,
                batch_index=batch_index,
                requirement=requirement,
                candidates=[],
                decision_source="system",
                selected_agent_id=None,
            )
            self.audit_log.append(empty_round)
            return SelectionDecision(
                selected=None,
                ranked_candidates=[],
                decision_source="system",
                batch_index=batch_index,
                audit_round=empty_round,
            )

        cold_state = {"used": 0}
        candidate_rankings = [
            self._compose_candidate_ranking(profile, requirement, now, cold_state)
            for profile in batch
        ]

        ordered_candidates = self._sorted_rankings(candidate_rankings, now)

        decision_source = "system"
        selected = ordered_candidates[0] if ordered_candidates else None
        if user_selected_agent_id:
            override = next(
                (
                    candidate
                    for candidate in ordered_candidates
                    if candidate.profile.agent_id == user_selected_agent_id
                ),
                None,
            )
            if override is None:
                raise ValueError(
                    "User override must reference candidates visible in the current batch",
                )
            selected = override
            decision_source = "user"

        selection_round = SelectionRound(
            role=role,
            batch_index=batch_index,
            requirement=requirement,
            candidates=ordered_candidates,
            decision_source=decision_source,
            selected_agent_id=selected.profile.agent_id if selected else None,
        )
        self.audit_log.append(selection_round)

        logger.debug(
            "AA selection round recorded: %s",
            asdict(selection_round),
        )

        return SelectionDecision(
            selected=selected,
            ranked_candidates=ordered_candidates,
            decision_source=decision_source,
            batch_index=batch_index,
            audit_round=selection_round,
        )

    def last_rounds(self, limit: int | None = None):
        """Return the latest selection rounds for transparency APIs."""

        limit = limit or self.config.log_round_limit
        return self.audit_log.tail(limit)
