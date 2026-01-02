# -*- coding: utf-8 -*-
"""Serializers for execution app."""
from rest_framework import serializers
from .models import (
    ExecutionRound,
    AgentSelectionDecision,
    ExecutionArtifact,
    ExecutionLog,
    ExecutionProgress,
)


class ExecutionProgressSerializer(serializers.ModelSerializer):
    """Serializer for execution progress."""

    class Meta:
        model = ExecutionProgress
        fields = [
            'current_phase',
            'current_agent',
            'current_task',
            'progress_percent',
            'completed_tasks',
            'total_tasks',
            'completed_requirements',
            'total_requirements',
            'last_event',
            'last_event_data',
            'updated_at',
        ]


class ExecutionRoundListSerializer(serializers.ModelSerializer):
    """Serializer for execution round list view."""

    project_name = serializers.CharField(source='project.name', read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = ExecutionRound
        fields = [
            'id',
            'project',
            'project_name',
            'round_number',
            'status',
            'started_at',
            'completed_at',
            'duration_seconds',
            'total_tokens',
            'total_cost_usd',
            'created_at',
        ]


class ExecutionRoundDetailSerializer(serializers.ModelSerializer):
    """Serializer for execution round detail view."""

    project_name = serializers.CharField(source='project.name', read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)
    progress = ExecutionProgressSerializer(read_only=True)

    class Meta:
        model = ExecutionRound
        fields = [
            'id',
            'project',
            'project_name',
            'round_number',
            'status',
            'started_at',
            'completed_at',
            'duration_seconds',
            'celery_task_id',
            'requirement_text',
            'options',
            'summary',
            'error_message',
            'total_tokens',
            'total_cost_usd',
            'total_llm_calls',
            'progress',
            'created_at',
            'updated_at',
        ]


class ExecutionStartSerializer(serializers.Serializer):
    """Serializer for starting execution."""

    requirement = serializers.CharField(required=True, help_text='Requirement text')
    max_rounds = serializers.IntegerField(default=3, min_value=1, max_value=10)
    parallel = serializers.BooleanField(default=True)
    pr_mode = serializers.BooleanField(default=True)
    skip_validation = serializers.BooleanField(default=False)
    edit_mode = serializers.BooleanField(default=False)


class AgentSelectionDecisionListSerializer(serializers.ModelSerializer):
    """Serializer for agent selection decision list view."""

    class Meta:
        model = AgentSelectionDecision
        fields = [
            'id',
            'agent',
            'agent_name',
            's_base_score',
            'requirement_fit_score',
            'total_score',
            'is_selected',
            'is_cold_start',
            'decision_source',
            'selection_order',
            'created_at',
        ]


class AgentSelectionDecisionSerializer(serializers.ModelSerializer):
    """Serializer for agent selection decision detail view."""

    class Meta:
        model = AgentSelectionDecision
        fields = [
            'id',
            'execution_round',
            'agent',
            'agent_name',
            's_base_score',
            'requirement_fit_score',
            'total_score',
            'scoring_breakdown',
            'requirement_fit_matched',
            'requirement_fit_missing',
            'requirement_fit_partial',
            'requirement_fit_rationales',
            'is_cold_start',
            'cold_start_slot_reserved',
            'risk_notes',
            'is_selected',
            'decision_source',
            'reasons',
            'role_assigned',
            'selection_order',
            'batch_index',
            'created_at',
        ]


class AgentSelectionDecisionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating agent selection decisions from AgentScope."""

    agent_id = serializers.CharField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = AgentSelectionDecision
        fields = [
            'execution_round',
            'agent',
            'agent_id',
            'agent_name',
            's_base_score',
            'requirement_fit_score',
            'total_score',
            'scoring_breakdown',
            'requirement_fit_matched',
            'requirement_fit_missing',
            'requirement_fit_partial',
            'requirement_fit_rationales',
            'is_cold_start',
            'cold_start_slot_reserved',
            'risk_notes',
            'is_selected',
            'decision_source',
            'reasons',
            'role_assigned',
            'selection_order',
            'batch_index',
        ]

    def create(self, validated_data):
        """Create selection decision, resolving agent by agent_id if needed."""
        from api.models import Agent

        agent_id = validated_data.pop('agent_id', None)

        # If agent_id is provided but agent is not, try to find the agent
        if agent_id and not validated_data.get('agent'):
            try:
                agent = Agent.objects.get(pk=agent_id)
                validated_data['agent'] = agent
            except Agent.DoesNotExist:
                pass  # Agent may be dynamically spawned, just save the name

        return super().create(validated_data)


class ExecutionArtifactListSerializer(serializers.ModelSerializer):
    """Serializer for artifact list view."""

    download_url = serializers.SerializerMethodField()
    storage_type = serializers.SerializerMethodField()

    class Meta:
        model = ExecutionArtifact
        fields = [
            'id',
            'artifact_type',
            'file_path',
            'file_name',
            'language',
            'size_bytes',
            'storage_type',
            'download_url',
            'created_at',
        ]

    def get_storage_type(self, obj) -> str:
        """Get storage type (s3 or database)."""
        return 's3' if obj.s3_key else 'database'

    def get_download_url(self, obj) -> str | None:
        """Get CloudFront URL for S3-stored artifacts."""
        if obj.s3_key:
            from .storage import get_cloudfront_url
            return get_cloudfront_url(obj.s3_key)
        return None


class ExecutionArtifactDetailSerializer(serializers.ModelSerializer):
    """Serializer for artifact detail view with content."""

    generated_by_agent_name = serializers.CharField(
        source='generated_by_agent.name',
        read_only=True,
        allow_null=True,
    )
    download_url = serializers.SerializerMethodField()
    storage_type = serializers.SerializerMethodField()

    class Meta:
        model = ExecutionArtifact
        fields = [
            'id',
            'execution_round',
            'artifact_type',
            'file_path',
            'file_name',
            'language',
            'content',
            'content_hash',
            'size_bytes',
            's3_key',
            'storage_type',
            'download_url',
            'generated_by_agent',
            'generated_by_agent_name',
            'created_at',
            'updated_at',
        ]

    def get_storage_type(self, obj) -> str:
        """Get storage type (s3 or database)."""
        return 's3' if obj.s3_key else 'database'

    def get_download_url(self, obj) -> str | None:
        """Get CloudFront URL for S3-stored artifacts."""
        if obj.s3_key:
            from .storage import get_cloudfront_url
            return get_cloudfront_url(obj.s3_key)
        return None


class ExecutionLogSerializer(serializers.ModelSerializer):
    """Serializer for execution log."""

    agent_name = serializers.CharField(source='agent.name', read_only=True, allow_null=True)

    class Meta:
        model = ExecutionLog
        fields = [
            'id',
            'level',
            'message',
            'metadata',
            'agent',
            'agent_name',
            'source',
            'timestamp',
        ]


# ============== Suggest Agents Serializers ==============


class RequirementItemSerializer(serializers.Serializer):
    """Serializer for a single requirement item."""

    id = serializers.CharField(required=True, help_text='Requirement ID')
    content = serializers.CharField(required=True, help_text='Requirement content')
    skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='Optional skills for this requirement',
    )


class SuggestAgentsRequestSerializer(serializers.Serializer):
    """Serializer for suggest-agents request."""

    requirements = serializers.ListField(
        child=RequirementItemSerializer(),
        required=True,
        min_length=1,
        help_text='List of requirements to analyze',
    )


class AgentSuggestionSerializer(serializers.Serializer):
    """Serializer for a single agent suggestion (legacy format)."""

    role = serializers.CharField(help_text='Agent role identifier')
    agent_id = serializers.CharField(help_text='Unique agent identifier')
    name = serializers.CharField(help_text='Agent display name')
    description = serializers.CharField(help_text='Agent description')
    skills = serializers.ListField(
        child=serializers.CharField(),
        help_text='Agent skills',
    )
    domains = serializers.ListField(
        child=serializers.CharField(),
        help_text='Agent domains',
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        help_text='Agent tags',
    )
    parent_domain = serializers.CharField(
        allow_null=True,
        required=False,
        help_text='Parent domain',
    )
    system_prompt = serializers.CharField(
        allow_null=True,
        required=False,
        help_text='Agent system prompt',
    )


class MetasoAgentSerializer(serializers.Serializer):
    """Serializer for Metaso-generated agent spec (planned, not yet in library)."""

    agent_id = serializers.CharField(help_text='Temporary agent ID (e.g., metaso_frontend_xxx)')
    name = serializers.CharField(help_text='Agent display name')
    description = serializers.CharField(help_text='Agent description')
    skills = serializers.ListField(
        child=serializers.CharField(),
        help_text='Agent skills',
    )
    domains = serializers.ListField(
        child=serializers.CharField(),
        help_text='Agent domains',
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='Agent tags',
    )
    parent_domain = serializers.CharField(
        allow_null=True,
        required=False,
        help_text='Parent domain',
    )
    system_prompt = serializers.CharField(
        allow_null=True,
        required=False,
        help_text='Agent system prompt',
    )
    estimated_score = serializers.FloatField(help_text='Estimated score for this agent')


class LibraryAgentSerializer(serializers.Serializer):
    """Serializer for library agent (existing agent in database)."""

    agent_id = serializers.IntegerField(help_text='Agent ID in database')
    name = serializers.CharField(help_text='Agent display name')
    avatar = serializers.CharField(allow_blank=True, help_text='Agent avatar URL')
    duty = serializers.CharField(allow_blank=True, required=False, help_text='Agent duty/role')
    detail = serializers.CharField(allow_blank=True, required=False, help_text='Agent detail')
    cost_per_min = serializers.FloatField(required=False, help_text='Cost per minute')
    score = serializers.FloatField(help_text='Computed score for this agent')


class RoleSuggestionSerializer(serializers.Serializer):
    """Serializer for role suggestion with both Metaso and library agents."""

    role = serializers.CharField(help_text='Role/position name')
    metaso_agent = MetasoAgentSerializer(help_text='Metaso-generated agent spec')
    library_agent = LibraryAgentSerializer(
        allow_null=True,
        required=False,
        help_text='Best matching library agent (null if none found)',
    )
    default_is_metaso = serializers.BooleanField(
        help_text='True if Metaso agent has higher score and should be default',
    )
    default_agent_id = serializers.CharField(
        help_text='ID of the default selected agent (Metaso temp ID or library agent ID)',
    )


class SuggestAgentsResponseSerializer(serializers.Serializer):
    """Serializer for suggest-agents response (enhanced format)."""

    suggestions = serializers.ListField(
        child=RoleSuggestionSerializer(),
        help_text='List of role suggestions with Metaso and library agents',
    )
    reasoning = serializers.CharField(
        allow_blank=True,
        help_text='LLM reasoning for suggestions',
    )
    complexity = serializers.CharField(help_text='Project complexity assessment')


# ============ Rank Agents Serializers ============

class RankAgentsRequestSerializer(serializers.Serializer):
    """Serializer for rank-agents request."""

    role = serializers.CharField(help_text='Role/position to find candidates for')
    skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='Required skills for this role',
    )
    domains = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='Required domains for this role',
    )
    metaso_spec = MetasoAgentSerializer(
        required=False,
        allow_null=True,
        help_text='Metaso agent spec to include in ranking',
    )
    offset = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        help_text='Pagination offset',
    )
    limit = serializers.IntegerField(
        required=False,
        default=3,
        min_value=1,
        max_value=20,
        help_text='Number of candidates to return',
    )


class RankedAgentSerializer(serializers.Serializer):
    """Serializer for a ranked agent candidate."""

    agent_id = serializers.CharField(help_text='Agent ID (Metaso temp ID or library ID)')
    is_metaso = serializers.BooleanField(help_text='True if this is a Metaso agent')
    name = serializers.CharField(help_text='Agent display name')
    avatar = serializers.CharField(allow_blank=True, help_text='Agent avatar URL')
    duty = serializers.CharField(allow_blank=True, help_text='Agent duty/role')
    detail = serializers.CharField(allow_blank=True, help_text='Agent detail')
    cost_per_min = serializers.FloatField(help_text='Cost per minute')
    total_score = serializers.FloatField(help_text='Total combined score')
    s_base_score = serializers.FloatField(help_text='Static base score')
    requirement_fit_score = serializers.FloatField(help_text='Requirement fit score')


class RankAgentsResponseSerializer(serializers.Serializer):
    """Serializer for rank-agents response."""

    candidates = serializers.ListField(
        child=RankedAgentSerializer(),
        help_text='List of ranked agent candidates',
    )
    has_more = serializers.BooleanField(help_text='True if more candidates available')
    threshold_reached = serializers.BooleanField(
        help_text='True if remaining candidates are below score threshold',
    )


# ============ Create Metaso Agent Serializers ============

class CreateMetasoAgentRequestSerializer(serializers.Serializer):
    """Serializer for create-metaso-agent request."""

    spec = MetasoAgentSerializer(help_text='Metaso agent specification')
    project_id = serializers.IntegerField(help_text='Project ID to associate with')


# ============ Avatar Generation Serializers ============

class AvatarGenerationRequestSerializer(serializers.Serializer):
    """Serializer for avatar generation request."""

    agents = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of agents needing avatars, each with agent_id, name, description',
    )
    style = serializers.ChoiceField(
        choices=['professional', 'cartoon', 'pixel', '3d'],
        default='professional',
        help_text='Avatar style: professional, cartoon, pixel, or 3d',
    )


class AvatarResultSerializer(serializers.Serializer):
    """Serializer for a single avatar generation result."""

    agent_id = serializers.CharField(help_text='Agent identifier')
    avatar_url = serializers.CharField(
        allow_null=True,
        help_text='URL to generated avatar image',
    )
    error = serializers.CharField(
        allow_null=True,
        help_text='Error message if generation failed',
    )


class AvatarGenerationResponseSerializer(serializers.Serializer):
    """Serializer for avatar generation response."""

    results = serializers.ListField(
        child=AvatarResultSerializer(),
        help_text='List of avatar generation results',
    )
    success_count = serializers.IntegerField(help_text='Number of successful generations')
    error_count = serializers.IntegerField(help_text='Number of failed generations')
