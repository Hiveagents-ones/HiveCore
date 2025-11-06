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
    """Keeps running view vs. the 90% optimization target."""

    def __init__(self, *, target_reduction: float = 0.9) -> None:
        self.target = target_reduction
        self.records: list[KPIRecord] = []

    def record_cycle(
        self,
        baseline_cost: float,
        observed_cost: float,
        baseline_time: float,
        observed_time: float,
    ) -> KPIRecord:
        record = KPIRecord(
            timestamp=datetime.now(timezone.utc),
            baseline_cost=baseline_cost,
            observed_cost=observed_cost,
            baseline_time=baseline_time,
            observed_time=observed_time,
        )
        self.records.append(record)
        return record

    def achieved_target(self) -> bool:
        if not self.records:
            return False
        latest = self.records[-1]
        return (
            latest.cost_reduction >= self.target
            and latest.time_reduction >= self.target
        )
