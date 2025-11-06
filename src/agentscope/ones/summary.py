# -*- coding: utf-8 -*-
"""Summary utilities (Section VI)."""
from __future__ import annotations

from dataclasses import dataclass

from ._system import SystemProfile
from .kpi import KPITracker
from .questions import OpenQuestionTracker


@dataclass
class SummaryReport:
    overview: str
    achieved_target: bool
    unresolved_questions: int


def build_summary(
    profile: SystemProfile,
    kpi_tracker: KPITracker,
    questions: OpenQuestionTracker,
) -> SummaryReport:
    overview = (
        f"Project {profile.project_name} pursuing {profile.mission.goal_statement}"
        f" via {profile.aa_description}."
    )
    return SummaryReport(
        overview=overview,
        achieved_target=kpi_tracker.achieved_target(),
        unresolved_questions=len(questions.unresolved()),
    )
