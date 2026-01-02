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
