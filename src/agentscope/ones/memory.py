# -*- coding: utf-8 -*-
"""Memory, project, and resource pools (Section II.1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


@dataclass
class ProjectDescriptor:
    project_id: str
    name: str
    status: str = "draft"
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectPool:
    """Registry that groups all project contexts."""

    def __init__(self) -> None:
        self._projects: dict[str, ProjectDescriptor] = {}

    def register(self, descriptor: ProjectDescriptor) -> None:
        self._projects[descriptor.project_id] = descriptor

    def get(self, project_id: str) -> ProjectDescriptor | None:
        return self._projects.get(project_id)

    def update_status(self, project_id: str, status: str) -> None:
        if project_id in self._projects:
            self._projects[project_id].status = status

    def list_projects(self) -> list[ProjectDescriptor]:
        return list(self._projects.values())


@dataclass
class MemoryEntry:
    """Captures prompts, tasks, agent descriptors, etc."""

    key: str
    content: str
    tags: set[str] = field(default_factory=set)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryPool:
    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}

    def save(self, entry: MemoryEntry) -> None:
        entry.updated_at = datetime.now(timezone.utc)
        self._store[entry.key] = entry

    def load(self, key: str) -> MemoryEntry | None:
        return self._store.get(key)

    def query_by_tag(self, tag: str) -> list[MemoryEntry]:
        return [entry for entry in self._store.values() if tag in entry.tags]


@dataclass
class ResourceHandle:
    identifier: str
    type: str
    uri: str
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)


class ResourceLibrary:
    """Tracks available MCP endpoints, tools, docs, etc."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceHandle] = {}

    def register(self, resource: ResourceHandle) -> None:
        self._resources[resource.identifier] = resource

    def remove(self, resource_id: str) -> None:
        self._resources.pop(resource_id, None)

    def get(self, resource_id: str) -> ResourceHandle | None:
        return self._resources.get(resource_id)

    def search(self, *, tags: Iterable[str] | None = None, type_: str | None = None) -> list[ResourceHandle]:
        tags = set(tags or [])
        results: list[ResourceHandle] = []
        for handle in self._resources.values():
            if type_ and handle.type != type_:
                continue
            if tags and not tags.issubset(handle.tags):
                continue
            results.append(handle)
        return results
