"""
Observability models for agentscope integration.

Stores token usage, agent executions, and timeline events
pushed from agentscope's ObservabilityHub.
"""

import uuid
from django.db import models
from tenants.mixins import TenantModelMixin


class UsageRecord(TenantModelMixin):
    """Token usage record from agentscope LLM calls.

    Maps to agentscope's UsageRecord dataclass.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(db_index=True)

    # Link to Django Project (optional, for UI display)
    project = models.ForeignKey(
        'api.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_records'
    )

    # agentscope identifiers (used for data correlation)
    agentscope_project_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='agentscope project ID'
    )
    agentscope_agent_id = models.CharField(
        max_length=100,
        verbose_name='agentscope agent ID'
    )

    # Agent and model info
    agent_name = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)

    # Token counts
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    # Cost and duration
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        verbose_name='Cost (USD)'
    )
    duration_ms = models.FloatField(default=0, verbose_name='Duration (ms)')

    # OpenTelemetry integration
    span_id = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Usage Record'
        verbose_name_plural = 'Usage Records'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['tenant', 'agentscope_project_id']),
            models.Index(fields=['agentscope_project_id', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.agent_name} @ {self.timestamp}: {self.total_tokens} tokens"


class ExecutionRecord(TenantModelMixin):
    """Agent execution record from agentscope.

    Maps to agentscope's AgentExecution dataclass.
    """

    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Unique execution identifier from agentscope
    execution_id = models.CharField(max_length=100, unique=True, db_index=True)

    # Link to Django Project (optional)
    project = models.ForeignKey(
        'api.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='execution_records'
    )

    # agentscope identifiers
    agentscope_project_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='agentscope project ID'
    )
    agentscope_agent_id = models.CharField(
        max_length=100,
        verbose_name='agentscope agent ID'
    )

    # Agent info
    agent_name = models.CharField(max_length=100)
    node_id = models.CharField(max_length=100, blank=True)
    round_index = models.IntegerField(default=0)

    # Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_ms = models.FloatField(null=True, blank=True)

    # Result
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING
    )
    content = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    # Aggregated stats
    llm_calls = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    total_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )

    class Meta:
        verbose_name = 'Execution Record'
        verbose_name_plural = 'Execution Records'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'agentscope_project_id']),
        ]

    def __str__(self):
        return f"{self.agent_name} [{self.status}] @ {self.start_time}"


class TimelineEvent(TenantModelMixin):
    """Timeline event for real-time visualization.

    Maps to agentscope's TimelineEvent dataclass.
    """

    class EventType(models.TextChoices):
        AGENT_START = 'agent_start', 'Agent Start'
        AGENT_END = 'agent_end', 'Agent End'
        LLM_CALL = 'llm_call', 'LLM Call'
        TASK_STATUS = 'task_status', 'Task Status'
        ACCEPTANCE_START = 'acceptance_start', 'Acceptance Start'
        ACCEPTANCE_END = 'acceptance_end', 'Acceptance End'
        ACCEPTANCE_STEP = 'acceptance_step', 'Acceptance Step'
        ACCEPTANCE_CHECK = 'acceptance_check', 'Acceptance Check'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    event_type = models.CharField(max_length=50)

    # agentscope identifiers
    agentscope_project_id = models.CharField(
        max_length=100,
        db_index=True,
        blank=True
    )
    agentscope_agent_id = models.CharField(max_length=100, blank=True)
    node_id = models.CharField(max_length=100, blank=True)

    # Event data
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Timeline Event'
        verbose_name_plural = 'Timeline Events'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['agentscope_project_id', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.timestamp}"
