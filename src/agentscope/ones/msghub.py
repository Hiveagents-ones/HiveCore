# -*- coding: utf-8 -*-
"""Utilities to broadcast project updates via MsgHub-like sinks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RoundUpdate:
    """Structured payload describing a project round snapshot."""

    project_id: str
    round_index: int
    summary: str
    status: dict[str, str]


class MsgHubBroadcaster(Protocol):
    """Protocol for broadcasting round updates to interested parties."""

    def broadcast(self, update: RoundUpdate) -> None:  # pragma: no cover - interface
        ...


class InMemoryMsgHub(MsgHubBroadcaster):
    """Testing/diagnostic sink that just records broadcasts."""

    def __init__(self) -> None:
        self.updates: list[RoundUpdate] = []

    def broadcast(self, update: RoundUpdate) -> None:
        self.updates.append(update)
