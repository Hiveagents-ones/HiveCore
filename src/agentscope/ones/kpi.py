# -*- coding: utf-8 -*-
"""KPI and optimization tracking (Section IV)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class KPIRecord:
    timestamp: datetime
    baseline_cost: float
    observed_cost: float
    baseline_time: float
    observed_time: float

    @property
    def cost_reduction(self) -> float:
        if self.baseline_cost == 0:
            return 0.0
        return 1 - (self.observed_cost / self.baseline_cost)

    @property
    def time_reduction(self) -> float:
        if self.baseline_time == 0:
            return 0.0
        return 1 - (self.observed_time / self.baseline_time)


class KPITracker:
    """Keeps running view vs. the 90% optimization target.

    This tracker now integrates with ObservabilityHub to get real cost data
    when a project_id is provided.
    """

    def __init__(self, *, target_reduction: float = 0.9) -> None:
        self.target = target_reduction
        self.records: list[KPIRecord] = []

    def record_cycle(
        self,
        baseline_cost: float,
        observed_cost: float,
        baseline_time: float,
        observed_time: float,
        project_id: str | None = None,
    ) -> KPIRecord:
        """Record a KPI cycle.

        Args:
            baseline_cost (`float`):
                The baseline cost (without optimization).
            observed_cost (`float`):
                The observed cost. If project_id is provided, this will be
                overwritten with real cost from ObservabilityHub.
            baseline_time (`float`):
                The baseline time.
            observed_time (`float`):
                The observed time.
            project_id (`str | None`, optional):
                If provided, fetch real cost from ObservabilityHub.

        Returns:
            `KPIRecord`:
                The recorded KPI entry.
        """
        # If project_id is provided, fetch real cost from ObservabilityHub
        if project_id:
            observed_cost = self._get_real_cost(project_id, observed_cost)

        record = KPIRecord(
            timestamp=datetime.now(timezone.utc),
            baseline_cost=baseline_cost,
            observed_cost=observed_cost,
            baseline_time=baseline_time,
            observed_time=observed_time,
        )
        self.records.append(record)
        return record

    def _get_real_cost(
        self,
        project_id: str,
        fallback: float,
    ) -> float:
        """Get real cost from ObservabilityHub.

        Args:
            project_id (`str`):
                The project ID.
            fallback (`float`):
                Fallback value if ObservabilityHub is not available.

        Returns:
            `float`:
                The real cost or fallback.
        """
        try:
            from ..observability import ObservabilityHub

            hub = ObservabilityHub()
            summary = hub.get_project_summary(project_id)
            return summary.get("total_cost_usd", fallback)
        except Exception:
            return fallback

    def achieved_target(self) -> bool:
        if not self.records:
            return False
        latest = self.records[-1]
        return (
            latest.cost_reduction >= self.target
            and latest.time_reduction >= self.target
        )
