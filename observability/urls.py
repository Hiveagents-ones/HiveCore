"""
Observability URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'observability'

router = DefaultRouter()
router.register(r'usage', views.UsageViewSet, basename='usage')
router.register(r'executions', views.ExecutionViewSet, basename='executions')
router.register(r'timeline', views.TimelineViewSet, basename='timeline')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),

    # Ingest endpoints (for agentscope)
    path('ingest/usage/', views.IngestUsageView.as_view(), name='ingest-usage'),
    path('ingest/execution/', views.IngestExecutionView.as_view(), name='ingest-execution'),
    path('ingest/timeline/', views.IngestTimelineView.as_view(), name='ingest-timeline'),
    path('ingest/decision/', views.IngestDecisionView.as_view(), name='ingest-decision'),
    path('ingest/file-registry/', views.IngestFileRegistryView.as_view(), name='ingest-file-registry'),
    path('ingest/agent-selection/', views.IngestAgentSelectionView.as_view(), name='ingest-agent-selection'),

    # Project stats
    path('project/<str:project_id>/stats/', views.ProjectStatsView.as_view(), name='project-stats'),

    # SSE stream
    path('stream/', views.SSEStreamView.as_view(), name='stream'),
]
