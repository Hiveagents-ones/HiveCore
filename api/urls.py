"""
HiveCore API URL Configuration

Defines URL patterns for all API endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AgentCollaborationViewSet,
    AgentTaskItemViewSet,
    AgentThinkingViewSet,
    AgentViewSetExtended,
    ConversationViewSet,
    DeliveryStandardViewSet,
    FileViewSet,
    FolderViewSet,
    MessageViewSet,
    ProjectContextView,
    ProjectDecisionViewSet,
    ProjectFileRegistryViewSet,
    ProjectViewSetExtended,
    RequirementViewSet,
    TaskViewSet,
    TeamMemberViewSet,
)

router = DefaultRouter()
# Core resources
router.register(r"agents", AgentViewSetExtended, basename="agent")
router.register(r"projects", ProjectViewSetExtended, basename="project")
router.register(r"conversations", ConversationViewSet, basename="conversation")
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"requirements", RequirementViewSet, basename="requirement")
router.register(
    r"delivery-standards", DeliveryStandardViewSet, basename="delivery-standard"
)
router.register(r"team-members", TeamMemberViewSet, basename="team-member")
router.register(r"tasks", TaskViewSet, basename="task")

# Agent detail panel resources
router.register(r"agent-thinkings", AgentThinkingViewSet, basename="agent-thinking")
router.register(r"agent-task-items", AgentTaskItemViewSet, basename="agent-task-item")
router.register(
    r"agent-collaborations", AgentCollaborationViewSet, basename="agent-collaboration"
)

# File management resources
router.register(r"folders", FolderViewSet, basename="folder")
router.register(r"files", FileViewSet, basename="file")

# Project decisions and file registry
router.register(r"decisions", ProjectDecisionViewSet, basename="decision")
router.register(r"file-registry", ProjectFileRegistryViewSet, basename="file-registry")

urlpatterns = [
    path("", include(router.urls)),
    # Project context endpoint (for agent prompts)
    path("projects/<int:project_id>/context/", ProjectContextView.as_view(), name="project-context"),
]
