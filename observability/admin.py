from django.contrib import admin
from .models import UsageRecord, ExecutionRecord, TimelineEvent


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'tenant', 'agent_name', 'model_name',
        'total_tokens', 'cost_usd', 'duration_ms'
    ]
    list_filter = ['tenant', 'model_name', 'agent_name']
    search_fields = ['agentscope_project_id', 'agent_name']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'timestamp', 'project')
        }),
        ('agentscope IDs', {
            'fields': ('agentscope_project_id', 'agentscope_agent_id')
        }),
        ('Agent Info', {
            'fields': ('agent_name', 'model_name')
        }),
        ('Token Usage', {
            'fields': ('input_tokens', 'output_tokens', 'total_tokens')
        }),
        ('Metrics', {
            'fields': ('cost_usd', 'duration_ms', 'span_id')
        }),
    )


@admin.register(ExecutionRecord)
class ExecutionRecordAdmin(admin.ModelAdmin):
    list_display = [
        'start_time', 'tenant', 'agent_name', 'status',
        'duration_ms', 'total_tokens'
    ]
    list_filter = ['tenant', 'status', 'agent_name']
    search_fields = ['execution_id', 'agentscope_project_id', 'agent_name']
    readonly_fields = ['id', 'execution_id']
    date_hierarchy = 'start_time'


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'tenant', 'event_type', 'agentscope_agent_id', 'message']
    list_filter = ['tenant', 'event_type']
    search_fields = ['agentscope_project_id', 'message']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'
