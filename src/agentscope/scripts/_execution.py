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
    from ._runtime_workspace import RuntimeWorkspaceWithPR, MergeResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DELIVERABLE_DIR = Path("deliverables")


def _get_formatter_for_model(llm: Any) -> Any:
    """Get the appropriate formatter based on the LLM model type.

    Args:
        llm: The LLM model instance.

    Returns:
        The appropriate formatter instance.
    """
    from agentscope.model import AnthropicChatModel
    from agentscope.formatter import OpenAIChatFormatter, AnthropicChatFormatter

    if isinstance(llm, AnthropicChatModel):
        return AnthropicChatFormatter()
    return OpenAIChatFormatter()


def _extract_error_files(errors: list[str]) -> set[str]:
    """Extract file paths from validation error messages.

    Args:
        errors: List of validation error strings.

    Returns:
        Set of file paths mentioned in the errors.
    """
    import re

    file_paths: set[str] = set()

    # Valid source code file extensions
    valid_extensions = {
        "py", "js", "jsx", "ts", "tsx", "vue", "html", "css", "scss",
        "json", "yaml", "yml", "toml", "ini", "txt", "md", "sql",
    }

    def is_valid_path(path: str) -> bool:
        """Check if path looks like a valid source file path."""
        if not path:
            return False
        # Must have at least one / for relative paths (otherwise too easy to match error names)
        # Exception: single file names that look like actual files
        if "/" not in path:
            # Single filename: only valid if it has a valid extension and doesn't look like Python module
            # e.g., "pydantic.errors.PydanticImportError" should be rejected
            parts = path.rsplit(".", 1)
            if len(parts) != 2:
                return False
            name, ext = parts
            # Reject if name contains dots (like pydantic.errors)
            if "." in name:
                return False
            return ext.lower() in valid_extensions
        # For paths with /, check extension
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext not in valid_extensions:
            return False
        # Reject paths that look like Python module names (no actual directories)
        if path.count("/") == 1 and path.startswith("app/"):
            # "app/something.py" is likely a module path, not a real file path
            # Real paths are like "backend/app/something.py"
            pass  # Allow it but it might need frontend/ or backend/ prefix
        return True

    # Common patterns for file paths in error messages
    patterns = [
        # "(/workspace/path/to/file.py)" - Docker container paths in parentheses (highest priority)
        r"\((/[a-zA-Z0-9_/\.\-]+\.[a-zA-Z0-9]+)\)",
        # "from 'module' (/path/file.py)" - Python import error format
        r"from\s+'[^']+'\s+\(([^)]+\.py)\)",
        # "file.py:10: error message" or "file.py(10): error"
        r"^([a-zA-Z0-9_/\\\-]+\.[a-zA-Z0-9]+)[\s:\(]",
        # "in file.py" or "File: file.py"
        r"(?:in|File:?)\s+['\"]?([a-zA-Z0-9_/\\\-]+\.[a-zA-Z0-9]+)['\"]?",
        # "./path/to/file.py" or "path/to/file.py" (must have at least one /)
        r"(?:^|\s)\.?/?([a-zA-Z0-9_]+/[a-zA-Z0-9_/\-]+\.[a-zA-Z0-9]+)",
    ]

    for error in errors:
        for pattern in patterns:
            matches = re.findall(pattern, error)
            for match in matches:
                # Clean up the path
                path = match.strip().lstrip("./")
                # Remove Docker workspace prefix if present
                if path.startswith("/workspace/"):
                    path = path[len("/workspace/"):]
                elif path.startswith("workspace/"):
                    path = path[len("workspace/"):]
                # Validate the path
                if is_valid_path(path) and not path.startswith("node_modules"):
                    file_paths.add(path)

    return file_paths


# ---------------------------------------------------------------------------
# Error Classification System (Framework Layer - 框架普适化)
# ---------------------------------------------------------------------------
class ErrorCategory:
    """Error category constants for structured error handling."""
    TYPE_CHECK = "type_check"           # mypy, pyright, tsc errors
    IMPORT_MISSING = "import_missing"   # ImportError: cannot import name X
    MODULE_NOT_FOUND = "module_not_found"  # ModuleNotFoundError
    CIRCULAR_IMPORT = "circular_import"    # Circular import errors
    SYNTAX = "syntax"                   # SyntaxError
    RUNTIME = "runtime"                 # General runtime errors
    INIT_MISSING = "init_missing"       # Initialization not done (empty db, etc.)
    LINTER = "linter"                   # Ruff, ESLint, etc.
    OTHER = "other"


def _classify_errors(errors: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Classify errors into categories with structured information.

    This is the framework layer - it provides generic error classification
    without hardcoding specific solutions.

    Args:
        errors: List of error messages.

    Returns:
        Dict mapping error category to list of structured error info.
    """
    import re

    classified: dict[str, list[dict[str, Any]]] = {
        ErrorCategory.TYPE_CHECK: [],
        ErrorCategory.IMPORT_MISSING: [],
        ErrorCategory.MODULE_NOT_FOUND: [],
        ErrorCategory.CIRCULAR_IMPORT: [],
        ErrorCategory.SYNTAX: [],
        ErrorCategory.RUNTIME: [],
        ErrorCategory.INIT_MISSING: [],
        ErrorCategory.LINTER: [],
        ErrorCategory.OTHER: [],
    }

    for error in errors:
        error_lower = error.lower()
        error_info: dict[str, Any] = {"raw": error}

        # Circular import (highest priority - blocks everything)
        if "circular import" in error_lower or "partially initialized module" in error_lower:
            # Extract module path
            match = re.search(r"\(([^)]+\.py)\)", error)
            if match:
                error_info["file"] = match.group(1)
            classified[ErrorCategory.CIRCULAR_IMPORT].append(error_info)

        # Type checking errors (mypy, pyright, tsc)
        elif any(x in error_lower for x in ["mypy", "type check", "pyright", "tsc"]) or \
             re.search(r"\[[\w-]+\]$", error):  # mypy error codes like [assignment]
            # Extract file:line:column pattern
            match = re.search(r"([^\s:]+):(\d+):?\d*:\s*error:", error)
            if match:
                error_info["file"] = match.group(1)
                error_info["line"] = int(match.group(2))
            # Extract error code
            code_match = re.search(r"\[([\w-]+)\]", error)
            if code_match:
                error_info["code"] = code_match.group(1)
            classified[ErrorCategory.TYPE_CHECK].append(error_info)

        # ImportError: cannot import name X from Y
        elif "cannot import name" in error_lower:
            # Extract symbol and package
            match = re.search(r"cannot import name ['\"]?(\w+)['\"]?\s+from\s+['\"]?([^'\"]+)['\"]?", error, re.I)
            if match:
                error_info["symbol"] = match.group(1)
                error_info["package"] = match.group(2)
            # Extract file path
            file_match = re.search(r"\(([^)]+\.py)\)", error)
            if file_match:
                error_info["file"] = file_match.group(1)
            classified[ErrorCategory.IMPORT_MISSING].append(error_info)

        # ModuleNotFoundError
        elif "modulenotfounderror" in error_lower or "no module named" in error_lower:
            match = re.search(r"[Nn]o module named ['\"]?([^'\"]+)['\"]?", error)
            if match:
                error_info["module"] = match.group(1)
            classified[ErrorCategory.MODULE_NOT_FOUND].append(error_info)

        # Syntax errors
        elif "syntaxerror" in error_lower or "unterminated string" in error_lower:
            match = re.search(r"([^\s:]+):(\d+)", error)
            if match:
                error_info["file"] = match.group(1)
                error_info["line"] = int(match.group(2))
            classified[ErrorCategory.SYNTAX].append(error_info)

        # Initialization missing (empty files, db not created)
        elif "empty file" in error_lower or "empty database" in error_lower:
            match = re.search(r"([^\s:]+):\s*[Ee]mpty", error)
            if match:
                error_info["file"] = match.group(1)
            classified[ErrorCategory.INIT_MISSING].append(error_info)

        # Linter errors (ruff, eslint, etc.)
        elif any(x in error_lower for x in ["ruff", "eslint", "flake8", "pylint"]):
            classified[ErrorCategory.LINTER].append(error_info)

        # Other errors
        else:
            classified[ErrorCategory.OTHER].append(error_info)

    return classified


def _find_symbol_definition(symbol: str, package: str, workspace_dir: Path) -> str | None:
    """Find where a symbol is actually defined in the codebase.

    This helps the agent understand where to fix the import issue.

    Args:
        symbol: The symbol name that couldn't be imported.
        package: The package path where import was attempted.
        workspace_dir: Workspace directory to search.

    Returns:
        The file path where the symbol is defined, or None if not found.
    """
    import re

    # Convert package path to directory
    # e.g., "app.models" -> "app/models" or "backend/app/models"
    package_parts = package.replace("'", "").replace('"', "").split(".")

    # Search patterns
    patterns = [
        rf"^class\s+{symbol}\s*[\(:]",  # class definition
        rf"^{symbol}\s*=",               # assignment
        rf"^def\s+{symbol}\s*\(",        # function definition
        rf"^{symbol}\s*:\s*\w+\s*=",     # typed assignment
    ]

    # Try to find in package directory
    for prefix in ["", "backend/", "src/"]:
        package_dir = workspace_dir / prefix / "/".join(package_parts)
        if package_dir.exists():
            for py_file in package_dir.glob("**/*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    for pattern in patterns:
                        if re.search(pattern, content, re.MULTILINE):
                            return str(py_file.relative_to(workspace_dir))
                except Exception:
                    continue

    return None


def _check_code_syntax_completeness(content: str, file_path: str) -> tuple[bool, str, str]:
    """Check if code has basic syntax completeness (unclosed quotes, brackets).

    This is a lightweight pre-validation to catch obvious LLM generation issues
    like truncated strings or unbalanced brackets before saving.

    Args:
        content: Code content to check.
        file_path: File path for context.

    Returns:
        Tuple of (is_complete, error_message, fixed_content).
        If is_complete is True, error_message is empty and fixed_content equals content.
        If is_complete is False but fixable, fixed_content contains the fix attempt.
    """
    if not content or not content.strip():
        return False, "Empty content", ""

    errors: list[str] = []
    fixed_content = content

    # Determine file type
    is_python = file_path.endswith(".py")
    is_js_ts = file_path.endswith((".js", ".jsx", ".ts", ".tsx", ".vue"))

    # Check for unclosed string literals (common LLM truncation issue)
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.lstrip()
        if is_python and stripped.startswith("#"):
            continue
        if is_js_ts and stripped.startswith("//"):
            continue

        # Count quotes (simplified check for obvious issues)
        # Check for lines ending with unclosed string pattern
        # e.g., pattern = r'^[1-9]...$ (missing closing quote)
        if is_python:
            # Check for r' or r" raw strings without closing
            if "r'" in line or 'r"' in line:
                # Count raw string quotes
                single_raw = line.count("r'")
                double_raw = line.count('r"')
                single_total = line.count("'") - single_raw
                double_total = line.count('"') - double_raw
                # Rough check: if line has odd quotes and ends without quote
                if (single_total + single_raw) % 2 != 0 and not line.rstrip().endswith("'"):
                    if "pattern" in line.lower() or "regex" in line.lower():
                        errors.append(f"Line {i}: Unclosed regex/pattern string")
                        # Try to fix by adding closing quote
                        fixed_line = line.rstrip() + "'"
                        fixed_content = fixed_content.replace(line, fixed_line)
                if (double_total + double_raw) % 2 != 0 and not line.rstrip().endswith('"'):
                    if "pattern" in line.lower() or "regex" in line.lower():
                        errors.append(f"Line {i}: Unclosed regex/pattern string")
                        fixed_line = line.rstrip() + '"'
                        fixed_content = fixed_content.replace(line, fixed_line)

    # Check bracket balance
    brackets = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []

    # Simple bracket balance check (ignoring strings for speed)
    for char in content:
        if char in brackets:
            stack.append(brackets[char])
        elif char in brackets.values():
            if stack and stack[-1] == char:
                stack.pop()

    if stack:
        # Unbalanced brackets - likely truncated code
        errors.append(f"Unbalanced brackets: missing {len(stack)} closing bracket(s)")

    if errors:
        return False, "; ".join(errors), fixed_content

    return True, "", content


def _detect_shared_error_files(
    global_error_files: dict[str, set[str]],
    threshold: int = 2,
) -> list[str]:
    """Detect files that cause errors in multiple requirements.

    These shared error files should be prioritized for fixing.

    Args:
        global_error_files: Dict mapping file path to set of requirement IDs
                           that encountered errors in that file.
        threshold: Minimum number of requirements affected to be considered shared.

    Returns:
        List of file paths that are shared error sources, sorted by impact.
    """
    shared_files: list[tuple[str, int]] = []

    for file_path, affected_reqs in global_error_files.items():
        if len(affected_reqs) >= threshold:
            shared_files.append((file_path, len(affected_reqs)))

    # Sort by number of affected requirements (descending)
    shared_files.sort(key=lambda x: x[1], reverse=True)

    return [f[0] for f in shared_files]


def _build_detailed_error_feedback(
    validation_errors: list[str],
    error_files: set[str],
    shared_error_files: list[str],
) -> str:
    """Build detailed error feedback for LLM with actionable information.

    Args:
        validation_errors: List of validation error messages.
        error_files: Set of files with errors.
        shared_error_files: List of shared error files (affecting multiple requirements).

    Returns:
        Formatted error feedback string.
    """
    parts: list[str] = []

    # Highlight shared error files that block multiple requirements
    if shared_error_files:
        shared_in_current = [f for f in shared_error_files if f in error_files]
        if shared_in_current:
            parts.append("【严重：共享文件错误 - 影响多个需求，必须优先修复】")
            for f in shared_in_current:
                parts.append(f"  ⚠️ {f}")
            parts.append("")

    # Group errors by file for clarity
    errors_by_file: dict[str, list[str]] = {}
    other_errors: list[str] = []

    for err in validation_errors:
        matched = False
        for fpath in error_files:
            if fpath in err:
                if fpath not in errors_by_file:
                    errors_by_file[fpath] = []
                errors_by_file[fpath].append(err)
                matched = True
                break
        if not matched:
            other_errors.append(err)

    # Format errors by file
    if errors_by_file:
        parts.append("【代码验证错误 - 按文件分组】")
        for fpath, errs in errors_by_file.items():
            is_shared = fpath in shared_error_files
            marker = "🔴" if is_shared else "❌"
            parts.append(f"{marker} {fpath}:")
            for e in errs[:5]:  # Limit per file
                parts.append(f"    - {e}")
        parts.append("")

    if other_errors:
        parts.append("【其他错误】")
        for e in other_errors[:5]:
            parts.append(f"  - {e}")

    return "\n".join(parts)


def _enrich_failed_criteria(
    criteria: list[dict[str, Any]],
    passed_ids: set[str],
    last_qa_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Enrich failed criteria with QA report's specific failure reasons.

    This function merges the original acceptance criteria with the detailed
    failure information from the QA report (reason, recommendation), so the
    LLM can understand exactly WHY each criterion failed and HOW to fix it.

    Args:
        criteria: Original acceptance criteria list
        passed_ids: Set of passed criteria IDs
        last_qa_report: Previous QA report with detailed failure info

    Returns:
        List of failed criteria enriched with reason/recommendation
    """
    # Build lookup map from QA report
    qa_results_map: dict[str, dict[str, Any]] = {}
    if last_qa_report:
        for item in last_qa_report.get("criteria", []):
            crit_id = item.get("id", "")
            if crit_id and not item.get("pass"):
                qa_results_map[crit_id] = item

    enriched: list[dict[str, Any]] = []
    for c in criteria:
        crit_id = c.get("id", "")
        if crit_id in passed_ids:
            continue

        # Start with original criterion
        enriched_crit = dict(c)

        # Merge QA failure details
        if crit_id in qa_results_map:
            qa_item = qa_results_map[crit_id]
            # Add failure reason from QA
            reason = qa_item.get("reason", "")
            if reason:
                enriched_crit["qa_failure_reason"] = reason
            # Add recommendation from QA
            recommendation = qa_item.get("recommendation", "")
            if recommendation:
                enriched_crit["recommendation"] = recommendation

        enriched.append(enriched_crit)

    return enriched


# ---------------------------------------------------------------------------
# Parallel Execution Support
# ---------------------------------------------------------------------------
from dataclasses import dataclass, field
from typing import Callable


def _analyze_requirement_dependencies(
    requirements: list[dict[str, Any]],
    architecture_contract: dict[str, Any] | None = None,
) -> dict[str, set[str]]:
    """Analyze dependencies between requirements.

    This function determines which requirements depend on others based on:
    1. Explicit dependencies in spec
    2. Shared file ownership from architecture contract
    3. API dependencies (backend must come before frontend that uses it)

    Args:
        requirements: List of requirement dicts
        architecture_contract: Optional architecture contract with file ownership

    Returns:
        Dict mapping requirement ID to set of dependency requirement IDs
    """
    dependencies: dict[str, set[str]] = {req["id"]: set() for req in requirements}

    # Extract file ownership from architecture contract
    file_ownership: dict[str, str] = {}
    if architecture_contract:
        file_ownership = architecture_contract.get("file_ownership", {})

    # Analyze each requirement
    for req in requirements:
        rid = req["id"]
        req_text = (req.get("description", "") + " " + req.get("title", "")).lower()

        # Check for explicit dependencies
        if req.get("depends_on"):
            deps = req["depends_on"]
            if isinstance(deps, str):
                deps = [deps]
            dependencies[rid].update(deps)

        # Heuristic: Backend requirements should complete before frontend
        # (if a frontend requirement references backend APIs)
        if any(kw in req_text for kw in ["前端", "frontend", "页面", "组件", "ui", "view"]):
            # This looks like a frontend requirement
            for other_req in requirements:
                other_rid = other_req["id"]
                if other_rid == rid:
                    continue
                other_text = (other_req.get("description", "") + " " + other_req.get("title", "")).lower()
                # Check if other requirement is backend-related
                if any(kw in other_text for kw in ["后端", "backend", "api", "接口", "数据库", "database"]):
                    # Frontend depends on backend
                    dependencies[rid].add(other_rid)

        # Check for shared file dependencies
        req_files = set()
        if req.get("files"):
            req_files = set(req["files"])

        for fpath, owner_rid in file_ownership.items():
            if owner_rid != rid and fpath in req_files:
                # This requirement uses a file owned by another requirement
                dependencies[rid].add(owner_rid)

    return dependencies


def _group_requirements_by_parallelism(
    requirements: list[dict[str, Any]],
    dependencies: dict[str, set[str]],
) -> list[list[dict[str, Any]]]:
    """Group requirements into batches that can be executed in parallel.

    Requirements in the same batch have no dependencies on each other.
    Batches are ordered so that dependencies are always satisfied.

    Args:
        requirements: List of requirement dicts
        dependencies: Dependency map from _analyze_requirement_dependencies

    Returns:
        List of batches, each batch is a list of requirements that can run in parallel
    """
    # Build reverse lookup
    req_map = {req["id"]: req for req in requirements}
    remaining = set(req_map.keys())
    completed: set[str] = set()
    batches: list[list[dict[str, Any]]] = []

    while remaining:
        # Find requirements whose dependencies are all completed
        ready = []
        for rid in remaining:
            deps = dependencies.get(rid, set())
            if deps <= completed:
                ready.append(rid)

        if not ready:
            # Circular dependency or missing dependency - break cycle
            # Just take the first remaining requirement
            ready = [next(iter(remaining))]

        # Create batch from ready requirements
        batch = [req_map[rid] for rid in ready]
        batches.append(batch)

        # Mark as completed
        completed.update(ready)
        remaining -= set(ready)

    return batches


def _should_parallelize_batch(
    batch: list[dict[str, Any]],
    round_idx: int,
    scaffold_initialized: dict[str, bool],
) -> bool:
    """Determine if a batch should be parallelized.

    Agent-level decision on whether to run in parallel based on:
    1. Batch size (single item = no parallelization needed)
    2. First round with scaffold not initialized (serialize to avoid conflicts)
    3. Resource constraints

    Args:
        batch: List of requirements in this batch
        round_idx: Current round index
        scaffold_initialized: Scaffold initialization state

    Returns:
        True if batch should be parallelized, False for sequential
    """
    # Single requirement - no need to parallelize
    if len(batch) <= 1:
        return False

    # First round and scaffold not initialized - serialize to avoid conflicts
    if round_idx == 1 and not all(scaffold_initialized.values()):
        return False

    # Default: parallelize if we have multiple requirements
    return True


@dataclass
class ParallelExecutionContext:
    """Context for parallel requirement execution.

    This class manages shared state and synchronization for parallel execution.
    All shared resources are protected by asyncio locks.
    """
    # Shared state (protected by locks)
    scaffold_initialized: dict[str, bool] = field(default_factory=lambda: {"frontend": False, "backend": False})
    installed_packages: dict[str, set[str]] = field(default_factory=lambda: {"frontend": set(), "backend": set()})
    global_error_files: dict[str, set[str]] = field(default_factory=dict)

    # Locks for shared state
    scaffold_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    packages_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    error_files_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    workspace_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # Execution control
    semaphore: asyncio.Semaphore | None = None
    max_concurrency: int = 4
    timeout: float = 300.0

    def __post_init__(self) -> None:
        """Initialize semaphore after dataclass init."""
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(self.max_concurrency)

    async def acquire_scaffold_state(self) -> dict[str, bool]:
        """Get current scaffold state (thread-safe)."""
        async with self.scaffold_lock:
            return dict(self.scaffold_initialized)

    async def update_scaffold_state(self, frontend: bool | None = None, backend: bool | None = None) -> None:
        """Update scaffold state (thread-safe)."""
        async with self.scaffold_lock:
            if frontend is not None:
                self.scaffold_initialized["frontend"] = frontend
            if backend is not None:
                self.scaffold_initialized["backend"] = backend

    async def add_installed_packages(self, frontend: set[str] | None = None, backend: set[str] | None = None) -> None:
        """Add installed packages (thread-safe)."""
        async with self.packages_lock:
            if frontend:
                self.installed_packages["frontend"].update(frontend)
            if backend:
                self.installed_packages["backend"].update(backend)

    async def track_error_files(self, rid: str, files: set[str]) -> None:
        """Track error files for a requirement (thread-safe)."""
        async with self.error_files_lock:
            self.global_error_files[rid] = files


@dataclass
class RequirementResult:
    """Result of processing a single requirement."""
    rid: str
    passed: bool
    pass_ratio: float
    blueprint: dict[str, Any] | None = None
    implementation: dict[str, Any] | None = None
    qa_report: dict[str, Any] | None = None
    validation_result: Any = None
    error: str | None = None
    state_updates: dict[str, Any] = field(default_factory=dict)


async def _process_requirement_parallel(
    rid: str,
    requirement: dict[str, Any],
    round_idx: int,
    ctx: ParallelExecutionContext,
    # Core dependencies
    llm: Any,
    spec: dict[str, Any],
    req_state: dict[str, dict[str, Any]],
    feedback_map: dict[str, str],
    # Workspace and runtime
    workspace_dir: Path | None,
    runtime_workspace: Any,
    use_runtime_mode: bool,
    use_agent_mode: bool,
    # Feature flags
    use_collaborative_agents: bool,
    use_edit_mode: bool,
    pr_mode_active: bool,
    skip_code_validation: bool,
    verbose: bool,
    # Context
    contextual_notes: str,
    skeleton_context: dict[str, Any] | None,
    architecture_contract: dict[str, Any],
    project_memory: Any,
    # Helpers
    criteria_for_requirement: Callable,
    get_memory_context: Callable,
    file_manager: Any = None,
    code_guard: Any = None,
    git_workspace: Any = None,
    playwright_mcp: Any = None,
    serve_url: str | None = None,
    http_server_available: bool = False,
    observer: Any = None,
) -> RequirementResult:
    """Process a single requirement (can be run in parallel).

    This function encapsulates all the logic for processing one requirement,
    including blueprint design, implementation, validation, and QA.

    Args:
        rid: Requirement ID
        requirement: Requirement dict
        round_idx: Current round index
        ctx: Parallel execution context with shared state
        ... other args for the execution

    Returns:
        RequirementResult with execution outcome
    """
    from ._spec import criteria_for_requirement as get_criteria, sanitize_filename
    from ._agent_roles import (
        design_requirement,
        implement_requirement,
        stepwise_generate_files,
        implement_requirement_autonomous,
        run_scaffold_commands,
        validate_blueprint_criteria_coverage,
        fix_blueprint_coverage,
        USE_CLAUDE_CODE,
        CLAUDE_CODE_MODE,
    )
    from ._file_editor import stepwise_edit_files
    from ._qa import qa_requirement, qa_requirement_pr, _normalize_qa_report
    from ._validation import layered_code_validation

    # Acquire semaphore to limit concurrency
    async with ctx.semaphore:
        try:
            is_first_requirement = (round_idx == 1 and rid == list(req_state.keys())[0])
            criteria = get_criteria(spec, rid)

            # Ensure criteria have IDs
            for idx, item in enumerate(criteria, 1):
                item.setdefault("id", f"{rid}.{idx}")

            state = req_state[rid]

            # Skip if fully passed
            if state["fully_passed"]:
                if observer:
                    observer.on_requirement_skip(rid, "已全部通过，沿用上一轮成果")
                last_qa = state.get("last_qa_report") or {"criteria": []}
                return RequirementResult(
                    rid=rid,
                    passed=True,
                    pass_ratio=1.0,
                    qa_report=last_qa,
                    state_updates={},
                )

            # Enrich failed criteria
            passed_ids = state["passed"]
            last_qa_report = state.get("last_qa_report")
            failed_criteria = _enrich_failed_criteria(criteria, passed_ids, last_qa_report)

            # PR Mode: Initialize working directory (needs lock for shared resources)
            if pr_mode_active and runtime_workspace:
                async with ctx.workspace_lock:
                    try:
                        await runtime_workspace.init_for_requirement(rid)
                    except Exception as e:
                        if observer:
                            observer.ctx.logger.warn(f"[PR Mode] [{rid}] 工作目录初始化失败: {e}")

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

            # Git branch (needs lock)
            if git_workspace:
                async with ctx.workspace_lock:
                    branch = git_workspace.create_branch(rid)
                    if observer:
                        observer.ctx.logger.debug(f"[Git] [{rid}] 切换到分支 {branch}")

            # Design blueprint
            if observer:
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
                skeleton_context=skeleton_context if skeleton_context and skeleton_context.get("skeleton_generated") else None,
                verbose=verbose,
            )

            # Inject spec-level tech_stack and project_type
            if "tech_stack" not in blueprint and spec.get("tech_stack"):
                blueprint["tech_stack"] = spec.get("tech_stack")
            if "project_type" not in blueprint and spec.get("project_type"):
                blueprint["project_type"] = spec.get("project_type")

            if observer:
                observer.on_phase_complete(rid, "blueprint", blueprint.get("deliverable_pitch", ""))

            # Validate Blueprint coverage
            if failed_criteria and blueprint.get("files_plan"):
                coverage_result = validate_blueprint_criteria_coverage(blueprint, failed_criteria)
                if not coverage_result["is_valid"]:
                    uncovered_ids = coverage_result["uncovered_ids"]
                    uncovered_criteria = [c for c in failed_criteria if c.get("id") in uncovered_ids]
                    blueprint = await fix_blueprint_coverage(llm, blueprint, uncovered_criteria, verbose=verbose)

            # Implementation
            if observer:
                observer.on_phase_start(rid, "implementation")

            generation_mode = blueprint.get("generation_mode", "single")
            files_plan = blueprint.get("files_plan", [])
            scaffold_config = blueprint.get("scaffold")

            # Scaffold mode (needs lock for shared state)
            if generation_mode == "scaffold" and scaffold_config and runtime_workspace:
                scaffold_state = await ctx.acquire_scaffold_state()
                async with ctx.workspace_lock:
                    scaffold_result = await run_scaffold_commands(
                        runtime_workspace=runtime_workspace,
                        scaffold_config=scaffold_config,
                        llm=llm,
                        scaffold_initialized=scaffold_state,
                        installed_packages=ctx.installed_packages,
                        verbose=verbose,
                    )
                    if scaffold_result["success"]:
                        # Update shared state
                        if scaffold_result.get("initialized", {}).get("frontend"):
                            await ctx.update_scaffold_state(frontend=True)
                        if scaffold_result.get("initialized", {}).get("backend"):
                            await ctx.update_scaffold_state(backend=True)
                        new_pkgs = scaffold_result.get("new_packages", {})
                        await ctx.add_installed_packages(
                            frontend=set(new_pkgs.get("frontend", [])),
                            backend=set(new_pkgs.get("backend", [])),
                        )
                    else:
                        generation_mode = "stepwise"

            # Generate implementation (simplified - actual implementation would need more)
            impl: dict[str, Any] = {}
            if use_collaborative_agents and workspace_dir:
                from ._agent_execution import execute_with_agent
                formatter = _get_formatter_for_model(llm)
                impl = await execute_with_agent(
                    llm=llm,
                    formatter=formatter,
                    requirement=requirement,
                    blueprint=blueprint,
                    workspace_dir=workspace_dir,
                    feedback=feedback_map[rid],
                    verbose=verbose,
                    runtime_workspace=runtime_workspace,
                    skeleton_context=skeleton_context if skeleton_context and skeleton_context.get("skeleton_generated") else None,
                    is_first_requirement=is_first_requirement,
                )
            elif generation_mode in ("stepwise", "scaffold") and files_plan:
                if use_edit_mode and file_manager:
                    impl = await stepwise_edit_files(
                        llm=llm,
                        requirement=requirement,
                        blueprint=blueprint,
                        file_manager=file_manager,
                        all_criteria=criteria,
                        failed_criteria=failed_criteria,
                        code_guard=code_guard,
                        verbose=verbose,
                    )
                else:
                    impl = await stepwise_generate_files(
                        llm=llm,
                        requirement=requirement,
                        blueprint=blueprint,
                        contextual_notes=full_context or None,
                        runtime_workspace=runtime_workspace if use_runtime_mode else None,
                        feedback=feedback_map[rid],
                        failed_criteria=failed_criteria,
                        previous_errors=state.get("validation_errors", []),
                        skeleton_context=skeleton_context if skeleton_context and skeleton_context.get("skeleton_generated") else None,
                        all_criteria=criteria,
                        workspace_dir=workspace_dir,
                        code_guard=code_guard,
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
                    skeleton_context=skeleton_context if skeleton_context and skeleton_context.get("skeleton_generated") else None,
                    verbose=verbose,
                )

            if observer:
                observer.on_implementation_summary(rid, impl.get("summary", ""))

            # Simplified QA (actual implementation would be more complex)
            if observer:
                observer.on_phase_start(rid, "qa")

            qa_report_raw = await qa_requirement(
                llm=llm,
                requirement=requirement,
                blueprint=blueprint,
                artifact_path=None,
                criteria=criteria,
                round_index=round_idx,
                workspace_files=None,
                playwright_mcp=playwright_mcp if http_server_available else None,
                http_url=serve_url if http_server_available else None,
                verbose=verbose,
                mandatory_files=[],
                runtime_workspace=runtime_workspace if use_runtime_mode else None,
                enable_runtime_validation=use_runtime_mode,
            )
            qa_report = _normalize_qa_report(qa_report_raw, criteria)

            # Calculate results
            crit = qa_report.get("criteria", [])
            passed_count = sum(1 for item in crit if item.get("pass"))
            total = max(len(crit), 1)
            pass_ratio = passed_count / total
            overall_passed = qa_report.get("overall_pass", passed_count == total)

            return RequirementResult(
                rid=rid,
                passed=overall_passed,
                pass_ratio=pass_ratio,
                blueprint=blueprint,
                implementation=impl,
                qa_report=qa_report,
                state_updates={
                    "blueprint": blueprint,
                    "summary": impl.get("summary", ""),
                    "last_qa_report": qa_report,
                    "passed": set(c.get("id") for c in crit if c.get("pass")),
                    "fully_passed": overall_passed,
                },
            )

        except Exception as e:
            import traceback
            error_msg = f"[{rid}] 处理失败: {e}\n{traceback.format_exc()}"
            if observer:
                observer.ctx.logger.error(error_msg)
            return RequirementResult(
                rid=rid,
                passed=False,
                pass_ratio=0.0,
                error=str(e),
            )


async def _execute_requirements_parallel(
    requirements: list[dict[str, Any]],
    round_idx: int,
    ctx: ParallelExecutionContext,
    **kwargs: Any,
) -> list[RequirementResult]:
    """Execute multiple requirements in parallel.

    Args:
        requirements: List of requirement dicts
        round_idx: Current round index
        ctx: Parallel execution context
        **kwargs: Additional arguments passed to _process_requirement_parallel

    Returns:
        List of RequirementResult for each requirement
    """
    tasks = []
    for requirement in requirements:
        rid = requirement["id"]
        task = asyncio.create_task(
            _process_requirement_parallel(
                rid=rid,
                requirement=requirement,
                round_idx=round_idx,
                ctx=ctx,
                **kwargs,
            )
        )
        tasks.append(task)

    # Wait for all tasks with timeout
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=ctx.timeout * len(requirements),  # Scale timeout with number of requirements
        )
    except asyncio.TimeoutError:
        # Cancel remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        # Collect completed results
        results = []
        for task in tasks:
            try:
                if task.done() and not task.cancelled():
                    results.append(task.result())
                else:
                    results.append(RequirementResult(
                        rid="unknown",
                        passed=False,
                        pass_ratio=0.0,
                        error="Timeout",
                    ))
            except Exception as e:
                results.append(RequirementResult(
                    rid="unknown",
                    passed=False,
                    pass_ratio=0.0,
                    error=str(e),
                ))

    # Convert exceptions to RequirementResult
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            rid = requirements[i]["id"] if i < len(requirements) else "unknown"
            final_results.append(RequirementResult(
                rid=rid,
                passed=False,
                pass_ratio=0.0,
                error=str(result),
            ))
        else:
            final_results.append(result)

    return final_results


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
    runtime_workspace: "RuntimeWorkspace | RuntimeWorkspaceWithPR | None" = None,
    skip_code_validation: bool = False,
    use_collaborative_agents: bool = False,
    use_parallel_execution: bool = False,
    parallel_timeout: float = 300.0,
    require_runtime: bool = True,
    use_edit_mode: bool = False,
    use_git_isolation: bool = True,
    use_pr_mode: bool = False,
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
        use_edit_mode: Whether to use Claude Code style edit mode (read-before-write,
            incremental edits instead of full file rewrites)
        use_git_isolation: Whether to use Git for branch isolation per requirement.
            Each requirement gets its own branch, changes are validated before commit,
            and branches are merged at the end. This prevents file conflicts and
            enables easy rollback. Default: True
        use_pr_mode: Whether to use PR (Pull Request) mode for requirement isolation.
            In PR mode, each requirement works in a separate working/ directory,
            changes are reviewed via diff before merging to delivery/ directory.
            This prevents requirement regression. Default: False

    Returns:
        dict: Execution results containing:
            - rounds: List of round results with per-requirement status
            - deliverables: Dict mapping requirement IDs to output paths
            - finalization: Project finalization report
            - final_regression: Final regression check results with:
                - checked: Number of requirements checked
                - regressed: List of requirement IDs that regressed
                - regressed_count: Number of regressed requirements
                - still_valid: List of requirement IDs still valid
            - execution_summary: Overall execution summary with:
                - total_requirements: Total number of requirements
                - passed_count: Number of passed requirements
                - failed_count: Number of failed requirements
                - all_passed: Whether all requirements passed (bool)
                - total_rounds: Number of rounds executed
                - regressed_in_final_check: Requirements that regressed in final check

        Note: If execution_summary.all_passed is False due to final regression,
        caller may re-run execution to fix regressed requirements.
    """
    from ._spec import criteria_for_requirement, sanitize_filename
    from ._architecture import generate_architecture_contract, format_architecture_contract
    from ._agent_roles import (
        design_requirement,
        implement_requirement,
        stepwise_generate_files,
        implement_requirement_autonomous,
        run_scaffold_commands,
        USE_CLAUDE_CODE,
        CLAUDE_CODE_MODE,
    )
    from ._file_editor import FileStateManager, stepwise_edit_files
    from ._qa import qa_requirement, qa_requirement_pr, _normalize_qa_report
    from ._validation import layered_code_validation, CodeValidationResult
    from ._debug import analyze_finalization_errors
    from ._sandbox import SimpleHTTPServer, BrowserSandboxManager
    from ._project_scaffolding import (
        generate_project_scaffolding,
        finalize_project,
        initialize_project_memory,
    )
    from ._observability import get_execution_observer
    from agentscope.ones.code_guard import CodeGuardManager, CodeGuardConfig

    # Initialize observer
    observer = get_execution_observer()

    # Debug: Log entry point with key parameters
    observer.ctx.logger.debug(
        f"[Execution] run_execution 开始: "
        f"use_parallel_execution={use_parallel_execution}, "
        f"parallel_timeout={parallel_timeout}, "
        f"max_rounds={max_rounds}, "
        f"requirements_count={len(spec.get('requirements', []))}"
    )

    # Log parallel execution mode status
    if use_parallel_execution:
        observer.ctx.logger.info(
            f"[Parallel] 并行执行模式已启用 (timeout={parallel_timeout}s)"
        )
        observer.ctx.logger.info(
            "[Parallel] 注意: CLI 层面的完整并行实现正在开发中。"
            "核心 ExecutionLoop 已支持并行模式。"
        )

    requirements = spec.get("requirements", [])
    overall_target = spec.get("acceptance", {}).get("overall_target", 0.85)

    # State tracking
    feedback_map = {req["id"]: "" for req in requirements}
    req_state = {
        req["id"]: {
            "passed": set(),
            "fully_passed": False,  # Whether requirement fully passed (QA + code validation)
            "code_validation_passed": False,  # Whether code validation passed
            "last_qa_report": None,  # Store last QA report for skipped requirements
            "artifact": "",
            "summary": "",
            "feedback": "",
            "validation_errors": [],  # Track previous validation errors
            "validation_error_files": set(),  # Track files with validation errors
            "validated_files": set(),  # Track files that passed validation
            "modified_files": set(),  # Track files modified by this requirement
            "last_validation_score": 0.0,  # Track last validation score for regression
            "blueprint": None,
            "path": None,
            "accumulated_files": {},  # Accumulate files across rounds for complete deliverable
            "must_fix_files": set(),  # Files that MUST be regenerated next round (syntax errors etc)
        }
        for req in requirements
    }

    # Track which files are shared across requirements (for regression detection)
    file_to_requirements: dict[str, set[str]] = {}

    # Track files that cause errors across multiple requirements (shared error sources)
    # Key: file path, Value: set of requirement IDs that had errors in this file
    global_error_files: dict[str, set[str]] = {}

    # Track scaffold initialization to avoid re-running project creation commands
    # Key: scaffold type (e.g., "frontend", "backend"), Value: True if project created
    scaffold_initialized: dict[str, bool] = {}
    # Track installed packages to enable incremental dependency installation
    # Key: scaffold type, Value: set of installed package names
    installed_packages: dict[str, set[str]] = {"frontend": set(), "backend": set()}

    def _track_modified_files(rid: str, files: list[str]) -> None:
        """Track files modified by a requirement for regression detection.

        Args:
            rid: Requirement ID
            files: List of file paths modified
        """
        state = req_state.get(rid)
        if not state:
            return

        for fpath in files:
            # Normalize path
            normalized = fpath.lstrip("./")
            state["modified_files"].add(normalized)

            # Update file->requirements mapping
            if normalized not in file_to_requirements:
                file_to_requirements[normalized] = set()
            file_to_requirements[normalized].add(rid)

    def _get_affected_requirements(rid: str, modified_files: set[str]) -> set[str]:
        """Find requirements that might be affected by modified files.

        Args:
            rid: Current requirement ID (to exclude)
            modified_files: Files modified in this round

        Returns:
            Set of requirement IDs that may need regression check
        """
        affected: set[str] = set()
        for fpath in modified_files:
            normalized = fpath.lstrip("./")
            if normalized in file_to_requirements:
                affected.update(file_to_requirements[normalized])
        # Exclude current requirement
        affected.discard(rid)
        return affected

    async def _perform_regression_check(
        affected_rids: set[str],
        workspace_dir: Path,
        round_idx: int,
    ) -> dict[str, bool]:
        """Perform regression validation on affected requirements.

        Args:
            affected_rids: Requirement IDs to check
            workspace_dir: Workspace directory
            round_idx: Current round index

        Returns:
            Dict mapping requirement ID to regression pass status
        """
        regression_results: dict[str, bool] = {}

        for rid in affected_rids:
            state = req_state.get(rid)
            if not state:
                continue

            # Only check requirements that fully passed (both QA and code validation)
            if not state.get("fully_passed"):
                continue

            observer.on_regression_check_start(rid)

            # Read current workspace files for validation
            synced_files: dict[str, str] = {}
            skipped_files: list[str] = []
            for fpath in workspace_dir.rglob("*"):
                if fpath.is_file() and not fpath.name.startswith("."):
                    try:
                        rel_path = str(fpath.relative_to(workspace_dir))
                        if "node_modules" not in rel_path and "__pycache__" not in rel_path:
                            synced_files[rel_path] = fpath.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        # Binary file, skip silently
                        pass
                    except Exception as e:
                        skipped_files.append(f"{fpath}: {e}")
            if skipped_files and verbose:
                observer.ctx.logger.debug(f"[REGRESSION] 跳过 {len(skipped_files)} 个无法读取的文件")

            if not synced_files:
                regression_results[rid] = True
                continue

            # Get requirement info
            req_info = next((r for r in requirements if r["id"] == rid), None)
            if not req_info:
                regression_results[rid] = True
                continue

            # Run code validation
            req_summary = req_info.get("summary", req_info.get("description", ""))[:200]
            tech_stack_info = project_memory.get_tech_stack_info() if project_memory else ""

            validation_result = await layered_code_validation(
                runtime_workspace=runtime_workspace if use_runtime_mode else None,
                llm=llm,
                files=synced_files,
                requirement_summary=req_summary,
                tech_stack_info=tech_stack_info,
                verbose=verbose,
            )

            # Check if regression occurred
            prev_score = state.get("last_validation_score", 1.0)
            current_score = validation_result.score
            # Use same criteria as main pass logic: only check is_valid, no score threshold
            is_valid = validation_result.is_valid

            # Regression = previously valid but now invalid, or significant score drop (>20%)
            score_drop = prev_score - current_score
            has_regression = not is_valid or (prev_score > 0 and score_drop > 0.2)

            if has_regression:
                observer.on_regression_detected(rid, prev_score, current_score)
                # Clear passed status to force re-implementation
                state["passed"] = set()
                state["fully_passed"] = False  # Reset fully_passed flag
                state["code_validation_passed"] = False
                state["validation_errors"] = validation_result.errors[:15]
                state["feedback"] = f"回归检测: 代码修改导致验证分数从 {prev_score:.2f} 降至 {current_score:.2f}"
                feedback_map[rid] = state["feedback"]
                regression_results[rid] = False
            else:
                observer.on_regression_check_pass(rid, current_score)
                # Update validation score
                state["last_validation_score"] = current_score
                regression_results[rid] = True

        return regression_results

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

    # PR mode check: requires RuntimeWorkspaceWithPR
    pr_mode_active = False
    if use_pr_mode and use_runtime_mode:
        from ._runtime_workspace import RuntimeWorkspaceWithPR
        if isinstance(runtime_workspace, RuntimeWorkspaceWithPR):
            pr_mode_active = runtime_workspace.enable_pr_mode
            if pr_mode_active and verbose:
                observer.ctx.logger.info("[PR Mode] 双目录隔离模式已启用")
        elif verbose:
            observer.ctx.logger.warn(
                "[PR Mode] use_pr_mode=True 但 runtime_workspace 不是 RuntimeWorkspaceWithPR 实例"
            )

    # Multi-tenant mode: require RuntimeWorkspace for all file operations
    if require_runtime and not use_runtime_mode:
        raise RuntimeError(
            "RuntimeWorkspace is required but not available. "
            "Multi-tenant mode requires all file operations to run in containers. "
            "Please ensure Docker is running and RuntimeWorkspace is properly initialized."
        )

    # Agent mode: enabled when we have workspace_dir OR runtime_workspace
    # (container isolation mode uses runtime_workspace instead of workspace_dir)
    use_agent_mode = workspace_dir is not None or use_runtime_mode

    # File state manager for edit mode (Claude Code style)
    file_manager: FileStateManager | None = None
    if use_edit_mode and workspace_dir:
        file_manager = FileStateManager(workspace_dir)
        if verbose:
            observer.ctx.logger.info("[Edit Mode] FileStateManager 已初始化")

    # CodeGuard for anti-hallucination validation (always enabled)
    # Create FileRegistry for import validation
    from agentscope.ones.file_tracking import FileRegistry
    file_registry = FileRegistry()
    # Pre-populate with workspace files if available
    if workspace_dir:
        for fpath in workspace_dir.rglob("*"):
            if fpath.is_file() and fpath.suffix in (".py", ".ts", ".tsx", ".js", ".jsx", ".vue"):
                try:
                    rel_path = str(fpath.relative_to(workspace_dir))
                    content = fpath.read_text(encoding="utf-8")
                    file_registry.register(rel_path, content)
                except Exception:
                    pass

    code_guard_config = CodeGuardConfig(
        block_unread_writes=False,  # Don't block, just warn (FileEditor already reads)
        warn_unknown_calls=True,    # Warn about unknown function calls
        check_syntax=True,          # Check bracket balance etc.
        import_guard_enabled=True,  # Enable import validation
    )
    code_guard = CodeGuardManager(code_guard_config, file_registry=file_registry)
    if verbose:
        observer.ctx.logger.info("[CodeGuard] 防幻觉验证已启用 (含导入验证)")

    # HTTP server for Playwright
    http_server: SimpleHTTPServer | None = None
    http_port: int | None = None
    serve_url: str | None = None
    http_server_available: bool = False

    # In runtime mode, start HTTP server inside container
    if use_runtime_mode and playwright_mcp:
        if runtime_workspace.start_http_server():
            serve_url = runtime_workspace.http_url
            http_server_available = True
            observer.ctx.logger.info(f"[HTTP] Container HTTP server: {serve_url}")
        else:
            observer.ctx.logger.warn("[HTTP] Failed to start container HTTP server")

    # Enable playwright_mcp if HTTP server is available
    effective_playwright_mcp = playwright_mcp if http_server_available else None

    # Generate project scaffolding files and initialize project memory
    from agentscope.ones.memory import ProjectMemory
    project_memory: ProjectMemory | None = None

    # Prepare scaffold files info for Agent (no pre-write, Agent will create them)
    scaffold_files_plan: list[dict[str, Any]] = []
    if workspace_dir and len(requirements) > 1:
        from ._project_scaffolding import get_scaffold_files_plan
        observer.on_scaffolding_start()

        # Get scaffold files plan - Agent will create these files in container
        scaffold_files_plan = get_scaffold_files_plan(project_type="fullstack")
        observer.ctx.logger.info(f"[Scaffold] 准备 {len(scaffold_files_plan)} 个基础文件（由 Agent 创建）")

        # Mark scaffold as needing initialization (Agent will handle this)
        has_frontend = any(sf["path"].startswith("frontend/") for sf in scaffold_files_plan)
        has_backend = any(sf["path"].startswith("backend/") for sf in scaffold_files_plan)

        # Don't pre-initialize - let Agent run npm create vite if needed
        # The Agent will set up the project structure properly
        if has_frontend:
            observer.ctx.logger.debug("[Scaffold] 前端文件将由 Agent 创建")
        if has_backend:
            observer.ctx.logger.debug("[Scaffold] 后端文件将由 Agent 创建")

        observer.on_scaffolding_complete(0, [sf["path"] for sf in scaffold_files_plan])

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

    # Generate unified code skeleton for shared modules
    # Include scaffold files for Agent to create
    skeleton_context: dict[str, Any] = {
        "file_ownership": {},
        "shared_files": [],
        "skeleton_generated": False,
        "scaffold_files": scaffold_files_plan,  # Pass scaffold files for Agent to create
    }
    if workspace_dir and len(requirements) > 1:
        from ._agent_roles import generate_unified_skeleton

        observer.on_skeleton_start()
        skeleton_result = await generate_unified_skeleton(
            llm,
            requirements,
            workspace_dir,
            architecture_contract=architecture_contract,
            runtime_workspace=runtime_workspace if use_runtime_mode else None,
            verbose=verbose,
        )
        if skeleton_result.get("skeleton_files"):
            skeleton_context["file_ownership"] = skeleton_result.get("file_ownership", {})
            skeleton_context["shared_files"] = skeleton_result.get("shared_files", [])
            skeleton_context["skeleton_generated"] = True
            observer.on_skeleton_complete(
                len(skeleton_result.get("skeleton_files", [])),
                len(skeleton_result.get("shared_files", [])),
            )

    # Fix permissions for all workspace files after scaffolding/skeleton generation
    # This ensures Claude Code (running as node user) can modify files created by root
    if runtime_workspace and use_runtime_mode:
        try:
            runtime_workspace.execute_command(
                "chown -R node:node /workspace 2>/dev/null || true",
                timeout=30,
            )
        except Exception:
            pass  # Ignore permission fix errors

    # Initialize Git workspace for branch isolation
    from ._git_workspace import GitWorkspace
    git_workspace: GitWorkspace | None = None

    if use_git_isolation and workspace_dir:
        git_workspace = GitWorkspace(workspace_dir)
        if git_workspace.init():
            observer.ctx.logger.info("[Git] 初始化 Git 仓库成功 (scaffolding 已提交)")
        else:
            observer.ctx.logger.warn("[Git] Git 初始化失败，禁用分支隔离")
            git_workspace = None

    # Helper to get current project memory context for prompts
    def get_memory_context() -> str:
        """Get project memory context to prepend to contextual notes."""
        if project_memory:
            memory_ctx = project_memory.get_context_for_prompt(include_instructions=False)
            if memory_ctx:
                return memory_ctx
        return ""

    # Initialize delivery directory for PR mode (before processing any requirements)
    if pr_mode_active and runtime_workspace:
        observer.ctx.logger.info("[PR Mode] 初始化 delivery 目录...")
        # Copy scaffold content to delivery directory if it doesn't exist
        init_result = await runtime_workspace.exec(
            f"if [ ! -d {runtime_workspace.delivery_dir} ] || [ -z \"$(ls -A {runtime_workspace.delivery_dir} 2>/dev/null)\" ]; then "
            f"mkdir -p {runtime_workspace.delivery_dir} && "
            f"rsync -a /workspace/ {runtime_workspace.delivery_dir}/ "
            f"--exclude=delivery --exclude=working 2>/dev/null || true; "
            f"fi"
        )
        if verbose:
            observer.ctx.logger.debug(f"[PR Mode] delivery 目录初始化: {init_result.get('success', False)}")

    # Main execution loop
    observer.on_execution_start(len(requirements), max_rounds)

    # Initialize parallel execution context if enabled
    parallel_ctx: ParallelExecutionContext | None = None
    if use_parallel_execution:
        import os
        # Determine max concurrency (default: min of CPU count and requirement count)
        max_concurrency = min(
            os.cpu_count() or 4,
            len(requirements),
            4,  # Cap at 4 to avoid overwhelming resources
        )
        parallel_ctx = ParallelExecutionContext(
            scaffold_initialized=dict(scaffold_initialized),
            installed_packages={k: set(v) for k, v in installed_packages.items()},
            global_error_files=dict(global_error_files),
            max_concurrency=max_concurrency,
            timeout=parallel_timeout,
        )
        observer.ctx.logger.info(
            f"[Parallel] 并行执行上下文已初始化 (并发数: {max_concurrency}, 超时: {parallel_timeout}s)"
        )

    for round_idx in range(1, max_rounds + 1):
        # Count pending requirements for this round
        # Use fully_passed flag instead of just checking QA criteria
        pending_count = sum(1 for req in requirements
                          if not req_state[req["id"]]["fully_passed"])
        observer.on_round_start(round_idx, pending_count)

        # Detect and log shared error files at round start
        if round_idx > 1:
            shared_error_files = _detect_shared_error_files(global_error_files, threshold=2)
            if shared_error_files:
                observer.ctx.logger.info(
                    f"[Round {round_idx}] 检测到 {len(shared_error_files)} 个共享错误文件 "
                    f"(影响多个需求): {shared_error_files[:5]}"
                )
                if len(shared_error_files) > 5:
                    observer.ctx.logger.info(f"  ... 及其他 {len(shared_error_files) - 5} 个文件")

        round_entry = {"round": round_idx, "results": []}
        requirement_pass_flags: list[bool] = []

        # Smart parallel execution mode
        if use_parallel_execution and parallel_ctx is not None:
            # Analyze dependencies and group requirements into batches
            dependencies = _analyze_requirement_dependencies(requirements, architecture_contract)
            batches = _group_requirements_by_parallelism(requirements, dependencies)

            # Log dependency analysis
            dep_count = sum(len(deps) for deps in dependencies.values())
            observer.ctx.logger.info(
                f"[Parallel] Round {round_idx}: 分析完成 - {len(batches)} 批次, "
                f"{dep_count} 个依赖关系"
            )

            all_parallel_results: list[RequirementResult] = []

            # Process each batch
            for batch_idx, batch in enumerate(batches, 1):
                # Filter to only pending requirements in this batch
                pending_batch = [
                    req for req in batch
                    if not req_state[req["id"]]["fully_passed"]
                ]

                if not pending_batch:
                    observer.ctx.logger.debug(
                        f"[Parallel] 批次 {batch_idx}/{len(batches)}: 所有需求已完成，跳过"
                    )
                    continue

                # Decide whether to parallelize this batch
                should_parallel = _should_parallelize_batch(
                    pending_batch,
                    round_idx,
                    parallel_ctx.scaffold_initialized,
                )

                batch_rids = [req["id"] for req in pending_batch]
                if should_parallel:
                    observer.ctx.logger.info(
                        f"[Parallel] 批次 {batch_idx}/{len(batches)}: "
                        f"并行处理 {len(pending_batch)} 个需求 {batch_rids}"
                    )
                    # Execute batch in parallel
                    batch_results = await _execute_requirements_parallel(
                        requirements=pending_batch,
                        round_idx=round_idx,
                        ctx=parallel_ctx,
                        llm=llm,
                        spec=spec,
                        req_state=req_state,
                        feedback_map=feedback_map,
                        workspace_dir=workspace_dir,
                        runtime_workspace=runtime_workspace,
                        use_runtime_mode=use_runtime_mode,
                        use_agent_mode=use_agent_mode,
                        use_collaborative_agents=use_collaborative_agents,
                        use_edit_mode=use_edit_mode,
                        pr_mode_active=pr_mode_active,
                        skip_code_validation=skip_code_validation,
                        verbose=verbose,
                        contextual_notes=contextual_notes,
                        skeleton_context=skeleton_context if skeleton_context.get("skeleton_generated") else None,
                        architecture_contract=architecture_contract,
                        project_memory=project_memory,
                        criteria_for_requirement=criteria_for_requirement,
                        get_memory_context=get_memory_context,
                        file_manager=file_manager,
                        code_guard=code_guard,
                        git_workspace=git_workspace,
                        playwright_mcp=effective_playwright_mcp,
                        serve_url=serve_url,
                        http_server_available=http_server_available,
                        observer=observer,
                    )
                else:
                    observer.ctx.logger.info(
                        f"[Parallel] 批次 {batch_idx}/{len(batches)}: "
                        f"串行处理 {len(pending_batch)} 个需求 {batch_rids}"
                    )
                    # Execute batch sequentially (one at a time)
                    batch_results = []
                    for req in pending_batch:
                        result = await _process_requirement_parallel(
                            rid=req["id"],
                            requirement=req,
                            round_idx=round_idx,
                            ctx=parallel_ctx,
                            llm=llm,
                            spec=spec,
                            req_state=req_state,
                            feedback_map=feedback_map,
                            workspace_dir=workspace_dir,
                            runtime_workspace=runtime_workspace,
                            use_runtime_mode=use_runtime_mode,
                            use_agent_mode=use_agent_mode,
                            use_collaborative_agents=use_collaborative_agents,
                            use_edit_mode=use_edit_mode,
                            pr_mode_active=pr_mode_active,
                            skip_code_validation=skip_code_validation,
                            verbose=verbose,
                            contextual_notes=contextual_notes,
                            skeleton_context=skeleton_context if skeleton_context.get("skeleton_generated") else None,
                            architecture_contract=architecture_contract,
                            project_memory=project_memory,
                            criteria_for_requirement=criteria_for_requirement,
                            get_memory_context=get_memory_context,
                            file_manager=file_manager,
                            code_guard=code_guard,
                            git_workspace=git_workspace,
                            playwright_mcp=effective_playwright_mcp,
                            serve_url=serve_url,
                            http_server_available=http_server_available,
                            observer=observer,
                        )
                        batch_results.append(result)

                all_parallel_results.extend(batch_results)

            # Process all results
            for result in all_parallel_results:
                rid = result.rid
                requirement = next((r for r in requirements if r["id"] == rid), None)
                if not requirement:
                    continue

                # Update state from result
                state = req_state[rid]
                if result.state_updates:
                    state.update(result.state_updates)

                # Record result
                requirement_pass_flags.append(result.passed)
                qa_report = result.qa_report or {"criteria": []}
                round_entry["results"].append({
                    "requirement_id": rid,
                    "blueprint": result.blueprint,
                    "implementation": {"summary": result.implementation.get("summary", "") if result.implementation else ""},
                    "qa": qa_report,
                    "pass_ratio": result.pass_ratio,
                    "overall_passed": result.passed,
                    "error": result.error,
                })

                if result.error:
                    observer.ctx.logger.warn(f"[Parallel] [{rid}] 处理失败: {result.error}")
                else:
                    status = "✓" if result.passed else "✗"
                    observer.ctx.logger.info(f"[Parallel] [{rid}] {status} 通过率: {result.pass_ratio:.0%}")

            # Sync shared state back from parallel context
            scaffold_initialized.update(parallel_ctx.scaffold_initialized)
            for k, v in parallel_ctx.installed_packages.items():
                installed_packages[k].update(v)
            global_error_files.update(parallel_ctx.global_error_files)

            # Skip sequential processing
            rounds.append(round_entry)

            # Early exit check
            passed_count = sum(requirement_pass_flags)
            if passed_count == len(requirements):
                observer.on_round_end(round_idx, passed_count, len(requirements))
                break

            observer.on_round_end(round_idx, passed_count, len(requirements))
            continue

        # Sequential execution mode (original logic)
        observer.ctx.logger.debug(
            f"[Execution] 使用串行执行模式 (use_parallel_execution={use_parallel_execution}, "
            f"parallel_ctx={parallel_ctx is not None})"
        )
        for req_idx, requirement in enumerate(requirements):
            rid = requirement["id"]
            # First requirement in first round should create skeleton files
            is_first_requirement = (round_idx == 1 and req_idx == 0)
            criteria = criteria_for_requirement(spec, rid)

            # Ensure criteria have IDs
            for idx, item in enumerate(criteria, 1):
                item.setdefault("id", f"{rid}.{idx}")

            state = req_state[rid]

            # Skip only if fully passed (both QA and code validation)
            # This ensures requirements with QA pass but code validation fail are retried
            if state["fully_passed"]:
                observer.on_requirement_skip(rid, "已全部通过，沿用上一轮成果")
                requirement_pass_flags.append(True)
                # Use stored QA report instead of empty criteria
                last_qa = state.get("last_qa_report") or {"criteria": []}
                last_pass_ratio = len([c for c in last_qa.get("criteria", []) if c.get("pass")]) / max(len(last_qa.get("criteria", [])), 1)
                round_entry["results"].append({
                    "requirement_id": rid,
                    "blueprint": state.get("blueprint"),
                    "implementation": {"summary": state.get("summary", ""), "path": str(state.get("path") or "")},
                    "qa": last_qa,
                    "pass_ratio": last_pass_ratio if last_qa.get("criteria") else 1.0,
                    "code_validation_score": state.get("last_validation_score"),
                    "overall_passed": True,
                })
                final_paths[rid] = state.get("path") or final_paths.get(rid)
                continue

            # Check which QA criteria still need work
            # Enrich failed criteria with specific failure reasons from QA report
            passed_ids = state["passed"]
            last_qa_report = state.get("last_qa_report")
            failed_criteria = _enrich_failed_criteria(criteria, passed_ids, last_qa_report)

            # PR Mode: Initialize working directory for this requirement
            if pr_mode_active and runtime_workspace:
                try:
                    await runtime_workspace.init_for_requirement(rid)
                    if verbose:
                        observer.ctx.logger.debug(f"[PR Mode] [{rid}] 工作目录已初始化")
                except Exception as e:
                    observer.ctx.logger.warn(f"[PR Mode] [{rid}] 工作目录初始化失败: {e}")

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

            # Create Git branch for this requirement (if enabled)
            if git_workspace:
                branch = git_workspace.create_branch(rid)
                observer.ctx.logger.debug(f"[Git] 切换到分支 {branch}")

            # Design blueprint
            observer.on_requirement_start(rid, requirement.get("title", ""))
            observer.on_phase_start(rid, "blueprint")
            # NOTE: Scaffold files are now pre-written BEFORE skeleton generation
            # (see scaffold pre-write logic earlier in this function)
            blueprint = await design_requirement(
                llm,
                requirement,
                feedback_map[rid],
                passed_ids,
                failed_criteria,
                state.get("blueprint"),
                contextual_notes=full_context or None,
                existing_workspace_files=existing_files,
                skeleton_context=skeleton_context if skeleton_context.get("skeleton_generated") else None,
                verbose=verbose,
            )
            # Inject spec-level tech_stack and project_type into blueprint for QA runtime validation
            if "tech_stack" not in blueprint and spec.get("tech_stack"):
                blueprint["tech_stack"] = spec.get("tech_stack")
            if "project_type" not in blueprint and spec.get("project_type"):
                blueprint["project_type"] = spec.get("project_type")
            observer.on_phase_complete(rid, "blueprint", blueprint.get("deliverable_pitch", ""))

            # Validate Blueprint covers all failed criteria
            if failed_criteria and blueprint.get("files_plan"):
                from ._agent_roles import validate_blueprint_criteria_coverage, fix_blueprint_coverage

                coverage_result = validate_blueprint_criteria_coverage(blueprint, failed_criteria)
                if not coverage_result["is_valid"]:
                    uncovered_ids = coverage_result["uncovered_ids"]
                    if verbose:
                        observer.ctx.logger.warn(
                            f"[{rid}] Blueprint 未覆盖 {len(uncovered_ids)} 个验收标准: {uncovered_ids}"
                        )
                    # Find uncovered criteria objects
                    uncovered_criteria = [
                        c for c in failed_criteria if c.get("id") in uncovered_ids
                    ]
                    # Fix Blueprint
                    blueprint = await fix_blueprint_coverage(
                        llm, blueprint, uncovered_criteria, verbose=verbose
                    )
                    if verbose:
                        observer.ctx.logger.info(f"[{rid}] Blueprint 已修复，重新验证覆盖率...")
                    # Re-validate
                    new_coverage = validate_blueprint_criteria_coverage(blueprint, failed_criteria)
                    if not new_coverage["is_valid"]:
                        observer.ctx.logger.warn(
                            f"[{rid}] Blueprint 修复后仍有未覆盖标准: {new_coverage['uncovered_ids']}"
                        )

            # Implementation
            observer.on_phase_start(rid, "implementation")

            generation_mode = blueprint.get("generation_mode", "single")
            files_plan = blueprint.get("files_plan", [])
            scaffold_config = blueprint.get("scaffold")

            # Scaffold mode - incremental package installation support
            if generation_mode == "scaffold" and scaffold_config and runtime_workspace:
                observer.on_scaffold_mode_start(rid)
                scaffold_result = await run_scaffold_commands(
                    runtime_workspace=runtime_workspace,
                    scaffold_config=scaffold_config,
                    llm=llm,
                    scaffold_initialized=scaffold_initialized,
                    installed_packages=installed_packages,
                    verbose=verbose,
                )
                if not scaffold_result["success"]:
                    observer.on_scaffold_mode_fallback(rid)
                    generation_mode = "stepwise"
                else:
                    # Update tracking state from result
                    if scaffold_result.get("initialized", {}).get("frontend"):
                        scaffold_initialized["frontend"] = True
                    if scaffold_result.get("initialized", {}).get("backend"):
                        scaffold_initialized["backend"] = True

                    # Track newly installed packages
                    new_pkgs = scaffold_result.get("new_packages", {})
                    if new_pkgs.get("frontend"):
                        installed_packages["frontend"].update(new_pkgs["frontend"])
                    if new_pkgs.get("backend"):
                        installed_packages["backend"].update(new_pkgs["backend"])

                    # Files stay in container, no sync to local
                    if workspace_dir:
                        source_files = runtime_workspace.list_files()
                        source_files = [f for f in source_files if "node_modules" not in f and "__pycache__" not in f]
                        observer.on_scaffold_sync(rid, len(source_files), len(source_files))

            # Generate implementation
            if use_collaborative_agents and workspace_dir:
                # Use ReActAgent with file operation tools (Claude Code style)
                from ._agent_execution import execute_with_agent

                # Note: Scaffold files are now created by Agent, not pre-written
                # run_scaffold_commands handles npm create vite for frontend
                # Agent will create/modify files on top of that

                observer.on_agent_mode_start(rid)
                formatter = _get_formatter_for_model(llm)
                impl = await execute_with_agent(
                    llm=llm,
                    formatter=formatter,
                    requirement=requirement,
                    blueprint=blueprint,
                    workspace_dir=workspace_dir,
                    feedback=feedback_map[rid],
                    verbose=verbose,
                    runtime_workspace=runtime_workspace,
                    skeleton_context=skeleton_context if skeleton_context.get("skeleton_generated") else None,
                    is_first_requirement=is_first_requirement,
                )
            elif generation_mode in ("stepwise", "scaffold") and files_plan:
                # Determine which files need regeneration vs which can be skipped
                validated_files = state.get("validated_files", set())
                error_files = state.get("validation_error_files", set())
                must_fix_files = state.get("must_fix_files", set())

                # Detect shared error files (files causing errors in multiple requirements)
                shared_error_files = _detect_shared_error_files(global_error_files, threshold=2)

                # Add shared error files to must_fix_files for this requirement
                files_plan_paths = {f["path"] for f in files_plan}
                shared_in_plan = set(shared_error_files) & files_plan_paths
                shared_not_in_plan = set(shared_error_files) - files_plan_paths

                # Force add shared error files that are NOT in the original blueprint
                # This handles scaffolding files like __init__.py that affect multiple requirements
                if shared_not_in_plan:
                    for shared_path in shared_not_in_plan:
                        # Add as a new file entry with high priority
                        files_plan.insert(0, {
                            "path": shared_path,
                            "role": "shared_fix",
                            "description": f"[共享错误修复] 此文件导致多个需求验证失败，必须修复导入/导出问题",
                        })
                    files_plan_paths = {f["path"] for f in files_plan}
                    if verbose:
                        observer.ctx.logger.info(
                            f"[{rid}] 添加共享错误文件到构建计划: {list(shared_not_in_plan)}"
                        )

                if shared_in_plan:
                    must_fix_files = must_fix_files | shared_in_plan
                    if verbose:
                        observer.ctx.logger.info(
                            f"[{rid}] 检测到共享错误文件，强制重建: {list(shared_in_plan)}"
                        )

                # Check QA acceptance status to decide regeneration strategy
                # If QA failed (business logic incomplete), regenerate ALL files
                # If QA passed but code validation failed, only fix error files
                last_qa = state.get("last_qa_report")
                qa_criteria = last_qa.get("criteria", []) if last_qa else []
                qa_passed_count = sum(1 for c in qa_criteria if c.get("pass"))
                qa_total = max(len(qa_criteria), 1)
                qa_pass_ratio = qa_passed_count / qa_total

                # QA failed significantly (< 80% pass rate) - regenerate all files
                # This handles cases where code validates but business logic is incomplete
                qa_failed_significantly = qa_pass_ratio < 0.8 and qa_total > 0

                # Combine error_files with must_fix_files for filtering
                all_error_files = error_files | must_fix_files

                # Filter files_plan to only regenerate files with errors
                # Keep all files in first round (validated_files is empty)
                # ALSO regenerate all if QA failed significantly (business logic incomplete)
                if validated_files and all_error_files and not qa_failed_significantly:
                    # Incremental mode: only regenerate files with errors + must_fix_files
                    # Only use this when QA mostly passed (code structure is correct)
                    filtered_files_plan = [
                        f for f in files_plan
                        if f["path"] in all_error_files or f["path"] not in validated_files
                    ]
                    if filtered_files_plan:
                        shared_count = len(shared_in_plan)
                        if shared_count > 0:
                            mode_desc = f"增量修复 ({len(filtered_files_plan)}/{len(files_plan)} 文件, 含{shared_count}个共享错误)"
                        else:
                            mode_desc = f"增量修复 ({len(filtered_files_plan)}/{len(files_plan)} 文件)"
                        observer.on_stepwise_mode_start(rid, len(filtered_files_plan), mode_desc)
                        # Update blueprint with filtered plan
                        blueprint = {**blueprint, "files_plan": filtered_files_plan}
                    else:
                        # All files validated, but still failing - regenerate all
                        mode_desc = "脚手架+业务代码" if generation_mode == "scaffold" else "分步生成"
                        observer.on_stepwise_mode_start(rid, len(files_plan), mode_desc)
                else:
                    # First round OR QA failed significantly - regenerate all files
                    if qa_failed_significantly:
                        mode_desc = f"完整重建 (QA通过率{qa_pass_ratio:.0%})"
                    elif shared_in_plan:
                        mode_desc = f"完整重建 (含{len(shared_in_plan)}个共享错误文件)"
                    else:
                        mode_desc = "脚手架+业务代码" if generation_mode == "scaffold" else "分步生成"
                    observer.on_stepwise_mode_start(rid, len(files_plan), mode_desc)

                # Choose between edit mode and generate mode
                if use_edit_mode and file_manager:
                    # Claude Code style: read before write, incremental edits
                    mode_desc = "编辑模式" if generation_mode != "scaffold" else "脚手架+编辑模式"
                    if code_guard:
                        mode_desc += " + CodeGuard"
                    observer.on_stepwise_mode_start(rid, len(files_plan), mode_desc)
                    impl = await stepwise_edit_files(
                        llm=llm,
                        requirement=requirement,
                        blueprint=blueprint,
                        file_manager=file_manager,
                        all_criteria=criteria,
                        failed_criteria=failed_criteria,
                        code_guard=code_guard,  # Anti-hallucination validation
                        verbose=verbose,
                    )
                else:
                    # Check Claude Code mode
                    if USE_CLAUDE_CODE and CLAUDE_CODE_MODE == "agent_with_limbs":
                        # NEW: Agent (brain) + Claude Code (limbs) mode
                        # Agent makes decisions, calls claude_code_edit via toolkit
                        from ._agent_execution import execute_with_agent

                        # NOTE: Scaffold files are now pre-written BEFORE skeleton generation
                        # (see scaffold pre-write logic earlier in this function)
                        # No need to pre-write here anymore

                        observer.on_stepwise_mode_start(rid, 0, "Agent + 四肢模式")
                        agent_formatter = _get_formatter_for_model(llm)
                        impl = await execute_with_agent(
                            llm=llm,
                            formatter=agent_formatter,
                            requirement=requirement,
                            blueprint=blueprint,
                            workspace_dir=Path(workspace_dir) if workspace_dir else Path.cwd(),
                            feedback=feedback_map[rid],
                            verbose=verbose,
                            runtime_workspace=runtime_workspace,
                            skeleton_context=skeleton_context if skeleton_context.get("skeleton_generated") else None,
                            is_first_requirement=is_first_requirement,
                        )
                    elif USE_CLAUDE_CODE and CLAUDE_CODE_MODE == "autonomous":
                        # Autonomous mode - Claude Code has full control (direct call)
                        observer.on_stepwise_mode_start(rid, 0, "自主模式 (Claude Code)")
                        impl = await implement_requirement_autonomous(
                            requirement=requirement,
                            blueprint=blueprint,
                            all_criteria=criteria,
                            workspace_dir=workspace_dir,
                            contextual_notes=full_context or None,
                            feedback=feedback_map[rid],
                            failed_criteria=failed_criteria,
                            previous_errors=state.get("validation_errors", []),
                            architecture_contract=architecture_contract,
                            verbose=verbose,
                        )
                    else:
                        # Legacy mode: stepwise file generation
                        impl = await stepwise_generate_files(
                            llm=llm,
                            requirement=requirement,
                            blueprint=blueprint,
                            contextual_notes=full_context or None,
                            runtime_workspace=runtime_workspace if use_runtime_mode else None,
                            feedback=feedback_map[rid],
                            failed_criteria=failed_criteria,
                            previous_errors=state.get("validation_errors", []),
                            skeleton_context=skeleton_context if skeleton_context.get("skeleton_generated") else None,
                            all_criteria=criteria,
                            workspace_dir=workspace_dir,
                            code_guard=code_guard,  # Anti-hallucination validation
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
                    skeleton_context=skeleton_context if skeleton_context.get("skeleton_generated") else None,
                    verbose=verbose,
                )

            observer.on_implementation_summary(rid, impl.get("summary", ""))

            # Log CodeGuard warnings if any
            if impl.get("code_guard_warnings"):
                observer.ctx.logger.warn(f"[{rid}] CodeGuard 警告:\n{impl['code_guard_warnings']}")

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
                    # Track modified files for regression detection
                    _track_modified_files(rid, written_files)

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
                                    except UnicodeDecodeError:
                                        # Binary file, skip silently
                                        pass
                                    except Exception as e:
                                        if verbose:
                                            observer.ctx.logger.debug(f"[{rid}] 跳过文件 {rel_path}: {e}")

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

                            # Validation errors will be passed to agent in next round
                            # via previous_errors parameter - no separate debug phase needed

                elif use_runtime_mode:
                    write_results = runtime_workspace.write_files(files_list)
                    for result in write_results:
                        if result.get("success"):
                            written_files.append(result["path"])
                            observer.on_file_written(rid, result["path"], "Runtime")
                    # Track modified files for regression detection
                    _track_modified_files(rid, written_files)

                    # CodeGuard validation for generated files
                    code_guard_issues: list[str] = []
                    if code_guard and files_list:
                        for file_info in files_list:
                            fpath = file_info.get("path", "")
                            content = file_info.get("content", "")
                            if fpath and content:
                                code_guard.record_file_read(fpath, str(content))
                                cg_result = code_guard.validate_content(
                                    fpath, str(content), is_new_file=True
                                )
                                cg_warnings = code_guard.format_warnings(cg_result)
                                if cg_warnings:
                                    # Collect issues for LLM feedback
                                    code_guard_issues.append(f"[CodeGuard] {fpath}: {cg_warnings}")
                                    if verbose:
                                        observer.ctx.logger.warn(
                                            f"[{rid}] CodeGuard ({fpath}):\n{cg_warnings}"
                                        )
                    # Store CodeGuard issues for next round feedback
                    if code_guard_issues:
                        state["code_guard_issues"] = code_guard_issues

                    # Register generated files in project memory
                    if project_memory and files_list:
                        from ._code_context import register_generated_files
                        register_generated_files(project_memory, files_list, rid)

                    # Execute setup commands
                    setup_commands = impl.get("setup_commands", [])
                    if setup_commands:
                        observer.on_setup_commands(rid, len(setup_commands))
                        runtime_workspace.execute_setup_commands(setup_commands)

                    # Files stay in container, read from container for validation
                    if workspace_dir:
                        container_files = runtime_workspace.list_files()
                        observer.on_files_synced(rid, len(container_files))

                        # Code validation (read files from container)
                        if container_files and not skip_code_validation:
                            observer.on_validation_start(rid)
                            synced_files = {}
                            for rel_path in container_files:
                                if not rel_path.startswith("."):
                                    try:
                                        content = runtime_workspace.read_file(rel_path)
                                        if content:  # Skip empty/binary files
                                            synced_files[rel_path] = content
                                    except Exception as e:
                                        if verbose:
                                            observer.ctx.logger.debug(f"[{rid}] 跳过文件 {rel_path}: {e}")

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
                                # Validation errors will be passed to agent in next round
                                # via previous_errors parameter - no separate debug phase needed
                else:
                    # Local mode
                    local_files_dict = {}
                    syntax_issues: list[str] = []
                    for file_info in files_list:
                        file_path = file_info.get("path", "")
                        file_content = file_info.get("content", "")
                        if not file_path:
                            continue

                        # Pre-validation: Check syntax completeness before saving
                        # This catches LLM truncation issues early
                        is_complete, syntax_error, fixed_content = _check_code_syntax_completeness(
                            str(file_content), file_path
                        )
                        if not is_complete:
                            syntax_issues.append(f"{file_path}: {syntax_error}")
                            # Try to use fixed content if available
                            if fixed_content and fixed_content != file_content:
                                file_content = fixed_content
                                if verbose:
                                    observer.ctx.logger.info(
                                        f"[{rid}] 自动修复语法问题: {file_path}"
                                    )
                            else:
                                # Mark file for must-fix in next round
                                state["must_fix_files"].add(file_path)

                        full_path = workspace_dir / file_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(str(file_content), encoding="utf-8")
                        written_files.append(file_path)
                        local_files_dict[file_path] = str(file_content)
                        observer.on_file_written(rid, file_path)

                    # Log syntax issues if any
                    if syntax_issues and verbose:
                        observer.ctx.logger.warn(
                            f"[{rid}] 检测到 {len(syntax_issues)} 个语法完整性问题"
                        )

                    # CodeGuard validation for each file
                    code_guard_issues: list[str] = []
                    if code_guard and local_files_dict:
                        for fpath, content in local_files_dict.items():
                            # Record the file content for interface extraction
                            code_guard.record_file_read(fpath, content)
                            # Validate content
                            cg_result = code_guard.validate_content(
                                fpath, content, is_new_file=True
                            )
                            cg_warnings = code_guard.format_warnings(cg_result)
                            if cg_warnings:
                                # Collect issues for LLM feedback
                                code_guard_issues.append(f"[CodeGuard] {fpath}: {cg_warnings}")
                                if verbose:
                                    observer.ctx.logger.warn(
                                        f"[{rid}] CodeGuard ({fpath}):\n{cg_warnings}"
                                    )
                    # Store CodeGuard issues for next round feedback
                    if code_guard_issues:
                        state["code_guard_issues"] = code_guard_issues

                    # Track modified files for regression detection
                    _track_modified_files(rid, written_files)

                    # Register generated files in project memory
                    if project_memory and files_list:
                        from ._code_context import register_generated_files
                        register_generated_files(project_memory, files_list, rid)

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

                # Accumulate files across rounds for complete deliverable
                # This ensures QA can see all files, not just the ones modified this round
                accumulated = state.get("accumulated_files", {})
                for f in impl.get("files", []):
                    fpath = f.get("path", "")
                    if fpath and f.get("content"):
                        accumulated[fpath] = f
                state["accumulated_files"] = accumulated

                # Build accumulated impl with all files from all rounds
                accumulated_files_list = list(accumulated.values())
                accumulated_impl = {
                    **impl,
                    "files": accumulated_files_list,
                    "summary": f"累积 {len(accumulated_files_list)} 个文件 (本轮生成 {len(impl.get('files', []))} 个)",
                }

                # Save project info with accumulated files
                path = DELIVERABLE_DIR / f"{sanitize_filename(rid)}_{round_idx}_project.json"
                path.write_text(json.dumps(accumulated_impl, ensure_ascii=False, indent=2), encoding="utf-8")
                artifact_content = json.dumps({"files": written_files}, ensure_ascii=False)
            else:
                # Single file mode
                ext = impl.get("artifact_extension", "txt").lstrip(".")
                artifact_content = impl.get("artifact_content", "")
                if isinstance(artifact_content, (dict, list)):
                    artifact_content = json.dumps(artifact_content, ensure_ascii=False, indent=2)

                if use_runtime_mode:
                    # Write to container only, no local export
                    main_file = f"app.{ext}"
                    runtime_workspace.write_file(main_file, str(artifact_content))
                    path = None  # No local path
                elif use_agent_mode and workspace_dir:
                    # Write to container only
                    main_file = f"app.{ext}"
                    runtime_workspace.write_file(main_file, str(artifact_content))
                    path = None
                else:
                    # Legacy mode: write to DELIVERABLE_DIR
                    path = DELIVERABLE_DIR / f"{sanitize_filename(rid)}_{round_idx}.{ext}"
                    path.write_text(str(artifact_content), encoding="utf-8")

            final_paths[rid] = path
            # Memory optimization: store truncated artifact content for large files
            # Keep first 2000 chars for context in incremental updates
            artifact_str = str(artifact_content)
            truncated_artifact = (
                artifact_str[:2000] + f"\n... [truncated, total {len(artifact_str)} chars]"
                if len(artifact_str) > 2000
                else artifact_str
            )
            state.update({
                "artifact": truncated_artifact,
                "artifact_size": len(artifact_str),
                "path": path,
                "summary": impl.get("summary", ""),
                "blueprint": blueprint,
            })

            # QA validation
            observer.on_phase_start(rid, "qa")

            qa_workspace_files: dict[str, str] | None = None
            if use_agent_mode and (runtime_workspace or workspace_dir):
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

                # Read files from container if runtime_workspace is available
                if verbose:
                    observer.ctx.logger.debug(
                        f"[{rid}] QA 检查: runtime_workspace={runtime_workspace is not None}, "
                        f"is_initialized={runtime_workspace.is_initialized if runtime_workspace else 'N/A'}"
                    )
                if runtime_workspace and runtime_workspace.is_initialized:
                    # List all files in container workspace
                    container_files = runtime_workspace.list_files()
                    if verbose:
                        observer.ctx.logger.debug(f"[{rid}] QA 从容器读取 {len(container_files)} 个文件")
                    for rel_path in container_files:
                        # Skip hidden files and directories
                        if rel_path.startswith(".") or "/_" in rel_path:
                            continue
                        # Skip common non-source directories
                        if any(skip in rel_path for skip in ["node_modules", "__pycache__", ".git", "dist"]):
                            continue
                        # Exclude non-source files
                        if rel_path.lower().endswith(non_source_extensions):
                            continue
                        try:
                            content = runtime_workspace.read_file(rel_path)
                            if content:
                                qa_workspace_files[rel_path] = content
                        except Exception as e:
                            if verbose:
                                observer.ctx.logger.debug(f"[{rid}] QA跳过容器文件 {rel_path}: {e}")
                else:
                    # Fallback: read from host workspace (for non-container mode)
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
                            except UnicodeDecodeError:
                                # Binary file, skip silently
                                pass
                            except Exception as e:
                                if verbose:
                                    observer.ctx.logger.debug(f"[{rid}] QA跳过文件 {rel_path}: {e}")

            # Get files modified by this requirement for mandatory QA review
            # This ensures QA doesn't miss files that were actually modified
            modified_files_list = list(state.get("modified_files", set()))

            if verbose and qa_workspace_files:
                observer.ctx.logger.debug(f"[{rid}] QA 工作区文件: {len(qa_workspace_files)} 个")
                if qa_workspace_files:
                    sample_files = list(qa_workspace_files.keys())[:5]
                    observer.ctx.logger.debug(f"[{rid}] QA 示例文件: {sample_files}")

            # PR Mode: Use PR Review mode QA with diff-based validation
            if pr_mode_active and runtime_workspace:
                # Get PR diff for review
                try:
                    pr_diff = await runtime_workspace.get_pr_diff()
                    if verbose:
                        diff_len = len(pr_diff) if pr_diff else 0
                        observer.ctx.logger.debug(f"[PR Mode] [{rid}] PR diff: {diff_len} 字符")
                except Exception as e:
                    observer.ctx.logger.warn(f"[PR Mode] [{rid}] 获取 PR diff 失败: {e}")
                    pr_diff = ""

                # Get file lists from delivery and working directories
                try:
                    delivery_files_result = await runtime_workspace.exec(
                        f"find {runtime_workspace.delivery_dir} -type f -not -path '*/.git/*' "
                        f"-not -path '*/node_modules/*' -not -path '*/__pycache__/*' 2>/dev/null || true"
                    )
                    delivery_files = [
                        f.replace(f"{runtime_workspace.delivery_dir}/", "")
                        for f in delivery_files_result.get("output", "").strip().split("\n")
                        if f.strip()
                    ]
                    working_files_result = await runtime_workspace.exec(
                        f"find {runtime_workspace.working_dir} -type f -not -path '*/.git/*' "
                        f"-not -path '*/node_modules/*' -not -path '*/__pycache__/*' 2>/dev/null || true"
                    )
                    working_files = [
                        f.replace(f"{runtime_workspace.working_dir}/", "")
                        for f in working_files_result.get("output", "").strip().split("\n")
                        if f.strip()
                    ]
                except Exception as e:
                    observer.ctx.logger.warn(f"[PR Mode] [{rid}] 获取文件列表失败: {e}")
                    delivery_files = []
                    working_files = []

                if pr_diff:
                    # Use PR Review mode
                    observer.ctx.logger.info(f"[PR Mode] [{rid}] 使用 PR Review 模式进行 QA 验收")
                    qa_report_raw = await qa_requirement_pr(
                        llm=llm,
                        requirement=requirement,
                        criteria=criteria,
                        pr_diff=pr_diff,
                        delivery_files=delivery_files,
                        working_files=working_files,
                        blueprint=blueprint,
                        runtime_workspace=runtime_workspace,
                        verbose=verbose,
                    )
                    qa_report = _normalize_qa_report(qa_report_raw, criteria)
                else:
                    # No diff means no changes, use traditional QA
                    observer.ctx.logger.debug(f"[PR Mode] [{rid}] 无变更，使用传统 QA 模式")
                    qa_report_raw = await qa_requirement(
                        llm=llm,
                        requirement=requirement,
                        blueprint=blueprint,
                        artifact_path=path,
                        criteria=criteria,
                        round_index=round_idx,
                        workspace_files=qa_workspace_files,
                        playwright_mcp=effective_playwright_mcp,
                        http_url=serve_url if http_server_available else None,
                        verbose=verbose,
                        mandatory_files=modified_files_list,
                        runtime_workspace=runtime_workspace if use_runtime_mode else None,
                        enable_runtime_validation=use_runtime_mode,
                    )
                    qa_report = _normalize_qa_report(qa_report_raw, criteria)
            else:
                # Traditional QA mode
                qa_report_raw = await qa_requirement(
                    llm=llm,
                    requirement=requirement,
                    blueprint=blueprint,
                    artifact_path=path,
                    criteria=criteria,
                    round_index=round_idx,
                    workspace_files=qa_workspace_files,
                    playwright_mcp=effective_playwright_mcp,
                    http_url=serve_url if http_server_available else None,
                    verbose=verbose,
                    mandatory_files=modified_files_list,  # Force QA to review modified files
                    runtime_workspace=runtime_workspace if use_runtime_mode else None,  # NEW: Runtime validation
                    enable_runtime_validation=use_runtime_mode,  # Enable Claude Code based validation
                )
                qa_report = _normalize_qa_report(qa_report_raw, criteria)

            # Calculate results
            crit = qa_report.get("criteria", [])
            passed = sum(1 for item in crit if item.get("pass"))
            total = max(len(crit), 1)
            pass_ratio = passed / total

            # Calculate pass conditions
            # static_passed: All QA criteria must pass (100%), no threshold
            static_passed = passed == total
            code_validation_passed = True
            code_validation_score = 1.0

            if validation_result is not None:
                code_validation_score = validation_result.score
                # Code validation must have no errors (is_valid=True)
                code_validation_passed = validation_result.is_valid

            # Overall pass requires BOTH QA and code validation to pass
            # Also consider qa_report's overall_pass (which includes runtime validation result)
            qa_overall_pass = qa_report.get("overall_pass", static_passed)
            overall_passed = qa_overall_pass and code_validation_passed
            requirement_pass_flags.append(overall_passed)

            # Always store QA report for use when skipping in future rounds
            state["last_qa_report"] = qa_report
            state["code_validation_passed"] = code_validation_passed

            # Update passed criteria and fully_passed flag
            # ONLY if overall validation passed (both QA and code validation)
            if overall_passed:
                # PR Mode: Merge changes to delivery directory
                if pr_mode_active and runtime_workspace:
                    try:
                        merge_result = await runtime_workspace.merge_to_delivery(rid)
                        if merge_result.success:
                            observer.ctx.logger.info(f"[PR Mode] [{rid}] ✓ PR 已合并到 delivery")
                        else:
                            observer.ctx.logger.warn(
                                f"[PR Mode] [{rid}] ✗ 合并失败: {merge_result.message}"
                            )
                            if merge_result.conflicts:
                                observer.ctx.logger.warn(
                                    f"[PR Mode] [{rid}] 冲突文件: {merge_result.conflicts}"
                                )
                            # Mark as not passed if merge failed
                            overall_passed = False
                            requirement_pass_flags[-1] = False  # Update the last flag
                    except Exception as e:
                        observer.ctx.logger.warn(f"[PR Mode] [{rid}] 合并异常: {e}")
                        # Don't fail the requirement just because merge failed
                        # The code changes are still valid

                state["fully_passed"] = True
                for item in crit:
                    if item.get("pass") and item.get("id"):
                        state["passed"].add(item["id"])

            # Update feedback and validation errors for next round
            # Check for CodeGuard issues even if overall passed
            cg_issues = state.get("code_guard_issues", [])
            has_cg_errors = any("[ERROR]" in issue for issue in cg_issues) if cg_issues else False

            if overall_passed and not has_cg_errors:
                feedback_map[rid] = ""
                state["feedback"] = ""
                state["validation_errors"] = []  # Clear errors on success
                state["must_fix_files"] = set()  # Clear must-fix files on success
                # Store validation score for regression detection
                if validation_result is not None:
                    state["last_validation_score"] = validation_result.score
            else:
                feedback_parts = []
                # Add improvements from QA report (includes runtime_feedback when static check passed but runtime failed)
                # Runtime feedback is critical - it detects structural issues like missing files
                runtime_feedback = qa_report.get("runtime_feedback", "")
                if not static_passed:
                    feedback_parts.append(qa_report.get("improvements", ""))
                elif runtime_feedback:
                    # Static QA passed but runtime validation failed - prioritize runtime feedback
                    feedback_parts.append(f"⚠️ 【关键结构性问题】\n{runtime_feedback}")
                if not code_validation_passed and validation_result:
                    if validation_result.errors:
                        # Store validation errors for next round
                        all_errors = list(validation_result.errors[:15])
                        # Add CodeGuard issues if any
                        if cg_issues:
                            all_errors.extend(cg_issues)
                        state["validation_errors"] = all_errors
                        # Track which files have errors (for incremental fixing)
                        error_files = _extract_error_files(validation_result.errors)
                        state["validation_error_files"] = error_files

                        # Update global error files tracking (for shared error detection)
                        for efile in error_files:
                            if efile not in global_error_files:
                                global_error_files[efile] = set()
                            global_error_files[efile].add(rid)

                        # Detect shared error files for this round
                        shared_error_files = _detect_shared_error_files(global_error_files, threshold=2)

                        # Build detailed error feedback with shared file info
                        detailed_feedback = _build_detailed_error_feedback(
                            validation_result.errors[:15],
                            error_files,
                            shared_error_files,
                        )
                        feedback_parts.append(detailed_feedback)

                        # Files in current req that are NOT in error_files passed validation
                        current_files = {f.get("path", "") for f in impl.get("files", []) if f.get("path")}
                        state["validated_files"] = current_files - error_files

                        # Add error files to must_fix_files for next round
                        state["must_fix_files"] = state.get("must_fix_files", set()) | error_files

                # Handle CodeGuard errors when code validation passed but CG has issues
                elif has_cg_errors and cg_issues:
                    state["validation_errors"] = cg_issues
                    cg_feedback = "\n".join(cg_issues)
                    feedback_parts.append(f"[CodeGuard 检测到问题]\n{cg_feedback}")

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

            # Note: Files stay in container, no sync to host needed
            # Git operations are skipped in container isolation mode

            # Git: validate changes and commit (only if not using container isolation)
            if git_workspace and not use_runtime_mode:
                # Validate changes for suspicious patterns
                git_validation = git_workspace.validate_changes()
                if not git_validation.is_valid:
                    for violation in git_validation.violations:
                        observer.ctx.logger.warn(f"[Git] {rid} 可疑变更: {violation}")
                    # Rollback suspicious changes
                    git_workspace.rollback_changes()
                    observer.ctx.logger.warn(f"[Git] {rid} 已回滚可疑变更")
                else:
                    # Commit changes
                    changes = git_workspace.get_changes()
                    if changes.has_changes:
                        committed = git_workspace.commit_requirement(
                            rid,
                            message=f"Implement {rid}: {requirement.get('title', '')[:50]}",
                        )
                        if committed:
                            observer.ctx.logger.debug(
                                f"[Git] {rid} 提交成功 (+{len(changes.added)} ~{len(changes.modified)} -{len(changes.deleted)})"
                            )
                    else:
                        observer.ctx.logger.debug(f"[Git] {rid} 无文件变更")

                # Switch back to main branch
                git_workspace.switch_to_main()

        rounds.append(round_entry)

        # Regression validation: check if modifications affected previously passed requirements
        if workspace_dir and round_idx > 1:
            # Collect all files modified in this round
            round_modified_files: set[str] = set()
            for result in round_entry.get("results", []):
                rid = result.get("requirement_id", "")
                if rid in req_state:
                    round_modified_files.update(req_state[rid].get("modified_files", set()))

            # Find requirements that may be affected
            affected_rids: set[str] = set()
            for fpath in round_modified_files:
                normalized = fpath.lstrip("./")
                if normalized in file_to_requirements:
                    # Get requirements that previously modified this file
                    for prev_rid in file_to_requirements[normalized]:
                        # Only check requirements that fully passed (both QA and code validation)
                        state = req_state.get(prev_rid)
                        if state and state.get("fully_passed"):
                            affected_rids.add(prev_rid)

            # Exclude requirements that were just processed this round
            current_round_rids = {r.get("requirement_id") for r in round_entry.get("results", [])}
            affected_rids -= current_round_rids

            if affected_rids:
                observer.on_regression_check_batch_start(len(affected_rids), list(affected_rids))
                regression_results = await _perform_regression_check(
                    affected_rids, workspace_dir, round_idx
                )
                # Update pass flags if regressions were found
                regressed_rids = [rid for rid, passed in regression_results.items() if not passed]
                if regressed_rids:
                    observer.on_regression_batch_complete(len(regressed_rids), regressed_rids)
                    # Mark these as failed in requirement_pass_flags
                    for idx, req in enumerate(requirements):
                        if req["id"] in regressed_rids:
                            requirement_pass_flags[idx] = False

        # Report round completion
        passed_reqs = [requirements[idx]["id"] for idx, ok in enumerate(requirement_pass_flags) if ok]
        failed_reqs = [requirements[idx]["id"] for idx, ok in enumerate(requirement_pass_flags) if not ok]
        observer.on_round_complete(round_idx, passed_reqs, failed_reqs)

        if all(requirement_pass_flags):
            observer.on_execution_complete(round_idx, True)
            break
        elif round_idx == max_rounds:
            observer.on_execution_complete(round_idx, False)

    # Final regression check: validate ALL fully_passed requirements
    # This catches regressions that weren't detected during incremental checks
    # (e.g., when a new file is modified that affects previously passed requirements)

    # Initialize variables with proper scope to avoid 'in dir()' anti-pattern
    fully_passed_rids: list[str] = []
    regressed_in_final: list[str] = []
    final_regression_info: dict[str, Any] = {}

    if workspace_dir and len(requirements) > 1:
        fully_passed_rids = [
            req["id"] for req in requirements
            if req_state[req["id"]].get("fully_passed")
        ]

        if fully_passed_rids and len(fully_passed_rids) < len(requirements):
            # Only run final check if some requirements passed early
            # and there were subsequent rounds that might have caused regressions
            observer.ctx.logger.info("\n---- 最终回归检查 ----")
            observer.ctx.logger.info(f"[FINAL] 检查 {len(fully_passed_rids)} 个已通过需求的回归状态...")

            final_regression_results = await _perform_regression_check(
                set(fully_passed_rids), workspace_dir, round_idx + 1
            )

            regressed_in_final = [
                rid for rid, passed in final_regression_results.items()
                if not passed
            ]

            if regressed_in_final:
                observer.ctx.logger.warn(
                    f"[FINAL] ⚠ 发现 {len(regressed_in_final)} 个需求发生回归: {regressed_in_final}"
                )
                observer.ctx.logger.warn(
                    "[FINAL] 这些需求在后续轮次中被破坏，需要重新执行"
                )
                # Mark these requirements as not fully passed
                for rid in regressed_in_final:
                    req_state[rid]["fully_passed"] = False
                    req_state[rid]["code_validation_passed"] = False
                    # Clean up final_paths for regressed requirements
                    if rid in final_paths:
                        del final_paths[rid]

                # Update final regression info
                final_regression_info = {
                    "checked": len(fully_passed_rids),
                    "regressed": regressed_in_final,
                    "regressed_count": len(regressed_in_final),
                    "still_valid": [rid for rid in fully_passed_rids if rid not in regressed_in_final],
                }

                # Update the last round's results to reflect regression
                if rounds:
                    last_round = rounds[-1]
                    for result in last_round.get("results", []):
                        if result.get("requirement_id") in regressed_in_final:
                            result["overall_passed"] = False
                            result["regression_detected"] = True

            else:
                observer.ctx.logger.info(f"[FINAL] ✓ 所有 {len(fully_passed_rids)} 个需求回归检查通过")
                final_regression_info = {
                    "checked": len(fully_passed_rids),
                    "regressed": [],
                    "regressed_count": 0,
                    "still_valid": fully_passed_rids,
                }

    # Git: merge all requirement branches into main
    git_merge_info: dict[str, Any] = {"enabled": False}
    if git_workspace:
        git_merge_info["enabled"] = True
        git_merge_info["branches"] = []
        git_merge_info["conflicts"] = []

        observer.ctx.logger.info("[Git] 开始合并所有需求分支...")

        for req in requirements:
            rid = req["id"]
            merge_result = git_workspace.merge_requirement(rid)

            branch_info = {
                "requirement_id": rid,
                "success": merge_result.success,
                "conflicts": merge_result.conflicts,
            }
            git_merge_info["branches"].append(branch_info)

            if merge_result.success:
                observer.ctx.logger.debug(f"[Git] ✓ 合并 {rid} 成功")
            elif merge_result.conflicts:
                git_merge_info["conflicts"].extend(
                    [(rid, f) for f in merge_result.conflicts]
                )
                observer.ctx.logger.warn(
                    f"[Git] ✗ 合并 {rid} 存在冲突: {merge_result.conflicts}"
                )
                # Auto-resolve by accepting incoming (requirement) changes
                git_workspace.resolve_conflicts_theirs()
                observer.ctx.logger.info(f"[Git] 自动解决冲突: 接受 {rid} 的变更")

        # Clean up merged branches
        git_workspace.cleanup()

        if git_merge_info["conflicts"]:
            observer.ctx.logger.warn(
                f"[Git] 合并完成，共 {len(git_merge_info['conflicts'])} 个文件存在冲突已自动解决"
            )
        else:
            observer.ctx.logger.info("[Git] ✓ 所有分支合并成功，无冲突")

    # Finalize project - merge files and validate
    finalization_report: dict[str, Any] = {}
    if workspace_dir and len(requirements) > 1:
        observer.on_finalization_start()
        try:
            # In edit mode, files are already in workspace_dir (no merge needed)
            if use_edit_mode and file_manager:
                # Skip merge - files are already correctly edited in place
                observer.ctx.logger.info("[Edit Mode] 跳过文件合并 - 文件已就地编辑")
                finalization_report = {
                    "merged_files": [],
                    "copied_files": [],
                    "conflicts": [],
                    "file_errors": [],
                    "validation": {"passed": True, "missing": [], "errors": []},
                    "edit_mode": True,
                }
                # Just validate completeness
                from ._project_scaffolding import validate_project_completeness
                validation = validate_project_completeness(workspace_dir)
                finalization_report["validation"].update(validation)
            else:
                # Legacy mode: merge from deliverables
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
                # NOTE: Scaffold files should have been created by Claude Code
                # If missing, log warning instead of generating on host
                if missing:
                    observer.ctx.logger.warn(
                        f"[Finalize] 缺失文件应由 Claude Code 创建: {missing}"
                    )

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

    # Calculate final execution status
    final_passed_count = sum(
        1 for req in requirements
        if req_state[req["id"]].get("fully_passed")
    )
    all_passed = final_passed_count == len(requirements)

    # NOTE: If final_regression.regressed is non-empty, caller should consider
    # re-running execution to fix the regressed requirements. Automatic re-execution
    # is intentionally NOT implemented to:
    # 1. Give caller control over retry policy
    # 2. Prevent potential infinite loops
    # 3. Allow caller to inspect results before deciding
    #
    # Example caller retry logic:
    #   result = await run_execution(...)
    #   while result["final_regression"].get("regressed"):
    #       if max_retries_exceeded: break
    #       result = await run_execution(...)

    return {
        "rounds": rounds,
        "deliverables": final_paths,
        "finalization": finalization_report,
        "final_regression": final_regression_info,
        "git_merge": git_merge_info,
        "execution_summary": {
            "total_requirements": len(requirements),
            "passed_count": final_passed_count,
            "failed_count": len(requirements) - final_passed_count,
            "all_passed": all_passed,
            "total_rounds": len(rounds),
            "regressed_in_final_check": regressed_in_final,
        },
    }


# ---------------------------------------------------------------------------
# Single Requirement Execution (for Task Sharding)
# ---------------------------------------------------------------------------
async def run_single_requirement(
    llm: Any,
    spec: dict[str, Any],
    requirement: dict[str, Any],
    workspace_dir: Path | None = None,
    runtime_workspace: Any = None,
    round_idx: int = 1,
    feedback: str = "",
    passed_ids: set[str] | None = None,
    prev_blueprint: dict[str, Any] | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute a single requirement through Blueprint -> Code -> QA flow.

    This function is designed for task sharding, where each requirement is
    executed independently by a Celery task. It provides a simplified interface
    that doesn't require the full execution context.

    Args:
        llm: LLM model instance
        spec: Full specification dict (for acceptance criteria lookup)
        requirement: Single requirement dict with id, content, type, etc.
        workspace_dir: Workspace directory path
        runtime_workspace: RuntimeWorkspace instance (optional)
        round_idx: Current round number (for retries)
        feedback: Previous QA feedback (for retries)
        passed_ids: Set of already-passed criteria IDs (for retries)
        prev_blueprint: Previous blueprint dict (for retries)
        verbose: Whether to print debug info

    Returns:
        dict: Execution result containing:
            - rid: Requirement ID
            - passed: Whether requirement passed QA
            - pass_ratio: Ratio of passed criteria
            - blueprint: Blueprint dict
            - code_result: Code generation result
            - qa_result: QA validation result
            - modified_files: List of files modified
            - tokens: Estimated tokens used
            - cost: Estimated cost in USD
            - llm_calls: Number of LLM calls made
            - error: Error message if failed
    """
    from ._spec import criteria_for_requirement
    from ._agent_roles import (
        design_requirement,
        stepwise_generate_files,
        implement_requirement,
    )
    from ._qa import qa_requirement, _normalize_qa_report

    rid = requirement.get("id", "UNKNOWN")
    passed_ids = passed_ids or set()

    # Track metrics
    llm_calls = 0
    tokens_used = 0
    cost_usd = 0.0

    try:
        # 1. Get acceptance criteria for this requirement
        criteria = criteria_for_requirement(spec, rid)
        if not criteria:
            # Fallback to requirement's own acceptance field
            acceptance = requirement.get("acceptance", [])
            criteria = [
                {"id": f"{rid}.{i+1}", "title": acc, "description": acc}
                for i, acc in enumerate(acceptance)
            ]

        # Ensure criteria have IDs
        for idx, item in enumerate(criteria, 1):
            item.setdefault("id", f"{rid}.{idx}")

        # Calculate failed criteria (not yet passed)
        failed_criteria = [c for c in criteria if c.get("id") not in passed_ids]

        # 2. Design Blueprint
        blueprint = await design_requirement(
            llm,
            requirement,
            feedback,
            passed_ids,
            failed_criteria,
            prev_blueprint,
            contextual_notes=None,
            existing_workspace_files=None,
            skeleton_context=None,
            verbose=verbose,
        )
        llm_calls += 1

        # Inject spec-level tech_stack and project_type
        if "tech_stack" not in blueprint and spec.get("tech_stack"):
            blueprint["tech_stack"] = spec.get("tech_stack")
        if "project_type" not in blueprint and spec.get("project_type"):
            blueprint["project_type"] = spec.get("project_type")

        # 3. Generate Code
        files_plan = blueprint.get("files_plan", [])
        code_result: dict[str, Any] = {}

        if files_plan:
            # Use stepwise generation for structured file plans
            code_result = await stepwise_generate_files(
                llm=llm,
                requirement=requirement,
                blueprint=blueprint,
                contextual_notes=None,
                runtime_workspace=runtime_workspace,
                feedback=feedback,
                failed_criteria=failed_criteria,
                previous_errors=[],
                skeleton_context=None,
                all_criteria=criteria,
                workspace_dir=workspace_dir,
                code_guard=None,
                verbose=verbose,
            )
            llm_calls += len(files_plan)  # Approximate
        else:
            # Fallback to single-shot implementation
            code_result = await implement_requirement(
                llm,
                requirement,
                blueprint,
                feedback,
                passed_ids,
                failed_criteria,
                "",  # prev_artifact
                contextual_notes=None,
                workspace_files=None,
                skeleton_context=None,
                verbose=verbose,
            )
            llm_calls += 1

        # Extract modified files
        modified_files = []
        if runtime_workspace:
            # Get from runtime workspace
            modified_files = list(code_result.get("files_created", []))
        elif "files" in code_result:
            modified_files = list(code_result.get("files", {}).keys())

        # 4. QA Validation
        qa_report_raw = await qa_requirement(
            llm=llm,
            requirement=requirement,
            blueprint=blueprint,
            artifact_path=None,
            criteria=criteria,
            round_index=round_idx,
            workspace_files=None,
            playwright_mcp=None,
            http_url=None,
            verbose=verbose,
            mandatory_files=[],
            runtime_workspace=runtime_workspace,
            enable_runtime_validation=runtime_workspace is not None,
        )
        llm_calls += 1
        qa_report = _normalize_qa_report(qa_report_raw, criteria)

        # Calculate pass ratio
        crit = qa_report.get("criteria", [])
        passed_count = sum(1 for item in crit if item.get("pass"))
        total = max(len(crit), 1)
        pass_ratio = passed_count / total
        overall_passed = qa_report.get("overall_pass", passed_count == total)

        # Estimate token usage (rough approximation)
        tokens_used = llm_calls * 2000  # ~2k tokens per call average
        cost_usd = tokens_used * 0.00001  # Rough cost estimate

        return {
            "rid": rid,
            "passed": overall_passed,
            "pass_ratio": pass_ratio,
            "blueprint": blueprint,
            "code_result": code_result,
            "qa_result": {
                "passed": passed_count,
                "total": total,
                "details": crit,
                "overall_pass": overall_passed,
            },
            "validation_result": None,
            "modified_files": modified_files,
            "tokens": tokens_used,
            "cost": cost_usd,
            "llm_calls": llm_calls,
            "error": None,
        }

    except Exception as e:
        import traceback
        error_msg = f"[{rid}] Execution failed: {e}\n{traceback.format_exc()}"
        return {
            "rid": rid,
            "passed": False,
            "pass_ratio": 0.0,
            "blueprint": prev_blueprint,
            "code_result": {},
            "qa_result": {"passed": 0, "total": 0, "details": []},
            "validation_result": None,
            "modified_files": [],
            "tokens": tokens_used,
            "cost": cost_usd,
            "llm_calls": llm_calls,
            "error": error_msg,
        }


__all__ = [
    "DELIVERABLE_DIR",
    "run_execution",
    "run_single_requirement",
    "RequirementResult",
]
