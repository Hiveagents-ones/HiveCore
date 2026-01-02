"""
HiveCore API Models

Data models for the HiveCore multi-agent orchestration system.
"""

from django.db import models


class Agent(models.Model):
    """Agent (AI assistant) model.

    Agents are system-level resources shared across all tenants.
    They represent the available AI assistants in the system.
    """

    name = models.CharField(max_length=100, verbose_name="Agent name")
    agent_no = models.CharField(
        max_length=50, unique=True, verbose_name="Agent number (e.g., Agent No.1)"
    )
    duty = models.CharField(max_length=200, verbose_name="Agent duty/role")
    detail = models.TextField(verbose_name="Agent capability details")
    preview = models.TextField(blank=True, verbose_name="Preview content/deliverables")
    avatar = models.URLField(blank=True, verbose_name="Avatar URL")
    cost_per_min = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Cost per minute ($)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
        ordering = ["agent_no"]

    def __str__(self):
        return f"{self.agent_no} - {self.name}"


class Project(models.Model):
    """Project model.

    Projects are tenant-scoped. All related data (conversations, tasks, etc.)
    are isolated by tenant through the project relationship.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Phase(models.TextChoices):
        """Project workflow phases (四个阶段)."""
        CONVERSATION = "conversation", "需求对话"      # 阶段1: 对话澄清需求
        TEAM_BUILDING = "team_building", "团队组建"    # 阶段2: 选择/确认Agent团队
        WORKING = "working", "工作中"                  # 阶段3: Agent执行任务
        DELIVERY = "delivery", "交付"                  # 阶段4: 交付产物

    # Tenant isolation
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='projects',
        null=True,  # Allow null for existing data during migration
        blank=True,
        verbose_name='Tenant'
    )

    name = models.CharField(max_length=200, verbose_name="Project name")
    description = models.TextField(blank=True, verbose_name="Project description")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    phase = models.CharField(
        max_length=20,
        choices=Phase.choices,
        default=Phase.CONVERSATION,
        verbose_name="Current workflow phase"
    )
    # 主对话（需求澄清对话）
    main_conversation = models.OneToOneField(
        'Conversation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='as_main_project',
        verbose_name="Main conversation for requirements"
    )
    member_count = models.IntegerField(default=0, verbose_name="Team member count")
    run_time = models.CharField(
        max_length=50, blank=True, verbose_name="Total run time"
    )
    credits_usage = models.IntegerField(default=0, verbose_name="Credits used")
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Total cost ($)"
    )
    progress = models.IntegerField(default=0, verbose_name="Progress percentage (0-100)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Conversation(models.Model):
    """Conversation session model."""

    class SourceType(models.TextChoices):
        UPLOAD_DOC = "upload_doc", "上传文档"
        MEMORY = "memory", "读取记忆"
        COMMUNITY = "community", "社区论坛"
        NO_DATA = "no_data", "无数据来源"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, blank=True, verbose_name="Conversation title")
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        blank=True,
        verbose_name="Data source type",
    )
    first_user_message = models.TextField(
        blank=True, verbose_name="First user message (for quick display)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Conversation {self.id}"


class Message(models.Model):
    """Chat message model."""

    class MessageType(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    type = models.CharField(max_length=20, choices=MessageType.choices)
    content = models.TextField(verbose_name="Message content")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.type}: {self.content[:50]}..."


class MessageAttachment(models.Model):
    """Attachment for a chat message.

    Links uploaded files to messages, allowing users to reference files
    in their conversations with the AA assistant.
    """

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Parent message",
    )
    file = models.ForeignKey(
        'File',
        on_delete=models.CASCADE,
        related_name="message_attachments",
        verbose_name="Attached file",
    )
    # Cached file info for quick access
    filename = models.CharField(max_length=255, verbose_name="File name")
    file_type = models.CharField(max_length=50, verbose_name="File type")
    # AI-generated summary for complex files (PDFs, images, etc.)
    summary = models.TextField(blank=True, verbose_name="AI summary of file content")
    # Extracted text content for text-based files
    text_content = models.TextField(blank=True, verbose_name="Extracted text content")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message Attachment"
        verbose_name_plural = "Message Attachments"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.filename} attached to message {self.message_id}"


class Requirement(models.Model):
    """Requirement model."""

    class RequirementType(models.TextChoices):
        REQUIREMENT = "requirement", "Requirement"
        DELIVERY_STANDARD = "delivery_standard", "Delivery Standard"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="requirements",
        null=True,
        blank=True,
    )
    content = models.TextField(verbose_name="Requirement content")
    type = models.CharField(
        max_length=30,
        choices=RequirementType.choices,
        default=RequirementType.REQUIREMENT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Requirement"
        verbose_name_plural = "Requirements"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.content[:50]}..."


class DeliveryStandard(models.Model):
    """Delivery standard for a requirement."""

    requirement = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="delivery_standards"
    )
    content = models.TextField(verbose_name="Delivery standard content")
    order = models.IntegerField(default=0, verbose_name="Display order")

    class Meta:
        verbose_name = "Delivery Standard"
        verbose_name_plural = "Delivery Standards"
        ordering = ["order"]

    def __str__(self):
        return f"{self.content[:50]}..."


class TeamMember(models.Model):
    """Project team member (Agent assignment)."""

    class MemberStatus(models.TextChoices):
        COMPLETE = "Complete", "Complete"
        ERROR = "Error", "Error"
        WORKING = "Working", "Working"
        AWAIT = "Await", "Await"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="team_members"
    )
    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="assignments"
    )
    role = models.CharField(max_length=100, blank=True, verbose_name="Role in project")
    status = models.CharField(
        max_length=20, choices=MemberStatus.choices, default=MemberStatus.AWAIT
    )
    time_spent = models.CharField(max_length=50, blank=True, verbose_name="Time spent")
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Cost ($)"
    )
    progress = models.IntegerField(default=0, verbose_name="Current progress")
    progress_total = models.IntegerField(default=100, verbose_name="Total progress")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"
        unique_together = ["project", "agent"]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.agent.agent_no} in {self.project.name}"


class Task(models.Model):
    """Task item for project monitoring."""

    class TaskStatus(models.TextChoices):
        COMPLETE = "Complete", "Complete"
        ERROR = "Error", "Error"
        WORKING = "Working", "Working"
        AWAIT = "Await", "Await"

    class AgentType(models.TextChoices):
        FE = "FE", "Frontend"
        BE = "BE", "Backend"
        PM = "PM", "Project Manager"
        QA = "QA", "Quality Assurance"
        DESIGN = "Design", "Design"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="tasks"
    )
    agent = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, related_name="tasks"
    )
    title = models.CharField(max_length=200, verbose_name="Task title")
    status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.AWAIT
    )
    agent_type = models.CharField(
        max_length=20, choices=AgentType.choices, blank=True, verbose_name="Agent type"
    )
    time_spent = models.CharField(max_length=50, blank=True, verbose_name="Time spent")
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Cost ($)"
    )
    progress = models.IntegerField(default=0, verbose_name="Current progress")
    progress_total = models.IntegerField(default=100, verbose_name="Total progress")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"


class AgentThinking(models.Model):
    """Agent thinking process for the detail panel."""

    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="thinkings"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="agent_thinkings"
    )
    content = models.TextField(verbose_name="Thinking content")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agent Thinking"
        verbose_name_plural = "Agent Thinkings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agent.agent_no} thinking in {self.project.name}"


class AgentTaskItem(models.Model):
    """Agent task board items for the detail panel."""

    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="task_items"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="agent_task_items"
    )
    category = models.CharField(max_length=100, verbose_name="Task category (e.g., A. 项目启动)")
    content = models.TextField(verbose_name="Task item content")
    is_checked = models.BooleanField(default=False, verbose_name="Is checked")
    order = models.IntegerField(default=0, verbose_name="Display order")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Agent Task Item"
        verbose_name_plural = "Agent Task Items"
        ordering = ["category", "order"]

    def __str__(self):
        return f"{self.agent.agent_no}: {self.content[:30]}..."


class AgentCollaboration(models.Model):
    """Agent collaboration messages for the detail panel."""

    class Direction(models.TextChoices):
        RECEIVED = "received", "Received"
        SENT = "sent", "Sent"

    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="collaborations"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="agent_collaborations"
    )
    direction = models.CharField(
        max_length=20, choices=Direction.choices, default=Direction.RECEIVED
    )
    from_agent = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_collaborations", verbose_name="From agent (for received)"
    )
    to_agent = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="received_collaborations", verbose_name="To agent (for sent)"
    )
    content = models.TextField(verbose_name="Message content")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Agent Collaboration"
        verbose_name_plural = "Agent Collaborations"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.agent.agent_no} {self.direction}: {self.content[:30]}..."


class Folder(models.Model):
    """Folder model for file management."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="folders"
    )
    name = models.CharField(max_length=200, verbose_name="Folder name")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children", verbose_name="Parent folder"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Folder"
        verbose_name_plural = "Folders"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_path(self):
        """Get full path of folder."""
        if self.parent:
            return f"{self.parent.get_path()}/{self.name}"
        return self.name


class File(models.Model):
    """File model for file management."""

    class FileType(models.TextChoices):
        DOCUMENT = "document", "Document"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        SPREADSHEET = "spreadsheet", "Spreadsheet"
        PRESENTATION = "presentation", "Presentation"
        CODE = "code", "Code"
        OTHER = "other", "Other"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="files"
    )
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, null=True, blank=True,
        related_name="files", verbose_name="Parent folder"
    )
    name = models.CharField(max_length=200, verbose_name="File name")
    file_type = models.CharField(
        max_length=20, choices=FileType.choices, default=FileType.OTHER
    )
    size = models.BigIntegerField(default=0, verbose_name="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True, verbose_name="MIME type")
    url = models.URLField(blank=True, verbose_name="File URL or path")
    thumbnail_url = models.URLField(blank=True, verbose_name="Thumbnail URL")
    description = models.TextField(blank=True, verbose_name="File description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "File"
        verbose_name_plural = "Files"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_path(self):
        """Get full path of file."""
        if self.folder:
            return f"{self.folder.get_path()}/{self.name}"
        return self.name


class ProjectDecision(models.Model):
    """Project-level decision record.

    Tracks technology choices, architecture decisions, and other
    project-level decisions made by agents. Corresponds to AgentScope's
    ProjectMemory.record_decision().

    Example:
        - category: tech_stack, key: frontend_framework, value: Vue 3
        - category: architecture, key: api_pattern, value: REST
        - category: dependency, key: pydantic, value: >=2.0.0
    """

    class Category(models.TextChoices):
        TECH_STACK = "tech_stack", "Tech Stack"
        ARCHITECTURE = "architecture", "Architecture"
        FILE_STRUCTURE = "file_structure", "File Structure"
        API_DESIGN = "api_design", "API Design"
        COMPONENT = "component", "Component"
        CONSTRAINT = "constraint", "Constraint"
        DEPENDENCY = "dependency", "Dependency"
        TOOLING = "tooling", "Tooling"

    # Tenant isolation through project
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="decisions",
        verbose_name="Project",
    )

    # Link to execution round where decision was made
    execution_round = models.ForeignKey(
        'execution.ExecutionRound',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decisions",
        verbose_name="Execution round",
    )

    # Decision data
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        verbose_name="Decision category",
    )
    key = models.CharField(
        max_length=200,
        verbose_name="Decision key (e.g., frontend_framework, linter)",
    )
    value = models.TextField(
        verbose_name="Decision value (e.g., Vue 3, ESLint)",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Human-readable explanation/rationale",
    )

    # Who made the decision
    made_by_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decisions_made",
        verbose_name="Agent that made this decision",
    )
    made_by_agent_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Agent name (preserved even if agent deleted)",
    )

    # Round tracking
    round_index = models.IntegerField(
        default=0,
        verbose_name="Round index when decision was made",
    )

    # Metadata
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is this decision still active",
    )
    superseded_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supersedes",
        verbose_name="Newer decision that replaced this one",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project Decision"
        verbose_name_plural = "Project Decisions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "category"]),
            models.Index(fields=["project", "category", "key"]),
            models.Index(fields=["execution_round"]),
        ]
        # Same category+key in a project should be unique for active decisions
        constraints = [
            models.UniqueConstraint(
                fields=["project", "category", "key"],
                condition=models.Q(is_active=True),
                name="unique_active_decision_per_project",
            )
        ]

    def __str__(self):
        return f"{self.category}:{self.key} = {self.value[:50]}"

    def save(self, *args, **kwargs):
        # Preserve agent name if agent is set
        if self.made_by_agent and not self.made_by_agent_name:
            self.made_by_agent_name = self.made_by_agent.name
        super().save(*args, **kwargs)

    def supersede(self, new_decision: 'ProjectDecision') -> None:
        """Mark this decision as superseded by a newer one."""
        self.is_active = False
        self.superseded_by = new_decision
        self.save(update_fields=["is_active", "superseded_by", "updated_at"])


class ProjectFileRegistry(models.Model):
    """Registry of files created in a project.

    Tracks the purpose and description of each file in the project
    workspace. Corresponds to AgentScope's ProjectMemory.register_file().
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="file_registry",
        verbose_name="Project",
    )
    execution_round = models.ForeignKey(
        'execution.ExecutionRound',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_files",
        verbose_name="Execution round",
    )

    file_path = models.CharField(
        max_length=500,
        verbose_name="Relative file path from workspace root",
    )
    description = models.TextField(
        verbose_name="Brief description of the file's purpose",
    )

    # Who created/registered the file
    created_by_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_files",
        verbose_name="Agent that created this file",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project File Registry"
        verbose_name_plural = "Project File Registries"
        ordering = ["file_path"]
        unique_together = ["project", "file_path"]

    def __str__(self):
        return f"{self.file_path}: {self.description[:50]}"
