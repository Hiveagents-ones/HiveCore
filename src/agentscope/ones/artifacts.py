# -*- coding: utf-8 -*-
"""Artifact delivery adapters for final hand-off."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import shortuuid


@dataclass
class ArtifactDeliveryResult:
    """Represents the outcome of a delivery adapter."""

    artifact_type: str
    uri: str
    metadata: dict[str, str]


class ArtifactAdapter:
    """Base adapter that turns task outputs into user-facing artifacts."""

    artifact_type: str = "generic"

    def deliver(
        self,
        *,
        project_id: str,
        plan_summary: str,
        task_status: dict[str, str],
    ) -> ArtifactDeliveryResult:
        raise NotImplementedError


class WebDeployAdapter(ArtifactAdapter):
    artifact_type = "web"

    def __init__(self, base_domain: str = "hivecore.local") -> None:
        self.base_domain = base_domain

    def deliver(
        self,
        *,
        project_id: str,
        plan_summary: str,
        task_status: dict[str, str],
    ) -> ArtifactDeliveryResult:
        slug = shortuuid.uuid()[:8]
        url = f"https://{slug}.{self.base_domain}/{project_id}"
        metadata = {
            "summary": plan_summary,
            "tasks": ";".join(f"{k}:{v}" for k, v in task_status.items()),
        }
        return ArtifactDeliveryResult(artifact_type=self.artifact_type, uri=url, metadata=metadata)


class MediaPackageAdapter(ArtifactAdapter):
    artifact_type = "media"

    def __init__(self, storage_root: str = "s3://hivecore-artifacts") -> None:
        self.storage_root = storage_root.rstrip("/")

    def deliver(
        self,
        *,
        project_id: str,
        plan_summary: str,
        task_status: dict[str, str],
    ) -> ArtifactDeliveryResult:
        package_id = shortuuid.uuid()
        uri = f"{self.storage_root}/{project_id}/{package_id}.zip"
        metadata = {
            "summary": plan_summary,
            "package": package_id,
        }
        return ArtifactDeliveryResult(artifact_type=self.artifact_type, uri=uri, metadata=metadata)


class ArtifactDeliveryManager:
    """Routes delivery requests to registered adapters."""

    def __init__(self, adapters: list[ArtifactAdapter] | None = None) -> None:
        adapters = adapters or []
        self._registry: Dict[str, ArtifactAdapter] = {adapter.artifact_type: adapter for adapter in adapters}

    def register(self, adapter: ArtifactAdapter) -> None:
        self._registry[adapter.artifact_type] = adapter

    def deliver(
        self,
        *,
        artifact_type: str,
        project_id: str,
        plan_summary: str,
        task_status: dict[str, str],
    ) -> ArtifactDeliveryResult | None:
        adapter = self._registry.get(artifact_type)
        if adapter is None:
            return None
        return adapter.deliver(
            project_id=project_id,
            plan_summary=plan_summary,
            task_status=task_status,
        )
