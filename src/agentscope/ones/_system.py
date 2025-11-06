# -*- coding: utf-8 -*-
"""System-level definitions for the One·s / AgentScope deployment."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class SystemMission:
    """High level description of what the platform optimizes for."""

    name: str
    value_proposition: str
    goal_statement: str
    automation_target: Literal["self_drive", "manual_assist"] = "self_drive"
    target_reduction_pct: float = 0.9


@dataclass
class UserProfile:
    """Persisted context per end-user bound AA instance."""

    user_id: str
    preferences: dict[str, str] = field(default_factory=dict)
    permissions: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SystemProfile:
    """Captures the overall positioning (section I in the whiteboard)."""

    project_name: str
    mission: SystemMission
    aa_description: str
    msg: str = "所求即所得"
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def record_update(self) -> None:
        self.last_updated = datetime.now(timezone.utc)


class SystemRegistry:
    """Keeps mapping between user profiles and their AA instance metadata."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._aa_bindings: dict[str, str] = {}

    def register_user(self, profile: UserProfile, aa_id: str) -> None:
        self._profiles[profile.user_id] = profile
        self._aa_bindings[profile.user_id] = aa_id

    def get_user(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)

    def aa_binding(self, user_id: str) -> str | None:
        return self._aa_bindings.get(user_id)

    def users(self) -> list[UserProfile]:
        return list(self._profiles.values())
