# -*- coding: utf-8 -*-
"""SSE (Server-Sent Events) views for execution progress streaming.

Provides real-time execution progress updates to the frontend via SSE.
"""
import json
import time
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from observability.views import IsAuthenticatedOrAPIKey
from observability.pubsub import subscribe_execution, _get_redis_client
from .models import ExecutionRound, ExecutionProgress


class ExecutionSSEView(APIView):
    """SSE stream for execution progress.

    GET /api/v1/execution/rounds/{id}/stream/

    Streams real-time updates for a specific execution round including:
    - Progress updates (phase, percentage, current agent)
    - Agent lifecycle events (started, completed, error)
    - Artifact creation events
    - Status changes

    Falls back to polling if Redis is unavailable.
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def get(self, request, pk):
        """Start SSE stream for execution round."""
        tenant = getattr(request, 'tenant', None)

        # Verify execution round exists and belongs to tenant
        try:
            execution_round = ExecutionRound.objects.get(pk=pk)
            if tenant and execution_round.tenant and execution_round.tenant != tenant:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except ExecutionRound.DoesNotExist:
            return Response(
                {'error': 'Execution round not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        response = StreamingHttpResponse(
            self._event_stream(str(pk), execution_round),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Connection'] = 'keep-alive'
        return response

    def _event_stream(self, execution_round_id: str, execution_round: ExecutionRound):
        """Generate SSE event stream for execution round.

        Args:
            execution_round_id: The execution round UUID.
            execution_round: The ExecutionRound model instance.

        Yields:
            SSE formatted strings.
        """
        # Send initial state
        initial_data = self._get_current_state(execution_round)
        yield f"event: connected\ndata: {json.dumps(initial_data)}\n\n"

        # Check if execution is already completed
        if execution_round.status in ['completed', 'failed', 'cancelled']:
            yield f"event: {execution_round.status}\ndata: {json.dumps(initial_data)}\n\n"
            return

        # Try Redis pub/sub for real-time updates
        redis_client = _get_redis_client()
        if redis_client:
            yield from self._redis_stream(execution_round_id, execution_round)
        else:
            yield from self._polling_stream(execution_round_id, execution_round)

    def _redis_stream(self, execution_round_id: str, execution_round: ExecutionRound):
        """Stream events via Redis pub/sub.

        Args:
            execution_round_id: The execution round UUID.
            execution_round: The ExecutionRound model instance.

        Yields:
            SSE formatted strings.
        """
        try:
            for event in subscribe_execution(execution_round_id):
                event_type = event.get('type', 'message')
                event_data = event.get('data', {})

                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                # Stop streaming if execution completed
                if event_type in ['execution_completed', 'execution_failed', 'execution_cancelled']:
                    break

        except GeneratorExit:
            # Client disconnected
            pass
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    def _polling_stream(self, execution_round_id: str, execution_round: ExecutionRound):
        """Fallback polling stream when Redis is unavailable.

        Polls the database every 2 seconds for updates.

        Args:
            execution_round_id: The execution round UUID.
            execution_round: The ExecutionRound model instance.

        Yields:
            SSE formatted strings.
        """
        last_status = execution_round.status
        last_progress = None
        poll_interval = 2  # seconds
        max_polls = 1800  # 1 hour max

        for _ in range(max_polls):
            try:
                # Refresh from database
                execution_round.refresh_from_db()

                # Check for status change
                if execution_round.status != last_status:
                    last_status = execution_round.status
                    state = self._get_current_state(execution_round)

                    if execution_round.status == 'completed':
                        yield f"event: execution_completed\ndata: {json.dumps(state)}\n\n"
                        break
                    elif execution_round.status == 'failed':
                        yield f"event: execution_failed\ndata: {json.dumps(state)}\n\n"
                        break
                    elif execution_round.status == 'cancelled':
                        yield f"event: execution_cancelled\ndata: {json.dumps(state)}\n\n"
                        break
                    else:
                        yield f"event: status_change\ndata: {json.dumps(state)}\n\n"

                # Check for progress change
                try:
                    progress = execution_round.progress
                    progress_data = {
                        'phase': progress.current_phase,
                        'agent': progress.current_agent,
                        'task': progress.current_task,
                        'progress_percent': progress.progress_percent,
                        'completed_tasks': progress.completed_tasks,
                        'total_tasks': progress.total_tasks,
                    }

                    if progress_data != last_progress:
                        last_progress = progress_data
                        yield f"event: execution_progress\ndata: {json.dumps(progress_data)}\n\n"

                except ExecutionProgress.DoesNotExist:
                    pass

                # Send heartbeat
                yield f"event: heartbeat\ndata: {json.dumps({'time': timezone.now().isoformat()})}\n\n"

                time.sleep(poll_interval)

            except GeneratorExit:
                break
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

    def _get_current_state(self, execution_round: ExecutionRound) -> dict:
        """Get current execution state.

        Args:
            execution_round: The ExecutionRound model instance.

        Returns:
            dict: Current state including status, progress, and summary.
        """
        state = {
            'execution_round_id': str(execution_round.id),
            'status': execution_round.status,
            'round_number': execution_round.round_number,
            'started_at': execution_round.started_at.isoformat() if execution_round.started_at else None,
            'completed_at': execution_round.completed_at.isoformat() if execution_round.completed_at else None,
            'total_tokens': execution_round.total_tokens,
            'total_cost_usd': float(execution_round.total_cost_usd),
            'total_llm_calls': execution_round.total_llm_calls,
        }

        # Add progress if available
        try:
            progress = execution_round.progress
            state['progress'] = {
                'phase': progress.current_phase,
                'agent': progress.current_agent,
                'task': progress.current_task,
                'progress_percent': progress.progress_percent,
                'completed_tasks': progress.completed_tasks,
                'total_tasks': progress.total_tasks,
                'completed_requirements': progress.completed_requirements,
                'total_requirements': progress.total_requirements,
            }
        except ExecutionProgress.DoesNotExist:
            state['progress'] = None

        # Add summary/error for completed executions
        if execution_round.status in ['completed', 'failed']:
            state['summary'] = execution_round.summary
            state['error_message'] = execution_round.error_message

        return state


class ActiveExecutionsSSEView(APIView):
    """SSE stream for all active executions of a tenant.

    GET /api/v1/execution/stream/

    Streams updates for all currently running executions.
    Useful for monitoring dashboards.
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def get(self, request):
        """Start SSE stream for all active executions."""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Optional project filter
        project_id = request.query_params.get('project')

        response = StreamingHttpResponse(
            self._event_stream(tenant, project_id),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Connection'] = 'keep-alive'
        return response

    def _event_stream(self, tenant, project_id=None):
        """Generate SSE stream for tenant's active executions.

        Args:
            tenant: The tenant instance.
            project_id: Optional project ID filter.

        Yields:
            SSE formatted strings.
        """
        from observability.pubsub import subscribe_events

        # Send initial list of active executions
        qs = ExecutionRound.objects.filter(
            tenant=tenant,
            status__in=['pending', 'running']
        ).select_related('project')

        if project_id:
            qs = qs.filter(project_id=project_id)

        active_list = []
        for execution in qs:
            active_list.append({
                'execution_round_id': str(execution.id),
                'project_id': execution.project_id,
                'project_name': execution.project.name if execution.project else None,
                'status': execution.status,
                'round_number': execution.round_number,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
            })

        yield f"event: connected\ndata: {json.dumps({'active_executions': active_list})}\n\n"

        # Stream updates via Redis or fallback to polling
        redis_client = _get_redis_client()
        if redis_client:
            try:
                for event in subscribe_events(str(tenant.id)):
                    # Filter by project if specified
                    if project_id:
                        event_project = event.get('project_id')
                        if event_project and str(event_project) != str(project_id):
                            continue

                    event_type = event.get('type', 'message')
                    event_data = event.get('data', {})

                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

            except GeneratorExit:
                pass
        else:
            # Polling fallback
            while True:
                yield f"event: heartbeat\ndata: {json.dumps({'time': timezone.now().isoformat()})}\n\n"
                time.sleep(5)
