# -*- coding: utf-8 -*-
"""URL configuration for execution app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ExecutionRoundViewSet,
    ExecutionArtifactViewSet,
    AgentSelectionDecisionViewSet,
    ProjectExecuteView,
    ActiveExecutionsView,
)
from .sse import ExecutionSSEView, ActiveExecutionsSSEView

router = DefaultRouter()
router.register(r'rounds', ExecutionRoundViewSet, basename='execution-round')
router.register(r'artifacts', ExecutionArtifactViewSet, basename='execution-artifact')
router.register(r'selections', AgentSelectionDecisionViewSet, basename='agent-selection')

urlpatterns = [
    path('', include(router.urls)),
    path('active/', ActiveExecutionsView.as_view(), name='execution-active'),
    # SSE endpoints for real-time updates
    path('stream/', ActiveExecutionsSSEView.as_view(), name='execution-stream'),
    path('rounds/<uuid:pk>/stream/', ExecutionSSEView.as_view(), name='execution-round-stream'),
]

# Note: ProjectExecuteView is mounted under /api/v1/projects/{id}/execute/
# in the main urls.py, not here
