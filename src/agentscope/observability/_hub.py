# -*- coding: utf-8 -*-
"""Observability data hub - central storage and query."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Dict, List

from typing import TYPE_CHECKING

from ._types import AgentExecution, TimelineEvent, UsageRecord

if TYPE_CHECKING:
    from ._webhook import WebhookExporter


class ObservabilityHub:
    """Centralized observability data store.

    This is a singleton class that stores all observability data in memory
    and provides query interfaces for metrics, timelines, and summaries.

    Usage::

        hub = ObservabilityHub()
        hub.record_usage(usage_record)
        summary = hub.get_project_summary("project-123")

    Thread-safety is ensured via locks.
    """

    _instance: "ObservabilityHub | None" = None
    _lock: Lock = Lock()

    def __new__(cls) -> "ObservabilityHub":
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize the hub."""
        if getattr(self, "_initialized", False):
            return

        self._data_lock = Lock()

        # Data storage
        self.usage_records: List[UsageRecord] = []
        self.agent_executions: List[AgentExecution] = []
        self.timeline_events: List[TimelineEvent] = []

        # Indexes for fast lookup
        self._project_usage_index: Dict[str, List[int]] = defaultdict(list)
        self._agent_usage_index: Dict[str, List[int]] = defaultdict(list)
        self._project_execution_index: Dict[str, List[int]] = defaultdict(list)

        # Webhook exporter (optional)
        self._webhook: "WebhookExporter | None" = None

        self._initialized = True

    def set_webhook(self, webhook: "WebhookExporter") -> None:
        """Set webhook exporter for pushing data to backend.

        Args:
            webhook (`WebhookExporter`):
                The webhook exporter instance.

        Example::

            from agentscope.observability import ObservabilityHub, WebhookExporter

            hub = ObservabilityHub()
            exporter = WebhookExporter(
                api_url="http://localhost:8000/api/v1/observability",
                api_key="hc_your_api_key"
            )
            hub.set_webhook(exporter)
        """
        self._webhook = webhook

    def clear_webhook(self) -> None:
        """Remove the webhook exporter."""
        self._webhook = None

    def record_usage(self, usage: UsageRecord) -> None:
        """Record a token usage entry.

        Args:
            usage (`UsageRecord`):
                The usage record to store.
        """
        with self._data_lock:
            idx = len(self.usage_records)
            self.usage_records.append(usage)

            if usage.project_id:
                self._project_usage_index[usage.project_id].append(idx)
            self._agent_usage_index[usage.agent_id].append(idx)

        # Push to webhook if configured
        if self._webhook:
            self._webhook.push_usage(usage)

    def record_execution(self, execution: AgentExecution) -> None:
        """Record an agent execution entry.

        Args:
            execution (`AgentExecution`):
                The execution record to store.
        """
        with self._data_lock:
            idx = len(self.agent_executions)
            self.agent_executions.append(execution)

            if execution.project_id:
                self._project_execution_index[execution.project_id].append(idx)

        # Push to webhook if configured
        if self._webhook:
            self._webhook.push_execution(execution)

    def record_timeline_event(self, event: TimelineEvent) -> None:
        """Record a timeline event.

        Args:
            event (`TimelineEvent`):
                The timeline event to store.
        """
        with self._data_lock:
            self.timeline_events.append(event)

        # Push to webhook if configured
        if self._webhook:
            self._webhook.push_timeline_event(event)

    def get_usage_by_project(
        self,
        project_id: str,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> List[UsageRecord]:
        """Get usage records for a project.

        Args:
            project_id (`str`):
                The project ID to query.
            time_range (`tuple[datetime, datetime] | None`, optional):
                Filter by time range (start, end).

        Returns:
            `List[UsageRecord]`:
                List of usage records.
        """
        with self._data_lock:
            indices = self._project_usage_index.get(project_id, [])
            records = [self.usage_records[i] for i in indices]

        if time_range:
            start, end = time_range
            records = [r for r in records if start <= r.timestamp <= end]

        return records

    def get_usage_by_agent(
        self,
        agent_id: str,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> List[UsageRecord]:
        """Get usage records for an agent.

        Args:
            agent_id (`str`):
                The agent ID to query.
            time_range (`tuple[datetime, datetime] | None`, optional):
                Filter by time range (start, end).

        Returns:
            `List[UsageRecord]`:
                List of usage records.
        """
        with self._data_lock:
            indices = self._agent_usage_index.get(agent_id, [])
            records = [self.usage_records[i] for i in indices]

        if time_range:
            start, end = time_range
            records = [r for r in records if start <= r.timestamp <= end]

        return records

    def get_executions_by_project(
        self,
        project_id: str,
    ) -> List[AgentExecution]:
        """Get execution records for a project.

        Args:
            project_id (`str`):
                The project ID to query.

        Returns:
            `List[AgentExecution]`:
                List of execution records.
        """
        with self._data_lock:
            indices = self._project_execution_index.get(project_id, [])
            return [self.agent_executions[i] for i in indices]

    def get_project_summary(self, project_id: str) -> dict:
        """Get aggregated summary for a project.

        Args:
            project_id (`str`):
                The project ID to query.

        Returns:
            `dict`:
                Summary dictionary with keys:
                - project_id
                - total_tokens
                - total_cost_usd
                - llm_calls
                - agent_executions
                - agents_used
                - success_rate
                - avg_execution_time_ms
        """
        records = self.get_usage_by_project(project_id)
        executions = self.get_executions_by_project(project_id)

        total_duration = sum(
            e.duration_ms for e in executions if e.duration_ms is not None
        )
        success_count = sum(1 for e in executions if e.success)

        return {
            "project_id": project_id,
            "total_tokens": sum(r.total_tokens for r in records),
            "total_cost_usd": sum(r.cost_usd for r in records),
            "llm_calls": len(records),
            "agent_executions": len(executions),
            "agents_used": len(set(e.agent_id for e in executions)),
            "success_rate": (
                success_count / len(executions) if executions else 0.0
            ),
            "avg_execution_time_ms": (
                total_duration / len(executions) if executions else 0.0
            ),
        }

    def get_timeline(
        self,
        project_id: str | None = None,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> List[TimelineEvent]:
        """Get timeline events for visualization.

        Args:
            project_id (`str | None`, optional):
                Filter by project.
            time_range (`tuple[datetime, datetime] | None`, optional):
                Filter by time range.

        Returns:
            `List[TimelineEvent]`:
                Sorted list of timeline events.
        """
        with self._data_lock:
            events = list(self.timeline_events)

        if project_id:
            events = [e for e in events if e.project_id == project_id]

        if time_range:
            start, end = time_range
            events = [e for e in events if start <= e.timestamp <= end]

        return sorted(events, key=lambda e: e.timestamp)

    def get_all_agents(self) -> List[str]:
        """Get all agent IDs that have usage records.

        Returns:
            `List[str]`:
                List of unique agent IDs.
        """
        with self._data_lock:
            return list(self._agent_usage_index.keys())

    def get_all_projects(self) -> List[str]:
        """Get all project IDs that have usage records.

        Returns:
            `List[str]`:
                List of unique project IDs.
        """
        with self._data_lock:
            return list(self._project_usage_index.keys())

    def clear(self) -> None:
        """Clear all data. Useful for testing."""
        with self._data_lock:
            self.usage_records.clear()
            self.agent_executions.clear()
            self.timeline_events.clear()
            self._project_usage_index.clear()
            self._agent_usage_index.clear()
            self._project_execution_index.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        with cls._lock:
            cls._instance = None
