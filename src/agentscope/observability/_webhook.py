# -*- coding: utf-8 -*-
"""Webhook exporter for pushing observability data to backend API."""
from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ._types import UsageRecord, AgentExecution, TimelineEvent

logger = logging.getLogger(__name__)


class WebhookExporter:
    """Export observability data to HiveCore backend API.

    This exporter pushes observability data (token usage, agent executions,
    timeline events) to the backend API for persistence and visualization.

    Usage::

        from agentscope.observability import WebhookExporter, ObservabilityHub

        # Initialize exporter
        exporter = WebhookExporter(
            api_url="http://localhost:8000/api/v1/observability",
            api_key="hc_your_api_key_here"
        )

        # Attach to hub for automatic pushing
        hub = ObservabilityHub()
        hub.set_webhook(exporter)

        # Or push manually
        exporter.push_usage(usage_record)
        exporter.push_execution(execution_record)
        exporter.push_timeline_event(timeline_event)

    Args:
        api_url (`str`):
            Base URL of the observability API.
            Defaults to http://localhost:8000/api/v1/observability
        api_key (`str | None`):
            API key for authentication (X-API-Key header).
        timeout (`float`):
            Request timeout in seconds. Defaults to 5.0.
        async_mode (`bool`):
            If True, push requests in background thread.
            Defaults to True for non-blocking operation.
        extra_headers (`dict | None`):
            Additional headers to include in requests.
            Useful for passing execution context like X-Execution-Round.
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000/api/v1/observability",
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        async_mode: bool = True,
        extra_headers: Optional[dict] = None,
    ) -> None:
        """Initialize the webhook exporter."""
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.async_mode = async_mode
        self.extra_headers = extra_headers or {}

        self._session: Optional["requests.Session"] = None
        self._executor: Optional["ThreadPoolExecutor"] = None

    @property
    def session(self) -> "requests.Session":
        """Lazy-initialized requests session."""
        if self._session is None:
            import requests

            self._session = requests.Session()
            if self.api_key:
                self._session.headers["X-API-Key"] = self.api_key
            self._session.headers["Content-Type"] = "application/json"
            # Add extra headers if provided
            for key, value in self.extra_headers.items():
                self._session.headers[key] = value
        return self._session

    @property
    def executor(self) -> "ThreadPoolExecutor":
        """Lazy-initialized thread pool for async requests."""
        if self._executor is None:
            from concurrent.futures import ThreadPoolExecutor

            self._executor = ThreadPoolExecutor(max_workers=2)
        return self._executor

    def push_usage(self, usage: "UsageRecord") -> bool:
        """Push token usage record to backend.

        Args:
            usage (`UsageRecord`):
                The usage record to push.

        Returns:
            `bool`:
                True if successful, False otherwise.
        """
        data = {
            "timestamp": self._format_datetime(usage.timestamp),
            "agentscope_project_id": usage.project_id or "",
            "agentscope_agent_id": usage.agent_id,
            "agent_name": usage.agent_name,
            "model_name": usage.model_name,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "cost_usd": float(usage.cost_usd),
            "duration_ms": usage.duration_ms,
            "span_id": usage.span_id or "",
        }

        if self.async_mode:
            self.executor.submit(self._do_push, "usage", data)
            return True
        else:
            return self._do_push("usage", data)

    def push_execution(self, execution: "AgentExecution") -> bool:
        """Push agent execution record to backend.

        Args:
            execution (`AgentExecution`):
                The execution record to push.

        Returns:
            `bool`:
                True if successful, False otherwise.
        """
        data = {
            "execution_id": execution.execution_id,
            "agentscope_project_id": execution.project_id or "",
            "agentscope_agent_id": execution.agent_id,
            "agent_name": execution.agent_name,
            "node_id": execution.node_id,
            "round_index": execution.round_index,
            "start_time": self._format_datetime(execution.start_time),
            "end_time": (
                self._format_datetime(execution.end_time)
                if execution.end_time
                else None
            ),
            "duration_ms": execution.duration_ms,
            "status": self._get_execution_status(execution),
            "content": execution.content,
            "error_message": execution.error_message or "",
            "llm_calls": execution.llm_calls,
            "total_tokens": execution.total_tokens,
            "total_cost_usd": float(execution.total_cost_usd),
        }

        if self.async_mode:
            self.executor.submit(self._do_push, "execution", data)
            return True
        else:
            return self._do_push("execution", data)

    def push_timeline_event(self, event: "TimelineEvent") -> bool:
        """Push timeline event to backend.

        Args:
            event (`TimelineEvent`):
                The timeline event to push.

        Returns:
            `bool`:
                True if successful, False otherwise.
        """
        data = {
            "event_type": event.event_type,
            "project_id": event.project_id or "",
            "agent_id": event.agent_id or "",
            "node_id": event.node_id or "",
            "message": event.metadata.get("message", ""),
            "metadata": event.metadata,
        }

        if self.async_mode:
            self.executor.submit(self._do_push, "timeline", data)
            return True
        else:
            return self._do_push("timeline", data)

    def _do_push(self, endpoint: str, data: dict) -> bool:
        """Execute the HTTP POST request.

        Args:
            endpoint (`str`):
                The endpoint name (usage, execution, timeline).
            data (`dict`):
                The data to send.

        Returns:
            `bool`:
                True if successful.
        """
        url = f"{self.api_url}/ingest/{endpoint}/"
        try:
            import json

            resp = self.session.post(
                url,
                data=json.dumps(data, default=str),
                timeout=self.timeout,
            )
            if resp.status_code == 201:
                return True
            else:
                logger.warning(
                    f"[WebhookExporter] Failed to push {endpoint}: "
                    f"{resp.status_code} - {resp.text[:200]}"
                )
                return False
        except Exception as e:
            logger.warning(f"[WebhookExporter] Error pushing {endpoint}: {e}")
            return False

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime to ISO 8601 string."""
        return dt.isoformat()

    def _get_execution_status(self, execution: "AgentExecution") -> str:
        """Determine execution status."""
        if execution.end_time is None:
            return "running"
        elif execution.success:
            return "completed"
        else:
            return "failed"

    def close(self) -> None:
        """Close the exporter and cleanup resources."""
        if self._session:
            self._session.close()
            self._session = None
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def __enter__(self) -> "WebhookExporter":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
