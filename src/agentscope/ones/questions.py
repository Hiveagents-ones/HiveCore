# -*- coding: utf-8 -*-
"""Tracks open design questions (Section V)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class OpenQuestion:
    prompt: str
    owner: str | None = None
    status: str = "open"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None


class OpenQuestionTracker:
    def __init__(self) -> None:
        self._questions: list[OpenQuestion] = []

    def add(self, question: OpenQuestion) -> None:
        self._questions.append(question)

    def resolve(self, index: int, *, resolution: str | None = None) -> None:
        question = self._questions[index]
        question.status = resolution or "resolved"
        question.resolved_at = datetime.now(timezone.utc)

    def unresolved(self) -> list[OpenQuestion]:
        return [question for question in self._questions if question.status == "open"]
