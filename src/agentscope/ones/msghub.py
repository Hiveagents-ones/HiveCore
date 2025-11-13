# -*- coding: utf-8 -*-
"""Utilities to broadcast project updates via MsgHub-like sinks."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol

from ..message import Msg
from ..pipeline import MsgHub


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


class ProjectMsgHubRegistry:
    """Simple registry/factory mapping project id -> MsgHubBroadcaster."""

    def __init__(
        self,
        default_factory: Callable[[], MsgHubBroadcaster] | None = None,
    ) -> None:
        self._registry: dict[str, MsgHubBroadcaster] = {}
        if default_factory is None:
            default_factory = InMemoryMsgHub
        self._default_factory = default_factory

    def bind(self, project_id: str, broadcaster: MsgHubBroadcaster) -> None:
        """Bind/override the broadcaster for a specific project."""
        self._registry[project_id] = broadcaster

    def unbind(self, project_id: str) -> None:
        """Remove a previously registered broadcaster."""
        self._registry.pop(project_id, None)

    def get(self, project_id: str) -> MsgHubBroadcaster:
        """Return the broadcaster for the project (lazily instantiating one)."""
        if project_id not in self._registry:
            self._registry[project_id] = self._default_factory()
        return self._registry[project_id]

    def __call__(self, project_id: str) -> MsgHubBroadcaster:
        return self.get(project_id)


class AgentScopeMsgHubBroadcaster(MsgHubBroadcaster):
    """Bridge that relays round updates through AgentScope's MsgHub."""

    def __init__(
        self,
        *,
        hub: MsgHub,
        sender_name: str = "HiveCoreBroadcast",
        sender_role: Literal["system", "assistant", "user"] = "system",
        formatter: Callable[[RoundUpdate], str] | None = None,
        event_loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._hub = hub
        self._sender_name = sender_name
        self._sender_role = sender_role
        self._formatter = formatter or self._default_format
        self._loop = event_loop

    @staticmethod
    def _default_format(update: RoundUpdate) -> str:
        status_lines = "\n".join(
            f"- {node}: {state}" for node, state in sorted(update.status.items())
        )
        return (
            f"[HiveCore广播]\n"
            f"项目: {update.project_id}\n"
            f"轮次: {update.round_index}\n"
            f"{update.summary}\n"
            f"{status_lines}"
        )

    async def _async_broadcast(self, update: RoundUpdate) -> None:
        text = self._formatter(update)
        metadata = {
            "project_id": update.project_id,
            "round_index": update.round_index,
            "summary": update.summary,
            "status": update.status,
        }
        msg = Msg(
            name=self._sender_name,
            role=self._sender_role,
            content=text,
            metadata=metadata,
        )
        await self._hub.broadcast(msg)

    def _dispatch_on_loop(
        self,
        coro: Coroutine[Any, Any, None],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        if not loop.is_running():
            loop.run_until_complete(coro)
            return
        try:
            current = asyncio.get_running_loop()
        except RuntimeError:
            current = None
        if current is loop:
            loop.create_task(coro)
        else:
            asyncio.run_coroutine_threadsafe(coro, loop)

    def broadcast(self, update: RoundUpdate) -> None:
        coro = self._async_broadcast(update)
        if self._loop is not None:
            self._dispatch_on_loop(coro, self._loop)
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            self._dispatch_on_loop(coro, loop)
        else:
            asyncio.run(coro)
