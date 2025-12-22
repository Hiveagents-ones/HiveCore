# -*- coding: utf-8 -*-
"""Typed data structures for AssistantAgent selection and scoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal, Sequence


SeverityLevel = Literal["critical", "major", "minor", "notice"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return _utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class StaticScoreWeights:
    """Weight configuration for the static S_base components."""

    performance: float = 0.4
    brand: float = 0.2
    recognition: float = 0.3
    fault: float = 0.1

    def normalized(self) -> "StaticScoreWeights":
        """Return a normalized copy of the weights to keep the sum stable."""

        total = self.performance + self.brand + self.recognition + self.fault
        if total <= 0:
            raise ValueError("Static score weights must sum to a positive value")

        return StaticScoreWeights(
            performance=self.performance / total,
            brand=self.brand / total,
            recognition=self.recognition / total,
            fault=self.fault / total,
        )


@dataclass
class FaultRecord:
    """A single fault / violation event tracked in the fault ledger."""

    severity: SeverityLevel
    occurred_at: datetime
    cooling_days: int = 30
    description: str = ""

    def cooling_deadline(self) -> datetime:
        base = _ensure_utc(self.occurred_at)
        return base + timedelta(days=self.cooling_days)

    def is_active(self, now: datetime | None = None) -> bool:
        now = _ensure_utc(now)
        return now < self.cooling_deadline()


@dataclass
class FaultLedger:
    """Aggregates historical faults and exposes penalties / counts."""

    records: list[FaultRecord] = field(default_factory=list)

    def active_records(self, now: datetime | None = None) -> list[FaultRecord]:
        now = _ensure_utc(now)
        return [record for record in self.records if record.is_active(now)]

    def penalty(
        self,
        severity_weights: dict[SeverityLevel, float],
        now: datetime | None = None,
    ) -> float:
        """Return the additive penalty contributed by active fault records."""

        now = _ensure_utc(now)
        penalty = 0.0
        for record in self.records:
            if record.is_active(now):
                penalty += severity_weights.get(record.severity, 0.0)
        return penalty

    def record_event(self, record: FaultRecord) -> None:
        self.records.append(record)


@dataclass
class AgentCapabilities:
    """Capabilities that can be matched against runtime requirements."""

    skills: set[str] = field(default_factory=set)
    tools: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=set)
    regions: set[str] = field(default_factory=set)
    compliance_tags: set[str] = field(default_factory=set)
    certifications: set[str] = field(default_factory=set)
    similar_cases: Sequence[str] = field(default_factory=list)


@dataclass
class StaticScore:
    """Static S_base components that are assigned at profile creation."""

    performance: float
    brand: float
    recognition: float
    fault_impact: float = 0.0

    def clamp(self) -> "StaticScore":
        return StaticScore(
            performance=max(0.0, min(1.0, self.performance)),
            brand=max(0.0, min(1.0, self.brand)),
            recognition=max(0.0, min(1.0, self.recognition)),
            fault_impact=max(0.0, self.fault_impact),
        )


@dataclass
class AgentProfile:
    """Full profile describing an available Agent candidate.

    Agent selection is based on `capabilities` matching (skills, tools, domains, etc.).
    """

    agent_id: str
    name: str
    static_score: StaticScore
    capabilities: AgentCapabilities
    fault_ledger: FaultLedger = field(default_factory=FaultLedger)
    base_weights: StaticScoreWeights = field(default_factory=StaticScoreWeights)
    recent_success_at: datetime | None = None
    brand_level: str | None = None
    is_cold_start: bool = False
    metadata: dict[str, str] = field(default_factory=dict)
    s_base: float | None = None
    # Cold start learning fields
    task_count: int = 0
    cold_start_threshold: int = 5
    learning_rate: float = 0.1

    def update_after_task(
        self,
        quality_score: float,
        accepted: bool = True,
        user_rating: float | None = None,
    ) -> None:
        """Update scores after task completion.

        Uses exponential moving average to blend historical performance
        with recent task results.

        Args:
            quality_score: Quality score of the completed task (0.0-1.0).
            accepted: Whether the task result was accepted.
            user_rating: Optional user rating (0.0-1.0) to update recognition.
        """
        current = self.static_score

        if accepted:
            # EMA update for performance: new = (1-α) * old + α * new_value
            new_performance = (
                (1 - self.learning_rate) * current.performance
                + self.learning_rate * quality_score
            )
            new_fault_impact = current.fault_impact
        else:
            # Failed task: decrease performance and increase fault impact
            new_performance = current.performance * 0.95
            new_fault_impact = current.fault_impact + 0.1  # Fault penalty

        # Update recognition only if user provides explicit rating
        new_recognition = current.recognition
        if user_rating is not None:
            new_recognition = (
                (1 - self.learning_rate) * current.recognition
                + self.learning_rate * user_rating
            )

        self.static_score = StaticScore(
            performance=new_performance,
            brand=current.brand,  # Brand is manually controlled, never auto-update
            recognition=new_recognition,
            fault_impact=new_fault_impact,
        )

        self.task_count += 1
        self.recent_success_at = _utcnow() if accepted else self.recent_success_at

        # Exit cold start after threshold
        if self.task_count >= self.cold_start_threshold:
            self.is_cold_start = False

        # Reset cached s_base so it gets recomputed
        self.s_base = None

    def compute_s_base(
        self,
        severity_weights: dict[SeverityLevel, float],
        now: datetime | None = None,
    ) -> float:
        """Compute (or recompute) the static base score."""

        weights = self.base_weights.normalized()
        score = self.static_score.clamp()
        fault_penalty = self.fault_ledger.penalty(severity_weights, now)
        fault_component = max(0.0, 1.0 - fault_penalty)
        s_base = (
            weights.performance * score.performance
            + weights.brand * score.brand
            + weights.recognition * score.recognition
            + weights.fault * fault_component
        )
        self.s_base = s_base
        return s_base


@dataclass
class RequirementHardConstraints:
    """Hard constraints applied before ranking by S_base."""

    required_tools: set[str] = field(default_factory=set)
    required_certifications: set[str] = field(default_factory=set)
    required_compliance_tags: set[str] = field(default_factory=set)

    def satisfied_by(self, capabilities: AgentCapabilities) -> bool:
        if self.required_tools - capabilities.tools:
            return False
        if self.required_certifications - capabilities.certifications:
            return False
        if self.required_compliance_tags - capabilities.compliance_tags:
            return False
        return True


@dataclass
class Requirement:
    """Dynamic requirement for agent selection based on capabilities."""

    skills: set[str] = field(default_factory=set)
    tools: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=set)
    regions: set[str] = field(default_factory=set)
    compliance_tags: set[str] = field(default_factory=set)
    hard_constraints: RequirementHardConstraints = field(
        default_factory=RequirementHardConstraints,
    )
    weight_overrides: dict[str, float] = field(default_factory=dict)
    notes: str | None = None


# Alias for backward compatibility
RoleRequirement = Requirement


@dataclass
class RequirementFitBreakdown:
    """Detailed requirement fit evaluation."""

    score: float
    matched: dict[str, set[str]]
    missing: dict[str, set[str]]
    partial_matches: dict[str, float]
    rationales: list[str] = field(default_factory=list)


@dataclass
class CandidateRanking:
    """Computed ranking data for a single candidate."""

    profile: AgentProfile
    s_base: float
    requirement_fit: RequirementFitBreakdown
    combined_score: float
    cold_start_slot_reserved: bool
    risk_notes: list[str] = field(default_factory=list)


@dataclass
class AAScoringConfig:
    """Global configuration for AA selection and scoring."""

    top_n: int = 20  # Ensure all candidates including spawned ones are evaluated
    requirement_weight: float = 0.35
    cold_start_bonus: float = 0.05
    cold_start_quota: int = 1
    cold_start_overflow_penalty: float = 0.1
    severity_weights: dict[SeverityLevel, float] = field(
        default_factory=lambda: {
            "critical": 1.0,
            "major": 0.5,
            "minor": 0.2,
            "notice": 0.1,
        },
    )
    default_requirement_weights: dict[str, float] = field(
        default_factory=lambda: {
            "skills": 0.35,
            "tools": 0.2,
            "domains": 0.15,
            "languages": 0.1,
            "regions": 0.1,
            "compliance_tags": 0.1,
        },
    )
    tolerance: float = 1e-6
    log_round_limit: int = 20
    min_fit_threshold: float = 0.3  # Minimum requirement fit score to accept a match


@dataclass
class SelectionRound:
    """A recorded selection round for audit purposes."""

    batch_index: int
    requirement: Requirement
    candidates: list[CandidateRanking]
    decision_source: Literal["system", "user"]
    selected_agent_id: str | None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class SelectionDecision:
    """Return object produced by the selector."""

    selected: CandidateRanking | None
    ranked_candidates: list[CandidateRanking]
    decision_source: Literal["system", "user"]
    batch_index: int
    audit_round: SelectionRound


@dataclass
class SelectionAuditLog:
    """Keeps ordered selection rounds for traceability."""

    rounds: list[SelectionRound] = field(default_factory=list)

    def append(self, round_: SelectionRound) -> None:
        if len(self.rounds) >= 1000:
            self.rounds.pop(0)
        self.rounds.append(round_)

    def tail(self, limit: int | None = None) -> list[SelectionRound]:
        limit = limit or len(self.rounds)
        return self.rounds[-limit:]
