# -*- coding: utf-8 -*-
"""Redis pub/sub utilities for real-time event streaming.

This module provides a unified interface for publishing and subscribing
to real-time events via Redis pub/sub.

Usage:
    # Publishing events
    from observability.pubsub import publish_event, publish_execution_progress

    publish_event(tenant_id, 'agent_start', {'agent': 'Builder', 'task': 'Create component'})
    publish_execution_progress(execution_round_id, 'running', progress=50)

    # Subscribing (in SSE view)
    from observability.pubsub import subscribe_events

    for event in subscribe_events(tenant_id):
        yield f"event: {event['type']}\\ndata: {json.dumps(event['data'])}\\n\\n"
"""
import json
import logging
from datetime import datetime
from typing import Any, Generator, Literal

from django.conf import settings

logger = logging.getLogger(__name__)


# Event types for execution progress
ExecutionEventType = Literal[
    'execution_started',
    'execution_progress',
    'execution_completed',
    'execution_failed',
    'execution_cancelled',
    'agent_started',
    'agent_completed',
    'agent_error',
    'task_started',
    'task_completed',
    'artifact_created',
    'log_message',
    'usage_recorded',
]


def _get_redis_client():
    """Get Redis client if available.

    Returns:
        redis.Redis | None: Redis client or None if unavailable.
    """
    redis_url = getattr(settings, 'REDIS_URL', None)
    if not redis_url:
        return None

    try:
        import redis
        return redis.from_url(redis_url)
    except ImportError:
        logger.warning("redis package not installed")
        return None
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        return None


def publish_event(
    tenant_id: str,
    event_type: str,
    data: dict[str, Any],
    project_id: str | None = None,
    execution_round_id: str | None = None,
) -> bool:
    """Publish an event to Redis pub/sub.

    Args:
        tenant_id: Tenant UUID string.
        event_type: Type of event (e.g., 'agent_start', 'usage_recorded').
        data: Event data payload.
        project_id: Optional project ID for filtering.
        execution_round_id: Optional execution round ID for filtering.

    Returns:
        bool: True if published successfully, False otherwise.
    """
    client = _get_redis_client()
    if not client:
        return False

    try:
        message = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat(),
        }
        if project_id:
            message['project_id'] = project_id
        if execution_round_id:
            message['execution_round_id'] = execution_round_id

        # Publish to tenant channel
        channel = f"sse:{tenant_id}"
        client.publish(channel, json.dumps(message))

        # Also publish to execution-specific channel if provided
        if execution_round_id:
            exec_channel = f"execution:{execution_round_id}"
            client.publish(exec_channel, json.dumps(message))

        return True

    except Exception as e:
        logger.warning(f"Failed to publish event: {e}")
        return False


def publish_execution_progress(
    execution_round_id: str,
    tenant_id: str,
    status: str,
    *,
    phase: str = '',
    current_agent: str = '',
    current_task: str = '',
    progress_percent: int = 0,
    completed_tasks: int = 0,
    total_tasks: int = 0,
    message: str = '',
    extra_data: dict[str, Any] | None = None,
) -> bool:
    """Publish execution progress update.

    This is a convenience function for publishing execution progress events.

    Args:
        execution_round_id: The execution round UUID.
        tenant_id: Tenant UUID string.
        status: Current status (pending, running, completed, failed, cancelled).
        phase: Current phase (e.g., 'planning', 'executing', 'validating').
        current_agent: Currently active agent name.
        current_task: Currently executing task description.
        progress_percent: Overall progress percentage (0-100).
        completed_tasks: Number of completed tasks.
        total_tasks: Total number of tasks.
        message: Human-readable status message.
        extra_data: Additional data to include.

    Returns:
        bool: True if published successfully.
    """
    data = {
        'execution_round_id': execution_round_id,
        'status': status,
        'phase': phase,
        'current_agent': current_agent,
        'current_task': current_task,
        'progress_percent': progress_percent,
        'completed_tasks': completed_tasks,
        'total_tasks': total_tasks,
        'message': message,
    }

    if extra_data:
        data.update(extra_data)

    return publish_event(
        tenant_id=tenant_id,
        event_type='execution_progress',
        data=data,
        execution_round_id=execution_round_id,
    )


def publish_agent_event(
    execution_round_id: str,
    tenant_id: str,
    event_type: Literal['agent_started', 'agent_completed', 'agent_error'],
    agent_name: str,
    *,
    task: str = '',
    output: str = '',
    error: str = '',
    duration_ms: float = 0,
    tokens_used: int = 0,
) -> bool:
    """Publish agent lifecycle event.

    Args:
        execution_round_id: The execution round UUID.
        tenant_id: Tenant UUID string.
        event_type: Type of agent event.
        agent_name: Name of the agent.
        task: Task being executed.
        output: Output from agent (for completed events).
        error: Error message (for error events).
        duration_ms: Execution duration in milliseconds.
        tokens_used: Tokens consumed during execution.

    Returns:
        bool: True if published successfully.
    """
    data = {
        'execution_round_id': execution_round_id,
        'agent_name': agent_name,
        'task': task,
    }

    if event_type == 'agent_completed':
        data['output'] = output[:500] if output else ''  # Truncate large outputs
        data['duration_ms'] = duration_ms
        data['tokens_used'] = tokens_used
    elif event_type == 'agent_error':
        data['error'] = error

    return publish_event(
        tenant_id=tenant_id,
        event_type=event_type,
        data=data,
        execution_round_id=execution_round_id,
    )


def publish_artifact_event(
    execution_round_id: str,
    tenant_id: str,
    artifact_type: str,
    file_path: str,
    file_name: str,
    *,
    language: str = '',
    size_bytes: int = 0,
    generated_by: str = '',
) -> bool:
    """Publish artifact creation event.

    Args:
        execution_round_id: The execution round UUID.
        tenant_id: Tenant UUID string.
        artifact_type: Type of artifact (code, config, document, etc.).
        file_path: Full path to the file.
        file_name: File name.
        language: Programming language (for code files).
        size_bytes: File size in bytes.
        generated_by: Agent that generated this artifact.

    Returns:
        bool: True if published successfully.
    """
    return publish_event(
        tenant_id=tenant_id,
        event_type='artifact_created',
        data={
            'execution_round_id': execution_round_id,
            'artifact_type': artifact_type,
            'file_path': file_path,
            'file_name': file_name,
            'language': language,
            'size_bytes': size_bytes,
            'generated_by': generated_by,
        },
        execution_round_id=execution_round_id,
    )


def subscribe_events(
    tenant_id: str,
    timeout: float = 0,
) -> Generator[dict[str, Any], None, None]:
    """Subscribe to events for a tenant.

    Args:
        tenant_id: Tenant UUID string.
        timeout: Timeout in seconds (0 = no timeout).

    Yields:
        dict: Event messages with 'type' and 'data' keys.
    """
    client = _get_redis_client()
    if not client:
        return

    try:
        pubsub = client.pubsub()
        pubsub.subscribe(f"sse:{tenant_id}")

        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    yield json.loads(message['data'])
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        logger.warning(f"Error in subscribe_events: {e}")


def subscribe_execution(
    execution_round_id: str,
    timeout: float = 0,
) -> Generator[dict[str, Any], None, None]:
    """Subscribe to events for a specific execution round.

    Args:
        execution_round_id: Execution round UUID string.
        timeout: Timeout in seconds (0 = no timeout).

    Yields:
        dict: Event messages with 'type' and 'data' keys.
    """
    client = _get_redis_client()
    if not client:
        return

    try:
        pubsub = client.pubsub()
        pubsub.subscribe(f"execution:{execution_round_id}")

        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    yield json.loads(message['data'])
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        logger.warning(f"Error in subscribe_execution: {e}")
