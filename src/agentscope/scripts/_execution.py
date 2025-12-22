# -*- coding: utf-8 -*-
"""Execution flow for requirement implementation and validation.

This module provides:
- Main execution loop (run_execution)
- Requirement iteration with QA feedback
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.mcp import StdIOStatefulClient, StatefulClientBase
    from ._sandbox import RuntimeWorkspace, BrowserSandboxManager


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DELIVERABLE_DIR = Path("deliverables")


def _extract_error_files(errors: list[str]) -> set[str]:
    """Extract file paths from validation error messages.

    Args:
        errors: List of validation error strings.

    Returns:
        Set of file paths mentioned in the errors.
    """
    import re

    file_paths: set[str] = set()

    # Common patterns for file paths in error messages
    patterns = [
        # "file.py:10: error message" or "file.py(10): error"
        r"^([a-zA-Z0-9_/\\\.\-]+\.[a-zA-Z0-9]+)[\s:\(]",
        # "in file.py" or "File: file.py"
        r"(?:in|File:?)\s+['\"]?([a-zA-Z0-9_/\\\.\-]+\.[a-zA-Z0-9]+)['\"]?",
        # "./path/to/file.py" or "path/to/file.py"
        r"(?:^|\s)\.?/?([a-zA-Z0-9_]+/[a-zA-Z0-9_/\.\-]+\.[a-zA-Z0-9]+)",
    ]

    for error in errors:
        for pattern in patterns:
            matches = re.findall(pattern, error)
            for match in matches:
                # Clean up the path
                path = match.strip().lstrip("./")
                if path and not path.startswith("node_modules"):
                    file_paths.add(path)

    return file_paths


# ---------------------------------------------------------------------------
# Execution Flow
# ---------------------------------------------------------------------------
async def run_execution(
    llm: Any,
    spec: dict[str, Any],
    max_rounds: int = 3,
    verbose: bool = False,
    runtime_summary: str | None = None,
    mcp_context: str | None = None,
    filesystem_mcp: "StdIOStatefulClient | None" = None,
    workspace_dir: Path | None = None,
    playwright_mcp: "StatefulClientBase | BrowserSandboxManager | None" = None,
    runtime_workspace: "RuntimeWorkspace | None" = None,
    skip_code_validation: bool = False,
    use_collaborative_agents: bool = False,
    require_runtime: bool = True,
) -> dict[str, Any]:
    """Execute requirement implementation with iterative QA feedback.

    Args:
        llm: LLM model instance
        spec: Specification dict with requirements
        max_rounds: Maximum iteration rounds
        verbose: Whether to print debug info
        runtime_summary: Runtime summary text
        mcp_context: MCP context text
        filesystem_mcp: Filesystem MCP client
        workspace_dir: Workspace directory path (for sync only when require_runtime=True)
        playwright_mcp: Playwright test client
        runtime_workspace: RuntimeWorkspace instance
        skip_code_validation: Whether to skip code validation
        use_collaborative_agents: Whether to use collaborative agent mode
        require_runtime: Whether to require RuntimeWorkspace (multi-tenant mode)

    Returns:
        dict: Execution results with rounds and deliverables
    """
    from ._spec import criteria_for_requirement, sanitize_filename
    from ._architecture import generate_architecture_contract, format_architecture_contract
    from ._agent_roles import (
        design_requirement,
        implement_requirement,
        stepwise_generate_files,
        run_scaffold_commands,
    )
    from ._qa import qa_requirement, _normalize_qa_report
    from ._validation import layered_code_validation, CodeValidationResult
    from ._debug import debug_validation_errors, analyze_finalization_errors
    from ._sandbox import SimpleHTTPServer, BrowserSandboxManager
    from ._project_scaffolding import (
        generate_project_scaffolding,
        finalize_project,
        initialize_project_memory,
    )
    from ._observability import get_execution_observer

    # Initialize observer
    observer = get_execution_observer()

    requirements = spec.get("requirements", [])
    overall_target = spec.get("acceptance", {}).get("overall_target", 0.95)

    # State tracking
    feedback_map = {req["id"]: "" for req in requirements}
    req_state = {
        req["id"]: {
            "passed": set(),
            "artifact": "",
            "summary": "",
            "feedback": "",
            "validation_errors": [],  # Track previous validation errors
            "validation_error_files": set(),  # Track files with validation errors
            "validated_files": set(),  # Track files that passed validation
            "blueprint": None,
            "path": None,
        }
        for req in requirements
    }

    # Project context for file tracking and incremental updates
    from agentscope.ones import create_project_context, EnhancedProjectContext
    project_context: EnhancedProjectContext | None = None
    if workspace_dir:
        project_context = create_project_context(
            project_id=spec.get("project_id", "default"),
            workspace_dir=str(workspace_dir),
        )
    rounds: list[dict[str, Any]] = []
    final_paths: dict[str, Path] = {}

    # Build context notes
    notes_parts: list[str] = []
    if runtime_summary:
        notes_parts.append(f"Runtime 摘要:\n{runtime_summary}")
    if mcp_context:
        notes_parts.append(f"MCP 工具概览:\n{mcp_context}")
    contextual_notes = "\n\n".join(notes_parts)

    # Runtime mode check
    use_runtime_mode = runtime_workspace is not None and runtime_workspace.is_initialized

    # Multi-tenant mode: require RuntimeWorkspace for all file operations
    if require_runtime and not use_runtime_mode:
        raise RuntimeError(
            "RuntimeWorkspace is required but not available. "
            "Multi-tenant mode requires all file operations to run in containers. "
            "Please ensure Docker is running and RuntimeWorkspace is properly initialized."
        )

    # Agent mode is only allowed when require_runtime is False
    use_agent_mode = workspace_dir is not None and not require_runtime

    # HTTP server for Playwright
    http_server: SimpleHTTPServer | None = None
    http_port: int | None = None
    serve_url: str | None = None

    if use_runtime_mode and playwright_mcp:
        mount_dir = runtime_workspace.mount_dir
        if mount_dir:
            try:
                http_server = SimpleHTTPServer(mount_dir)
                http_port = http_server.start()
                serve_url = f"http://host.docker.internal:{http_port}"
                observer.on_http_server_start(http_port, f"http://127.0.0.1:{http_port}")
            except Exception as e:
                observer.on_http_server_error(e)
    elif use_agent_mode and playwright_mcp:
        try:
            http_server = SimpleHTTPServer(workspace_dir)
            http_port = http_server.start()
            serve_url = f"http://127.0.0.1:{http_port}"
            observer.on_http_server_start(http_port, serve_url)
        except Exception as e:
            observer.on_http_server_error(e)

    # Generate project scaffolding files and initialize project memory
    from agentscope.ones.memory import ProjectMemory
    project_memory: ProjectMemory | None = None

    if workspace_dir and len(requirements) > 1:
        observer.on_scaffolding_start()
        scaffolding_files = generate_project_scaffolding(
            workspace_dir,
            project_type="fullstack",
        )
        if scaffolding_files:
            observer.on_scaffolding_complete(len(scaffolding_files), scaffolding_files)

        # Initialize project memory for cross-agent context sharing
        project_memory = initialize_project_memory(
            workspace_dir,
            project_type="fullstack",
            project_id="default",
        )
        observer.on_memory_initialized()

    # Architecture contract for multi-requirement projects
    architecture_contract: dict[str, Any] = {}
    if len(requirements) > 1:
        observer.on_architecture_start()
        architecture_contract = await generate_architecture_contract(
            llm, spec, project_memory=project_memory, verbose=verbose
        )
        if architecture_contract:
            contract_text = format_architecture_contract(architecture_contract)
            if contract_text:
                contextual_notes = contract_text + "\n\n" + contextual_notes if contextual_notes else contract_text
                observer.on_architecture_complete(len(architecture_contract.get("api_endpoints", [])))

    # Helper to get current project memory context for prompts
    def get_memory_context() -> str:
        """Get project memory context to prepend to contextual notes."""
        if project_memory:
            memory_ctx = project_memory.get_context_for_prompt(include_instructions=False)
            if memory_ctx:
                return memory_ctx
        return ""

    # Main execution loop
    observer.on_execution_start(len(requirements), max_rounds)

    for round_idx in range(1, max_rounds + 1):
        # Count pending requirements for this round
        pending_count = sum(1 for req in requirements
                          if any(c.get("id") not in req_state[req["id"]]["passed"]
                                 for c in criteria_for_requirement(spec, req["id"])))
        observer.on_round_start(round_idx, pending_count)
        round_entry = {"round": round_idx, "results": []}
        requirement_pass_flags: list[bool] = []

        for requirement in requirements:
            rid = requirement["id"]
            criteria = criteria_for_requirement(spec, rid)

            # Ensure criteria have IDs
            for idx, item in enumerate(criteria, 1):
                item.setdefault("id", f"{rid}.{idx}")

            state = req_state[rid]
            passed_ids = state["passed"]
            failed_criteria = [c for c in criteria if c.get("id") not in passed_ids]

            # Skip if all criteria passed
            if not failed_criteria:
                observer.on_requirement_skip(rid, "已全部通过，沿用上一轮成果")
                requirement_pass_flags.append(True)
                round_entry["results"].append({
                    "requirement_id": rid,
                    "blueprint": state.get("blueprint"),
                    "implementation": {"summary": state.get("summary", ""), "path": str(state.get("path") or "")},
                    "qa": {"criteria": []},
                    "pass_ratio": 1.0,
                })
                final_paths[rid] = state.get("path") or final_paths.get(rid)
                continue

            # Get existing workspace files
            existing_files: list[str] | None = None
            if use_agent_mode and workspace_dir and workspace_dir.exists():
                existing_files = []
                for fpath in workspace_dir.rglob("*"):
                    if fpath.is_file() and not any(p.startswith(".") for p in fpath.relative_to(workspace_dir).parts):
                        rel_path = str(fpath.relative_to(workspace_dir))
                        if "node_modules" not in rel_path and "__pycache__" not in rel_path:
                            existing_files.append(rel_path)

            # Build contextual notes with project memory
            memory_ctx = get_memory_context()
            full_context = ""
            if memory_ctx:
                full_context = memory_ctx
            if contextual_notes:
                full_context = full_context + "\n\n" + contextual_notes if full_context else contextual_notes

            # Design blueprint
            observer.on_requirement_start(rid, requirement.get("title", ""))
            observer.on_phase_start(rid, "blueprint")
            blueprint = await design_requirement(
                llm,
                requirement,
                feedback_map[rid],
                passed_ids,
                failed_criteria,
                state.get("blueprint"),
                contextual_notes=full_context or None,
                existing_workspace_files=existing_files,
                verbose=verbose,
            )
            observer.on_phase_complete(rid, "blueprint", blueprint.get("deliverable_pitch", ""))

            # Implementation
            observer.on_phase_start(rid, "implementation")

            generation_mode = blueprint.get("generation_mode", "single")
            files_plan = blueprint.get("files_plan", [])
            scaffold_config = blueprint.get("scaffold")

            # Scaffold mode
            if generation_mode == "scaffold" and scaffold_config and runtime_workspace:
                observer.on_scaffold_mode_start(rid)
                scaffold_result = await run_scaffold_commands(
                    runtime_workspace=runtime_workspace,
                    scaffold_config=scaffold_config,
                    llm=llm,
                    verbose=verbose,
                )
                if not scaffold_result["success"]:
                    observer.on_scaffold_mode_fallback(rid)
                    generation_mode = "stepwise"
                else:
                    if workspace_dir:
                        synced = runtime_workspace.sync_to_local(workspace_dir)
                        # Filter out node_modules for cleaner logging
                        source_files = [f for f in synced if "node_modules" not in f and "__pycache__" not in f]
                        observer.on_scaffold_sync(rid, len(synced), len(source_files))
                        if source_files and verbose:
                            for sf in source_files[:20]:  # Show max 20 source files
                                observer.on_file_written(rid, sf)
                            if len(source_files) > 20:
                                observer.ctx.logger.debug(f"[{rid}]   ... 还有 {len(source_files) - 20} 个源文件")

            # Generate implementation
            if use_collaborative_agents and workspace_dir:
                # Use ReActAgent with file operation tools (Claude Code style)
                from ._agent_execution import execute_with_agent
                from agentscope.formatter import OpenAIChatFormatter

                observer.on_agent_mode_start(rid)
                formatter = OpenAIChatFormatter()
                impl = await execute_with_agent(
                    llm=llm,
                    formatter=formatter,
                    requirement=requirement,
                    blueprint=blueprint,
                    workspace_dir=workspace_dir,
                    feedback=feedback_map[rid],
                    verbose=verbose,
                )
            elif generation_mode in ("stepwise", "scaffold") and files_plan:
                # Determine which files need regeneration vs which can be skipped
                validated_files = state.get("validated_files", set())
                error_files = state.get("validation_error_files", set())

                # Filter files_plan to only regenerate files with errors
                # Keep all files in first round (validated_files is empty)
                if validated_files and error_files:
                    # Incremental mode: only regenerate files with errors
                    filtered_files_plan = [
                        f for f in files_plan
                        if f["path"] in error_files or f["path"] not in validated_files
                    ]
                    if filtered_files_plan:
                        mode_desc = f"增量修复 ({len(filtered_files_plan)}/{len(files_plan)} 文件)"
                        observer.on_stepwise_mode_start(rid, len(filtered_files_plan), mode_desc)
                        # Update blueprint with filtered plan
                        blueprint = {**blueprint, "files_plan": filtered_files_plan}
                    else:
                        # All files validated, but still failing - regenerate all
                        mode_desc = "脚手架+业务代码" if generation_mode == "scaffold" else "分步生成"
                        observer.on_stepwise_mode_start(rid, len(files_plan), mode_desc)
                else:
                    mode_desc = "脚手架+业务代码" if generation_mode == "scaffold" else "分步生成"
                    observer.on_stepwise_mode_start(rid, len(files_plan), mode_desc)

                impl = await stepwise_generate_files(
                    llm=llm,
                    requirement=requirement,
                    blueprint=blueprint,
                    contextual_notes=full_context or None,
                    runtime_workspace=runtime_workspace if use_runtime_mode else None,
                    feedback=feedback_map[rid],
                    failed_criteria=failed_criteria,
                    previous_errors=state.get("validation_errors", []),
                    verbose=verbose,
                )
            else:
                impl = await implement_requirement(
                    llm,
                    requirement,
                    blueprint,
                    feedback_map[rid],
                    passed_ids,
                    failed_criteria,
                    state.get("artifact", ""),
                    contextual_notes=full_context or None,
                    workspace_files=None,
                    verbose=verbose,
                )

            observer.on_implementation_summary(rid, impl.get("summary", ""))

            # Parse decisions from agent output and store in project memory
            if project_memory:
                # Check all text fields that might contain decisions
                output_texts = []
                if impl.get("summary"):
                    output_texts.append(impl["summary"])
                if impl.get("raw_output"):
                    output_texts.append(impl["raw_output"])
                if blueprint.get("raw_output"):
                    output_texts.append(blueprint["raw_output"])

                for text in output_texts:
                    decisions = project_memory.parse_decisions_from_output(
                        text, agent_id=f"agent_{rid}", round_index=round_idx
                    )
                    if decisions:
                        observer.on_decisions_recorded(rid, len(decisions))

            # Ensure deliverables directory exists
            DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)

            # Handle multi-file mode
            files_list = impl.get("files", [])
            is_multifile_mode = bool(files_list)
            validation_result: CodeValidationResult | None = None

            if is_multifile_mode and (use_runtime_mode or use_agent_mode):
                observer.on_multifile_start(rid, len(files_list))
                written_files: list[str] = []

                if use_agent_mode:
                    # Agent mode: files were already written by the agent via tools
                    # Just collect the file list for validation, don't overwrite
                    for file_info in files_list:
                        file_path = file_info.get("path", "")
                        if file_path:
                            written_files.append(file_path)
                            observer.on_file_written(rid, file_path)

                    # Code validation on existing files
                    if written_files and not skip_code_validation:
                        observer.on_validation_start(rid)
                        local_files_dict = {}
                        for fpath in workspace_dir.rglob("*"):
                            if fpath.is_file() and not fpath.name.startswith("."):
                                rel_path = str(fpath.relative_to(workspace_dir))
                                if "node_modules" not in rel_path and "__pycache__" not in rel_path:
                                    try:
                                        local_files_dict[rel_path] = fpath.read_text(encoding="utf-8")
                                    except Exception:
                                        pass

                        if local_files_dict:
                            req_summary = requirement.get("summary", requirement.get("description", ""))[:200]
                            tech_stack_info = project_memory.get_tech_stack_info() if project_memory else ""
                            # Use runtime_workspace if available for linter validation
                            validation_result = await layered_code_validation(
                                runtime_workspace=runtime_workspace,
                                llm=llm,
                                files=local_files_dict,
                                requirement_summary=req_summary,
                                tech_stack_info=tech_stack_info,
                                verbose=verbose,
                            )

                            observer.on_validation_result(
                                rid, validation_result.is_valid, validation_result.score,
                                len(validation_result.errors)
                            )

                            if not validation_result.is_valid:
                                # Agent-driven debug: let LLM analyze and fix errors
                                if runtime_workspace and validation_result.errors:
                                    observer.on_debug_start(rid)
                                    debug_result = await debug_validation_errors(
                                        llm=llm,
                                        runtime_workspace=runtime_workspace,
                                        validation_result=validation_result,
                                        project_memory=project_memory,
                                        verbose=verbose,
                                    )

                                    for action in debug_result.actions_taken[:3]:
                                        observer.on_debug_action(rid, action)

                                    if debug_result.fixed:
                                        observer.on_revalidation_start(rid)
                                        validation_result = await layered_code_validation(
                                            runtime_workspace=runtime_workspace,
                                            llm=llm,
                                            files=local_files_dict,
                                            requirement_summary=req_summary,
                                            tech_stack_info=tech_stack_info,
                                            verbose=verbose,
                                        )
                                        observer.on_validation_result(
                                            rid, validation_result.is_valid, validation_result.score,
                                            len(validation_result.errors)
                                        )

                elif use_runtime_mode:
                    write_results = runtime_workspace.write_files(files_list)
                    for result in write_results:
                        if result.get("success"):
                            written_files.append(result["path"])
                            observer.on_file_written(rid, result["path"], "Runtime")

                    # Execute setup commands
                    setup_commands = impl.get("setup_commands", [])
                    if setup_commands:
                        observer.on_setup_commands(rid, len(setup_commands))
                        runtime_workspace.execute_setup_commands(setup_commands)

                    # Sync to local
                    if workspace_dir:
                        synced = runtime_workspace.sync_to_local(workspace_dir)
                        observer.on_files_synced(rid, len(synced))

                        # Code validation
                        if synced and not skip_code_validation:
                            observer.on_validation_start(rid)
                            synced_files = {}
                            for fpath in workspace_dir.rglob("*"):
                                if fpath.is_file() and not fpath.name.startswith("."):
                                    try:
                                        rel_path = str(fpath.relative_to(workspace_dir))
                                        synced_files[rel_path] = fpath.read_text(encoding="utf-8")
                                    except Exception:
                                        pass

                            req_summary = requirement.get("summary", requirement.get("description", ""))[:200]
                            tech_stack_info = project_memory.get_tech_stack_info() if project_memory else ""
                            validation_result = await layered_code_validation(
                                runtime_workspace=runtime_workspace,
                                llm=llm,
                                files=synced_files,
                                requirement_summary=req_summary,
                                tech_stack_info=tech_stack_info,
                                verbose=verbose,
                            )

                            observer.on_validation_result(
                                rid, validation_result.is_valid, validation_result.score,
                                len(validation_result.errors)
                            )

                            if not validation_result.is_valid:
                                for err in validation_result.errors[:3]:
                                    observer.on_validation_error(rid, err)

                                # Agent-driven debug: let LLM analyze and fix errors
                                if runtime_workspace and validation_result.errors:
                                    observer.on_debug_start(rid)
                                    debug_result = await debug_validation_errors(
                                        llm=llm,
                                        runtime_workspace=runtime_workspace,
                                        validation_result=validation_result,
                                        project_memory=project_memory,
                                        verbose=verbose,
                                    )

                                    for action in debug_result.actions_taken[:3]:
                                        observer.on_debug_action(rid, action)

                                    if debug_result.fixed:
                                        observer.on_revalidation_start(rid)
                                        validation_result = await layered_code_validation(
                                            runtime_workspace=runtime_workspace,
                                            llm=llm,
                                            files=synced_files,
                                            requirement_summary=req_summary,
                                            tech_stack_info=tech_stack_info,
                                            verbose=verbose,
                                        )
                                        observer.on_validation_result(
                                            rid, validation_result.is_valid, validation_result.score,
                                            len(validation_result.errors)
                                        )
                else:
                    # Local mode
                    local_files_dict = {}
                    for file_info in files_list:
                        file_path = file_info.get("path", "")
                        file_content = file_info.get("content", "")
                        if not file_path:
                            continue
                        full_path = workspace_dir / file_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(str(file_content), encoding="utf-8")
                        written_files.append(file_path)
                        local_files_dict[file_path] = str(file_content)
                        observer.on_file_written(rid, file_path)

                    # Code validation
                    if local_files_dict and not skip_code_validation:
                        observer.on_validation_start(rid)
                        req_summary = requirement.get("summary", requirement.get("description", ""))[:200]
                        tech_stack_info = project_memory.get_tech_stack_info() if project_memory else ""
                        validation_result = await layered_code_validation(
                            runtime_workspace=None,
                            llm=llm,
                            files=local_files_dict,
                            requirement_summary=req_summary,
                            tech_stack_info=tech_stack_info,
                            verbose=verbose,
                        )

                        observer.on_validation_result(
                            rid, validation_result.is_valid, validation_result.score,
                            len(validation_result.errors)
                        )

                # Save project info
                path = DELIVERABLE_DIR / f"{sanitize_filename(rid)}_{round_idx}_project.json"
                path.write_text(json.dumps(impl, ensure_ascii=False, indent=2), encoding="utf-8")
                artifact_content = json.dumps({"files": written_files}, ensure_ascii=False)
            else:
                # Single file mode
                ext = impl.get("artifact_extension", "txt").lstrip(".")
                artifact_content = impl.get("artifact_content", "")
                if isinstance(artifact_content, (dict, list)):
                    artifact_content = json.dumps(artifact_content, ensure_ascii=False, indent=2)

                if use_runtime_mode:
                    main_file = f"app.{ext}"
                    runtime_workspace.write_file(main_file, str(artifact_content))
                    if workspace_dir:
                        runtime_workspace.sync_to_local(workspace_dir)
                    path = DELIVERABLE_DIR / f"{sanitize_filename(rid)}_{round_idx}.{ext}"
                    path.write_text(str(artifact_content), encoding="utf-8")
                elif use_agent_mode and workspace_dir:
                    main_file = f"app.{ext}"
                    (workspace_dir / main_file).write_text(str(artifact_content), encoding="utf-8")
                    path = DELIVERABLE_DIR / f"{sanitize_filename(rid)}_{round_idx}.{ext}"
                    path.write_text(str(artifact_content), encoding="utf-8")
                else:
                    path = DELIVERABLE_DIR / f"{sanitize_filename(rid)}_{round_idx}.{ext}"
                    path.write_text(str(artifact_content), encoding="utf-8")

            final_paths[rid] = path
            state.update({
                "artifact": str(artifact_content),
                "path": path,
                "summary": impl.get("summary", ""),
                "blueprint": blueprint,
            })

            # QA validation
            observer.on_phase_start(rid, "qa")

            qa_workspace_files: dict[str, str] | None = None
            if use_agent_mode and workspace_dir:
                qa_workspace_files = {}
                # Get files related to current requirement from implementation
                req_files = impl.get("files", [])
                req_file_paths = {f.get("path", "") for f in req_files if f.get("path")}

                # Non-source file extensions to exclude (language/framework agnostic)
                non_source_extensions = (
                    ".log", ".lock", ".map", ".min.js", ".min.css",
                    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
                    ".woff", ".woff2", ".ttf", ".eot", ".otf",
                    ".mp3", ".mp4", ".wav", ".avi", ".mov",
                    ".zip", ".tar", ".gz", ".rar", ".7z",
                    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
                    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe",
                    ".db", ".sqlite", ".sqlite3",
                )

                for fpath in workspace_dir.rglob("*"):
                    if fpath.is_file() and not fpath.name.startswith(".") and not fpath.name.startswith("_"):
                        try:
                            rel_path = str(fpath.relative_to(workspace_dir))
                            # Skip common non-source directories
                            if any(skip in rel_path for skip in ["node_modules", "__pycache__", ".git", "dist"]):
                                continue
                            # Prioritize files from current requirement
                            if req_file_paths and rel_path not in req_file_paths:
                                # Exclude non-source files (use blacklist instead of whitelist)
                                if rel_path.lower().endswith(non_source_extensions):
                                    continue
                            qa_workspace_files[rel_path] = fpath.read_text(encoding="utf-8")
                        except Exception:
                            pass

            qa_report_raw = await qa_requirement(
                llm=llm,
                requirement=requirement,
                blueprint=blueprint,
                artifact_path=path,
                criteria=criteria,
                round_index=round_idx,
                workspace_files=qa_workspace_files,
                playwright_mcp=playwright_mcp,
                http_port=http_port,
                verbose=verbose,
            )
            qa_report = _normalize_qa_report(qa_report_raw, criteria)

            # Calculate results
            crit = qa_report.get("criteria", [])
            passed = sum(1 for item in crit if item.get("pass"))
            total = max(len(crit), 1)
            pass_ratio = passed / total

            static_passed = pass_ratio >= overall_target and passed == total
            code_validation_passed = True
            code_validation_score = 1.0

            if validation_result is not None:
                code_validation_score = validation_result.score
                code_validation_passed = validation_result.is_valid and validation_result.score >= 0.6

            overall_passed = static_passed and code_validation_passed
            requirement_pass_flags.append(overall_passed)

            # Update passed criteria
            for item in crit:
                if item.get("pass") and item.get("id"):
                    state["passed"].add(item["id"])

            # Update feedback and validation errors for next round
            if overall_passed:
                feedback_map[rid] = ""
                state["feedback"] = ""
                state["validation_errors"] = []  # Clear errors on success
            else:
                feedback_parts = []
                if not static_passed:
                    feedback_parts.append(qa_report.get("improvements", ""))
                if not code_validation_passed and validation_result:
                    if validation_result.errors:
                        error_lines = [f"  - {err}" for err in validation_result.errors[:5]]
                        feedback_parts.append(f"代码验证失败:\n" + "\n".join(error_lines))
                        # Store validation errors for next round
                        state["validation_errors"] = validation_result.errors[:15]
                        # Track which files have errors (for incremental fixing)
                        error_files = _extract_error_files(validation_result.errors)
                        state["validation_error_files"] = error_files
                        # Files in current req that are NOT in error_files passed validation
                        current_files = {f.get("path", "") for f in impl.get("files", []) if f.get("path")}
                        state["validated_files"] = current_files - error_files
                feedback = "\n".join(feedback_parts) if feedback_parts else qa_report.get("improvements", "")
                feedback_map[rid] = feedback
                state["feedback"] = feedback

            round_entry["results"].append({
                "requirement_id": rid,
                "blueprint": blueprint,
                "implementation": {"summary": impl.get("summary", ""), "path": str(path)},
                "qa": qa_report,
                "pass_ratio": pass_ratio,
                "code_validation_score": code_validation_score if validation_result else None,
                "overall_passed": overall_passed,
            })

            # Report requirement completion
            scores = {"静态": pass_ratio}
            if validation_result is not None:
                scores["代码"] = code_validation_score
            observer.on_requirement_complete(rid, overall_passed, scores)

        rounds.append(round_entry)

        # Report round completion
        passed_reqs = [requirements[idx]["id"] for idx, ok in enumerate(requirement_pass_flags) if ok]
        failed_reqs = [requirements[idx]["id"] for idx, ok in enumerate(requirement_pass_flags) if not ok]
        observer.on_round_complete(round_idx, passed_reqs, failed_reqs)

        if all(requirement_pass_flags):
            observer.on_execution_complete(round_idx, True)
            break
        elif round_idx == max_rounds:
            observer.on_execution_complete(round_idx, False)

    # Finalize project - merge files and validate
    finalization_report: dict[str, Any] = {}
    if workspace_dir and len(requirements) > 1:
        observer.on_finalization_start()
        try:
            finalization_report = finalize_project(workspace_dir, DELIVERABLE_DIR)
            merged_count = len(finalization_report.get("merged_files", []))
            copied_count = len(finalization_report.get("copied_files", []))
            conflicts = finalization_report.get("conflicts", [])
            file_errors = finalization_report.get("file_errors", [])
            validation = finalization_report.get("validation", {})

            observer.on_finalization_complete(copied_count, merged_count, len(conflicts))

            # Analyze file errors with LLM
            if file_errors:
                observer.on_finalization_errors(len(file_errors))
                decisions, summary = await analyze_finalization_errors(
                    llm=llm,
                    file_errors=file_errors,
                    verbose=verbose,
                )
                ignored_count = sum(1 for d in decisions if d.action == "ignore")
                manual_count = sum(1 for d in decisions if d.action == "manual")

                manual_files = [
                    (d.path, d.reason) for d in decisions if d.action == "manual"
                ]
                observer.on_finalization_error_resolved(ignored_count, manual_count, manual_files)

                finalization_report["error_decisions"] = [
                    {"path": d.path, "action": d.action, "reason": d.reason}
                    for d in decisions
                ]
                finalization_report["error_summary"] = summary

            if validation.get("passed"):
                observer.on_project_validation(True)
            else:
                missing = validation.get("missing", [])
                observer.on_project_validation(False, missing)
                if missing:
                    # Try to generate missing files
                    extra_files = generate_project_scaffolding(workspace_dir, "fullstack")
                    if extra_files:
                        observer.on_supplemental_files(len(extra_files))

            warnings = validation.get("warnings", [])
            for warn in warnings:
                observer.on_project_warning(warn)

        except Exception as e:
            observer.on_finalization_error(e)

    # Cleanup
    if http_server:
        try:
            http_server.stop()
            observer.on_http_server_stop()
        except Exception as e:
            observer.on_http_server_error(e)

    return {
        "rounds": rounds,
        "deliverables": final_paths,
        "finalization": finalization_report,
    }


__all__ = [
    "DELIVERABLE_DIR",
    "run_execution",
]
