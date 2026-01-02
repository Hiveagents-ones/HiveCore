from django.contrib import admin
from .models import (
    ExecutionRound,
    AgentSelectionDecision,
    ExecutionArtifact,
    ExecutionLog,
    ExecutionProgress,
)


@admin.register(ExecutionRound)
class ExecutionRoundAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'round_number', 'status', 'started_at', 'completed_at', 'total_tokens']
    list_filter = ['status', 'created_at']
    search_fields = ['project__name', 'celery_task_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(AgentSelectionDecision)
class AgentSelectionDecisionAdmin(admin.ModelAdmin):
    list_display = ['id', 'execution_round', 'agent', 'total_score', 'role_assigned', 'selection_order']
    list_filter = ['created_at']
    search_fields = ['agent__name', 'role_assigned']
    ordering = ['-created_at']


@admin.register(ExecutionArtifact)
class ExecutionArtifactAdmin(admin.ModelAdmin):
    list_display = ['id', 'execution_round', 'artifact_type', 'file_path', 'size_bytes', 'created_at']
    list_filter = ['artifact_type', 'created_at']
    search_fields = ['file_path', 'file_name']
    ordering = ['-created_at']


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'execution_round', 'level', 'message_preview', 'source', 'timestamp']
    list_filter = ['level', 'timestamp']
    search_fields = ['message', 'source']
    ordering = ['-timestamp']

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(ExecutionProgress)
class ExecutionProgressAdmin(admin.ModelAdmin):
    list_display = ['execution_round', 'current_phase', 'current_agent', 'progress_percent', 'updated_at']
    search_fields = ['execution_round__project__name']
    ordering = ['-updated_at']
