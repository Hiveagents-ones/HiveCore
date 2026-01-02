"""
Observability views for agentscope integration.

Provides:
1. Ingest APIs for agentscope to push data
2. Query APIs for frontend to retrieve data
3. SSE stream for real-time updates
"""

import json
from django.conf import settings
from django.http import StreamingHttpResponse
from django.db.models import Sum, Avg, Count, Q
from django.db.models.functions import TruncHour, TruncDay
from django.utils import timezone
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission


class IsAuthenticatedOrAPIKey(BasePermission):
    """Allow access if user is authenticated OR has valid API key."""

    def has_permission(self, request, view):
        # Check if authenticated via JWT
        if request.user and request.user.is_authenticated:
            return True
        # Check if has tenant (via API key)
        if hasattr(request, 'tenant') and request.tenant:
            return True
        return False

from tenants.mixins import TenantQuerySetMixin
from .models import UsageRecord, ExecutionRecord, TimelineEvent
from .serializers import (
    UsageRecordSerializer, UsageRecordIngestSerializer,
    ExecutionRecordSerializer, ExecutionRecordIngestSerializer,
    TimelineEventSerializer, TimelineEventIngestSerializer,
)


# =============================================================================
# Ingest APIs (for agentscope)
# =============================================================================

class IngestUsageView(APIView):
    """Ingest token usage data from agentscope.

    POST /api/v1/observability/ingest/usage/

    Headers:
        X-API-Key: hc_xxxxx

    Body:
        {
            "timestamp": "2024-01-01T00:00:00Z",
            "agentscope_project_id": "proj-123",
            "agentscope_agent_id": "agent-456",
            "agent_name": "Strategy Agent",
            "model_name": "gpt-4",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost_usd": 0.01,
            "duration_ms": 1500
        }
    """

    # Allow API key auth (no user required)
    permission_classes = [AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Invalid or missing API key'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = UsageRecordIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Create usage record
        usage = UsageRecord.objects.create(
            tenant=tenant,
            timestamp=data['timestamp'],
            agentscope_project_id=data['agentscope_project_id'],
            agentscope_agent_id=data['agentscope_agent_id'],
            agent_name=data['agent_name'],
            model_name=data['model_name'],
            input_tokens=data['input_tokens'],
            output_tokens=data['output_tokens'],
            total_tokens=data['total_tokens'],
            cost_usd=data['cost_usd'],
            duration_ms=data['duration_ms'],
            span_id=data.get('span_id', ''),
        )

        # Publish SSE event
        self._publish_sse(tenant, 'usage', {
            'id': str(usage.id),
            'agent_name': usage.agent_name,
            'total_tokens': usage.total_tokens,
            'cost_usd': float(usage.cost_usd),
        })

        return Response({'status': 'ok', 'id': str(usage.id)}, status=status.HTTP_201_CREATED)

    def _publish_sse(self, tenant, event_type, data):
        """Publish event to Redis for SSE subscribers."""
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                r = redis.from_url(redis_url)
                r.publish(f"sse:{tenant.id}", json.dumps({
                    'type': event_type,
                    'data': data
                }))
        except Exception:
            # Redis not available, skip SSE
            pass


class IngestExecutionView(APIView):
    """Ingest agent execution data from agentscope.

    POST /api/v1/observability/ingest/execution/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Invalid or missing API key'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = ExecutionRecordIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        execution_id = data['execution_id']

        # Update or create execution record
        execution, created = ExecutionRecord.objects.update_or_create(
            execution_id=execution_id,
            defaults={
                'tenant': tenant,
                'agentscope_project_id': data['agentscope_project_id'],
                'agentscope_agent_id': data['agentscope_agent_id'],
                'agent_name': data['agent_name'],
                'node_id': data.get('node_id', ''),
                'round_index': data.get('round_index', 0),
                'start_time': data['start_time'],
                'end_time': data.get('end_time'),
                'duration_ms': data.get('duration_ms'),
                'status': data.get('status', 'running'),
                'content': data.get('content', ''),
                'error_message': data.get('error_message', ''),
                'llm_calls': data.get('llm_calls', 0),
                'total_tokens': data.get('total_tokens', 0),
                'total_cost_usd': data.get('total_cost_usd', 0),
            }
        )

        # Publish SSE event
        self._publish_sse(tenant, 'execution', {
            'execution_id': execution_id,
            'agent_name': execution.agent_name,
            'status': execution.status,
            'round_index': execution.round_index,
        })

        return Response(
            {'status': 'ok', 'id': str(execution.id), 'created': created},
            status=status.HTTP_201_CREATED
        )

    def _publish_sse(self, tenant, event_type, data):
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                r = redis.from_url(redis_url)
                r.publish(f"sse:{tenant.id}", json.dumps({
                    'type': event_type,
                    'data': data
                }))
        except Exception:
            pass


class IngestTimelineView(APIView):
    """Ingest timeline event from agentscope.

    POST /api/v1/observability/ingest/timeline/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Invalid or missing API key'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = TimelineEventIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        event = TimelineEvent.objects.create(
            tenant=tenant,
            event_type=data['event_type'],
            agentscope_project_id=data.get('project_id', ''),
            agentscope_agent_id=data.get('agent_id', ''),
            node_id=data.get('node_id', ''),
            message=data.get('message', ''),
            metadata=data.get('metadata', {}),
        )

        # Publish SSE event
        self._publish_sse(tenant, 'timeline', {
            'event_type': event.event_type,
            'agent_id': event.agentscope_agent_id,
            'message': event.message,
        })

        return Response({'status': 'ok', 'id': str(event.id)}, status=status.HTTP_201_CREATED)

    def _publish_sse(self, tenant, event_type, data):
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                r = redis.from_url(redis_url)
                r.publish(f"sse:{tenant.id}", json.dumps({
                    'type': event_type,
                    'data': data
                }))
        except Exception:
            pass


class IngestDecisionView(APIView):
    """Ingest project decision from agentscope.

    POST /api/v1/observability/ingest/decision/

    Headers:
        X-API-Key: hc_xxxxx

    Body:
        {
            "project_id": 1,
            "execution_round_id": "uuid-string",  // optional
            "category": "tech_stack",
            "key": "frontend_framework",
            "value": "Vue 3",
            "description": "Using Vue 3 with Composition API",
            "made_by_agent_name": "scaffold-agent",
            "round_index": 0
        }

    Categories: tech_stack, architecture, file_structure, api_design,
                component, constraint, dependency, tooling
    """

    permission_classes = [AllowAny]

    def post(self, request):
        from api.models import Project, Agent, ProjectDecision

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Invalid or missing API key'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate required fields
        required = ['project_id', 'category', 'key', 'value']
        for field in required:
            if field not in request.data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = request.data

        # Get project
        try:
            project = Project.objects.get(id=data['project_id'])
        except Project.DoesNotExist:
            return Response(
                {'error': f'Project {data["project_id"]} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get execution round if provided
        execution_round = None
        if data.get('execution_round_id'):
            from execution.models import ExecutionRound
            try:
                execution_round = ExecutionRound.objects.get(id=data['execution_round_id'])
            except ExecutionRound.DoesNotExist:
                pass

        # Get agent if name provided
        agent = None
        agent_name = data.get('made_by_agent_name', '')
        if agent_name:
            agent = Agent.objects.filter(name=agent_name).first()

        # Check for existing active decision with same category+key
        existing = ProjectDecision.objects.filter(
            project=project,
            category=data['category'],
            key=data['key'],
            is_active=True,
        ).first()

        # Create new decision
        decision = ProjectDecision.objects.create(
            project=project,
            execution_round=execution_round,
            category=data['category'],
            key=data['key'],
            value=data['value'],
            description=data.get('description', ''),
            made_by_agent=agent,
            made_by_agent_name=agent_name,
            round_index=data.get('round_index', 0),
        )

        # Supersede old decision if exists
        if existing:
            existing.supersede(decision)

        # Publish SSE event
        self._publish_sse(tenant, 'decision', {
            'project_id': project.id,
            'category': decision.category,
            'key': decision.key,
            'value': decision.value,
            'made_by': agent_name,
        })

        return Response({
            'status': 'ok',
            'id': decision.id,
            'superseded': existing.id if existing else None,
        }, status=status.HTTP_201_CREATED)

    def _publish_sse(self, tenant, event_type, data):
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                r = redis.from_url(redis_url)
                r.publish(f"sse:{tenant.id}", json.dumps({
                    'type': event_type,
                    'data': data
                }))
        except Exception:
            pass


class IngestFileRegistryView(APIView):
    """Ingest file registry entry from agentscope.

    POST /api/v1/observability/ingest/file-registry/

    Headers:
        X-API-Key: hc_xxxxx

    Body:
        {
            "project_id": 1,
            "execution_round_id": "uuid-string",  // optional
            "file_path": "src/components/Header.vue",
            "description": "Main header component with navigation",
            "created_by_agent_name": "frontend-agent"
        }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        from api.models import Project, Agent, ProjectFileRegistry

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Invalid or missing API key'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate required fields
        required = ['project_id', 'file_path', 'description']
        for field in required:
            if field not in request.data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = request.data

        # Get project
        try:
            project = Project.objects.get(id=data['project_id'])
        except Project.DoesNotExist:
            return Response(
                {'error': f'Project {data["project_id"]} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get execution round if provided
        execution_round = None
        if data.get('execution_round_id'):
            from execution.models import ExecutionRound
            try:
                execution_round = ExecutionRound.objects.get(id=data['execution_round_id'])
            except ExecutionRound.DoesNotExist:
                pass

        # Get agent if name provided
        agent = None
        agent_name = data.get('created_by_agent_name', '')
        if agent_name:
            agent = Agent.objects.filter(name=agent_name).first()

        # Create or update file registry entry
        registry, created = ProjectFileRegistry.objects.update_or_create(
            project=project,
            file_path=data['file_path'],
            defaults={
                'execution_round': execution_round,
                'description': data['description'],
                'created_by_agent': agent,
            }
        )

        return Response({
            'status': 'ok',
            'id': registry.id,
            'created': created,
        }, status=status.HTTP_201_CREATED)


class IngestAgentSelectionView(APIView):
    """Ingest agent selection decision from agentscope.

    POST /api/v1/observability/ingest/agent-selection/

    Headers:
        X-API-Key: hc_xxxxx

    Body:
        {
            "execution_round_id": "uuid-string",
            "candidates": [
                {
                    "agent_id": "agent-123",  // optional, for DB lookup
                    "agent_name": "Strategy Agent",
                    "s_base_score": 0.75,
                    "requirement_fit_score": 0.8,
                    "total_score": 0.95,
                    "scoring_breakdown": {...},
                    "requirement_fit_matched": {"skills": ["python"], "domains": ["backend"]},
                    "requirement_fit_missing": {"skills": ["rust"]},
                    "requirement_fit_partial": {"skills": 0.8, "domains": 1.0},
                    "requirement_fit_rationales": ["skills: matched 4/5 requirements"],
                    "is_cold_start": false,
                    "cold_start_slot_reserved": false,
                    "risk_notes": [],
                    "is_selected": true,
                    "decision_source": "system",
                    "selection_order": 0,
                    "batch_index": 0
                },
                ...more candidates
            ]
        }

    This corresponds to AgentScope's SelectionDecision and CandidateRanking.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        from api.models import Agent
        from execution.models import ExecutionRound, AgentSelectionDecision

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Invalid or missing API key'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate required fields
        if 'execution_round_id' not in request.data:
            return Response(
                {'error': 'Missing required field: execution_round_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'candidates' not in request.data or not request.data['candidates']:
            return Response(
                {'error': 'Missing required field: candidates (must be non-empty array)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data

        # Get execution round
        try:
            execution_round = ExecutionRound.objects.get(id=data['execution_round_id'])
        except ExecutionRound.DoesNotExist:
            return Response(
                {'error': f'ExecutionRound {data["execution_round_id"]} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete existing selections for this round (full replace)
        AgentSelectionDecision.objects.filter(execution_round=execution_round).delete()

        created_ids = []
        for idx, candidate in enumerate(data['candidates']):
            # Resolve agent if agent_id provided
            agent = None
            agent_id = candidate.get('agent_id')
            if agent_id:
                try:
                    agent = Agent.objects.get(pk=agent_id)
                except Agent.DoesNotExist:
                    pass

            # Convert set fields to lists for JSON storage
            def to_list(val):
                if isinstance(val, set):
                    return list(val)
                if isinstance(val, dict):
                    return {k: list(v) if isinstance(v, set) else v for k, v in val.items()}
                return val

            selection = AgentSelectionDecision.objects.create(
                tenant=tenant,
                execution_round=execution_round,
                agent=agent,
                agent_name=candidate.get('agent_name', ''),
                s_base_score=candidate.get('s_base_score', 0),
                requirement_fit_score=candidate.get('requirement_fit_score', 0),
                total_score=candidate.get('total_score', 0),
                scoring_breakdown=candidate.get('scoring_breakdown', {}),
                requirement_fit_matched=to_list(candidate.get('requirement_fit_matched', {})),
                requirement_fit_missing=to_list(candidate.get('requirement_fit_missing', {})),
                requirement_fit_partial=candidate.get('requirement_fit_partial', {}),
                requirement_fit_rationales=candidate.get('requirement_fit_rationales', []),
                is_cold_start=candidate.get('is_cold_start', False),
                cold_start_slot_reserved=candidate.get('cold_start_slot_reserved', False),
                risk_notes=candidate.get('risk_notes', []),
                is_selected=candidate.get('is_selected', False),
                decision_source=candidate.get('decision_source', 'system'),
                selection_order=candidate.get('selection_order', idx),
                batch_index=candidate.get('batch_index', 0),
            )
            created_ids.append(str(selection.id))

        # Publish SSE event
        selected = next((c for c in data['candidates'] if c.get('is_selected')), None)
        self._publish_sse(tenant, 'agent_selection', {
            'execution_round_id': str(execution_round.id),
            'selected_agent': selected.get('agent_name') if selected else None,
            'candidate_count': len(data['candidates']),
        })

        return Response({
            'status': 'ok',
            'created': len(created_ids),
            'ids': created_ids,
        }, status=status.HTTP_201_CREATED)

    def _publish_sse(self, tenant, event_type, data):
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                r = redis.from_url(redis_url)
                r.publish(f"sse:{tenant.id}", json.dumps({
                    'type': event_type,
                    'data': data
                }))
        except Exception:
            pass


# =============================================================================
# Query APIs (for frontend)
# =============================================================================

class UsageViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """Query token usage records."""

    queryset = UsageRecord.objects.all()
    serializer_class = UsageRecordSerializer
    permission_classes = [IsAuthenticatedOrAPIKey]
    filterset_fields = ['agentscope_project_id', 'agent_name', 'model_name']

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get usage summary.

        GET /api/v1/observability/usage/summary/?project=xxx&days=30
        """
        project_id = request.GET.get('project')
        days = int(request.GET.get('days', 30))

        qs = self.get_queryset().filter(
            timestamp__gte=timezone.now() - timedelta(days=days)
        )

        if project_id:
            qs = qs.filter(agentscope_project_id=project_id)

        stats = qs.aggregate(
            total_tokens=Sum('total_tokens'),
            total_cost=Sum('cost_usd'),
            total_calls=Count('id'),
            avg_duration=Avg('duration_ms'),
        )

        # By agent
        by_agent = list(qs.values('agent_name').annotate(
            tokens=Sum('total_tokens'),
            cost=Sum('cost_usd'),
            calls=Count('id'),
        ).order_by('-tokens')[:10])

        # By model
        by_model = list(qs.values('model_name').annotate(
            tokens=Sum('total_tokens'),
            cost=Sum('cost_usd'),
            calls=Count('id'),
        ).order_by('-tokens'))

        return Response({
            'summary': {
                'total_tokens': stats['total_tokens'] or 0,
                'total_cost_usd': float(stats['total_cost'] or 0),
                'total_calls': stats['total_calls'] or 0,
                'avg_duration_ms': float(stats['avg_duration'] or 0),
            },
            'by_agent': by_agent,
            'by_model': by_model,
        })

    @action(detail=False, methods=['get'])
    def trend(self, request):
        """Get usage trend over time.

        GET /api/v1/observability/usage/trend/?project=xxx&interval=hour
        """
        project_id = request.GET.get('project')
        interval = request.GET.get('interval', 'hour')

        qs = self.get_queryset()
        if project_id:
            qs = qs.filter(agentscope_project_id=project_id)

        if interval == 'hour':
            qs = qs.filter(timestamp__gte=timezone.now() - timedelta(hours=24))
            truncate_fn = TruncHour('timestamp')
        else:
            qs = qs.filter(timestamp__gte=timezone.now() - timedelta(days=30))
            truncate_fn = TruncDay('timestamp')

        trend = list(qs.annotate(
            period=truncate_fn
        ).values('period').annotate(
            tokens=Sum('total_tokens'),
            cost=Sum('cost_usd'),
            calls=Count('id'),
        ).order_by('period'))

        # Convert datetime to string
        for item in trend:
            item['period'] = item['period'].isoformat() if item['period'] else None
            item['cost'] = float(item['cost']) if item['cost'] else 0

        return Response(trend)


class ExecutionViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """Query execution records."""

    queryset = ExecutionRecord.objects.all()
    serializer_class = ExecutionRecordSerializer
    permission_classes = [IsAuthenticatedOrAPIKey]
    filterset_fields = ['status', 'agentscope_project_id', 'agent_name']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently running executions.

        GET /api/v1/observability/executions/active/
        """
        qs = self.get_queryset().filter(status='running')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class TimelineViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """Query timeline events."""

    queryset = TimelineEvent.objects.all()
    serializer_class = TimelineEventSerializer
    permission_classes = [IsAuthenticatedOrAPIKey]
    filterset_fields = ['event_type', 'agentscope_project_id']


class ProjectStatsView(APIView):
    """Get observability stats for a project.

    GET /api/v1/observability/project/{project_id}/stats/
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def get(self, request, project_id):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=status.HTTP_401_UNAUTHORIZED)

        # Usage stats
        usage_stats = UsageRecord.objects.filter(
            tenant=tenant,
            agentscope_project_id=project_id
        ).aggregate(
            total_tokens=Sum('total_tokens'),
            total_cost=Sum('cost_usd'),
            llm_calls=Count('id'),
        )

        # Execution stats
        exec_stats = ExecutionRecord.objects.filter(
            tenant=tenant,
            agentscope_project_id=project_id
        ).aggregate(
            total_executions=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed')),
            avg_duration=Avg('duration_ms'),
        )

        total_exec = exec_stats['total_executions'] or 0
        completed = exec_stats['completed'] or 0

        # Active agents
        active_agents = list(ExecutionRecord.objects.filter(
            tenant=tenant,
            agentscope_project_id=project_id,
            status='running'
        ).values('agent_name', 'start_time', 'round_index'))

        return Response({
            'project_id': project_id,
            'usage': {
                'total_tokens': usage_stats['total_tokens'] or 0,
                'total_cost_usd': float(usage_stats['total_cost'] or 0),
                'llm_calls': usage_stats['llm_calls'] or 0,
            },
            'executions': {
                'total': total_exec,
                'completed': completed,
                'failed': exec_stats['failed'] or 0,
                'success_rate': round(completed / total_exec * 100, 2) if total_exec else 0,
                'avg_duration_ms': float(exec_stats['avg_duration'] or 0),
            },
            'active_agents': active_agents,
        })


# =============================================================================
# SSE Stream (for real-time updates)
# =============================================================================

class SSEStreamView(APIView):
    """Server-Sent Events stream for real-time updates.

    GET /api/v1/observability/stream/?project=xxx

    Requires Redis for pub/sub. Falls back to polling if Redis unavailable.
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant'}, status=status.HTTP_401_UNAUTHORIZED)

        project_id = request.GET.get('project')

        response = StreamingHttpResponse(
            self._event_stream(tenant, project_id),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    def _event_stream(self, tenant, project_id=None):
        """Generate SSE event stream."""
        import time

        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'status': 'ok'})}\n\n"

        # Try Redis pub/sub
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                r = redis.from_url(redis_url)
                pubsub = r.pubsub()
                pubsub.subscribe(f"sse:{tenant.id}")

                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])

                            # Filter by project if specified
                            if project_id:
                                msg_project = data.get('data', {}).get('project_id')
                                if msg_project and msg_project != project_id:
                                    continue

                            event_type = data.get('type', 'message')
                            yield f"event: {event_type}\ndata: {json.dumps(data['data'])}\n\n"
                        except (json.JSONDecodeError, KeyError):
                            pass

        except Exception:
            # Redis not available, use simple heartbeat
            while True:
                yield f"event: heartbeat\ndata: {json.dumps({'time': timezone.now().isoformat()})}\n\n"
                time.sleep(30)
