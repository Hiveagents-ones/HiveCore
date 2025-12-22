# -*- coding: utf-8 -*-
"""The tracing types class in agentscope."""
from enum import Enum

from opentelemetry import trace

StatusCode = trace.StatusCode


class SpanKind(str, Enum):
    """The span kind."""

    AGENT = "AGENT"
    TOOL = "TOOL"
    LLM = "LLM"
    EMBEDDING = "EMBEDDING"
    FORMATTER = "FORMATTER"
    COMMON = "COMMON"


class SpanAttributes:
    """The span attributes."""

    SPAN_KIND = "span.kind"
    OUTPUT = "output"
    INPUT = "input"
    META = "metadata"
    PROJECT_RUN_ID = "project.run_id"

    # Observability attributes for token usage and cost tracking
    USAGE_TOKENS_INPUT = "usage.tokens.input"
    USAGE_TOKENS_OUTPUT = "usage.tokens.output"
    USAGE_TOKENS_TOTAL = "usage.tokens.total"
    USAGE_COST_USD = "usage.cost.usd"
    USAGE_DURATION_MS = "usage.duration.ms"
    MODEL_NAME = "llm.model_name"
