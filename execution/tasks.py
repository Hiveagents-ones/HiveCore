# -*- coding: utf-8 -*-
"""Celery tasks for project execution."""
import logging
import traceback
from celery import shared_task

from backend.celery import app

logger = logging.getLogger(__name__)


def _publish_progress(execution_round, phase: str, message: str, progress_percent: int = 0):
    """Helper to publish progress events via Redis.

    Args:
        execution_round: ExecutionRound instance
        phase: Current execution phase
        message: Progress message
        progress_percent: Progress percentage (0-100)
    """
    from observability.pubsub import publish_execution_progress

    tenant_id = str(execution_round.tenant.id) if execution_round.tenant else ''
    if not tenant_id:
        return

    publish_execution_progress(
        execution_round_id=str(execution_round.id),
        tenant_id=tenant_id,
        status=execution_round.status,
        phase=phase,
        progress_percent=progress_percent,
        message=message,
    )


def _publish_status_change(execution_round, status: str, message: str = '', extra_data: dict = None):
    """Helper to publish status change events via Redis.

    Args:
        execution_round: ExecutionRound instance
        status: New status
        message: Status message
        extra_data: Additional data to include
    """
    from observability.pubsub import publish_event

    tenant_id = str(execution_round.tenant.id) if execution_round.tenant else ''
    if not tenant_id:
        return

    event_type = f"execution_{status}"
    data = {
        'execution_round_id': str(execution_round.id),
        'project_id': execution_round.project_id,
        'status': status,
        'message': message,
        'round_number': execution_round.round_number,
    }

    if extra_data:
        data.update(extra_data)

    publish_event(
        tenant_id=tenant_id,
        event_type=event_type,
        data=data,
        project_id=str(execution_round.project_id) if execution_round.project_id else None,
        execution_round_id=str(execution_round.id),
    )


@shared_task(bind=True, max_retries=0, time_limit=3600, soft_time_limit=3500)
def execute_project_task(self, execution_round_id: str):
    """Execute a project in the background.

    This task:
    1. Loads the ExecutionRound from database
    2. Initializes WebhookExporter for progress reporting
    3. Calls run_cli_for_api() to execute the project
    4. Updates execution status on completion/failure
    5. Publishes real-time progress events via Redis SSE

    Args:
        execution_round_id: UUID of the ExecutionRound to execute
    """
    from django.conf import settings
    from execution.models import ExecutionRound, ExecutionProgress

    logger.info(f"Starting execution for round {execution_round_id}")

    # Load execution round
    try:
        execution_round = ExecutionRound.objects.select_related(
            'project', 'tenant'
        ).get(id=execution_round_id)
    except ExecutionRound.DoesNotExist:
        logger.error(f"ExecutionRound {execution_round_id} not found")
        return {'error': 'ExecutionRound not found'}

    # Mark as running
    execution_round.start()

    # Publish started event
    _publish_status_change(execution_round, 'started', 'Execution started')

    # Update progress
    try:
        progress = execution_round.progress
    except ExecutionProgress.DoesNotExist:
        progress = ExecutionProgress.objects.create(execution_round=execution_round)

    progress.update_phase('initializing', '', 'Setting up execution environment')
    _publish_progress(execution_round, 'initializing', 'Setting up execution environment', 5)

    try:
        # Get tenant API key for webhook
        api_key = execution_round.tenant.api_key if execution_round.tenant else None
        backend_url = getattr(settings, 'INTERNAL_API_URL', 'http://localhost:8000')

        # Get execution options
        options = execution_round.options or {}

        # Update progress: starting execution
        progress.update_phase('executing', '', 'Starting project execution')
        _publish_progress(execution_round, 'executing', 'Starting project execution', 10)

        # Import and run the API execution function
        from execution.runner import run_execution_for_api

        result = run_execution_for_api(
            execution_round_id=str(execution_round.id),
            project_id=str(execution_round.project.id),
            requirement=execution_round.requirement_text,
            tenant_id=str(execution_round.tenant_id) if execution_round.tenant_id else None,
            api_key=api_key,
            backend_url=backend_url,
            max_rounds=options.get('max_rounds', 3),
            use_parallel=options.get('parallel', True),
            use_pr_mode=options.get('pr_mode', True),
            skip_validation=options.get('skip_validation', False),
            use_edit_mode=options.get('edit_mode', False),
        )

        # Update execution round with results
        execution_round.total_tokens = result.get('total_tokens', 0)
        execution_round.total_cost_usd = result.get('total_cost', 0)
        execution_round.total_llm_calls = result.get('total_llm_calls', 0)
        execution_round.complete(summary=result.get('summary', ''))

        # Update progress to completed
        progress.update_phase('completed', '', '')
        progress.update_progress(100)

        # Publish completed event
        _publish_status_change(
            execution_round,
            'completed',
            'Execution completed successfully',
            extra_data={
                'summary': result.get('summary', ''),
                'total_tokens': result.get('total_tokens', 0),
                'total_cost_usd': result.get('total_cost', 0),
            }
        )

        logger.info(f"Execution completed for round {execution_round_id}")
        return {
            'status': 'completed',
            'execution_round_id': execution_round_id,
            'summary': result.get('summary', ''),
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Execution failed for round {execution_round_id}: {error_msg}")

        execution_round.fail(error_msg)
        progress.update_phase('failed', '', str(e))

        # Publish failed event
        _publish_status_change(
            execution_round,
            'failed',
            f'Execution failed: {str(e)}',
            extra_data={'error': str(e)}
        )

        return {
            'status': 'failed',
            'execution_round_id': execution_round_id,
            'error': str(e),
        }


@shared_task
def cleanup_old_executions(days: int = 30):
    """Clean up old execution data.

    Args:
        days: Number of days to keep execution data
    """
    from django.utils import timezone
    from datetime import timedelta
    from execution.models import ExecutionRound, ExecutionLog, ExecutionArtifact

    cutoff = timezone.now() - timedelta(days=days)

    # Delete old logs (keep artifacts longer)
    old_logs = ExecutionLog.objects.filter(timestamp__lt=cutoff)
    log_count = old_logs.count()
    old_logs.delete()

    logger.info(f"Cleaned up {log_count} old execution logs")
    return {'deleted_logs': log_count}


@shared_task
def migrate_artifacts_to_s3(batch_size: int = 100):
    """Migrate large artifacts from database to S3.

    Scans for artifacts with content in database that exceed
    the S3 threshold and migrates them to S3.

    Args:
        batch_size: Maximum number of artifacts to migrate per run
    """
    from execution.models import ExecutionArtifact
    from execution.storage import migrate_artifact_to_s3, S3_THRESHOLD_BYTES

    # Find artifacts that should be in S3 but aren't
    large_artifacts = ExecutionArtifact.objects.filter(
        s3_key='',  # Not in S3
        size_bytes__gt=S3_THRESHOLD_BYTES,  # Large enough for S3
    ).exclude(
        content=''  # Has content in DB
    )[:batch_size]

    migrated = 0
    failed = 0

    for artifact in large_artifacts:
        try:
            if migrate_artifact_to_s3(artifact):
                migrated += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to migrate artifact {artifact.id}: {e}")
            failed += 1

    logger.info(f"S3 migration: {migrated} migrated, {failed} failed")
    return {'migrated': migrated, 'failed': failed}


@shared_task
def cleanup_orphan_s3_artifacts(dry_run: bool = True):
    """Clean up S3 artifacts that no longer have database records.

    Args:
        dry_run: If True, only report what would be deleted
    """
    from django.conf import settings
    from execution.models import ExecutionArtifact
    from execution.storage import _get_s3_client, _get_bucket_name, _is_s3_enabled

    if not _is_s3_enabled():
        return {'status': 'skipped', 'reason': 'S3 not enabled'}

    try:
        client = _get_s3_client()
        bucket = _get_bucket_name()

        # List all artifact S3 keys in database
        db_keys = set(
            ExecutionArtifact.objects.exclude(s3_key='').values_list('s3_key', flat=True)
        )

        # List all S3 objects under artifacts/ prefix
        s3_keys = set()
        paginator = client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix='artifacts/'):
            for obj in page.get('Contents', []):
                s3_keys.add(obj['Key'])

        # Find orphans (in S3 but not in DB)
        orphans = s3_keys - db_keys

        if dry_run:
            logger.info(f"Dry run: Found {len(orphans)} orphan S3 objects")
            return {
                'status': 'dry_run',
                'orphan_count': len(orphans),
                'orphan_keys': list(orphans)[:100],  # Limit to first 100
            }

        # Delete orphans
        deleted = 0
        for key in orphans:
            try:
                client.delete_object(Bucket=bucket, Key=key)
                deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete orphan {key}: {e}")

        logger.info(f"Cleaned up {deleted} orphan S3 objects")
        return {'status': 'completed', 'deleted': deleted}

    except Exception as e:
        logger.error(f"Failed to cleanup orphan S3 artifacts: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def sync_artifact_from_workspace(
    execution_round_id: str,
    file_path: str,
    content: str,
    artifact_type: str = 'code',
    language: str = '',
    agent_id: int | None = None,
):
    """Sync a single artifact from execution workspace to storage.

    Called by the execution runner to save generated artifacts.

    Args:
        execution_round_id: UUID of the execution round
        file_path: Relative file path
        content: File content
        artifact_type: Type of artifact (code, config, document, etc.)
        language: Programming language if code
        agent_id: ID of agent that generated this artifact
    """
    import os
    from execution.models import ExecutionRound, ExecutionArtifact
    from execution.storage import store_artifact_content

    try:
        execution_round = ExecutionRound.objects.get(id=execution_round_id)
    except ExecutionRound.DoesNotExist:
        logger.error(f"ExecutionRound {execution_round_id} not found")
        return {'error': 'ExecutionRound not found'}

    # Determine content type
    ext = os.path.splitext(file_path)[1].lower()
    content_type_map = {
        '.py': 'text/x-python',
        '.js': 'text/javascript',
        '.ts': 'text/typescript',
        '.tsx': 'text/typescript-jsx',
        '.jsx': 'text/javascript-jsx',
        '.json': 'application/json',
        '.yaml': 'text/yaml',
        '.yml': 'text/yaml',
        '.md': 'text/markdown',
        '.html': 'text/html',
        '.css': 'text/css',
        '.sql': 'text/x-sql',
    }
    content_type = content_type_map.get(ext, 'text/plain')

    # Store content with automatic S3/DB decision
    content_for_db, content_hash, size_bytes, s3_key = store_artifact_content(
        execution_round_id=execution_round_id,
        file_path=file_path,
        content=content,
        content_type=content_type,
    )

    # Create or update artifact record
    artifact, created = ExecutionArtifact.objects.update_or_create(
        execution_round=execution_round,
        file_path=file_path,
        defaults={
            'tenant': execution_round.tenant,
            'artifact_type': artifact_type,
            'file_name': os.path.basename(file_path),
            'language': language,
            'content': content_for_db,
            'content_hash': content_hash,
            'size_bytes': size_bytes,
            's3_key': s3_key,
            'generated_by_agent_id': agent_id,
        }
    )

    logger.info(
        f"Artifact {'created' if created else 'updated'}: {file_path} "
        f"({size_bytes} bytes, storage: {'S3' if s3_key else 'DB'})"
    )

    return {
        'artifact_id': str(artifact.id),
        'file_path': file_path,
        'size_bytes': size_bytes,
        'storage': 's3' if s3_key else 'database',
    }


# ============ Task Sharding Tasks ============
# These tasks implement fine-grained execution with per-requirement isolation
# Enable with: ExecutionRound.use_task_sharding = True


@shared_task(bind=True, max_retries=0, time_limit=180, soft_time_limit=160)
def plan_execution_task(self, execution_round_id: str):
    """
    Phase 1: Parse requirements and create execution plan.

    Responsibilities:
    1. Load ExecutionRound
    2. Call LLM to parse requirements (collect_spec)
    3. Generate acceptance criteria (enrich_acceptance_map)
    4. Analyze dependencies, create RequirementExecution records
    5. Schedule first inner round (schedule_round_task)

    Duration: 10-60 seconds

    Args:
        execution_round_id: ExecutionRound UUID string
    """
    from execution.models import ExecutionRound, RequirementExecution
    from execution.sharding_runner import parse_requirements_sync

    logger.info(f"[Plan] Starting execution planning: {execution_round_id}")

    # 1. Load ExecutionRound
    try:
        execution_round = ExecutionRound.objects.select_related(
            'project', 'tenant'
        ).get(id=execution_round_id)
    except ExecutionRound.DoesNotExist:
        logger.error(f"ExecutionRound {execution_round_id} not found")
        return {'error': 'ExecutionRound not found', 'status': 'failed'}

    # Mark as running
    execution_round.start()
    _publish_progress(execution_round, 'planning', 'Parsing requirements', 5)

    try:
        # 2. Parse requirements (calls LLM)
        spec = parse_requirements_sync(
            requirement_text=execution_round.requirement_text,
            execution_round_id=execution_round_id,
        )

        if not spec or 'requirements' not in spec:
            raise ValueError("Failed to parse requirements: empty spec")

        # 3. Save parsed spec
        execution_round.parsed_spec = spec
        execution_round.total_requirements = len(spec.get('requirements', []))
        execution_round.total_inner_rounds = 1  # Will increment as needed
        execution_round.save(update_fields=[
            'parsed_spec', 'total_requirements', 'total_inner_rounds', 'updated_at'
        ])

        _publish_progress(execution_round, 'planning', 'Creating execution plan', 8)

        # 4. Extract dependencies and create RequirementExecution records
        requirements = spec.get('requirements', [])
        dependencies = _extract_dependencies_from_spec(requirements)

        for req in requirements:
            req_id = req.get('id') or f"REQ-{requirements.index(req) + 1:03d}"
            RequirementExecution.objects.create(
                execution_round=execution_round,
                tenant=execution_round.tenant,
                requirement_id=req_id,
                requirement_content=req.get('content', ''),
                requirement_type=req.get('type', ''),
                inner_round_number=1,
                depends_on=dependencies.get(req_id, []),
                acceptance_criteria_total=len(req.get('acceptance', [])),
            )

        _publish_progress(execution_round, 'planning', 'Scheduling tasks', 10)

        # 5. Schedule first inner round
        schedule_round_task.delay(execution_round_id, inner_round_number=1)

        logger.info(f"[Plan] Planning complete: {len(requirements)} requirements")

        return {
            'status': 'planned',
            'execution_round_id': execution_round_id,
            'total_requirements': len(requirements),
        }

    except Exception as e:
        logger.exception(f"[Plan] Planning failed: {e}")
        execution_round.fail(str(e))
        _publish_status_change(execution_round, 'failed', f'Planning failed: {str(e)}')
        return {'error': str(e), 'status': 'failed'}


@shared_task(bind=True, max_retries=0, time_limit=30)
def schedule_round_task(self, execution_round_id: str, inner_round_number: int):
    """
    Phase 2: Schedule one inner round of execution.

    Responsibilities:
    1. Get pending requirements for this round
    2. Topologically sort by dependencies
    3. Create Celery workflow (group + chain)
    4. Dispatch execute_requirement_task for each requirement

    Duration: < 1 second

    Args:
        execution_round_id: ExecutionRound UUID string
        inner_round_number: Which inner round to schedule (1, 2, 3, ...)
    """
    from execution.models import ExecutionRound, RequirementExecution
    from execution.orchestration import topological_sort_requirements, create_round_workflow

    logger.info(f"[Schedule] Scheduling inner round {inner_round_number}: {execution_round_id}")

    execution_round = ExecutionRound.objects.get(id=execution_round_id)

    # Update current inner round
    execution_round.current_inner_round = inner_round_number
    execution_round.save(update_fields=['current_inner_round', 'updated_at'])

    # Get pending requirements for this round
    pending_reqs = RequirementExecution.objects.filter(
        execution_round=execution_round,
        inner_round_number=inner_round_number,
        status='pending',
    )

    if not pending_reqs.exists():
        logger.info(f"[Schedule] No pending requirements for round {inner_round_number}")
        # No pending requirements, skip to aggregate
        aggregate_round_task.delay(execution_round_id, inner_round_number)
        return {'status': 'skipped', 'reason': 'no pending requirements'}

    # Build dependency map
    requirements = []
    dependencies = {}
    req_id_to_exec_id = {}

    for req in pending_reqs:
        requirements.append({'id': req.requirement_id})
        req_id_to_exec_id[req.requirement_id] = str(req.id)
        if req.depends_on:
            dependencies[req.requirement_id] = req.depends_on

    # Topological sort
    batches = topological_sort_requirements(requirements, dependencies)
    logger.info(f"[Schedule] Sorted into {len(batches)} batches: {batches}")

    # Update status to scheduled
    pending_reqs.update(status='scheduled')

    # Create and dispatch workflow
    workflow = create_round_workflow(
        execution_round_id=execution_round_id,
        req_id_to_exec_id=req_id_to_exec_id,
        batches=batches,
        inner_round_number=inner_round_number,
    )

    # Dispatch workflow
    workflow.delay()

    # Publish progress
    progress_pct = 15 + inner_round_number * 20
    _publish_progress(
        execution_round,
        'executing',
        f'Round {inner_round_number}: {len(requirements)} requirements in {len(batches)} batches',
        min(progress_pct, 85),
    )

    return {
        'status': 'scheduled',
        'inner_round_number': inner_round_number,
        'requirement_count': len(requirements),
        'batch_count': len(batches),
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=10,
             time_limit=600, soft_time_limit=550)
def execute_requirement_task(self, requirement_execution_id: str):
    """
    Phase 3: Execute a single requirement.

    Responsibilities:
    1. Blueprint design
    2. Code generation (stepwise_generate_files)
    3. QA acceptance
    4. Code validation (optional)
    5. Update RequirementExecution status

    Duration: 1-5 minutes

    Args:
        requirement_execution_id: RequirementExecution UUID string
    """
    from execution.models import RequirementExecution
    from execution.sharding_runner import execute_single_requirement_sync

    logger.info(f"[Execute] Executing requirement: {requirement_execution_id}")

    # Load RequirementExecution
    try:
        req_exec = RequirementExecution.objects.select_related(
            'execution_round', 'execution_round__project', 'execution_round__tenant'
        ).get(id=requirement_execution_id)
    except RequirementExecution.DoesNotExist:
        logger.error(f"RequirementExecution {requirement_execution_id} not found")
        return {'error': 'RequirementExecution not found', 'status': 'failed'}

    # Update celery task id and start
    req_exec.celery_task_id = self.request.id or ''
    req_exec.start()

    execution_round = req_exec.execution_round

    try:
        # Execute requirement (Blueprint -> Code -> QA)
        result = execute_single_requirement_sync(
            execution_round=execution_round,
            requirement_execution=req_exec,
        )

        # Update results
        req_exec.blueprint = result.get('blueprint')
        req_exec.code_result = result.get('code_result')
        req_exec.qa_result = result.get('qa_result')
        req_exec.validation_result = result.get('validation_result')
        req_exec.modified_files = result.get('modified_files', [])
        req_exec.tokens_used = result.get('tokens', 0)
        req_exec.cost_usd = result.get('cost', 0)
        req_exec.llm_calls = result.get('llm_calls', 0)

        # Calculate pass rate
        qa = result.get('qa_result', {})
        passed_count = qa.get('passed', 0)
        total_count = qa.get('total', 0) or req_exec.acceptance_criteria_total or 1
        pass_rate = passed_count / total_count if total_count > 0 else 0.0

        req_exec.acceptance_criteria_passed = passed_count
        req_exec.pass_rate = pass_rate
        req_exec.complete(
            passed=(pass_rate >= 0.9),  # 90% threshold
            pass_rate=pass_rate,
        )

        logger.info(
            f"[Execute] Requirement {req_exec.requirement_id} completed: "
            f"pass_rate={pass_rate:.1%}, passed={req_exec.is_passed}"
        )

        return {
            'requirement_id': req_exec.requirement_id,
            'requirement_execution_id': requirement_execution_id,
            'status': 'completed',
            'passed': req_exec.is_passed,
            'pass_rate': pass_rate,
        }

    except Exception as e:
        logger.exception(f"[Execute] Requirement {req_exec.requirement_id} failed: {e}")
        req_exec.fail(str(e), traceback.format_exc())

        # Retry for retryable errors
        if self.request.retries < self.max_retries:
            logger.info(f"[Execute] Retrying requirement {req_exec.requirement_id}")
            raise self.retry(exc=e)

        return {
            'requirement_id': req_exec.requirement_id,
            'requirement_execution_id': requirement_execution_id,
            'status': 'failed',
            'error': str(e),
        }


@shared_task(bind=True, max_retries=0, time_limit=60)
def aggregate_round_task(self, execution_round_id: str, inner_round_number: int):
    """
    Phase 4: Aggregate round results and decide next step.

    Responsibilities:
    1. Count passed/failed requirements
    2. Run regression check (optional)
    3. Decide next action:
       - All passed -> complete_execution_task
       - Some failed + not max rounds -> schedule_round_task (next round)
       - Max rounds reached -> complete_execution_task (partial failure)

    Duration: 1-5 seconds

    Args:
        execution_round_id: ExecutionRound UUID string
        inner_round_number: Which inner round just completed
    """
    from execution.models import ExecutionRound, RequirementExecution

    logger.info(f"[Aggregate] Aggregating inner round {inner_round_number}: {execution_round_id}")

    execution_round = ExecutionRound.objects.get(id=execution_round_id)
    options = execution_round.options or {}
    max_rounds = options.get('max_rounds', 3)

    # Count results for this round
    round_reqs = RequirementExecution.objects.filter(
        execution_round=execution_round,
        inner_round_number=inner_round_number,
    )

    total = round_reqs.count()
    passed_count = round_reqs.filter(is_passed=True).count()
    failed_qa_count = round_reqs.filter(status='completed', is_passed=False).count()
    error_count = round_reqs.filter(status='failed').count()

    logger.info(
        f"[Aggregate] Round {inner_round_number} results: "
        f"total={total}, passed={passed_count}, failed_qa={failed_qa_count}, errors={error_count}"
    )

    # Publish progress
    progress_pct = min(90, 25 + inner_round_number * 25)
    _publish_progress(
        execution_round,
        'aggregating',
        f'Round {inner_round_number}: {passed_count}/{total} passed',
        progress_pct,
    )

    # Update round stats
    execution_round.passed_requirements = RequirementExecution.objects.filter(
        execution_round=execution_round,
        is_passed=True,
    ).values('requirement_id').distinct().count()

    execution_round.save(update_fields=['passed_requirements', 'updated_at'])

    # Decide next action
    if passed_count == total:
        # All passed, complete execution
        logger.info(f"[Aggregate] All requirements passed, completing execution")
        complete_execution_task.delay(execution_round_id)

    elif inner_round_number < max_rounds and (failed_qa_count > 0 or error_count > 0):
        # Some failed, schedule next round for retry
        next_round = inner_round_number + 1
        logger.info(f"[Aggregate] {failed_qa_count + error_count} failures, scheduling round {next_round}")

        # Create next round records for failed requirements
        failed_reqs = round_reqs.filter(is_passed=False) | round_reqs.filter(status='failed')

        for req in failed_reqs:
            RequirementExecution.objects.create(
                execution_round=execution_round,
                tenant=execution_round.tenant,
                requirement_id=req.requirement_id,
                requirement_content=req.requirement_content,
                requirement_type=req.requirement_type,
                inner_round_number=next_round,
                attempt_number=req.attempt_number + 1,
                depends_on=req.depends_on,
                acceptance_criteria_total=req.acceptance_criteria_total,
            )

        execution_round.total_inner_rounds = next_round
        execution_round.save(update_fields=['total_inner_rounds', 'updated_at'])

        # Schedule next round
        schedule_round_task.delay(execution_round_id, next_round)

    else:
        # Max rounds reached or other terminal condition
        logger.info(f"[Aggregate] Max rounds reached or terminal, completing execution")
        complete_execution_task.delay(execution_round_id)

    return {
        'status': 'aggregated',
        'inner_round_number': inner_round_number,
        'total': total,
        'passed': passed_count,
        'failed': failed_qa_count + error_count,
    }


@shared_task(bind=True, max_retries=0, time_limit=60)
def complete_execution_task(self, execution_round_id: str):
    """
    Phase 5: Complete execution and generate report.

    Responsibilities:
    1. Aggregate final statistics
    2. Generate execution report
    3. Clean up temporary resources
    4. Update ExecutionRound status
    5. Publish SSE completion event

    Duration: < 5 seconds

    Args:
        execution_round_id: ExecutionRound UUID string
    """
    from django.db.models import Sum, Max
    from execution.models import ExecutionRound, RequirementExecution

    logger.info(f"[Complete] Completing execution: {execution_round_id}")

    execution_round = ExecutionRound.objects.get(id=execution_round_id)

    # Get all requirement executions
    all_reqs = RequirementExecution.objects.filter(execution_round=execution_round)

    # Get final status for each requirement (latest round)
    requirement_ids = all_reqs.values_list('requirement_id', flat=True).distinct()

    passed = 0
    failed = 0

    for req_id in requirement_ids:
        # Get the latest attempt for this requirement
        final_req = all_reqs.filter(
            requirement_id=req_id
        ).order_by('-inner_round_number', '-attempt_number').first()

        if final_req and final_req.is_passed:
            passed += 1
        else:
            failed += 1

    # Update statistics
    execution_round.passed_requirements = passed
    execution_round.failed_requirements = failed

    # Aggregate token/cost
    totals = all_reqs.aggregate(
        total_tokens=Sum('tokens_used'),
        total_cost=Sum('cost_usd'),
        total_calls=Sum('llm_calls'),
    )

    execution_round.total_tokens = totals.get('total_tokens') or 0
    execution_round.total_cost_usd = totals.get('total_cost') or 0
    execution_round.total_llm_calls = totals.get('total_calls') or 0

    # Generate summary
    total = passed + failed
    summary = f"Completed: {passed}/{total} requirements passed"
    if failed > 0:
        summary += f" ({failed} failed)"

    # Complete execution round
    execution_round.complete(summary=summary)

    # Publish completion events
    _publish_progress(execution_round, 'completed', summary, 100)
    _publish_status_change(
        execution_round,
        'completed',
        summary,
        extra_data={
            'passed_requirements': passed,
            'failed_requirements': failed,
            'total_tokens': execution_round.total_tokens,
            'total_cost_usd': float(execution_round.total_cost_usd or 0),
        }
    )

    logger.info(f"[Complete] Execution completed: {summary}")

    return {
        'status': 'completed',
        'execution_round_id': execution_round_id,
        'passed': passed,
        'failed': failed,
        'total_tokens': execution_round.total_tokens,
        'summary': summary,
    }


# ============ Helper Functions ============


def _extract_dependencies_from_spec(requirements: list) -> dict:
    """
    Extract dependency map from parsed requirements.

    Args:
        requirements: List of requirement dicts from spec

    Returns:
        Dict mapping requirement_id to list of dependency requirement_ids
    """
    dependencies = {}

    for req in requirements:
        req_id = req.get('id')
        if not req_id:
            continue

        deps = req.get('depends_on', []) or req.get('dependencies', []) or []
        if deps:
            dependencies[req_id] = deps

    return dependencies


def start_sharded_execution(execution_round_id: str) -> str:
    """
    Entry point for task-sharded execution.

    Call this instead of execute_project_task when
    ExecutionRound.use_task_sharding is True.

    Args:
        execution_round_id: ExecutionRound UUID string

    Returns:
        Celery task ID of the plan_execution_task
    """
    from execution.models import ExecutionRound

    execution_round = ExecutionRound.objects.get(id=execution_round_id)

    if not execution_round.use_task_sharding:
        logger.warning(
            f"start_sharded_execution called but use_task_sharding=False, "
            f"falling back to execute_project_task"
        )
        result = execute_project_task.delay(execution_round_id)
        return result.id

    logger.info(f"Starting sharded execution for {execution_round_id}")

    # Update celery task id
    result = plan_execution_task.delay(execution_round_id)
    execution_round.celery_task_id = result.id
    execution_round.save(update_fields=['celery_task_id', 'updated_at'])

    return result.id
