# -*- coding: utf-8 -*-
"""Selection logic for AA (AssistantAgent) orchestration."""
from __future__ import annotations

import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Sequence

from .._logging import logger
from ._types import (
    AAScoringConfig,
    AgentCapabilities,
    AgentProfile,
    CandidateRanking,
    RequirementFitBreakdown,
    RequirementHardConstraints,
    Requirement,
    SelectionAuditLog,
    SelectionDecision,
    SelectionRound,
)
from ._vocabulary import normalize_skills, normalize_domains


def _extract_keywords(text: str) -> set[str]:
    """Extract keywords from text for matching.

    Extracts both Chinese and English words, filtering common stopwords.
    """
    if not text:
        return set()

    # 中英文分词
    # 英文：按空格和标点分割
    # 中文：按字符分割（简单实现）
    words = set()

    # 英文单词
    english_words = re.findall(r"[a-zA-Z]+", text.lower())
    words.update(english_words)

    # 中文：提取2-4字词组（简单的n-gram）
    chinese_chars = re.findall(r"[\u4e00-\u9fff]+", text)
    for segment in chinese_chars:
        # 添加完整片段
        if len(segment) >= 2:
            words.add(segment)
        # 添加2-gram
        for i in range(len(segment) - 1):
            words.add(segment[i : i + 2])
        # 添加3-gram
        for i in range(len(segment) - 2):
            words.add(segment[i : i + 3])

    # 过滤常见停用词
    stopwords = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "when",
        "at",
        "by",
        "for",
        "with",
        "about",
        "against",
        "between",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "to",
        "from",
        "up",
        "down",
        "in",
        "out",
        "on",
        "off",
        "over",
        "under",
        "again",
        "further",
        "once",
        "here",
        "there",
        "all",
        "each",
        "both",
        "this",
        "that",
        "these",
        "those",
        "的",
        "是",
        "在",
        "了",
        "和",
        "与",
        "及",
        "或",
        "不",
        "也",
        "就",
        "都",
        "而",
        "及",
        "着",
        "把",
        "被",
        "让",
        "给",
        "向",
        "对",
        "从",
        "以",
        "为",
        "等",
        "能",
        "可",
        "会",
        "要",
        "用",
        "有",
        "个",
        "这",
        "那",
        "它",
        "他",
        "她",
        "我",
        "你",
    }

    return words - stopwords


def _compute_description_match(
    agent_description: str,
    requirement_notes: str | None,
) -> float:
    """Compute keyword match score between agent description and requirement.

    Returns:
        Float between 0.0 and 1.0 indicating match degree.
    """
    if not agent_description or not requirement_notes:
        return 0.0

    agent_keywords = _extract_keywords(agent_description)
    req_keywords = _extract_keywords(requirement_notes)

    if not req_keywords:
        return 0.0

    # 计算需求关键词在 Agent 简介中的覆盖率
    matched = agent_keywords & req_keywords
    coverage = len(matched) / len(req_keywords)

    return min(1.0, coverage)


class RequirementFitScorer:
    """Compute requirement fit score and explanation.

    Uses vocabulary normalization for skills and domains to handle synonyms
    (e.g., "后端" matches "backend", "python3" matches "python").
    """

    tracked_fields = (
        "skills",
        "tools",
        "domains",
        "languages",
        "regions",
        "compliance_tags",
    )

    # Fields that should be normalized before matching
    normalized_fields = {"skills", "domains"}

    def __init__(self, config: AAScoringConfig) -> None:
        self.config = config

    def _resolve_weights(self, requirement: Requirement) -> dict[str, float]:
        weights = self.config.default_requirement_weights.copy()
        weights.update(requirement.weight_overrides)
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("Requirement weight sum must be positive")
        return {k: v / total for k, v in weights.items()}

    def _normalize_field(self, field: str, values: set[str]) -> set[str]:
        """Normalize field values based on field type.

        Args:
            field: Field name (skills, domains, etc.)
            values: Set of values to normalize.

        Returns:
            Normalized set of values.
        """
        if field == "skills":
            return normalize_skills(values)
        elif field == "domains":
            return normalize_domains(values)
        return values

    def score(
        self,
        requirement: Requirement,
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

            # Normalize skills and domains for better matching
            if field in self.normalized_fields:
                req_normalized = self._normalize_field(field, req_values)
                cap_normalized = self._normalize_field(field, cap_values)
                hit = req_normalized & cap_normalized
                miss = req_normalized - cap_normalized
                coverage = len(hit) / len(req_normalized) if req_normalized else 0.0
            else:
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

        # Agent 简介与需求描述的匹配
        description_weight = weights.get("description", 0.0)
        if description_weight > 0 and (
            capabilities.description or requirement.notes
        ):
            desc_score = _compute_description_match(
                capabilities.description,
                requirement.notes,
            )
            partial["description"] = desc_score
            total_score += description_weight * desc_score
            if desc_score > 0:
                rationales.append(
                    f"description: keyword match score {desc_score:.2f}"
                    f" (weight={description_weight:.2f})."
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
        requirement: Requirement,
        candidates: Sequence[AgentProfile],
    ) -> list[AgentProfile]:
        """Filter candidates by hard constraints only (no role matching)."""
        hard_filter: RequirementHardConstraints = requirement.hard_constraints
        filtered: list[AgentProfile] = []
        for profile in candidates:
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
        requirement: Requirement,
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
        requirement: Requirement,
        candidates: Sequence[AgentProfile],
        batch_index: int = 0,
        user_selected_agent_id: str | None = None,
    ) -> SelectionDecision:
        """Select the best agent based on capabilities matching.

        Args:
            requirement: The capability requirements for selection.
            candidates: List of available agent profiles.
            batch_index: Pagination index for large candidate lists.
            user_selected_agent_id: Optional user override for selection.

        Returns:
            SelectionDecision with the selected agent and rankings.
        """
        if batch_index < 0:
            raise ValueError("batch_index must be non-negative")

        now = self._utcnow()
        filtered = self._filter_candidates(requirement, candidates)
        if not filtered:
            logger.warning("No candidates available for requirement: %s", requirement)
            empty_round = SelectionRound(
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
                "Batch index %s exceeds candidate list",
                batch_index,
            )
            empty_round = SelectionRound(
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

        # Check if best candidate meets minimum fit threshold
        if selected is not None:
            fit_score = selected.requirement_fit.score
            if fit_score < self.config.min_fit_threshold:
                logger.info(
                    "Best candidate %s has fit score %.2f below threshold %.2f, "
                    "returning None to trigger agent spawn",
                    selected.profile.agent_id,
                    fit_score,
                    self.config.min_fit_threshold,
                )
                selected = None

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
