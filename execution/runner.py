# -*- coding: utf-8 -*-
"""Execution runner - bridges Django backend with AgentScope.

This module provides the run_execution_for_api() function that can be called
from Celery tasks to execute HiveCore projects.
"""
import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def run_execution_for_api(
    execution_round_id: str,
    project_id: str,
    requirement: str,
    api_key: str | None = None,
    backend_url: str = 'http://localhost:8000',
    max_rounds: int = 3,
    use_parallel: bool = True,
    use_pr_mode: bool = True,
    skip_validation: bool = False,
    use_edit_mode: bool = False,
) -> dict[str, Any]:
    """Run HiveCore execution for API.

    This is the main entry point for executing projects from the backend.
    It sets up the environment and calls the async execution function.

    Args:
        execution_round_id: UUID of the ExecutionRound for progress tracking
        project_id: UUID of the Project being executed
        requirement: The requirement text to execute
        api_key: Tenant API key for webhook authentication
        backend_url: Backend URL for webhook callbacks
        max_rounds: Maximum execution rounds
        use_parallel: Whether to use parallel execution
        use_pr_mode: Whether to use PR mode (delivery/ + working/ isolation)
        skip_validation: Whether to skip code validation
        use_edit_mode: Whether to use edit mode

    Returns:
        dict: Execution result with keys:
            - status: 'completed' or 'failed'
            - summary: Execution summary text
            - total_tokens: Total tokens consumed
            - total_cost: Total cost in USD
            - total_llm_calls: Total LLM API calls
            - deliverables: Dict of requirement_id -> file_path
            - rounds: List of round results
    """
    return asyncio.run(_run_execution_async(
        execution_round_id=execution_round_id,
        project_id=project_id,
        requirement=requirement,
        api_key=api_key,
        backend_url=backend_url,
        max_rounds=max_rounds,
        use_parallel=use_parallel,
        use_pr_mode=use_pr_mode,
        skip_validation=skip_validation,
        use_edit_mode=use_edit_mode,
    ))


async def _run_execution_async(
    execution_round_id: str,
    project_id: str,
    requirement: str,
    api_key: str | None = None,
    backend_url: str = 'http://localhost:8000',
    max_rounds: int = 3,
    use_parallel: bool = True,
    use_pr_mode: bool = True,
    skip_validation: bool = False,
    use_edit_mode: bool = False,
) -> dict[str, Any]:
    """Async implementation of execution.

    This function:
    1. Sets up WebhookExporter for progress reporting
    2. Initializes the execution environment
    3. Runs the HiveCore execution flow
    4. Returns structured results
    """
    from django.conf import settings

    # Update progress helper
    def update_progress(phase: str, agent: str = '', task: str = '', percent: int = 0):
        """Update execution progress in database."""
        try:
            from execution.models import ExecutionProgress
            progress = ExecutionProgress.objects.get(execution_round_id=execution_round_id)
            progress.update_phase(phase, agent, task)
            if percent > 0:
                progress.update_progress(percent)
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")

    # Check if agentscope is available
    try:
        from agentscope.observability import ObservabilityHub, WebhookExporter
        agentscope_available = True
    except ImportError:
        agentscope_available = False
        logger.warning("AgentScope not available, running in mock mode")

    update_progress('initializing', '', 'Checking environment')

    if not agentscope_available:
        # Mock execution for testing without agentscope
        return await _mock_execution(
            execution_round_id=execution_round_id,
            project_id=project_id,
            requirement=requirement,
            update_progress=update_progress,
        )

    # Set up workspace directory (isolated per project)
    workspace_base = Path(getattr(settings, 'EXECUTION_WORKSPACE_DIR', '/tmp/hivecore_workspaces'))
    workspace_dir = workspace_base / project_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Configure WebhookExporter
    hub = ObservabilityHub()
    if api_key and backend_url:
        exporter = WebhookExporter(
            api_url=f"{backend_url}/api/v1/observability",
            api_key=api_key,
            extra_headers={
                'X-Execution-Round': execution_round_id,
                'X-Project-Id': project_id,
            },
        )
        hub.set_webhook(exporter)
        logger.info(f"WebhookExporter configured for {backend_url}")

    update_progress('collecting_spec', '', 'Parsing requirements', 10)

    try:
        # Import execution modules
        from agentscope.scripts._llm_utils import initialize_llm
        from agentscope.scripts._spec import collect_spec_from_text, enrich_acceptance_map
        from agentscope.scripts._runtime import build_runtime_harness
        from agentscope.scripts._execution import run_execution

        # Initialize LLM
        update_progress('initializing_llm', '', 'Initializing LLM', 15)
        llm, provider = initialize_llm('auto')
        logger.info(f"LLM initialized: {provider}")

        # Parse requirement into spec
        update_progress('parsing_requirement', '', 'Analyzing requirement', 20)
        spec = await collect_spec_from_text(llm, requirement)

        # Enrich acceptance criteria
        update_progress('enriching_spec', '', 'Building acceptance criteria', 25)
        await enrich_acceptance_map(llm, spec)

        # Build runtime harness
        update_progress('building_runtime', '', 'Setting up execution environment', 30)
        runtime = build_runtime_harness(
            spec,
            user_id=f"api-{execution_round_id[:8]}",
            project_hint=project_id,
            llm=llm,
            workspace_dir=str(workspace_dir),
        )

        # Run execution
        update_progress('executing', '', 'Running agents', 40)
        result = await run_execution(
            llm,
            spec,
            max_rounds=max_rounds,
            workspace_dir=workspace_dir,
            skip_code_validation=skip_validation,
            use_parallel_execution=use_parallel,
            use_pr_mode=use_pr_mode,
            use_edit_mode=use_edit_mode,
        )

        # Extract results
        deliverables = {}
        for rid, path in result.get('deliverables', {}).items():
            deliverables[rid] = str(path) if path else None

        rounds_data = result.get('rounds', [])

        # Get summary from last round
        summary = ''
        if rounds_data:
            last_round = rounds_data[-1]
            results = last_round.get('results', [])
            if results:
                summary_parts = []
                for item in results:
                    rid = item.get('requirement_id', '')
                    pass_ratio = item.get('pass_ratio', 0)
                    summary_parts.append(f"Requirement {rid}: {pass_ratio*100:.0f}% passed")
                summary = '\n'.join(summary_parts)

        # Get token/cost stats from hub
        hub_summary = hub.get_project_summary(project_id) if hasattr(hub, 'get_project_summary') else {}

        update_progress('completed', '', '', 100)

        return {
            'status': 'completed',
            'summary': summary,
            'total_tokens': hub_summary.get('total_tokens', 0),
            'total_cost': hub_summary.get('total_cost_usd', 0),
            'total_llm_calls': hub_summary.get('llm_calls', 0),
            'deliverables': deliverables,
            'rounds': rounds_data,
        }

    except Exception as e:
        logger.exception(f"Execution failed: {e}")
        update_progress('failed', '', str(e))
        raise

    finally:
        # Cleanup webhook
        if agentscope_available:
            hub.clear_webhook()


async def _mock_execution(
    execution_round_id: str,
    project_id: str,
    requirement: str,
    update_progress,
) -> dict[str, Any]:
    """Mock execution for testing without AgentScope.

    This simulates an execution flow for development/testing.
    """
    import time

    logger.info("Running mock execution")

    # Simulate phases
    phases = [
        ('collecting_spec', 'Parsing requirements', 20),
        ('initializing_llm', 'Initializing LLM', 30),
        ('building_runtime', 'Setting up environment', 40),
        ('executing', 'Running agents', 60),
        ('validating', 'Validating results', 80),
        ('completed', 'Execution complete', 100),
    ]

    for phase, task, percent in phases:
        update_progress(phase, '', task, percent)
        await asyncio.sleep(0.5)  # Simulate work

    return {
        'status': 'completed',
        'summary': f'Mock execution completed for: {requirement[:50]}...',
        'total_tokens': 1500,
        'total_cost': 0.015,
        'total_llm_calls': 10,
        'deliverables': {'req-1': '/mock/path/output.html'},
        'rounds': [
            {
                'round_number': 1,
                'results': [
                    {
                        'requirement_id': 'req-1',
                        'pass_ratio': 0.9,
                        'qa': {'criteria': []},
                    }
                ],
            }
        ],
    }
