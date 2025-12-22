# -*- coding: utf-8 -*-
"""Token usage collector from ChatUsage."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ._hub import ObservabilityHub
from ._pricing import calculate_cost
from ._types import UsageRecord

if TYPE_CHECKING:
    from ..model._model_usage import ChatUsage


class UsageCollector:
    """Collector for token usage from LLM calls.

    This class collects ChatUsage data from the tracing layer,
    calculates costs, and stores records in ObservabilityHub.

    Usage::

        collector = UsageCollector()
        record = collector.collect_from_chat_usage(
            usage=chat_usage,
            agent_id="agent-1",
            agent_name="MyAgent",
            model_name="gpt-4o-mini",
        )
    """

    def __init__(self, hub: ObservabilityHub | None = None) -> None:
        """Initialize the collector.

        Args:
            hub (`ObservabilityHub | None`, optional):
                The observability hub to store records.
                Defaults to the singleton instance.
        """
        self.hub = hub or ObservabilityHub()

    def collect_from_chat_usage(
        self,
        usage: "ChatUsage",
        *,
        agent_id: str,
        agent_name: str,
        model_name: str,
        project_id: str | None = None,
        span_id: str | None = None,
    ) -> UsageRecord:
        """Create a UsageRecord from ChatUsage and store it.

        Args:
            usage (`ChatUsage`):
                The chat usage data from model response.
            agent_id (`str`):
                The agent ID that made this call.
            agent_name (`str`):
                Human-readable name of the agent.
            model_name (`str`):
                The model used for this call.
            project_id (`str | None`, optional):
                The project ID if available.
            span_id (`str | None`, optional):
                The OpenTelemetry span ID if available.

        Returns:
            `UsageRecord`:
                The created and stored usage record.
        """
        # Calculate cost based on model pricing
        cost_usd = calculate_cost(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model_name=model_name,
        )

        record = UsageRecord(
            timestamp=datetime.now(),
            project_id=project_id,
            agent_id=agent_id,
            agent_name=agent_name,
            model_name=model_name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
            cost_usd=cost_usd,
            duration_ms=usage.time * 1000,  # Convert seconds to ms
            span_id=span_id,
        )

        self.hub.record_usage(record)
        return record

    def collect_raw(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        duration_seconds: float,
        agent_id: str,
        agent_name: str,
        model_name: str,
        project_id: str | None = None,
        span_id: str | None = None,
    ) -> UsageRecord:
        """Create a UsageRecord from raw values.

        Useful when ChatUsage is not available.

        Args:
            input_tokens (`int`):
                Number of input tokens.
            output_tokens (`int`):
                Number of output tokens.
            duration_seconds (`float`):
                Duration in seconds.
            agent_id (`str`):
                The agent ID.
            agent_name (`str`):
                Human-readable agent name.
            model_name (`str`):
                The model name.
            project_id (`str | None`, optional):
                The project ID.
            span_id (`str | None`, optional):
                The span ID.

        Returns:
            `UsageRecord`:
                The created and stored usage record.
        """
        cost_usd = calculate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
        )

        record = UsageRecord(
            timestamp=datetime.now(),
            project_id=project_id,
            agent_id=agent_id,
            agent_name=agent_name,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_seconds * 1000,
            span_id=span_id,
        )

        self.hub.record_usage(record)
        return record
