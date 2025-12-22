# -*- coding: utf-8 -*-
"""Prometheus metrics exporter."""
from __future__ import annotations

from typing import Protocol

from ._hub import ObservabilityHub


class MetricsExporter(Protocol):
    """Protocol for metrics exporters."""

    def export(self) -> str:
        """Export metrics in a specific format.

        Returns:
            `str`:
                Formatted metrics string.
        """
        ...


class PrometheusExporter:
    """Exporter for Prometheus format metrics.

    This class exports observability data in Prometheus text format,
    suitable for scraping by Prometheus server.

    Usage::

        exporter = PrometheusExporter()
        metrics_text = exporter.export()

        # Or for a specific project
        project_metrics = exporter.export_project_metrics("proj-123")
    """

    def __init__(self, hub: ObservabilityHub | None = None) -> None:
        """Initialize the exporter.

        Args:
            hub (`ObservabilityHub | None`, optional):
                The observability hub to read data from.
                Defaults to the singleton instance.
        """
        self.hub = hub or ObservabilityHub()

    def export(self) -> str:
        """Export all metrics in Prometheus format.

        Returns:
            `str`:
                Prometheus-formatted metrics text.
        """
        lines = []

        # Token usage metrics
        self._export_token_metrics(lines)

        # Cost metrics
        self._export_cost_metrics(lines)

        # LLM call metrics
        self._export_llm_call_metrics(lines)

        # Execution duration metrics
        self._export_execution_metrics(lines)

        return "\n".join(lines) + "\n"

    def _export_token_metrics(self, lines: list) -> None:
        """Export token usage metrics."""
        lines.append("# HELP hivecore_tokens_total Total tokens used")
        lines.append("# TYPE hivecore_tokens_total counter")

        for agent_id in self.hub.get_all_agents():
            records = self.hub.get_usage_by_agent(agent_id)
            if not records:
                continue

            input_tokens = sum(r.input_tokens for r in records)
            output_tokens = sum(r.output_tokens for r in records)
            total_tokens = sum(r.total_tokens for r in records)

            latest = records[-1]
            agent_name = self._escape_label(latest.agent_name)
            model_name = self._escape_label(latest.model_name)

            lines.append(
                f'hivecore_tokens_total{{agent_id="{agent_id}",'
                f'agent_name="{agent_name}",model="{model_name}",'
                f'type="input"}} {input_tokens}'
            )
            lines.append(
                f'hivecore_tokens_total{{agent_id="{agent_id}",'
                f'agent_name="{agent_name}",model="{model_name}",'
                f'type="output"}} {output_tokens}'
            )
            lines.append(
                f'hivecore_tokens_total{{agent_id="{agent_id}",'
                f'agent_name="{agent_name}",model="{model_name}",'
                f'type="total"}} {total_tokens}'
            )

    def _export_cost_metrics(self, lines: list) -> None:
        """Export cost metrics."""
        lines.append("# HELP hivecore_cost_usd_total Total cost in USD")
        lines.append("# TYPE hivecore_cost_usd_total counter")

        for agent_id in self.hub.get_all_agents():
            records = self.hub.get_usage_by_agent(agent_id)
            if not records:
                continue

            total_cost = sum(r.cost_usd for r in records)
            latest = records[-1]
            agent_name = self._escape_label(latest.agent_name)

            lines.append(
                f'hivecore_cost_usd_total{{agent_id="{agent_id}",'
                f'agent_name="{agent_name}"}} {total_cost:.6f}'
            )

    def _export_llm_call_metrics(self, lines: list) -> None:
        """Export LLM call count metrics."""
        lines.append("# HELP hivecore_llm_calls_total Total LLM calls")
        lines.append("# TYPE hivecore_llm_calls_total counter")

        for agent_id in self.hub.get_all_agents():
            records = self.hub.get_usage_by_agent(agent_id)
            if not records:
                continue

            latest = records[-1]
            agent_name = self._escape_label(latest.agent_name)

            lines.append(
                f'hivecore_llm_calls_total{{agent_id="{agent_id}",'
                f'agent_name="{agent_name}"}} {len(records)}'
            )

    def _export_execution_metrics(self, lines: list) -> None:
        """Export execution duration metrics."""
        lines.append(
            "# HELP hivecore_agent_execution_duration_ms "
            "Agent execution duration in milliseconds"
        )
        lines.append("# TYPE hivecore_agent_execution_duration_ms histogram")

        for execution in self.hub.agent_executions:
            if execution.duration_ms is None:
                continue

            agent_name = self._escape_label(execution.agent_name)
            node_id = self._escape_label(execution.node_id)
            success = "true" if execution.success else "false"

            lines.append(
                f'hivecore_agent_execution_duration_ms'
                f'{{agent_id="{execution.agent_id}",'
                f'agent_name="{agent_name}",'
                f'node_id="{node_id}",'
                f'success="{success}"}} {execution.duration_ms:.2f}'
            )

    def export_project_metrics(self, project_id: str) -> str:
        """Export metrics for a specific project.

        Args:
            project_id (`str`):
                The project ID to export metrics for.

        Returns:
            `str`:
                Prometheus-formatted metrics text for the project.
        """
        summary = self.hub.get_project_summary(project_id)
        project_label = self._escape_label(project_id)

        lines = [
            f"# Project: {project_id}",
            f'hivecore_project_tokens_total{{project_id="{project_label}"}} '
            f'{summary["total_tokens"]}',
            f'hivecore_project_cost_usd_total{{project_id="{project_label}"}} '
            f'{summary["total_cost_usd"]:.6f}',
            f'hivecore_project_llm_calls_total{{project_id="{project_label}"}} '
            f'{summary["llm_calls"]}',
            f'hivecore_project_agent_executions_total'
            f'{{project_id="{project_label}"}} {summary["agent_executions"]}',
            f'hivecore_project_success_rate{{project_id="{project_label}"}} '
            f'{summary["success_rate"]:.4f}',
            f'hivecore_project_avg_execution_time_ms'
            f'{{project_id="{project_label}"}} '
            f'{summary["avg_execution_time_ms"]:.2f}',
        ]

        return "\n".join(lines) + "\n"

    @staticmethod
    def _escape_label(value: str) -> str:
        """Escape special characters in Prometheus label values.

        Args:
            value (`str`):
                The label value to escape.

        Returns:
            `str`:
                Escaped label value.
        """
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class JsonExporter:
    """Exporter for JSON format metrics.

    Useful for custom dashboards and APIs.
    """

    def __init__(self, hub: ObservabilityHub | None = None) -> None:
        """Initialize the exporter.

        Args:
            hub (`ObservabilityHub | None`, optional):
                The observability hub to read data from.
        """
        self.hub = hub or ObservabilityHub()

    def export(self) -> dict:
        """Export all metrics as a dictionary.

        Returns:
            `dict`:
                Dictionary with metrics data.
        """
        agents_data = {}

        for agent_id in self.hub.get_all_agents():
            records = self.hub.get_usage_by_agent(agent_id)
            if not records:
                continue

            latest = records[-1]
            agents_data[agent_id] = {
                "agent_name": latest.agent_name,
                "model": latest.model_name,
                "input_tokens": sum(r.input_tokens for r in records),
                "output_tokens": sum(r.output_tokens for r in records),
                "total_tokens": sum(r.total_tokens for r in records),
                "total_cost_usd": sum(r.cost_usd for r in records),
                "llm_calls": len(records),
            }

        executions_data = [
            {
                "execution_id": e.execution_id,
                "agent_id": e.agent_id,
                "agent_name": e.agent_name,
                "node_id": e.node_id,
                "project_id": e.project_id,
                "round_index": e.round_index,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "duration_ms": e.duration_ms,
                "success": e.success,
            }
            for e in self.hub.agent_executions
        ]

        return {
            "agents": agents_data,
            "executions": executions_data,
            "projects": {
                pid: self.hub.get_project_summary(pid)
                for pid in self.hub.get_all_projects()
            },
        }

    def export_timeline(self, project_id: str | None = None) -> dict:
        """Export timeline data for visualization.

        Args:
            project_id (`str | None`, optional):
                Filter by project ID.

        Returns:
            `dict`:
                Timeline data dictionary.
        """
        events = self.hub.get_timeline(project_id=project_id)

        return {
            "project_id": project_id,
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "agent_id": e.agent_id,
                    "node_id": e.node_id,
                    "metadata": e.metadata,
                }
                for e in events
            ],
        }
