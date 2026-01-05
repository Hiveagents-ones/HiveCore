# -*- coding: utf-8 -*-
"""Views for execution app."""
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Sum, Avg
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from tenants.mixins import TenantQuerySetMixin
from observability.views import IsAuthenticatedOrAPIKey
from observability.models import UsageRecord

from .models import (
    ExecutionRound,
    AgentSelectionDecision,
    ExecutionArtifact,
    ExecutionLog,
    ExecutionProgress,
)
from .serializers import (
    ExecutionRoundListSerializer,
    ExecutionRoundDetailSerializer,
    ExecutionStartSerializer,
    AgentSelectionDecisionSerializer,
    AgentSelectionDecisionListSerializer,
    ExecutionArtifactListSerializer,
    ExecutionArtifactDetailSerializer,
    ExecutionLogSerializer,
    ExecutionProgressSerializer,
)


class ExecutionRoundViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for execution rounds.

    list: GET /api/v1/execution/rounds/
    retrieve: GET /api/v1/execution/rounds/{id}/
    """

    queryset = ExecutionRound.objects.all()
    permission_classes = [IsAuthenticatedOrAPIKey]

    def get_serializer_class(self):
        if self.action == 'list':
            return ExecutionRoundListSerializer
        return ExecutionRoundDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by project if specified
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        # Filter by status if specified
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related('project')

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get execution status with usage stats.

        GET /api/v1/execution/rounds/{id}/status/
        """
        round_obj = self.get_object()

        # Get usage stats from observability
        usage_stats = UsageRecord.objects.filter(
            tenant=round_obj.tenant,
            # Match by time range if no direct FK
            timestamp__gte=round_obj.started_at,
        ).aggregate(
            total_tokens=Sum('total_tokens'),
            total_cost=Sum('cost_usd'),
        ) if round_obj.started_at else {'total_tokens': 0, 'total_cost': 0}

        # Get progress if exists
        progress_data = None
        try:
            progress = round_obj.progress
            progress_data = ExecutionProgressSerializer(progress).data
        except ExecutionProgress.DoesNotExist:
            pass

        return Response({
            'id': str(round_obj.id),
            'status': round_obj.status,
            'round_number': round_obj.round_number,
            'started_at': round_obj.started_at.isoformat() if round_obj.started_at else None,
            'completed_at': round_obj.completed_at.isoformat() if round_obj.completed_at else None,
            'duration_seconds': round_obj.duration_seconds,
            'summary': round_obj.summary,
            'error_message': round_obj.error_message,
            'usage': {
                'total_tokens': round_obj.total_tokens or usage_stats.get('total_tokens') or 0,
                'total_cost_usd': float(round_obj.total_cost_usd or usage_stats.get('total_cost') or 0),
                'total_llm_calls': round_obj.total_llm_calls,
            },
            'progress': progress_data,
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running execution.

        POST /api/v1/execution/rounds/{id}/cancel/
        """
        round_obj = self.get_object()

        if round_obj.status not in ['pending', 'running']:
            return Response(
                {'error': f'Cannot cancel execution in {round_obj.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cancel Celery task if running
        if round_obj.celery_task_id:
            try:
                from .tasks import app as celery_app
                celery_app.control.revoke(round_obj.celery_task_id, terminate=True)
            except Exception:
                pass  # Best effort cancellation

        round_obj.cancel()

        return Response({
            'id': str(round_obj.id),
            'status': 'cancelled',
            'message': 'Execution cancelled',
        })

    @action(detail=True, methods=['get'])
    def agents(self, request, pk=None):
        """Get agent selection decisions for this round.

        GET /api/v1/execution/rounds/{id}/agents/
        """
        round_obj = self.get_object()
        selections = round_obj.agent_selections.select_related('agent').all()
        serializer = AgentSelectionDecisionSerializer(selections, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def artifacts(self, request, pk=None):
        """Get artifacts generated in this round.

        GET /api/v1/execution/rounds/{id}/artifacts/
        """
        round_obj = self.get_object()
        artifacts = round_obj.artifacts.all()

        # Filter by type if specified
        artifact_type = request.query_params.get('type')
        if artifact_type:
            artifacts = artifacts.filter(artifact_type=artifact_type)

        serializer = ExecutionArtifactListSerializer(artifacts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get execution logs for this round.

        GET /api/v1/execution/rounds/{id}/logs/
        """
        round_obj = self.get_object()
        logs = round_obj.logs.select_related('agent').all()

        # Filter by level if specified
        level = request.query_params.get('level')
        if level:
            logs = logs.filter(level=level)

        # Limit results
        limit = int(request.query_params.get('limit', 100))
        logs = logs[:limit]

        serializer = ExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)


class AgentSelectionDecisionViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for agent selection decisions.

    list: GET /api/v1/execution/selections/
    retrieve: GET /api/v1/execution/selections/{id}/
    """

    queryset = AgentSelectionDecision.objects.all()
    permission_classes = [IsAuthenticatedOrAPIKey]

    def get_serializer_class(self):
        if self.action == 'list':
            return AgentSelectionDecisionListSerializer
        return AgentSelectionDecisionSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # Filter by execution round
        round_id = self.request.query_params.get('round')
        if round_id:
            qs = qs.filter(execution_round_id=round_id)

        # Filter by agent
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)

        # Filter by is_selected
        is_selected = self.request.query_params.get('is_selected')
        if is_selected is not None:
            qs = qs.filter(is_selected=is_selected.lower() == 'true')

        # Filter by decision_source
        decision_source = self.request.query_params.get('decision_source')
        if decision_source:
            qs = qs.filter(decision_source=decision_source)

        return qs.select_related('agent', 'execution_round')

    @action(detail=False, methods=['get'])
    def by_round(self, request):
        """Get selections grouped by execution round.

        GET /api/v1/execution/selections/by_round/?project={id}
        """
        project_id = request.query_params.get('project')
        if not project_id:
            return Response(
                {'error': 'project parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rounds = ExecutionRound.objects.filter(project_id=project_id).order_by('-created_at')[:10]
        result = []

        for round_obj in rounds:
            selections = self.get_queryset().filter(execution_round=round_obj)
            serializer = AgentSelectionDecisionListSerializer(selections, many=True)
            result.append({
                'round_id': str(round_obj.id),
                'round_number': round_obj.round_number,
                'status': round_obj.status,
                'created_at': round_obj.created_at.isoformat(),
                'selections': serializer.data,
            })

        return Response(result)

    @action(detail=False, methods=['get'])
    def agent_history(self, request):
        """Get selection history for an agent.

        GET /api/v1/execution/selections/agent_history/?agent={id}
        """
        agent_id = request.query_params.get('agent')
        if not agent_id:
            return Response(
                {'error': 'agent parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        selections = self.get_queryset().filter(agent_id=agent_id).order_by('-created_at')[:50]
        serializer = AgentSelectionDecisionSerializer(selections, many=True)

        # Compute stats
        total = selections.count()
        selected_count = selections.filter(is_selected=True).count()
        avg_score = selections.aggregate(avg=models.Avg('total_score'))['avg'] or 0

        return Response({
            'agent_id': agent_id,
            'total_selections': total,
            'times_selected': selected_count,
            'selection_rate': selected_count / total if total > 0 else 0,
            'average_score': avg_score,
            'history': serializer.data,
        })


class ExecutionArtifactViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for execution artifacts.

    list: GET /api/v1/execution/artifacts/
    retrieve: GET /api/v1/execution/artifacts/{id}/
    """

    queryset = ExecutionArtifact.objects.all()
    permission_classes = [IsAuthenticatedOrAPIKey]

    def get_serializer_class(self):
        if self.action == 'list':
            return ExecutionArtifactListSerializer
        return ExecutionArtifactDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by execution round if specified
        round_id = self.request.query_params.get('round')
        if round_id:
            qs = qs.filter(execution_round_id=round_id)
        return qs

    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """Get artifact content.

        GET /api/v1/execution/artifacts/{id}/content/

        Returns the artifact content from DB or S3.
        For large S3-stored artifacts, use the download_url instead.
        """
        from .storage import get_artifact_content, MAX_DIRECT_DOWNLOAD_BYTES

        artifact = self.get_object()

        # Check size limit for direct download
        if artifact.size_bytes > MAX_DIRECT_DOWNLOAD_BYTES:
            return Response(
                {
                    'error': 'Artifact too large for direct download',
                    'size_bytes': artifact.size_bytes,
                    'use_download_url': True,
                },
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        content = get_artifact_content(artifact)

        if content is None:
            return Response(
                {'error': 'Artifact content not available'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'id': str(artifact.id),
            'file_path': artifact.file_path,
            'content': content,
            'content_hash': artifact.content_hash,
            'size_bytes': artifact.size_bytes,
        })

    @action(detail=True, methods=['get'])
    def download_url(self, request, pk=None):
        """Get download URL for artifact.

        GET /api/v1/execution/artifacts/{id}/download_url/

        Returns CloudFront URL for S3-stored artifacts,
        or direct content for DB-stored artifacts.
        """
        from .storage import get_artifact_url, get_presigned_url

        artifact = self.get_object()

        # Get URL expiration from query params (default 1 hour)
        expires_in = int(request.query_params.get('expires_in', 3600))
        expires_in = min(max(expires_in, 60), 86400)  # Clamp between 1 min and 24 hours

        if artifact.s3_key:
            # Get presigned URL for S3-stored artifact
            url = get_presigned_url(artifact.s3_key, expires_in=expires_in)
            if url:
                return Response({
                    'id': str(artifact.id),
                    'file_path': artifact.file_path,
                    'download_url': url,
                    'expires_in': expires_in,
                    'storage_type': 's3',
                })
            else:
                return Response(
                    {'error': 'Failed to generate download URL'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # Content stored in DB, no URL needed
            return Response({
                'id': str(artifact.id),
                'file_path': artifact.file_path,
                'download_url': None,
                'storage_type': 'database',
                'message': 'Content available directly via /content/ endpoint',
            })


class ProjectExecuteView(APIView):
    """Start project execution.

    POST /api/v1/projects/{id}/execute/
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def post(self, request, project_id):
        from api.models import Project

        # Get project
        project = get_object_or_404(Project, pk=project_id)
        tenant = getattr(request, 'tenant', None)

        # Verify tenant access
        if tenant and project.tenant and project.tenant != tenant:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate input
        serializer = ExecutionStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get next round number
        last_round = ExecutionRound.objects.filter(project=project).order_by('-round_number').first()
        next_round_number = (last_round.round_number + 1) if last_round else 1

        # Check if task sharding is enabled
        use_task_sharding = data.get('use_task_sharding', False)

        # Create execution round
        execution_round = ExecutionRound.objects.create(
            tenant=tenant,
            project=project,
            round_number=next_round_number,
            requirement_text=data['requirement'],
            options={
                'max_rounds': data['max_rounds'],
                'parallel': data['parallel'],
                'pr_mode': data['pr_mode'],
                'skip_validation': data['skip_validation'],
                'edit_mode': data['edit_mode'],
            },
            status='pending',
            use_task_sharding=use_task_sharding,
        )

        # Create progress tracker
        ExecutionProgress.objects.create(
            execution_round=execution_round,
            current_phase='queued',
            total_requirements=1,  # Will be updated during execution
        )

        # Auto-create team members if project doesn't have any
        self._ensure_team_members(project)

        # Try Celery first, fallback to thread execution
        task_id = None
        use_thread = False

        try:
            # Check if Redis/Celery is available with a short timeout
            from django.conf import settings
            import redis as redis_lib

            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
            r.ping()  # Test connection

            # Redis is available, use Celery
            if use_task_sharding:
                # Use task sharding for fine-grained execution
                from .tasks import start_sharded_execution
                task_id = start_sharded_execution(str(execution_round.id))
            else:
                # Use traditional monolithic execution
                from .tasks import execute_project_task
                task = execute_project_task.delay(
                    execution_round_id=str(execution_round.id),
                )
                task_id = task.id
                execution_round.celery_task_id = task_id
                execution_round.save(update_fields=['celery_task_id'])
        except Exception as e:
            # Celery/Redis not available, use thread-based execution
            import logging
            import threading
            logger = logging.getLogger(__name__)
            logger.warning(f'Celery not available ({e}), using thread execution')
            use_thread = True

            def run_in_thread():
                """Run execution task in a background thread."""
                try:
                    # Import runner directly to avoid Celery self parameter issue
                    from execution.runner import run_execution_for_api
                    from execution.models import ExecutionRound, ExecutionProgress

                    exec_round = ExecutionRound.objects.select_related(
                        'project', 'tenant'
                    ).get(id=execution_round.id)

                    exec_round.start()

                    try:
                        progress = exec_round.progress
                    except ExecutionProgress.DoesNotExist:
                        progress = ExecutionProgress.objects.create(
                            execution_round=exec_round
                        )

                    progress.update_phase('executing', '', 'Starting execution')

                    api_key = exec_round.tenant.api_key if exec_round.tenant else None
                    options = exec_round.options or {}

                    result = run_execution_for_api(
                        execution_round_id=str(exec_round.id),
                        project_id=str(exec_round.project.id),
                        requirement=exec_round.requirement_text,
                        api_key=api_key,
                        backend_url='http://localhost:8000',
                        max_rounds=options.get('max_rounds', 3),
                        use_parallel=options.get('parallel', True),
                        use_pr_mode=options.get('pr_mode', True),
                        skip_validation=options.get('skip_validation', False),
                        use_edit_mode=options.get('edit_mode', False),
                    )

                    exec_round.total_tokens = result.get('total_tokens', 0)
                    exec_round.total_cost_usd = result.get('total_cost', 0)
                    exec_round.total_llm_calls = result.get('total_llm_calls', 0)
                    exec_round.complete(summary=result.get('summary', ''))
                    progress.update_phase('completed', '', '')
                    progress.update_progress(100)
                    logger.info(f'Thread execution completed: {exec_round.id}')
                except Exception as ex:
                    import traceback
                    error_msg = f'{type(ex).__name__}: {str(ex)}'
                    logger.error(f'Thread execution failed: {error_msg}')
                    logger.error(traceback.format_exc())
                    try:
                        exec_round.fail(error_msg)
                    except Exception:
                        pass

            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()
            task_id = f'thread-{execution_round.id}'

        return Response(
            {
                'execution_round_id': str(execution_round.id),
                'task_id': task_id,
                'status': 'started',
                'round_number': next_round_number,
                'execution_mode': 'thread' if use_thread else 'celery',
            },
            status=status.HTTP_202_ACCEPTED
        )

    def _ensure_team_members(self, project):
        """Ensure project has team members.

        If the project has no team members, create them from available agents.
        This ensures the frontend WorkPreview page has data to display.
        """
        from api.models import Agent, TeamMember

        # Check if project already has team members
        if project.team_members.exists():
            return

        # Get all available agents
        agents = Agent.objects.all()[:6]  # Limit to 6 team members

        # Create team members for each agent
        for agent in agents:
            TeamMember.objects.create(
                project=project,
                agent=agent,
                role=agent.duty or agent.name,
                status='Await',
                time_spent='0mins',
                cost=0,
                progress=0,
                progress_total=100,
            )

        # Update project member count
        project.member_count = project.team_members.count()
        project.save(update_fields=['member_count'])


class ActiveExecutionsView(APIView):
    """Get currently running executions.

    GET /api/v1/execution/active/
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)

        qs = ExecutionRound.objects.filter(status__in=['pending', 'running'])
        if tenant:
            qs = qs.filter(tenant=tenant)

        # Optional project filter
        project_id = request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)

        serializer = ExecutionRoundListSerializer(qs, many=True)
        return Response(serializer.data)


class SuggestAgentsView(APIView):
    """Suggest agents for project requirements using LLM.

    POST /api/v1/projects/{id}/suggest-agents/
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def post(self, request, project_id):
        from api.models import Project
        from .serializers import (
            SuggestAgentsRequestSerializer,
            SuggestAgentsResponseSerializer,
        )
        from .suggest_agents import suggest_agents_for_requirements

        # Get project
        project = get_object_or_404(Project, pk=project_id)
        tenant = getattr(request, 'tenant', None)

        # Verify tenant access
        if tenant and project.tenant and project.tenant != tenant:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate input
        serializer = SuggestAgentsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        requirements = serializer.validated_data['requirements']

        # Call LLM to suggest agents
        try:
            result = suggest_agents_for_requirements(requirements)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except RuntimeError as e:
            return Response(
                {'error': f'LLM service error: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Serialize response
        response_serializer = SuggestAgentsResponseSerializer(data=result)
        if not response_serializer.is_valid():
            return Response(
                {'error': 'Invalid response from LLM', 'details': response_serializer.errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)


class GenerateAvatarsView(APIView):
    """Generate avatars for agents using Nano Banana 2 (Gemini).

    POST /api/v1/agents/generate-avatars/
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def post(self, request):
        from .serializers import (
            AvatarGenerationRequestSerializer,
            AvatarGenerationResponseSerializer,
        )
        from .image_generation import generate_avatars_batch

        # Validate input
        serializer = AvatarGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        agents = serializer.validated_data['agents']
        style = serializer.validated_data.get('style', 'professional')

        # Generate avatars
        try:
            results = generate_avatars_batch(agents, style=style)
        except Exception as e:
            return Response(
                {'error': f'Avatar generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Count successes and failures
        success_count = sum(1 for r in results if r.get('avatar_url'))
        error_count = len(results) - success_count

        response_data = {
            'results': results,
            'success_count': success_count,
            'error_count': error_count,
        }

        # Serialize response
        response_serializer = AvatarGenerationResponseSerializer(data=response_data)
        if not response_serializer.is_valid():
            return Response(
                {'error': 'Invalid response format', 'details': response_serializer.errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)


class RankAgentsView(APIView):
    """Rank agents for a role based on score.

    POST /api/v1/projects/{id}/rank-agents/
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def post(self, request, project_id):
        from api.models import Project, Agent
        from .serializers import (
            RankAgentsRequestSerializer,
            RankAgentsResponseSerializer,
        )
        from .suggest_agents import _compute_library_agent_score

        # Get project
        project = get_object_or_404(Project, pk=project_id)
        tenant = getattr(request, 'tenant', None)

        # Verify tenant access
        if tenant and project.tenant and project.tenant != tenant:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate input
        serializer = RankAgentsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = serializer.validated_data['role']
        skills = serializer.validated_data.get('skills', [])
        domains = serializer.validated_data.get('domains', [])
        metaso_spec = serializer.validated_data.get('metaso_spec')
        offset = serializer.validated_data.get('offset', 0)
        limit = serializer.validated_data.get('limit', 3)

        # Get all library agents and compute scores
        candidates = []
        agents = Agent.objects.all()

        for agent in agents:
            score = _compute_library_agent_score(agent, role, skills, domains)
            if score >= 0.10:  # min_fit_threshold
                candidates.append({
                    'agent_id': str(agent.id),
                    'is_metaso': False,
                    'name': agent.name,
                    'avatar': agent.avatar or '',
                    'duty': agent.duty or '',
                    'detail': agent.detail or '',
                    'cost_per_min': float(agent.cost_per_min),
                    'total_score': score,
                    's_base_score': 0.5,  # Default base score
                    'requirement_fit_score': score,
                })

        # Add Metaso agent if provided
        if metaso_spec:
            metaso_score = metaso_spec.get('estimated_score', 0.50)
            candidates.append({
                'agent_id': metaso_spec['agent_id'],
                'is_metaso': True,
                'name': metaso_spec['name'],
                'avatar': '',  # Metaso agents don't have avatars yet
                'duty': role,
                'detail': metaso_spec['description'],
                'cost_per_min': 0.0,  # TBD
                'total_score': metaso_score,
                's_base_score': 0.50,
                'requirement_fit_score': metaso_score,
            })

        # Sort by total_score descending
        candidates.sort(key=lambda x: x['total_score'], reverse=True)

        # Apply pagination
        total_count = len(candidates)
        paginated = candidates[offset:offset + limit]
        has_more = offset + limit < total_count

        # Check if remaining candidates are below threshold
        threshold_reached = False
        if has_more and offset + limit < total_count:
            next_candidate = candidates[offset + limit]
            if next_candidate['total_score'] < 0.10:
                threshold_reached = True

        response_data = {
            'candidates': paginated,
            'has_more': has_more,
            'threshold_reached': threshold_reached,
        }

        response_serializer = RankAgentsResponseSerializer(data=response_data)
        if not response_serializer.is_valid():
            return Response(
                {'error': 'Invalid response format', 'details': response_serializer.errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)


class CreateMetasoAgentView(APIView):
    """Create a real agent from Metaso agent specification.

    POST /api/v1/agents/create-metaso/
    """

    permission_classes = [IsAuthenticatedOrAPIKey]

    def post(self, request):
        from api.models import Agent, Project
        from api.serializers import AgentSerializer
        from .serializers import CreateMetasoAgentRequestSerializer

        # Validate input
        serializer = CreateMetasoAgentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        spec = serializer.validated_data['spec']
        project_id = serializer.validated_data['project_id']

        # Verify project exists
        project = get_object_or_404(Project, pk=project_id)
        tenant = getattr(request, 'tenant', None)

        # Verify tenant access
        if tenant and project.tenant and project.tenant != tenant:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Generate a unique agent_no
        import uuid
        agent_no = f"metaso_{uuid.uuid4().hex[:8]}"

        # Create the agent (Agent is a system-level resource, no tenant field)
        agent = Agent.objects.create(
            name=spec['name'],
            agent_no=agent_no,
            duty=spec.get('domains', [''])[0] if spec.get('domains') else '',
            detail=spec['description'],
            preview='',
            avatar='',
            cost_per_min=0.0,
        )

        # Return created agent
        agent_serializer = AgentSerializer(agent)
        return Response({
            'agent': agent_serializer.data,
        }, status=status.HTTP_201_CREATED)
