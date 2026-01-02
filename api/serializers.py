"""
HiveCore API Serializers

Serializers for converting model instances to JSON and vice versa.
"""

from rest_framework import serializers

from .models import (
    Agent,
    AgentCollaboration,
    AgentTaskItem,
    AgentThinking,
    Conversation,
    DeliveryStandard,
    File,
    Folder,
    Message,
    MessageAttachment,
    Project,
    ProjectDecision,
    ProjectFileRegistry,
    Requirement,
    Task,
    TeamMember,
)


class AgentSerializer(serializers.ModelSerializer):
    """Serializer for Agent model."""

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "agent_no",
            "duty",
            "detail",
            "preview",
            "avatar",
            "cost_per_min",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AgentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for Agent list view."""

    class Meta:
        model = Agent
        fields = ["id", "name", "agent_no", "duty", "avatar", "cost_per_min"]


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""

    class Meta:
        model = Message
        fields = ["id", "type", "content", "created_at"]
        read_only_fields = ["id", "created_at"]


class DeliveryStandardSerializer(serializers.ModelSerializer):
    """Serializer for DeliveryStandard model."""

    class Meta:
        model = DeliveryStandard
        fields = ["id", "content", "order"]
        read_only_fields = ["id"]


class RequirementSerializer(serializers.ModelSerializer):
    """Serializer for Requirement model with nested delivery standards."""

    delivery_standards = DeliveryStandardSerializer(many=True, read_only=True)

    class Meta:
        model = Requirement
        fields = ["id", "content", "type", "delivery_standards", "created_at"]
        read_only_fields = ["id", "created_at"]


class RequirementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Requirement with delivery standards."""

    delivery_standards = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True
    )

    class Meta:
        model = Requirement
        fields = ["id", "content", "type", "delivery_standards", "conversation"]

    def create(self, validated_data):
        delivery_standards_data = validated_data.pop("delivery_standards", [])
        requirement = Requirement.objects.create(**validated_data)
        for idx, standard in enumerate(delivery_standards_data):
            DeliveryStandard.objects.create(
                requirement=requirement, content=standard, order=idx
            )
        return requirement


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation with nested messages and requirements."""

    messages = MessageSerializer(many=True, read_only=True)
    requirements = RequirementSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "project",
            "title",
            "source_type",
            "first_user_message",
            "messages",
            "requirements",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ConversationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for Conversation list view."""

    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "project",
            "title",
            "source_type",
            "first_user_message",
            "message_count",
            "created_at",
        ]

    def get_message_count(self, obj):
        return obj.messages.count()


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for TeamMember model."""

    agent = AgentListSerializer(read_only=True)
    agent_id = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.all(), source="agent", write_only=True
    )

    class Meta:
        model = TeamMember
        fields = [
            "id",
            "agent",
            "agent_id",
            "role",
            "status",
            "time_spent",
            "cost",
            "progress",
            "progress_total",
            "joined_at",
        ]
        read_only_fields = ["id", "joined_at"]


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""

    agent = AgentListSerializer(read_only=True)
    agent_id = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.all(),
        source="agent",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "agent",
            "agent_id",
            "time_spent",
            "cost",
            "progress",
            "progress_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model with nested data."""

    team_members = TeamMemberSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "status",
            "phase",
            "main_conversation",
            "member_count",
            "run_time",
            "credits_usage",
            "total_cost",
            "progress",
            "team_members",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_member_count(self, obj):
        """Dynamically calculate team member count."""
        return obj.team_members.count()


class ProjectListSerializer(serializers.ModelSerializer):
    """Simplified serializer for Project list view."""

    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "status",
            "phase",
            "main_conversation",
            "member_count",
            "progress",
            "total_cost",
            "created_at",
        ]

    def get_member_count(self, obj):
        """Dynamically calculate team member count."""
        return obj.team_members.count()


class ProjectStatsSerializer(serializers.Serializer):
    """Serializer for project statistics."""

    member_count = serializers.IntegerField()
    run_time = serializers.CharField()
    credits_usage = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    progress = serializers.IntegerField()
    progress_total = serializers.IntegerField()


# ============ Agent Detail Panel Serializers ============


class AgentThinkingSerializer(serializers.ModelSerializer):
    """Serializer for AgentThinking model."""

    class Meta:
        model = AgentThinking
        fields = ["id", "agent", "project", "content", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AgentTaskItemSerializer(serializers.ModelSerializer):
    """Serializer for AgentTaskItem model."""

    class Meta:
        model = AgentTaskItem
        fields = [
            "id",
            "agent",
            "project",
            "category",
            "content",
            "is_checked",
            "order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AgentCollaborationSerializer(serializers.ModelSerializer):
    """Serializer for AgentCollaboration model."""

    from_agent_detail = AgentListSerializer(source="from_agent", read_only=True)
    to_agent_detail = AgentListSerializer(source="to_agent", read_only=True)

    class Meta:
        model = AgentCollaboration
        fields = [
            "id",
            "agent",
            "project",
            "direction",
            "from_agent",
            "from_agent_detail",
            "to_agent",
            "to_agent_detail",
            "content",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AgentDetailPanelSerializer(serializers.Serializer):
    """Serializer for the complete agent detail panel data."""

    agent = AgentSerializer()
    thinking = AgentThinkingSerializer(allow_null=True)
    task_items = AgentTaskItemSerializer(many=True)
    collaborations = AgentCollaborationSerializer(many=True)


# ============ File Management Serializers ============


class FileSerializer(serializers.ModelSerializer):
    """Serializer for File model."""

    path = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = [
            "id",
            "project",
            "folder",
            "name",
            "file_type",
            "size",
            "mime_type",
            "url",
            "thumbnail_url",
            "description",
            "path",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_path(self, obj):
        return obj.get_path()


class FolderSerializer(serializers.ModelSerializer):
    """Serializer for Folder model."""

    path = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = Folder
        fields = [
            "id",
            "project",
            "name",
            "parent",
            "path",
            "children",
            "files",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_path(self, obj):
        return obj.get_path()

    def get_children(self, obj):
        children = obj.children.all()
        return FolderSerializer(children, many=True).data


class FolderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for Folder list view."""

    path = serializers.SerializerMethodField()
    file_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["id", "name", "parent", "path", "file_count", "created_at"]

    def get_path(self, obj):
        return obj.get_path()

    def get_file_count(self, obj):
        return obj.files.count()


class FileTreeSerializer(serializers.Serializer):
    """Serializer for the complete file tree."""

    total_files = serializers.IntegerField()
    folders = FolderSerializer(many=True)
    root_files = FileSerializer(many=True)


class ProjectDecisionSerializer(serializers.ModelSerializer):
    """Serializer for project decisions."""

    made_by_agent_name = serializers.CharField(read_only=True)
    execution_round_id = serializers.UUIDField(
        source='execution_round.id',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ProjectDecision
        fields = [
            'id',
            'project',
            'execution_round',
            'execution_round_id',
            'category',
            'key',
            'value',
            'description',
            'made_by_agent',
            'made_by_agent_name',
            'round_index',
            'is_active',
            'superseded_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'made_by_agent_name']


class ProjectDecisionListSerializer(serializers.ModelSerializer):
    """Serializer for project decision list view."""

    class Meta:
        model = ProjectDecision
        fields = [
            'id',
            'category',
            'key',
            'value',
            'description',
            'made_by_agent_name',
            'round_index',
            'is_active',
            'created_at',
        ]


class ProjectDecisionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating project decisions."""

    class Meta:
        model = ProjectDecision
        fields = [
            'project',
            'execution_round',
            'category',
            'key',
            'value',
            'description',
            'made_by_agent',
            'round_index',
        ]

    def create(self, validated_data):
        # Check if there's an existing active decision with same category+key
        project = validated_data['project']
        category = validated_data['category']
        key = validated_data['key']

        existing = models.ProjectDecision.objects.filter(
            project=project,
            category=category,
            key=key,
            is_active=True,
        ).first()

        # Create the new decision
        new_decision = super().create(validated_data)

        # Supersede the old one if exists
        if existing:
            existing.supersede(new_decision)

        return new_decision


class ProjectFileRegistrySerializer(serializers.ModelSerializer):
    """Serializer for project file registry."""

    created_by_agent_name = serializers.CharField(
        source='created_by_agent.name',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ProjectFileRegistry
        fields = [
            'id',
            'project',
            'execution_round',
            'file_path',
            'description',
            'created_by_agent',
            'created_by_agent_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProjectContextSerializer(serializers.Serializer):
    """Serializer for complete project context (decisions + files).

    Returns data formatted for agent prompts.
    """

    decisions = ProjectDecisionListSerializer(many=True)
    file_registry = ProjectFileRegistrySerializer(many=True)
    context_for_prompt = serializers.CharField()


# ============ Chat Serializers ============


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for MessageAttachment model."""

    file_url = serializers.CharField(source='file.url', read_only=True)

    class Meta:
        model = MessageAttachment
        fields = [
            'id',
            'file',
            'filename',
            'file_type',
            'file_url',
            'summary',
            'text_content',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MessageWithAttachmentsSerializer(serializers.ModelSerializer):
    """Serializer for Message model with attachments."""

    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'type', 'content', 'attachments', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat request with optional file attachments."""

    content = serializers.CharField(help_text="User message content")
    file_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="List of File IDs to attach to this message",
    )


class ExtractedRequirementSerializer(serializers.Serializer):
    """Serializer for extracted requirement from chat."""

    content = serializers.CharField()
    type = serializers.ChoiceField(
        choices=[('requirement', 'Requirement'), ('delivery_standard', 'Delivery Standard')],
        default='requirement',
    )
    delivery_standards = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response."""

    user_message = MessageWithAttachmentsSerializer(help_text="The user message that was created")
    assistant_message = MessageSerializer(help_text="The assistant's response")
    requirements_created = RequirementSerializer(many=True, help_text="Newly created requirements")
    requirements_updated = RequirementSerializer(many=True, help_text="Updated requirements")
