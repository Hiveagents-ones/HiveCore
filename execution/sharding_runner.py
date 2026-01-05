# -*- coding: utf-8 -*-
"""Task sharding runner - sync wrappers for async execution code.

This module provides synchronous wrapper functions that can be called from
Celery tasks to execute HiveCore components in isolated threads with their
own event loops.

Key functions:
- parse_requirements_sync: Parse requirements using LLM
- execute_single_requirement_sync: Execute a single requirement (Blueprint -> Code -> QA)
"""
import asyncio
import logging
import os
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Thread-local storage for event loops
_thread_local = threading.local()


def _get_event_loop():
    """Get or create an event loop for the current thread."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _run_async_in_thread(coro):
    """
    Run an async coroutine in a separate thread with its own event loop.

    This avoids the "cannot be called from a running event loop" issue
    that occurs when mixing asyncio with gevent or other async contexts.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        Exception: Any exception raised by the coroutine
    """
    result = None
    exception = None

    def run():
        nonlocal result, exception
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
        except Exception as e:
            exception = e
        finally:
            loop.close()

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()

    if exception:
        raise exception

    return result


def parse_requirements_sync(
    requirement_text: str,
    execution_round_id: str,
    auto_confirm: bool = True,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for requirement parsing.

    Calls LLM to parse requirements into structured spec.

    Args:
        requirement_text: Raw requirement text from user
        execution_round_id: For logging/tracking
        auto_confirm: Whether to auto-confirm prompts

    Returns:
        Parsed spec dict with structure:
        {
            "requirements": [
                {
                    "id": "REQ-001",
                    "content": "...",
                    "type": "backend",
                    "depends_on": [],
                    "acceptance": ["...", "..."]
                },
                ...
            ],
            "project_info": {...},
            "tech_stack": {...}
        }
    """
    logger.info(f"[parse_requirements_sync] Parsing requirements for {execution_round_id}")

    async def _parse():
        # Disable Django async safety for this context
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        try:
            # Import agentscope modules
            from agentscope.scripts._llm_utils import initialize_llm
            from agentscope.scripts._spec import collect_spec, enrich_acceptance_map

            # Initialize LLM
            llm, provider = initialize_llm('auto')
            logger.info(f"LLM initialized: {provider}")

            # Parse requirements
            spec = await collect_spec(llm, requirement_text, auto_confirm=auto_confirm)

            # Enrich with acceptance criteria
            await enrich_acceptance_map(llm, spec)

            return spec

        except ImportError as e:
            logger.warning(f"AgentScope not available: {e}, using mock")
            return _mock_parse_requirements(requirement_text)

    return _run_async_in_thread(_parse())


def execute_single_requirement_sync(
    execution_round,
    requirement_execution,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for single requirement execution.

    Executes the full flow: Blueprint -> Code Generation -> QA

    Args:
        execution_round: ExecutionRound model instance
        requirement_execution: RequirementExecution model instance

    Returns:
        Result dict with structure:
        {
            "blueprint": {...},
            "code_result": {...},
            "qa_result": {"passed": int, "total": int, "details": [...]},
            "validation_result": {...},
            "modified_files": [...],
            "tokens": int,
            "cost": float,
            "llm_calls": int
        }
    """
    req_id = requirement_execution.requirement_id
    logger.info(f"[execute_single_requirement_sync] Executing {req_id}")

    async def _execute():
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        try:
            from agentscope.scripts._llm_utils import initialize_llm
            from agentscope.scripts._runtime import build_runtime_harness
            from agentscope.scripts._execution import run_single_requirement

            # Initialize LLM
            llm, provider = initialize_llm('auto')

            # Setup workspace
            project_id = str(execution_round.project_id) if execution_round.project_id else 'default'
            workspace_base = Path(getattr(settings, 'EXECUTION_WORKSPACE_DIR', '/tmp/hivecore_workspaces'))
            workspace_dir = workspace_base / project_id
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # Get parsed spec from execution round
            spec = execution_round.parsed_spec or {}

            # Find this requirement in spec
            req_data = None
            for req in spec.get('requirements', []):
                if req.get('id') == req_id:
                    req_data = req
                    break

            if not req_data:
                # Use requirement_execution data
                req_data = {
                    'id': req_id,
                    'content': requirement_execution.requirement_content,
                    'type': requirement_execution.requirement_type,
                    'acceptance': [],
                }

            # Build minimal runtime for single requirement
            runtime = build_runtime_harness(
                spec,
                user_id=f"api-{str(execution_round.id)[:8]}",
                project_hint=project_id,
                llm=llm,
                workspace_dir=str(workspace_dir),
            )

            # Execute single requirement
            result = await run_single_requirement(
                runtime=runtime,
                requirement=req_data,
                llm=llm,
            )

            return result

        except ImportError as e:
            logger.warning(f"AgentScope not available: {e}, using mock")
            return _mock_execute_requirement(requirement_execution)

        except Exception as e:
            logger.exception(f"Requirement execution failed: {e}")
            raise

    return _run_async_in_thread(_execute())


# ============ Mock Functions for Testing ============


def _mock_parse_requirements(requirement_text: str) -> Dict[str, Any]:
    """Mock requirement parsing for testing without AgentScope."""
    import re

    # Simple parsing: split by newlines, create requirements
    lines = [l.strip() for l in requirement_text.split('\n') if l.strip()]
    requirements = []

    for i, line in enumerate(lines[:10]):  # Limit to 10 requirements
        req_id = f"REQ-{i + 1:03d}"
        # Try to detect type from keywords
        req_type = 'backend'
        if any(kw in line.lower() for kw in ['前端', 'frontend', 'ui', 'page', '页面']):
            req_type = 'frontend'
        elif any(kw in line.lower() for kw in ['api', 'backend', '后端', '接口']):
            req_type = 'backend'

        requirements.append({
            'id': req_id,
            'content': line,
            'type': req_type,
            'depends_on': [],
            'acceptance': [
                f"Code compiles without errors",
                f"Functionality works as described",
            ],
        })

    return {
        'requirements': requirements,
        'project_info': {
            'name': 'Mock Project',
            'description': requirement_text[:100],
        },
        'tech_stack': {
            'backend': 'Python/Django',
            'frontend': 'React/TypeScript',
        }
    }


def _mock_execute_requirement(requirement_execution) -> Dict[str, Any]:
    """Mock requirement execution for testing without AgentScope."""
    import random
    import time

    # Simulate some work
    time.sleep(random.uniform(1, 3))

    # Random pass/fail for testing
    passed = random.random() > 0.2  # 80% pass rate
    pass_count = 2 if passed else random.randint(0, 1)

    return {
        'blueprint': {
            'design': f"Mock blueprint for {requirement_execution.requirement_id}",
            'files_to_create': ['mock_file.py'],
        },
        'code_result': {
            'files_created': ['mock_file.py'],
            'success': True,
        },
        'qa_result': {
            'passed': pass_count,
            'total': 2,
            'details': [
                {'criterion': 'Compiles', 'passed': True},
                {'criterion': 'Functionality', 'passed': passed},
            ],
        },
        'validation_result': {
            'valid': True,
        },
        'modified_files': ['mock_file.py'],
        'tokens': random.randint(1000, 5000),
        'cost': random.uniform(0.01, 0.1),
        'llm_calls': random.randint(3, 10),
    }
