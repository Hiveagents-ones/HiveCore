"""
HiveCore API Views

ViewSets and API views for the HiveCore system.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from tenants.mixins import TenantQuerySetMixin, ProjectTenantQuerySetMixin

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
from .serializers import (
    AgentCollaborationSerializer,
    AgentDetailPanelSerializer,
    AgentListSerializer,
    AgentSerializer,
    AgentTaskItemSerializer,
    AgentThinkingSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
    ConversationListSerializer,
    ConversationSerializer,
    DeliveryStandardSerializer,
    FileSerializer,
    FileTreeSerializer,
    FolderListSerializer,
    FolderSerializer,
    MessageSerializer,
    MessageWithAttachmentsSerializer,
    ProjectDecisionCreateSerializer,
    ProjectDecisionListSerializer,
    ProjectDecisionSerializer,
    ProjectFileRegistrySerializer,
    ProjectListSerializer,
    ProjectSerializer,
    ProjectStatsSerializer,
    RequirementCreateSerializer,
    RequirementSerializer,
    TaskSerializer,
    TeamMemberSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List all agents", tags=["Agents"]),
    retrieve=extend_schema(summary="Get agent details", tags=["Agents"]),
    create=extend_schema(summary="Create a new agent", tags=["Agents"]),
    update=extend_schema(summary="Update an agent", tags=["Agents"]),
    partial_update=extend_schema(summary="Partially update an agent", tags=["Agents"]),
    destroy=extend_schema(summary="Delete an agent", tags=["Agents"]),
)
class AgentViewSet(viewsets.ModelViewSet):
    """ViewSet for Agent CRUD operations."""

    queryset = Agent.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return AgentListSerializer
        return AgentSerializer


@extend_schema_view(
    list=extend_schema(summary="List all projects", tags=["Projects"]),
    retrieve=extend_schema(summary="Get project details", tags=["Projects"]),
    create=extend_schema(summary="Create a new project", tags=["Projects"]),
    update=extend_schema(summary="Update a project", tags=["Projects"]),
    partial_update=extend_schema(
        summary="Partially update a project", tags=["Projects"]
    ),
    destroy=extend_schema(summary="Delete a project", tags=["Projects"]),
)
class ProjectViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for Project CRUD operations.

    Tenant-isolated: Users can only access projects belonging to their tenant.
    """

    queryset = Project.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectListSerializer
        return ProjectSerializer

    @extend_schema(
        summary="Get project statistics",
        tags=["Projects"],
        responses={200: ProjectStatsSerializer},
    )
    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Get statistics for a specific project."""
        project = self.get_object()
        tasks = project.tasks.all()
        total_progress = sum(t.progress for t in tasks)
        total_progress_max = sum(t.progress_total for t in tasks) or 100

        stats = {
            "member_count": project.team_members.count(),
            "run_time": project.run_time or "0h",
            "credits_usage": project.credits_usage,
            "total_cost": project.total_cost,
            "progress": total_progress,
            "progress_total": total_progress_max,
        }
        serializer = ProjectStatsSerializer(stats)
        return Response(serializer.data)

    @extend_schema(
        summary="Get project tasks",
        tags=["Projects"],
        responses={200: TaskSerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        """Get all tasks for a specific project."""
        project = self.get_object()
        tasks = project.tasks.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get project team members",
        tags=["Projects"],
        responses={200: TeamMemberSerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def team(self, request, pk=None):
        """Get all team members for a specific project."""
        project = self.get_object()
        members = project.team_members.all()
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List all conversations", tags=["Conversations"]),
    retrieve=extend_schema(summary="Get conversation details", tags=["Conversations"]),
    create=extend_schema(summary="Create a new conversation", tags=["Conversations"]),
    update=extend_schema(summary="Update a conversation", tags=["Conversations"]),
    partial_update=extend_schema(
        summary="Partially update a conversation", tags=["Conversations"]
    ),
    destroy=extend_schema(summary="Delete a conversation", tags=["Conversations"]),
)
class ConversationViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for Conversation CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = Conversation.objects.all()
    filterset_fields = ["project", "source_type"]

    def get_serializer_class(self):
        if self.action == "list":
            return ConversationListSerializer
        return ConversationSerializer

    @extend_schema(
        summary="Get conversation by source type",
        tags=["Conversations"],
        responses={200: ConversationSerializer},
    )
    @action(detail=False, methods=["get"], url_path="by-source-type/(?P<source_type>[^/.]+)")
    def by_source_type(self, request, source_type=None):
        """Get the first conversation with the specified source type."""
        conversation = self.queryset.filter(source_type=source_type).first()
        if not conversation:
            return Response(
                {"error": f"No conversation found with source_type: {source_type}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data)

    @extend_schema(
        summary="Add a message to conversation",
        tags=["Conversations"],
        request=MessageSerializer,
        responses={201: MessageSerializer},
    )
    @action(detail=True, methods=["post"])
    def add_message(self, request, pk=None):
        """Add a new message to the conversation."""
        conversation = self.get_object()
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(conversation=conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Add a requirement to conversation",
        tags=["Conversations"],
        request=RequirementCreateSerializer,
        responses={201: RequirementSerializer},
    )
    @action(detail=True, methods=["post"])
    def add_requirement(self, request, pk=None):
        """Add a new requirement to the conversation."""
        conversation = self.get_object()
        serializer = RequirementCreateSerializer(data=request.data)
        if serializer.is_valid():
            requirement = serializer.save(conversation=conversation)
            return Response(
                RequirementSerializer(requirement).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Chat with AA assistant",
        description="""
        Send a message to the AA assistant and receive a response.

        The AA will:
        1. Process the user message
        2. Generate an intelligent response
        3. Extract requirements and delivery standards from the conversation
        4. Update the requirements list automatically

        Each call creates:
        - A user message (type='user')
        - An assistant message (type='assistant')
        - Optionally new requirements with delivery standards
        """,
        tags=["Conversations"],
        request=ChatRequestSerializer,
        responses={201: ChatResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def chat(self, request, pk=None):
        """Chat with AA assistant and update requirements.

        This endpoint:
        1. Saves the user message with optional file attachments
        2. Calls the AA to generate a response with file context
        3. Extracts requirements from the conversation
        4. Creates/updates requirement records
        5. Returns the response with updated requirements
        """
        from .chat_service import get_chat_service, FileAttachment as ServiceFileAttachment

        conversation = self.get_object()

        # Validate request
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_content = serializer.validated_data['content']
        file_ids = serializer.validated_data.get('file_ids', [])

        # Get conversation history
        history = [
            {'type': msg.type, 'content': msg.content}
            for msg in conversation.messages.order_by('created_at')
        ]

        # Create user message
        user_message = Message.objects.create(
            conversation=conversation,
            type='user',
            content=user_content,
        )

        # Process file attachments
        attachments = []
        if file_ids:
            files = File.objects.filter(id__in=file_ids)
            for file in files:
                # Create MessageAttachment record
                attachment = MessageAttachment.objects.create(
                    message=user_message,
                    file=file,
                    filename=file.name,
                    file_type=file.file_type,
                    # text_content and summary would be populated by file processing
                )

                # Create service attachment for LLM context
                attachments.append(ServiceFileAttachment(
                    id=file.id,
                    filename=file.name,
                    file_type=file.file_type,
                    content=attachment.text_content or None,
                    summary=attachment.summary or None,
                ))

        # Call AA chat service with attachments
        chat_service = get_chat_service()
        try:
            chat_response = chat_service.chat_sync(
                history,
                user_content,
                attachments=attachments if attachments else None,
            )
        except Exception as e:
            # Rollback user message on error
            user_message.delete()
            return Response(
                {'error': f'Chat service error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Create assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            type='assistant',
            content=chat_response.content,
        )

        # Process extracted requirements
        requirements_created = []
        requirements_updated = []

        for extracted in chat_response.requirements:
            if not extracted.content:
                continue

            # Check if similar requirement exists
            existing = Requirement.objects.filter(
                conversation=conversation,
                content__icontains=extracted.content[:50],
            ).first()

            if existing:
                # Update existing requirement
                existing.content = extracted.content
                existing.type = extracted.type
                existing.save()

                # Update delivery standards
                existing.delivery_standards.all().delete()
                for idx, ds_content in enumerate(extracted.delivery_standards):
                    DeliveryStandard.objects.create(
                        requirement=existing,
                        content=ds_content,
                        order=idx,
                    )
                requirements_updated.append(existing)
            else:
                # Create new requirement
                requirement = Requirement.objects.create(
                    conversation=conversation,
                    content=extracted.content,
                    type=extracted.type,
                )
                for idx, ds_content in enumerate(extracted.delivery_standards):
                    DeliveryStandard.objects.create(
                        requirement=requirement,
                        content=ds_content,
                        order=idx,
                    )
                requirements_created.append(requirement)

        # Build response with attachments
        response_data = {
            'user_message': MessageWithAttachmentsSerializer(user_message).data,
            'assistant_message': MessageSerializer(assistant_message).data,
            'requirements_created': RequirementSerializer(requirements_created, many=True).data,
            'requirements_updated': RequirementSerializer(requirements_updated, many=True).data,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Stream chat with AA assistant",
        description="""
        Stream chat response from AA assistant using Server-Sent Events (SSE).

        The response is streamed as a series of SSE events:
        - event: token - Contains a text chunk
        - event: done - Contains the final message and extracted requirements
        - event: error - Contains error information
        """,
        tags=["Conversations"],
        request=ChatRequestSerializer,
        responses={200: None},
    )
    @action(detail=True, methods=["post"], url_path="chat-stream")
    def chat_stream(self, request, pk=None):
        """Stream chat with AA assistant using SSE."""
        import json
        from django.http import StreamingHttpResponse
        from .chat_service import get_chat_service, FileAttachment as ServiceFileAttachment

        conversation = self.get_object()

        # Validate request
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_content = serializer.validated_data['content']
        file_ids = serializer.validated_data.get('file_ids', [])

        # Get conversation history
        history = [
            {'type': msg.type, 'content': msg.content}
            for msg in conversation.messages.order_by('created_at')
        ]

        # Create user message
        user_message = Message.objects.create(
            conversation=conversation,
            type='user',
            content=user_content,
        )

        # Process file attachments
        attachments = []
        if file_ids:
            files = File.objects.filter(id__in=file_ids)
            for file in files:
                attachment = MessageAttachment.objects.create(
                    message=user_message,
                    file=file,
                    filename=file.name,
                    file_type=file.file_type,
                )
                attachments.append(ServiceFileAttachment(
                    id=file.id,
                    filename=file.name,
                    file_type=file.file_type,
                    content=attachment.text_content or None,
                    summary=attachment.summary or None,
                ))

        def event_stream():
            chat_service = get_chat_service()
            full_content = ""
            requirements_data = []

            try:
                for event in chat_service.chat_stream(
                    history,
                    user_content,
                    attachments=attachments if attachments else None,
                ):
                    if event['type'] == 'token':
                        full_content += event['content']
                        yield f"event: token\ndata: {json.dumps({'content': event['content']})}\n\n"
                    elif event['type'] == 'requirement_start':
                        # New requirement object started - send start event for UI to create placeholder
                        index = event.get('index', 0)
                        yield f"event: requirement_start\ndata: {json.dumps({'index': index})}\n\n"
                    elif event['type'] == 'requirement_token':
                        # Streaming token within a requirement - send for real-time display
                        content = event.get('content', '')
                        index = event.get('index', 0)
                        yield f"event: requirement_token\ndata: {json.dumps({'content': content, 'index': index})}\n\n"
                    elif event['type'] == 'requirement_end':
                        # Requirement object completed - send end event for UI to finalize
                        index = event.get('index', 0)
                        yield f"event: requirement_end\ndata: {json.dumps({'index': index})}\n\n"
                    elif event['type'] == 'requirement':
                        # Single requirement event (legacy) - send immediately for incremental UI update
                        requirement = event.get('requirement', {})
                        index = event.get('index', 0)
                        yield f"event: requirement\ndata: {json.dumps({'requirement': requirement, 'index': index})}\n\n"
                    elif event['type'] == 'requirements':
                        # Batch requirements event (legacy) - send immediately for UI update
                        requirements_data = event.get('requirements', [])
                        yield f"event: requirements\ndata: {json.dumps({'requirements': requirements_data})}\n\n"
                    elif event['type'] == 'done':
                        full_content = event['content']
                        requirements_data = event.get('requirements', [])
                        # Create assistant message with clean content
                        assistant_message = Message.objects.create(
                            conversation=conversation,
                            type='assistant',
                            content=full_content,
                        )
                        # Process requirements
                        requirements_created = []
                        for req in requirements_data:
                            if not req.get('content'):
                                continue
                            requirement = Requirement.objects.create(
                                conversation=conversation,
                                content=req['content'],
                                type=req.get('type', 'requirement'),
                            )
                            for idx, ds_content in enumerate(req.get('delivery_standards', [])):
                                DeliveryStandard.objects.create(
                                    requirement=requirement,
                                    content=ds_content,
                                    order=idx,
                                )
                            requirements_created.append({
                                'id': requirement.id,
                                'content': requirement.content,
                                'type': requirement.type,
                                'delivery_standards': [{'id': ds.id, 'content': ds.content} for ds in requirement.delivery_standards.all()],
                            })

                        done_data = {
                            'user_message': {'id': user_message.id, 'type': 'user', 'content': user_content},
                            'assistant_message': {'id': assistant_message.id, 'type': 'assistant', 'content': full_content},
                            'requirements_created': requirements_created,
                        }
                        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
                    elif event['type'] == 'error':
                        yield f"event: error\ndata: {json.dumps({'error': event['content']})}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    @extend_schema(
        summary="Extract requirements from conversation",
        description="""
        Re-analyze the entire conversation and extract/update all requirements.

        This is useful when you want to refresh the requirements list
        based on the full conversation context.
        """,
        tags=["Conversations"],
        responses={200: RequirementSerializer(many=True)},
    )
    @action(detail=True, methods=["post"])
    def extract_requirements(self, request, pk=None):
        """Extract all requirements from conversation history."""
        from .chat_service import get_extractor

        conversation = self.get_object()

        # Get conversation history
        messages = [
            {'type': msg.type, 'content': msg.content}
            for msg in conversation.messages.order_by('created_at')
        ]

        if not messages:
            return Response([])

        # Extract requirements
        extractor = get_extractor()
        try:
            extracted_list = extractor.extract_sync(messages)
        except Exception as e:
            return Response(
                {'error': f'Extraction error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Clear existing requirements and create new ones
        conversation.requirements.all().delete()

        requirements = []
        for extracted in extracted_list:
            if not extracted.content:
                continue

            requirement = Requirement.objects.create(
                conversation=conversation,
                content=extracted.content,
                type=extracted.type,
            )
            for idx, ds_content in enumerate(extracted.delivery_standards):
                DeliveryStandard.objects.create(
                    requirement=requirement,
                    content=ds_content,
                    order=idx,
                )
            requirements.append(requirement)

        return Response(RequirementSerializer(requirements, many=True).data)


@extend_schema_view(
    list=extend_schema(summary="List all messages", tags=["Messages"]),
    retrieve=extend_schema(summary="Get message details", tags=["Messages"]),
    create=extend_schema(summary="Create a new message", tags=["Messages"]),
    update=extend_schema(summary="Update a message", tags=["Messages"]),
    partial_update=extend_schema(
        summary="Partially update a message", tags=["Messages"]
    ),
    destroy=extend_schema(summary="Delete a message", tags=["Messages"]),
)
class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for Message CRUD operations."""

    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filterset_fields = ["conversation", "type"]


@extend_schema_view(
    list=extend_schema(summary="List all requirements", tags=["Requirements"]),
    retrieve=extend_schema(summary="Get requirement details", tags=["Requirements"]),
    create=extend_schema(summary="Create a new requirement", tags=["Requirements"]),
    update=extend_schema(summary="Update a requirement", tags=["Requirements"]),
    partial_update=extend_schema(
        summary="Partially update a requirement", tags=["Requirements"]
    ),
    destroy=extend_schema(summary="Delete a requirement", tags=["Requirements"]),
)
class RequirementViewSet(viewsets.ModelViewSet):
    """ViewSet for Requirement CRUD operations."""

    queryset = Requirement.objects.all()
    filterset_fields = ["conversation", "type"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RequirementCreateSerializer
        return RequirementSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List all delivery standards", tags=["Delivery Standards"]
    ),
    retrieve=extend_schema(
        summary="Get delivery standard details", tags=["Delivery Standards"]
    ),
    create=extend_schema(
        summary="Create a new delivery standard", tags=["Delivery Standards"]
    ),
    update=extend_schema(
        summary="Update a delivery standard", tags=["Delivery Standards"]
    ),
    partial_update=extend_schema(
        summary="Partially update a delivery standard", tags=["Delivery Standards"]
    ),
    destroy=extend_schema(
        summary="Delete a delivery standard", tags=["Delivery Standards"]
    ),
)
class DeliveryStandardViewSet(viewsets.ModelViewSet):
    """ViewSet for DeliveryStandard CRUD operations."""

    queryset = DeliveryStandard.objects.all()
    serializer_class = DeliveryStandardSerializer
    filterset_fields = ["requirement"]


@extend_schema_view(
    list=extend_schema(summary="List all team members", tags=["Team Members"]),
    retrieve=extend_schema(summary="Get team member details", tags=["Team Members"]),
    create=extend_schema(summary="Add a team member", tags=["Team Members"]),
    update=extend_schema(summary="Update a team member", tags=["Team Members"]),
    partial_update=extend_schema(
        summary="Partially update a team member", tags=["Team Members"]
    ),
    destroy=extend_schema(summary="Remove a team member", tags=["Team Members"]),
)
class TeamMemberViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for TeamMember CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    filterset_fields = ["project", "agent"]


@extend_schema_view(
    list=extend_schema(summary="List all tasks", tags=["Tasks"]),
    retrieve=extend_schema(summary="Get task details", tags=["Tasks"]),
    create=extend_schema(summary="Create a new task", tags=["Tasks"]),
    update=extend_schema(summary="Update a task", tags=["Tasks"]),
    partial_update=extend_schema(summary="Partially update a task", tags=["Tasks"]),
    destroy=extend_schema(summary="Delete a task", tags=["Tasks"]),
)
class TaskViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for Task CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filterset_fields = ["project", "agent", "status", "agent_type"]


# ============ Agent Detail Panel ViewSets ============


@extend_schema_view(
    list=extend_schema(summary="List all agent thinkings", tags=["Agent Detail"]),
    retrieve=extend_schema(summary="Get agent thinking details", tags=["Agent Detail"]),
    create=extend_schema(summary="Create agent thinking", tags=["Agent Detail"]),
    update=extend_schema(summary="Update agent thinking", tags=["Agent Detail"]),
    partial_update=extend_schema(
        summary="Partially update agent thinking", tags=["Agent Detail"]
    ),
    destroy=extend_schema(summary="Delete agent thinking", tags=["Agent Detail"]),
)
class AgentThinkingViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for AgentThinking CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = AgentThinking.objects.all()
    serializer_class = AgentThinkingSerializer
    filterset_fields = ["agent", "project"]


@extend_schema_view(
    list=extend_schema(summary="List all agent task items", tags=["Agent Detail"]),
    retrieve=extend_schema(summary="Get agent task item details", tags=["Agent Detail"]),
    create=extend_schema(summary="Create agent task item", tags=["Agent Detail"]),
    update=extend_schema(summary="Update agent task item", tags=["Agent Detail"]),
    partial_update=extend_schema(
        summary="Partially update agent task item", tags=["Agent Detail"]
    ),
    destroy=extend_schema(summary="Delete agent task item", tags=["Agent Detail"]),
)
class AgentTaskItemViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for AgentTaskItem CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = AgentTaskItem.objects.all()
    serializer_class = AgentTaskItemSerializer
    filterset_fields = ["agent", "project", "category", "is_checked"]


@extend_schema_view(
    list=extend_schema(summary="List all agent collaborations", tags=["Agent Detail"]),
    retrieve=extend_schema(
        summary="Get agent collaboration details", tags=["Agent Detail"]
    ),
    create=extend_schema(summary="Create agent collaboration", tags=["Agent Detail"]),
    update=extend_schema(summary="Update agent collaboration", tags=["Agent Detail"]),
    partial_update=extend_schema(
        summary="Partially update agent collaboration", tags=["Agent Detail"]
    ),
    destroy=extend_schema(summary="Delete agent collaboration", tags=["Agent Detail"]),
)
class AgentCollaborationViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for AgentCollaboration CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = AgentCollaboration.objects.all()
    serializer_class = AgentCollaborationSerializer
    filterset_fields = ["agent", "project", "direction", "from_agent", "to_agent"]


# ============ File Management ViewSets ============


@extend_schema_view(
    list=extend_schema(summary="List all folders", tags=["Files"]),
    retrieve=extend_schema(summary="Get folder details", tags=["Files"]),
    create=extend_schema(summary="Create a folder", tags=["Files"]),
    update=extend_schema(summary="Update a folder", tags=["Files"]),
    partial_update=extend_schema(summary="Partially update a folder", tags=["Files"]),
    destroy=extend_schema(summary="Delete a folder", tags=["Files"]),
)
class FolderViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for Folder CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = Folder.objects.all()
    filterset_fields = ["project", "parent"]

    def get_serializer_class(self):
        if self.action == "list":
            return FolderListSerializer
        return FolderSerializer


@extend_schema_view(
    list=extend_schema(summary="List all files", tags=["Files"]),
    retrieve=extend_schema(summary="Get file details", tags=["Files"]),
    create=extend_schema(summary="Create a file", tags=["Files"]),
    update=extend_schema(summary="Update a file", tags=["Files"]),
    partial_update=extend_schema(summary="Partially update a file", tags=["Files"]),
    destroy=extend_schema(summary="Delete a file", tags=["Files"]),
)
class FileViewSet(ProjectTenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for File CRUD operations.

    Tenant-isolated through project relationship.
    """

    queryset = File.objects.all()
    serializer_class = FileSerializer
    filterset_fields = ["project", "folder", "file_type"]

    # 可预览文件的类型和扩展名
    PREVIEWABLE_FILE_TYPES = ["document", "spreadsheet", "presentation"]
    PREVIEWABLE_EXTENSIONS = [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".ppt", ".pptx", ".txt", ".md"
    ]

    @extend_schema(
        summary="Search files",
        tags=["Files"],
        responses={200: FileSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search files by name."""
        query = request.query_params.get("q", "")
        project_id = request.query_params.get("project")
        files = self.queryset.filter(name__icontains=query)
        if project_id:
            files = files.filter(project_id=project_id)
        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Search previewable files",
        tags=["Files"],
        responses={200: FileSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="search-previewable")
    def search_previewable(self, request):
        """Search previewable files (documents, spreadsheets, presentations).

        Query parameters:
        - q: Search query (matches file name, case-insensitive)
        - project: Filter by project ID
        """
        from django.db.models import Q

        query = request.query_params.get("q", "")
        project_id = request.query_params.get("project")

        # 构建可预览文件的筛选条件
        # 条件1: file_type 在可预览类型列表中
        type_filter = Q(file_type__in=self.PREVIEWABLE_FILE_TYPES)

        # 条件2: 文件扩展名匹配
        extension_filter = Q()
        for ext in self.PREVIEWABLE_EXTENSIONS:
            extension_filter |= Q(name__iendswith=ext)

        # 组合条件：类型匹配 OR 扩展名匹配
        files = self.queryset.filter(type_filter | extension_filter)

        # 按项目筛选
        if project_id:
            files = files.filter(project_id=project_id)

        # 按名称搜索
        if query:
            files = files.filter(name__icontains=query)

        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get previewable files",
        tags=["Files"],
        responses={200: FileSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="previewable")
    def previewable(self, request):
        """Get all previewable files (documents, spreadsheets, presentations).

        Query parameters:
        - project: Filter by project ID
        """
        from django.db.models import Q

        project_id = request.query_params.get("project")

        # 构建可预览文件的筛选条件
        type_filter = Q(file_type__in=self.PREVIEWABLE_FILE_TYPES)
        extension_filter = Q()
        for ext in self.PREVIEWABLE_EXTENSIONS:
            extension_filter |= Q(name__iendswith=ext)

        files = self.queryset.filter(type_filter | extension_filter)

        if project_id:
            files = files.filter(project_id=project_id)

        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)


# ============ Combined Endpoints ============


@extend_schema_view(
    list=extend_schema(summary="List all agents", tags=["Agents"]),
    retrieve=extend_schema(summary="Get agent details", tags=["Agents"]),
    create=extend_schema(summary="Create a new agent", tags=["Agents"]),
    update=extend_schema(summary="Update an agent", tags=["Agents"]),
    partial_update=extend_schema(summary="Partially update an agent", tags=["Agents"]),
    destroy=extend_schema(summary="Delete an agent", tags=["Agents"]),
)
class AgentViewSetExtended(AgentViewSet):
    """Extended AgentViewSet with detail panel endpoint."""

    @extend_schema(
        summary="Get agent detail panel data",
        tags=["Agent Detail"],
        responses={200: AgentDetailPanelSerializer},
    )
    @action(detail=True, methods=["get"], url_path="detail-panel")
    def detail_panel(self, request, pk=None):
        """Get complete detail panel data for an agent in a project."""
        agent = self.get_object()
        project_id = request.query_params.get("project")

        if not project_id:
            return Response(
                {"error": "project query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        thinking = AgentThinking.objects.filter(
            agent=agent, project=project
        ).first()
        task_items = AgentTaskItem.objects.filter(agent=agent, project=project)
        collaborations = AgentCollaboration.objects.filter(agent=agent, project=project)

        data = {
            "agent": agent,
            "thinking": thinking,
            "task_items": task_items,
            "collaborations": collaborations,
        }

        serializer = AgentDetailPanelSerializer(data)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List all projects", tags=["Projects"]),
    retrieve=extend_schema(summary="Get project details", tags=["Projects"]),
    create=extend_schema(summary="Create a new project", tags=["Projects"]),
    update=extend_schema(summary="Update a project", tags=["Projects"]),
    partial_update=extend_schema(
        summary="Partially update a project", tags=["Projects"]
    ),
    destroy=extend_schema(summary="Delete a project", tags=["Projects"]),
)
class ProjectViewSetExtended(ProjectViewSet):
    """Extended ProjectViewSet with file tree endpoint."""

    @extend_schema(
        summary="Get project file tree",
        tags=["Files"],
        responses={200: FileTreeSerializer},
    )
    @action(detail=True, methods=["get"], url_path="file-tree")
    def file_tree(self, request, pk=None):
        """Get complete file tree for a project."""
        project = self.get_object()

        # Get root folders (no parent)
        root_folders = Folder.objects.filter(project=project, parent__isnull=True)
        # Get root files (no folder)
        root_files = File.objects.filter(project=project, folder__isnull=True)
        # Get total file count
        total_files = File.objects.filter(project=project).count()

        data = {
            "total_files": total_files,
            "folders": root_folders,
            "root_files": root_files,
        }

        serializer = FileTreeSerializer(data)
        return Response(serializer.data)


class ProjectDecisionViewSet(viewsets.ModelViewSet):
    """ViewSet for project decisions.

    Provides CRUD operations for project-level technology and
    architecture decisions.

    Tenant-isolated through project relationship.

    Endpoints:
        GET /api/v1/decisions/                  - List all decisions
        GET /api/v1/decisions/{id}/             - Get decision details
        POST /api/v1/decisions/                 - Create new decision
        GET /api/v1/projects/{id}/decisions/    - List project decisions (via ProjectViewSet)
    """

    queryset = ProjectDecision.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectDecisionListSerializer
        if self.action == 'create':
            return ProjectDecisionCreateSerializer
        return ProjectDecisionSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # Tenant isolation
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(project__tenant=tenant)
        else:
            qs = qs.none()

        # Filter by project
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        # Filter by active status (default: only active)
        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if include_inactive.lower() != 'true':
            qs = qs.filter(is_active=True)

        # Filter by execution round
        round_id = self.request.query_params.get('execution_round')
        if round_id:
            qs = qs.filter(execution_round_id=round_id)

        return qs.select_related('project', 'made_by_agent', 'execution_round')


class ProjectFileRegistryViewSet(viewsets.ModelViewSet):
    """ViewSet for project file registry.

    Tenant-isolated through project relationship.
    """

    queryset = ProjectFileRegistry.objects.all()
    serializer_class = ProjectFileRegistrySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()

        # Tenant isolation
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(project__tenant=tenant)
        else:
            qs = qs.none()

        # Filter by project
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)

        return qs.select_related('project', 'created_by_agent')


class ProjectContextView(APIView):
    """Get complete project context for agent prompts.

    GET /api/v1/projects/{id}/context/

    Returns all active decisions and file registry formatted
    for use in agent prompts.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, project_id):
        from django.shortcuts import get_object_or_404

        project = get_object_or_404(Project, pk=project_id)

        # Get active decisions
        decisions = ProjectDecision.objects.filter(
            project=project,
            is_active=True,
        ).select_related('made_by_agent').order_by('category', 'key')

        # Get file registry
        file_registry = ProjectFileRegistry.objects.filter(
            project=project,
        ).order_by('file_path')

        # Generate context for prompt (similar to AgentScope's get_context_for_prompt)
        context_lines = ["## 项目记忆 (Project Memory)", ""]

        if decisions.exists():
            context_lines.append(
                "以下是本项目已确定的技术决策和约束，**请务必遵循这些决策**，"
                "不要引入冲突的技术栈或库。"
            )
            context_lines.append("")

            # Group by category
            categories = {
                'tech_stack': "### 技术栈",
                'architecture': "### 架构决策",
                'api_design': "### API 设计",
                'component': "### 组件设计",
                'dependency': "### 依赖包",
                'constraint': "### 约束条件",
                'file_structure': "### 文件结构",
                'tooling': "### 开发工具",
            }

            for cat_key, header in categories.items():
                cat_decisions = [d for d in decisions if d.category == cat_key]
                if cat_decisions:
                    context_lines.append(header)
                    for d in cat_decisions:
                        context_lines.append(f"- **{d.key}**: {d.value}")
                        if d.description:
                            context_lines.append(f"  - {d.description}")
                    context_lines.append("")

            # Add file registry
            if file_registry.exists() and file_registry.count() <= 30:
                context_lines.append("### 已创建的文件")
                for f in file_registry:
                    context_lines.append(f"- `{f.file_path}`: {f.description}")
                context_lines.append("")
        else:
            context_lines.append("这是一个新项目，尚未做出任何技术决策。")
            context_lines.append("")

        context_for_prompt = "\n".join(context_lines)

        return Response({
            'decisions': ProjectDecisionListSerializer(decisions, many=True).data,
            'file_registry': ProjectFileRegistrySerializer(file_registry, many=True).data,
            'context_for_prompt': context_for_prompt,
        })
