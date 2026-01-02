# -*- coding: utf-8 -*-
"""Data types for the observability module."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class UsageRecord:
    """Token usage record for a single LLM call.

    Attributes:
        timestamp (`datetime`):
            When this usage occurred.
        project_id (`str | None`):
            The project this usage belongs to.
        agent_id (`str`):
            The agent that made this LLM call.
        agent_name (`str`):
            Human-readable name of the agent.
        model_name (`str`):
            The model used for this call.
        input_tokens (`int`):
            Number of input tokens.
        output_tokens (`int`):
            Number of output tokens.
        total_tokens (`int`):
            Total tokens (input + output).
        cost_usd (`float`):
            Estimated cost in USD.
        duration_ms (`float`):
            Duration of the LLM call in milliseconds.
        span_id (`str | None`):
            Associated OpenTelemetry span ID.
    """

    timestamp: datetime
    project_id: str | None
    agent_id: str
    agent_name: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: float
    span_id: str | None = None


@dataclass
class AgentExecution:
    """Agent execution record with timing information.

    Attributes:
        execution_id (`str`):
            Unique identifier for this execution.
        agent_id (`str`):
            The agent that executed.
        agent_name (`str`):
            Human-readable name of the agent.
        node_id (`str`):
            The task node ID.
        project_id (`str | None`):
            The project this execution belongs to.
        round_index (`int`):
            The execution round number.
        start_time (`datetime`):
            When execution started.
        end_time (`datetime | None`):
            When execution ended.
        duration_ms (`float | None`):
            Duration in milliseconds.
        content (`str`):
            The execution output content.
        success (`bool`):
            Whether execution succeeded.
        error_message (`str | None`):
            Error message if failed.
        llm_calls (`int`):
            Number of LLM calls made during execution.
        total_tokens (`int`):
            Total tokens used during execution.
        total_cost_usd (`float`):
            Total cost in USD during execution.
    """

    execution_id: str
    agent_id: str
    agent_name: str
    node_id: str
    project_id: str | None
    round_index: int
    start_time: datetime
    content: str
    success: bool
    end_time: datetime | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    llm_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


@dataclass
class TimelineEvent:
    """Timeline event for visualizing parallel execution.

    Attributes:
        timestamp (`datetime`):
            When the event occurred.
        event_type (`str`):
            Type of event:
            - agent_start, agent_end: Agent execution lifecycle
            - llm_call: LLM API call
            - task_status: Task status change
            - acceptance_start, acceptance_end: Acceptance validation lifecycle
            - acceptance_step: Acceptance validation step progress
            - acceptance_check: Individual validation check result
        project_id (`str | None`):
            The project this event belongs to.
        agent_id (`str | None`):
            The agent involved.
        node_id (`str | None`):
            The task node ID.
        metadata (`dict[str, Any]`):
            Additional event data.
    """

    timestamp: datetime
    event_type: Literal[
        "agent_start",
        "agent_end",
        "llm_call",
        "task_status",
        "acceptance_start",
        "acceptance_end",
        "acceptance_step",
        "acceptance_check",
    ]
    project_id: str | None = None
    agent_id: str | None = None
    node_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
