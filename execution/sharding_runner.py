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

        runtime_workspace = None

        try:
            from agentscope.scripts._llm_utils import initialize_llm
            from agentscope.scripts._execution import run_single_requirement

            # Initialize LLM
            llm, provider = initialize_llm('auto')
            logger.info(f"[{req_id}] LLM initialized: {provider}")

            # Check if runtime mode is enabled (Docker container execution)
            use_runtime = getattr(settings, 'USE_RUNTIME_WORKSPACE', True)

            workspace_dir = None

            if use_runtime:
                # Use Docker container for isolated execution
                try:
                    from agentscope.scripts._runtime_workspace import RuntimeWorkspaceWithPR

                    # Each requirement gets its own container
                    runtime_workspace = RuntimeWorkspaceWithPR(
                        base_workspace_dir="/workspace",
                        image=getattr(settings, 'RUNTIME_DOCKER_IMAGE', 'agentscope/runtime-sandbox-filesystem:latest'),
                        timeout=600,
                        enable_pr_mode=True,
                    )

                    # Start the container
                    if not runtime_workspace.start():
                        logger.warning(f"[{req_id}] Failed to start runtime workspace, falling back to local mode")
                        runtime_workspace = None
                    else:
                        logger.info(f"[{req_id}] Runtime workspace started: {runtime_workspace.sandbox_id}")

                except Exception as e:
                    logger.warning(f"[{req_id}] Runtime workspace init failed: {e}, falling back to local mode")
                    runtime_workspace = None

            if not runtime_workspace:
                # Fallback to local workspace with two-level isolation
                project_id = str(execution_round.project_id) if execution_round.project_id else 'default'
                workspace_base = Path(getattr(settings, 'EXECUTION_WORKSPACE_DIR', '/tmp/hivecore_workspaces'))

                # Structure:
                # /workspaces/{project_id}/
                #   ├── working/                    # Final merged code (all requirements)
                #   └── requirements/
                #       ├── {req_id}/
                #       │   ├── delivery/           # Merged code from all agents for this requirement
                #       │   └── agents/
                #       │       ├── {agent_id}/     # Isolated workspace for each agent
                #       │       └── ...
                #       └── ...

                # For now, use a default agent ID (single agent per requirement)
                agent_id = requirement_execution.agent_id if hasattr(requirement_execution, 'agent_id') and requirement_execution.agent_id else 'default'

                req_base = workspace_base / project_id / 'requirements' / req_id
                agent_workspace = req_base / 'agents' / agent_id
                agent_workspace.mkdir(parents=True, exist_ok=True)

                # Also ensure delivery dir exists for merging
                delivery_dir = req_base / 'delivery'
                delivery_dir.mkdir(parents=True, exist_ok=True)

                workspace_dir = agent_workspace

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
                    'acceptance': requirement_execution.qa_result.get('acceptance', []) if requirement_execution.qa_result else [],
                }

            # Get previous state for retry rounds
            inner_round = requirement_execution.inner_round_number
            feedback = ""
            passed_ids: set = set()
            prev_blueprint = None

            if inner_round > 1:
                # Get previous attempt's results for feedback
                prev_qa = requirement_execution.qa_result
                if prev_qa and prev_qa.get('details'):
                    # Collect feedback from failed criteria
                    failed_reasons = []
                    for item in prev_qa.get('details', []):
                        if not item.get('pass') and item.get('reason'):
                            failed_reasons.append(f"- {item.get('name', 'Criterion')}: {item.get('reason')}")
                    if failed_reasons:
                        feedback = "Previous QA feedback:\n" + "\n".join(failed_reasons)

                    # Collect passed IDs
                    passed_ids = {item.get('id') for item in prev_qa.get('details', []) if item.get('pass') and item.get('id')}

                prev_blueprint = requirement_execution.blueprint

            logger.info(f"[{req_id}] Executing with inner_round={inner_round}, feedback_len={len(feedback)}")

            # Execute single requirement
            result = await run_single_requirement(
                llm=llm,
                spec=spec,
                requirement=req_data,
                workspace_dir=workspace_dir,
                runtime_workspace=runtime_workspace,
                round_idx=inner_round,
                feedback=feedback,
                passed_ids=passed_ids,
                prev_blueprint=prev_blueprint,
                verbose=True,
            )

            logger.info(f"[{req_id}] Execution completed: passed={result.get('passed')}, pass_ratio={result.get('pass_ratio')}")
            return result

        except ImportError as e:
            logger.warning(f"AgentScope not available: {e}, using mock")
            return _mock_execute_requirement(requirement_execution)

        except Exception as e:
            logger.exception(f"Requirement execution failed: {e}")
            raise

        finally:
            # Clean up runtime workspace
            if runtime_workspace:
                try:
                    runtime_workspace.stop()
                    logger.info(f"[{req_id}] Runtime workspace stopped")
                except Exception as e:
                    logger.warning(f"[{req_id}] Failed to stop runtime workspace: {e}")

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


# ============ Workspace Merge Functions ============


def _collect_all_files(
    requirements_dir: Path,
    requirement_ids: list[str],
) -> Dict[str, Dict[str, Any]]:
    """
    Collect all files from requirement delivery directories and detect conflicts.

    Now reads from {req_id}/delivery/ instead of {req_id}/ directly.

    Returns:
        Dict mapping relative file paths to:
        {
            "sources": [{"req_id": "REQ-001", "path": Path, "content": str}, ...],
            "has_conflict": bool
        }
    """
    file_map: Dict[str, Dict[str, Any]] = {}

    for req_id in requirement_ids:
        # Read from delivery directory (merged result of all agents for this requirement)
        req_delivery = requirements_dir / req_id / 'delivery'
        if not req_delivery.exists():
            # Fallback: try old structure (direct in req_id dir)
            req_delivery = requirements_dir / req_id
            if not req_delivery.exists():
                continue

        for src_path in req_delivery.rglob('*'):
            if src_path.is_file():
                rel_path = str(src_path.relative_to(req_delivery))

                if rel_path not in file_map:
                    file_map[rel_path] = {"sources": [], "has_conflict": False}

                try:
                    content = src_path.read_text(encoding='utf-8')
                except Exception:
                    content = src_path.read_bytes().decode('utf-8', errors='replace')

                file_map[rel_path]["sources"].append({
                    "req_id": req_id,
                    "path": src_path,
                    "content": content,
                })

                # Mark as conflict if multiple sources
                if len(file_map[rel_path]["sources"]) > 1:
                    file_map[rel_path]["has_conflict"] = True

    return file_map


def merge_agents_to_delivery(
    project_id: str,
    req_id: str,
    agent_ids: list[str] | None = None,
    spec: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Merge all agent workspaces into the requirement's delivery directory.

    This is the first level of merge (Agent → Delivery within a requirement).

    Args:
        project_id: Project identifier
        req_id: Requirement ID
        agent_ids: List of agent IDs to merge, or None to discover all
        spec: Parsed spec for conflict resolution context

    Returns:
        Dict with merge results
    """
    import shutil

    workspace_base = Path(getattr(settings, 'EXECUTION_WORKSPACE_DIR', '/tmp/hivecore_workspaces'))
    req_base = workspace_base / project_id / 'requirements' / req_id
    agents_dir = req_base / 'agents'
    delivery_dir = req_base / 'delivery'

    delivery_dir.mkdir(parents=True, exist_ok=True)

    # Discover agents if not specified
    if agent_ids is None:
        if agents_dir.exists():
            agent_ids = [d.name for d in agents_dir.iterdir() if d.is_dir()]
        else:
            agent_ids = []

    if not agent_ids:
        logger.info(f"[Merge] No agents to merge for {req_id}")
        return {"merged_files": [], "conflicts_resolved": [], "delivery_dir": str(delivery_dir)}

    logger.info(f"[Merge] Merging {len(agent_ids)} agents for {req_id}: {agent_ids}")

    # Collect files from all agents
    file_map: Dict[str, Dict[str, Any]] = {}

    for agent_id in agent_ids:
        agent_workspace = agents_dir / agent_id
        if not agent_workspace.exists():
            continue

        for src_path in agent_workspace.rglob('*'):
            if src_path.is_file():
                rel_path = str(src_path.relative_to(agent_workspace))

                if rel_path not in file_map:
                    file_map[rel_path] = {"sources": [], "has_conflict": False}

                try:
                    content = src_path.read_text(encoding='utf-8')
                except Exception:
                    content = src_path.read_bytes().decode('utf-8', errors='replace')

                file_map[rel_path]["sources"].append({
                    "req_id": f"{req_id}/{agent_id}",  # For logging
                    "agent_id": agent_id,
                    "path": src_path,
                    "content": content,
                })

                if len(file_map[rel_path]["sources"]) > 1:
                    file_map[rel_path]["has_conflict"] = True

    # Merge files
    merged_files = []
    conflicts_resolved = []

    for rel_path, file_info in file_map.items():
        dst_path = delivery_dir / rel_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        sources = file_info["sources"]

        try:
            if file_info["has_conflict"]:
                logger.info(f"[Merge] Agent conflict for {rel_path}: {[s['agent_id'] for s in sources]}")

                if spec:
                    merged_content = _merge_file_with_agent(rel_path, sources, spec)
                    dst_path.write_text(merged_content, encoding='utf-8')
                    conflicts_resolved.append(rel_path)
                else:
                    # No spec, use last agent's version
                    shutil.copy2(sources[-1]["path"], dst_path)
            else:
                shutil.copy2(sources[0]["path"], dst_path)

            merged_files.append(rel_path)

        except Exception as e:
            logger.error(f"[Merge] Failed to merge {rel_path}: {e}")

    logger.info(f"[Merge] Agent merge for {req_id}: {len(merged_files)} files, {len(conflicts_resolved)} conflicts resolved")

    return {
        "merged_files": merged_files,
        "conflicts_resolved": conflicts_resolved,
        "delivery_dir": str(delivery_dir),
    }


def _merge_file_with_agent(
    file_path: str,
    sources: list[Dict[str, Any]],
    spec: Dict[str, Any],
) -> str:
    """
    Use LLM to intelligently merge conflicting file versions.

    This function reuses HiveCore's smart_merge for two versions.
    For more than 2 versions, it chains merges sequentially.

    Args:
        file_path: Relative file path
        sources: List of source versions, each with req_id and content
        spec: Parsed spec for context

    Returns:
        Merged file content
    """
    if len(sources) < 2:
        return sources[0]["content"] if sources else ""

    try:
        from agentscope.scripts._multi_agent import smart_merge
        from agentscope.scripts._llm_utils import initialize_llm

        async def _do_merge():
            llm, _ = initialize_llm('auto')

            # Start with first version as base
            merged = sources[0]["content"]

            # Merge each subsequent version into the result
            for i in range(1, len(sources)):
                head_content = sources[i]["content"]
                req_id = sources[i]["req_id"]

                merged_result, success = await smart_merge(
                    base_content=merged,
                    head_content=head_content,
                    file_path=file_path,
                    llm=llm,
                )

                if success:
                    merged = merged_result
                    logger.info(f"[Merge] smart_merge succeeded for {file_path} (merged {req_id})")
                else:
                    # Fallback: prefer the newer version (has more complete changes)
                    logger.warning(f"[Merge] smart_merge failed for {file_path}, using {req_id} version")
                    merged = head_content

            return merged

        return _run_async_in_thread(_do_merge())

    except ImportError as e:
        logger.warning(f"[Merge] smart_merge not available: {e}, using last version")
        return sources[-1]["content"]
    except Exception as e:
        logger.error(f"[Merge] Agent merge failed for {file_path}: {e}")
        return sources[-1]["content"]


def merge_requirement_workspaces(
    project_id: str,
    passed_requirement_ids: list[str],
    spec: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Merge files from passed requirements into the working directory.

    This function:
    1. Collects all files from requirement workspaces
    2. Detects conflicts (same file from multiple requirements)
    3. For conflicts: uses Agent (LLM) to intelligently merge
    4. For non-conflicts: copies directly

    Args:
        project_id: Project identifier
        passed_requirement_ids: List of requirement IDs that passed QA,
                               in dependency order
        spec: Parsed requirement spec (for Agent merge context)

    Returns:
        Dict with merge results:
        {
            "merged_files": ["path1", "path2", ...],
            "conflicts_resolved": ["path1", ...],
            "file_sources": {"path": "REQ-001", ...},
            "working_dir": "/path/to/working"
        }
    """
    import shutil

    workspace_base = Path(getattr(settings, 'EXECUTION_WORKSPACE_DIR', '/tmp/hivecore_workspaces'))
    project_dir = workspace_base / project_id
    working_dir = project_dir / 'working'
    requirements_dir = project_dir / 'requirements'

    # Ensure working directory exists
    working_dir.mkdir(parents=True, exist_ok=True)

    # Collect all files and detect conflicts
    file_map = _collect_all_files(requirements_dir, passed_requirement_ids)

    merged_files = []
    conflicts_resolved = []
    file_sources = {}

    logger.info(f"[Merge] Merging {len(passed_requirement_ids)} requirement workspaces to {working_dir}")
    logger.info(f"[Merge] Found {len(file_map)} unique files, {sum(1 for f in file_map.values() if f['has_conflict'])} with conflicts")

    for rel_path, file_info in file_map.items():
        dst_path = working_dir / rel_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        sources = file_info["sources"]

        try:
            if file_info["has_conflict"]:
                # Multiple sources - need Agent merge
                logger.info(f"[Merge] Conflict detected for {rel_path}: {[s['req_id'] for s in sources]}")

                if spec:
                    # Use Agent to merge
                    merged_content = _merge_file_with_agent(rel_path, sources, spec)
                    dst_path.write_text(merged_content, encoding='utf-8')
                    conflicts_resolved.append(rel_path)
                    file_sources[rel_path] = f"merged({','.join(s['req_id'] for s in sources)})"
                else:
                    # No spec available, fallback to last version
                    logger.warning(f"[Merge] No spec for Agent merge, using last version for {rel_path}")
                    shutil.copy2(sources[-1]["path"], dst_path)
                    file_sources[rel_path] = sources[-1]["req_id"]
            else:
                # Single source - direct copy
                shutil.copy2(sources[0]["path"], dst_path)
                file_sources[rel_path] = sources[0]["req_id"]

            merged_files.append(rel_path)

        except Exception as e:
            logger.error(f"[Merge] Failed to process {rel_path}: {e}")

    logger.info(f"[Merge] Merged {len(merged_files)} files, resolved {len(conflicts_resolved)} conflicts")

    return {
        "merged_files": merged_files,
        "conflicts_resolved": conflicts_resolved,
        "file_sources": file_sources,
        "working_dir": str(working_dir),
    }


def cleanup_requirement_workspaces(
    project_id: str,
    requirement_ids: list[str] | None = None,
) -> None:
    """
    Clean up individual requirement workspaces after successful merge.

    Args:
        project_id: Project identifier
        requirement_ids: Specific requirements to clean up, or None for all
    """
    import shutil

    workspace_base = Path(getattr(settings, 'EXECUTION_WORKSPACE_DIR', '/tmp/hivecore_workspaces'))
    requirements_dir = workspace_base / project_id / 'requirements'

    if not requirements_dir.exists():
        return

    if requirement_ids is None:
        # Clean all requirement workspaces
        try:
            shutil.rmtree(requirements_dir)
            logger.info(f"[Cleanup] Removed all requirement workspaces for project {project_id}")
        except Exception as e:
            logger.error(f"[Cleanup] Failed to remove requirements dir: {e}")
    else:
        # Clean specific workspaces
        for req_id in requirement_ids:
            req_workspace = requirements_dir / req_id
            if req_workspace.exists():
                try:
                    shutil.rmtree(req_workspace)
                    logger.debug(f"[Cleanup] Removed workspace for {req_id}")
                except Exception as e:
                    logger.error(f"[Cleanup] Failed to remove {req_id} workspace: {e}")
