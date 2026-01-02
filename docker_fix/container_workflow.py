# -*- coding: utf-8 -*-
"""Container-internal workflow execution.

This module provides workflow execution that runs entirely inside
the container, without creating nested containers.

Key differences from host-side execution:
- No RuntimeWorkspace creation (already in container)
- Claude Code runs locally (not via docker exec)
- Direct file system access to /workspace
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WorkflowProgress:
    """Progress update for workflow execution."""
    phase: str  # "init", "spec", "blueprint", "coding", "qa", "complete", "error"
    message: str
    requirement_id: str | None = None
    round_num: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    requirements_passed: int = 0
    requirements_total: int = 0
    files_created: list[str] = field(default_factory=list)
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)


async def run_workflow(
    requirement: str,
    zhipu_api_key: str,
    workspace_dir: str = "/workspace",
    max_rounds: int = 3,
    auto_confirm: bool = True,
    verbose: bool = False,
    progress_callback: Any = None,
) -> AsyncGenerator[WorkflowProgress, None]:
    """Run complete workflow inside container.

    This is a generator that yields progress updates and finally
    returns the result.

    Args:
        requirement: User requirement text
        zhipu_api_key: Zhipu API key for LLM and Claude Code
        workspace_dir: Working directory (default /workspace)
        max_rounds: Maximum QA iteration rounds
        auto_confirm: Auto-confirm without user input
        verbose: Enable verbose output
        progress_callback: Optional callback for progress updates

    Yields:
        WorkflowProgress objects with status updates
    """
    from agentscope.scripts._spec import collect_spec, enrich_acceptance_map
    from agentscope.scripts._execution import run_execution
    from agentscope.scripts._llm_init import initialize_llm_from_env
    from agentscope.scripts._claude_code import set_container_context

    # Ensure we're NOT in container mode (we're running locally inside the container)
    set_container_context(None)

    # Set up environment for Claude Code
    os.environ["ANTHROPIC_BASE_URL"] = "https://open.bigmodel.cn/api/anthropic"
    os.environ["ANTHROPIC_API_KEY"] = zhipu_api_key
    os.environ["ANTHROPIC_AUTH_TOKEN"] = zhipu_api_key
    os.environ["ZHIPU_API_KEY"] = zhipu_api_key

    yield WorkflowProgress(
        phase="init",
        message="Initializing LLM...",
    )

    try:
        # Initialize LLM
        llm = initialize_llm_from_env()

        yield WorkflowProgress(
            phase="spec",
            message="Collecting specification...",
        )

        # Collect specification
        spec = await collect_spec(
            llm,
            requirement,
            scripted_inputs=None,
            auto_confirm=auto_confirm,
            verbose=verbose,
        )

        if spec.get("cancelled"):
            yield WorkflowProgress(
                phase="error",
                message="Workflow cancelled by user",
            )
            return

        # Enrich acceptance criteria
        yield WorkflowProgress(
            phase="spec",
            message="Enriching acceptance criteria...",
        )
        await enrich_acceptance_map(llm, spec, verbose=verbose)

        requirements = spec.get("requirements", [])
        yield WorkflowProgress(
            phase="spec",
            message=f"Specification complete: {len(requirements)} requirements",
            details={"requirements": [r["id"] for r in requirements]},
        )

        # Ensure workspace exists
        workspace = Path(workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)

        yield WorkflowProgress(
            phase="coding",
            message="Starting implementation...",
        )

        # Run execution without RuntimeWorkspace (we're already in container)
        result = await run_execution(
            llm=llm,
            spec=spec,
            max_rounds=max_rounds,
            verbose=verbose,
            workspace_dir=workspace,
            require_runtime=False,  # Key: don't require RuntimeWorkspace
            skip_code_validation=False,
            use_collaborative_agents=False,
            use_edit_mode=True,
            use_git_isolation=False,  # Git might not be available in container
        )

        # Collect created files
        files_created = []
        for f in workspace.rglob("*"):
            if f.is_file() and not str(f.relative_to(workspace)).startswith("."):
                files_created.append(str(f.relative_to(workspace)))

        # Extract summary
        exec_summary = result.get("execution_summary", {})

        yield WorkflowProgress(
            phase="complete",
            message="Workflow complete",
            details={
                "passed": exec_summary.get("passed_count", 0),
                "total": exec_summary.get("total_requirements", 0),
                "all_passed": exec_summary.get("all_passed", False),
                "files_created": files_created,
                "rounds": exec_summary.get("total_rounds", 0),
            },
        )

    except Exception as exc:
        yield WorkflowProgress(
            phase="error",
            message=f"Workflow failed: {str(exc)}",
            details={"error_type": type(exc).__name__},
        )


async def run_workflow_simple(
    requirement: str,
    zhipu_api_key: str,
    workspace_dir: str = "/workspace",
    max_rounds: int = 3,
) -> WorkflowResult:
    """Run workflow and return final result.

    Simplified version that doesn't yield progress updates.
    """
    result = WorkflowResult(success=False)

    async for progress in run_workflow(
        requirement=requirement,
        zhipu_api_key=zhipu_api_key,
        workspace_dir=workspace_dir,
        max_rounds=max_rounds,
    ):
        if progress.phase == "complete":
            result.success = True
            result.requirements_passed = progress.details.get("passed", 0)
            result.requirements_total = progress.details.get("total", 0)
            result.files_created = progress.details.get("files_created", [])
            result.details = progress.details
        elif progress.phase == "error":
            result.success = False
            result.error = progress.message

    return result
