"""
Django Admin configuration for HiveCore API models.
"""

from django.contrib import admin

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
    Project,
    Requirement,
    Task,
    TeamMember,
)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ["agent_no", "name", "duty", "cost_per_min", "created_at"]
    search_fields = ["name", "agent_no", "duty"]
    list_filter = ["created_at"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "member_count", "progress", "total_cost", "created_at"]
    search_fields = ["name", "description"]
    list_filter = ["status", "created_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "project", "created_at"]
    search_fields = ["title"]
    list_filter = ["created_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "type", "content_preview", "created_at"]
    search_fields = ["content"]
    list_filter = ["type", "created_at"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "type", "content_preview", "created_at"]
    search_fields = ["content"]
    list_filter = ["type", "created_at"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(DeliveryStandard)
class DeliveryStandardAdmin(admin.ModelAdmin):
    list_display = ["id", "requirement", "content_preview", "order"]
    search_fields = ["content"]
    list_filter = ["requirement"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ["id", "project", "agent", "role", "joined_at"]
    search_fields = ["role"]
    list_filter = ["project", "joined_at"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "agent", "agent_type", "status", "progress", "cost", "created_at"]
    search_fields = ["title"]
    list_filter = ["status", "agent_type", "project", "created_at"]


@admin.register(AgentThinking)
class AgentThinkingAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "project", "content_preview", "created_at"]
    search_fields = ["content"]
    list_filter = ["agent", "project", "created_at"]

    def content_preview(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    content_preview.short_description = "Content"


@admin.register(AgentTaskItem)
class AgentTaskItemAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "project", "category", "content_preview", "is_checked", "order"]
    search_fields = ["content", "category"]
    list_filter = ["agent", "project", "category", "is_checked"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(AgentCollaboration)
class AgentCollaborationAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "project", "direction", "from_agent", "to_agent", "content_preview", "created_at"]
    search_fields = ["content"]
    list_filter = ["agent", "project", "direction", "created_at"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "project", "parent", "created_at"]
    search_fields = ["name"]
    list_filter = ["project", "created_at"]


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "project", "folder", "file_type", "size", "created_at"]
    search_fields = ["name", "description"]
    list_filter = ["project", "file_type", "created_at"]
