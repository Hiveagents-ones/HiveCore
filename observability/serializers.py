"""
Observability serializers.
"""

from rest_framework import serializers
from .models import UsageRecord, ExecutionRecord, TimelineEvent


class UsageRecordSerializer(serializers.ModelSerializer):
    """Serializer for UsageRecord."""

    class Meta:
        model = UsageRecord
        fields = [
            'id', 'timestamp', 'project',
            'agentscope_project_id', 'agentscope_agent_id',
            'agent_name', 'model_name',
            'input_tokens', 'output_tokens', 'total_tokens',
            'cost_usd', 'duration_ms', 'span_id'
        ]
        read_only_fields = ['id']


class UsageRecordIngestSerializer(serializers.Serializer):
    """Serializer for ingesting usage data from agentscope."""

    timestamp = serializers.DateTimeField()
    agentscope_project_id = serializers.CharField(max_length=100, allow_blank=True, default='')
    agentscope_agent_id = serializers.CharField(max_length=100)
    agent_name = serializers.CharField(max_length=100)
    model_name = serializers.CharField(max_length=100)
    input_tokens = serializers.IntegerField(default=0)
    output_tokens = serializers.IntegerField(default=0)
    total_tokens = serializers.IntegerField(default=0)
    cost_usd = serializers.DecimalField(max_digits=10, decimal_places=6, default=0)
    duration_ms = serializers.FloatField(default=0)
    span_id = serializers.CharField(max_length=100, allow_blank=True, default='')


class ExecutionRecordSerializer(serializers.ModelSerializer):
    """Serializer for ExecutionRecord."""

    class Meta:
        model = ExecutionRecord
        fields = [
            'id', 'execution_id', 'project',
            'agentscope_project_id', 'agentscope_agent_id',
            'agent_name', 'node_id', 'round_index',
            'start_time', 'end_time', 'duration_ms',
            'status', 'content', 'error_message',
            'llm_calls', 'total_tokens', 'total_cost_usd'
        ]
        read_only_fields = ['id']


class ExecutionRecordIngestSerializer(serializers.Serializer):
    """Serializer for ingesting execution data from agentscope."""

    execution_id = serializers.CharField(max_length=100)
    agentscope_project_id = serializers.CharField(max_length=100, allow_blank=True, default='')
    agentscope_agent_id = serializers.CharField(max_length=100)
    agent_name = serializers.CharField(max_length=100)
    node_id = serializers.CharField(max_length=100, allow_blank=True, default='')
    round_index = serializers.IntegerField(default=0)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(allow_null=True, required=False)
    duration_ms = serializers.FloatField(allow_null=True, required=False)
    status = serializers.ChoiceField(
        choices=['running', 'completed', 'failed'],
        default='running'
    )
    content = serializers.CharField(allow_blank=True, default='')
    error_message = serializers.CharField(allow_blank=True, default='')
    llm_calls = serializers.IntegerField(default=0)
    total_tokens = serializers.IntegerField(default=0)
    total_cost_usd = serializers.DecimalField(
        max_digits=10, decimal_places=6, default=0
    )


class TimelineEventSerializer(serializers.ModelSerializer):
    """Serializer for TimelineEvent."""

    class Meta:
        model = TimelineEvent
        fields = [
            'id', 'timestamp', 'event_type',
            'agentscope_project_id', 'agentscope_agent_id', 'node_id',
            'message', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']


class TimelineEventIngestSerializer(serializers.Serializer):
    """Serializer for ingesting timeline events from agentscope."""

    event_type = serializers.CharField(max_length=50)
    project_id = serializers.CharField(max_length=100, allow_blank=True, default='')
    agent_id = serializers.CharField(max_length=100, allow_blank=True, default='')
    node_id = serializers.CharField(max_length=100, allow_blank=True, default='')
    message = serializers.CharField(allow_blank=True, default='')
    metadata = serializers.DictField(default=dict)


class UsageSummarySerializer(serializers.Serializer):
    """Serializer for usage summary response."""

    total_tokens = serializers.IntegerField()
    total_cost_usd = serializers.FloatField()
    total_calls = serializers.IntegerField()
    avg_duration_ms = serializers.FloatField()


class ProjectStatsSerializer(serializers.Serializer):
    """Serializer for project observability stats."""

    project_id = serializers.CharField()
    usage = serializers.DictField()
    executions = serializers.DictField()
    active_agents = serializers.ListField()


class ExecutionLogIngestSerializer(serializers.Serializer):
    """Serializer for ingesting execution logs from agentscope.

    Used by AgentScope to push detailed execution logs to Django.
    """

    execution_round_id = serializers.UUIDField()
    level = serializers.ChoiceField(
        choices=['debug', 'info', 'warning', 'error'],
        default='info'
    )
    message = serializers.CharField()
    metadata = serializers.DictField(default=dict, required=False)
    agent_name = serializers.CharField(max_length=100, allow_blank=True, default='')
    source = serializers.CharField(max_length=100, allow_blank=True, default='')
    timestamp = serializers.DateTimeField(required=False)
