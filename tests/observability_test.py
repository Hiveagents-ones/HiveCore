# -*- coding: utf-8 -*-
"""Unit tests for the observability module."""
import pytest
from datetime import datetime

from agentscope.observability import (
    ObservabilityHub,
    UsageCollector,
    TimelineTracker,
    PrometheusExporter,
    JsonExporter,
    AgentExecution,
    UsageRecord,
    TimelineEvent,
    get_model_pricing,
    calculate_cost,
)


@pytest.fixture(autouse=True)
def reset_hub():
    """Reset the ObservabilityHub singleton before each test."""
    ObservabilityHub.reset_instance()
    yield
    ObservabilityHub.reset_instance()


class TestModelPricing:
    """Tests for model pricing utilities."""

    def test_exact_match(self):
        """Test exact model name match."""
        pricing = get_model_pricing("gpt-4o")
        assert pricing["input_per_1k"] == 0.005
        assert pricing["output_per_1k"] == 0.015

    def test_prefix_match(self):
        """Test prefix matching for versioned model names."""
        pricing = get_model_pricing("gpt-4o-2024-08-06")
        assert pricing["input_per_1k"] == 0.005

    def test_contains_match(self):
        """Test contains matching for model families."""
        pricing = get_model_pricing("some-qwen-model")
        assert pricing["input_per_1k"] == 0.0001  # qwen2.5 pricing

    def test_local_model(self):
        """Test local model detection."""
        pricing = get_model_pricing("ollama/llama3")
        assert pricing["input_per_1k"] == 0.0
        assert pricing["output_per_1k"] == 0.0

    def test_calculate_cost(self):
        """Test cost calculation."""
        cost = calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model_name="gpt-4o",
        )
        # 1000 * 0.005/1000 + 500 * 0.015/1000 = 0.005 + 0.0075 = 0.0125
        assert abs(cost - 0.0125) < 0.0001


class TestObservabilityHub:
    """Tests for ObservabilityHub."""

    def test_singleton(self):
        """Test that ObservabilityHub is a singleton."""
        hub1 = ObservabilityHub()
        hub2 = ObservabilityHub()
        assert hub1 is hub2

    def test_record_usage(self):
        """Test recording usage."""
        hub = ObservabilityHub()

        record = UsageRecord(
            timestamp=datetime.now(),
            project_id="proj-1",
            agent_id="agent-1",
            agent_name="TestAgent",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.01,
            duration_ms=500.0,
        )

        hub.record_usage(record)

        assert len(hub.usage_records) == 1
        assert hub.usage_records[0].agent_id == "agent-1"

    def test_get_usage_by_project(self):
        """Test querying usage by project."""
        hub = ObservabilityHub()

        for i in range(3):
            record = UsageRecord(
                timestamp=datetime.now(),
                project_id="proj-1",
                agent_id=f"agent-{i}",
                agent_name=f"Agent{i}",
                model_name="gpt-4o",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.01,
                duration_ms=500.0,
            )
            hub.record_usage(record)

        records = hub.get_usage_by_project("proj-1")
        assert len(records) == 3

    def test_get_project_summary(self):
        """Test project summary calculation."""
        hub = ObservabilityHub()

        for i in range(3):
            record = UsageRecord(
                timestamp=datetime.now(),
                project_id="proj-1",
                agent_id="agent-1",
                agent_name="TestAgent",
                model_name="gpt-4o",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.01,
                duration_ms=500.0,
            )
            hub.record_usage(record)

        summary = hub.get_project_summary("proj-1")

        assert summary["project_id"] == "proj-1"
        assert summary["total_tokens"] == 450
        assert abs(summary["total_cost_usd"] - 0.03) < 0.0001
        assert summary["llm_calls"] == 3


class TestUsageCollector:
    """Tests for UsageCollector."""

    def test_collect_from_chat_usage(self):
        """Test collecting from ChatUsage-like object."""
        hub = ObservabilityHub()
        collector = UsageCollector(hub)

        # Create a mock ChatUsage
        class MockUsage:
            input_tokens = 100
            output_tokens = 50
            time = 0.5

        record = collector.collect_from_chat_usage(
            usage=MockUsage(),
            agent_id="agent-1",
            agent_name="TestAgent",
            model_name="gpt-4o",
            project_id="proj-1",
        )

        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150
        assert record.duration_ms == 500.0
        assert record.cost_usd > 0

        # Verify it was added to hub
        assert len(hub.usage_records) == 1


class TestTimelineTracker:
    """Tests for TimelineTracker."""

    def test_start_and_end_execution(self):
        """Test starting and ending an execution."""
        hub = ObservabilityHub()
        tracker = TimelineTracker(hub)

        exec_id = tracker.start_execution(
            agent_id="agent-1",
            agent_name="TestAgent",
            node_id="task-1",
            project_id="proj-1",
            round_index=1,
        )

        assert exec_id is not None
        assert tracker.is_active(exec_id)

        execution = tracker.end_execution(
            execution_id=exec_id,
            content="Task completed",
            success=True,
        )

        assert not tracker.is_active(exec_id)
        assert execution.success is True
        assert execution.duration_ms is not None
        assert execution.duration_ms > 0

        # Verify timeline events
        events = hub.get_timeline(project_id="proj-1")
        assert len(events) == 2
        assert events[0].event_type == "agent_start"
        assert events[1].event_type == "agent_end"

    def test_update_llm_usage(self):
        """Test updating LLM usage for active execution."""
        tracker = TimelineTracker()

        exec_id = tracker.start_execution(
            agent_id="agent-1",
            agent_name="TestAgent",
            node_id="task-1",
            project_id="proj-1",
            round_index=1,
        )

        tracker.update_llm_usage(exec_id, tokens=150, cost_usd=0.01)
        tracker.update_llm_usage(exec_id, tokens=200, cost_usd=0.02)

        active = tracker.get_active_executions()
        assert active[exec_id].llm_calls == 2
        assert active[exec_id].total_tokens == 350
        assert abs(active[exec_id].total_cost_usd - 0.03) < 0.0001


class TestPrometheusExporter:
    """Tests for PrometheusExporter."""

    def test_export(self):
        """Test Prometheus format export."""
        hub = ObservabilityHub()
        collector = UsageCollector(hub)

        # Add some test data
        class MockUsage:
            input_tokens = 100
            output_tokens = 50
            time = 0.5

        collector.collect_from_chat_usage(
            usage=MockUsage(),
            agent_id="agent-1",
            agent_name="TestAgent",
            model_name="gpt-4o",
        )

        exporter = PrometheusExporter(hub)
        metrics = exporter.export()

        assert "hivecore_tokens_total" in metrics
        assert "hivecore_cost_usd_total" in metrics
        assert "hivecore_llm_calls_total" in metrics
        assert 'agent_id="agent-1"' in metrics

    def test_export_project_metrics(self):
        """Test project-specific metrics export."""
        hub = ObservabilityHub()
        collector = UsageCollector(hub)

        class MockUsage:
            input_tokens = 100
            output_tokens = 50
            time = 0.5

        collector.collect_from_chat_usage(
            usage=MockUsage(),
            agent_id="agent-1",
            agent_name="TestAgent",
            model_name="gpt-4o",
            project_id="proj-1",
        )

        exporter = PrometheusExporter(hub)
        metrics = exporter.export_project_metrics("proj-1")

        assert "hivecore_project_tokens_total" in metrics
        assert 'project_id="proj-1"' in metrics


class TestJsonExporter:
    """Tests for JsonExporter."""

    def test_export(self):
        """Test JSON export."""
        hub = ObservabilityHub()
        collector = UsageCollector(hub)

        class MockUsage:
            input_tokens = 100
            output_tokens = 50
            time = 0.5

        collector.collect_from_chat_usage(
            usage=MockUsage(),
            agent_id="agent-1",
            agent_name="TestAgent",
            model_name="gpt-4o",
            project_id="proj-1",
        )

        exporter = JsonExporter(hub)
        data = exporter.export()

        assert "agents" in data
        assert "executions" in data
        assert "projects" in data
        assert "agent-1" in data["agents"]

    def test_export_timeline(self):
        """Test timeline JSON export."""
        hub = ObservabilityHub()
        tracker = TimelineTracker(hub)

        exec_id = tracker.start_execution(
            agent_id="agent-1",
            agent_name="TestAgent",
            node_id="task-1",
            project_id="proj-1",
            round_index=1,
        )
        tracker.end_execution(exec_id, "Done", True)

        exporter = JsonExporter(hub)
        timeline = exporter.export_timeline("proj-1")

        assert timeline["project_id"] == "proj-1"
        assert len(timeline["events"]) == 2


class TestIntegration:
    """Integration tests for the observability module."""

    def test_full_workflow(self):
        """Test a complete observability workflow."""
        hub = ObservabilityHub()
        collector = UsageCollector(hub)
        tracker = TimelineTracker(hub)

        # Start execution
        exec_id = tracker.start_execution(
            agent_id="agent-1",
            agent_name="StrategyAgent",
            node_id="strategy-task",
            project_id="proj-123",
            round_index=1,
        )

        # Simulate LLM calls
        class MockUsage:
            input_tokens = 500
            output_tokens = 300
            time = 2.5

        record = collector.collect_from_chat_usage(
            usage=MockUsage(),
            agent_id="agent-1",
            agent_name="StrategyAgent",
            model_name="gpt-4o",
            project_id="proj-123",
        )

        # Update execution with LLM usage
        tracker.update_llm_usage(exec_id, record.total_tokens, record.cost_usd)

        # End execution
        execution = tracker.end_execution(
            exec_id,
            content="Strategy plan generated",
            success=True,
        )

        # Verify everything is recorded
        summary = hub.get_project_summary("proj-123")
        assert summary["total_tokens"] == 800
        assert summary["llm_calls"] == 1
        assert summary["agent_executions"] == 1
        assert summary["success_rate"] == 1.0

        # Export metrics
        prom_exporter = PrometheusExporter(hub)
        metrics = prom_exporter.export()
        assert "hivecore_tokens_total" in metrics

        json_exporter = JsonExporter(hub)
        data = json_exporter.export()
        assert "proj-123" in data["projects"]
