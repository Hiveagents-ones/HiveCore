# -*- coding: utf-8 -*-
"""Observability module for HiveCore.

This module provides comprehensive observability features for monitoring
agent execution, token usage, costs, and performance metrics.

Components:
    - ObservabilityHub: Central data store for all observability data
    - UsageCollector: Collects token usage from LLM calls
    - TimelineTracker: Tracks agent execution timelines
    - PrometheusExporter: Exports metrics in Prometheus format
    - JsonExporter: Exports metrics as JSON

Usage::

    from agentscope.observability import (
        ObservabilityHub,
        UsageCollector,
        TimelineTracker,
        PrometheusExporter,
    )

    # Data is automatically collected when tracing is enabled
    hub = ObservabilityHub()

    # Query project summary
    summary = hub.get_project_summary("project-123")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Total cost: ${summary['total_cost_usd']:.4f}")

    # Export Prometheus metrics
    exporter = PrometheusExporter()
    print(exporter.export())
"""
from ._hub import ObservabilityHub
from ._metrics_exporter import JsonExporter, PrometheusExporter
from ._pricing import calculate_cost, get_model_pricing
from ._timeline_tracker import TimelineTracker
from ._types import AgentExecution, TimelineEvent, UsageRecord
from ._usage_collector import UsageCollector

__all__ = [
    # Core hub
    "ObservabilityHub",
    # Collectors and trackers
    "UsageCollector",
    "TimelineTracker",
    # Exporters
    "PrometheusExporter",
    "JsonExporter",
    # Types
    "UsageRecord",
    "AgentExecution",
    "TimelineEvent",
    # Utilities
    "get_model_pricing",
    "calculate_cost",
]
