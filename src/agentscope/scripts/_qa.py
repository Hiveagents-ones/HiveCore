# -*- coding: utf-8 -*-
"""QA validation and acceptance testing utilities.

This module provides:
- QA report normalization
- Requirement/blueprint summarization for QA
- QA acceptance via LLM
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ._sandbox import BrowserSandboxManager
    from ._runtime_workspace import RuntimeWorkspaceWithPR
    from agentscope.mcp import StatefulClientBase


# ---------------------------------------------------------------------------
# PR Review Prompt Template
# ---------------------------------------------------------------------------
PR_REVIEW_PROMPT = '''
## PR Review 验收

### 需求描述
{requirement_description}

### 变更差异 (git diff)
```diff
{pr_diff}
```

### 验收标准
{criteria_list}

### 审阅要求
1. 检查 diff 是否完整实现了需求描述的功能
2. 检查新增代码是否符合项目规范
3. 检查是否有潜在的回归风险（影响其他功能）
4. 检查边界条件和错误处理

请根据验收标准逐条评估，返回 JSON 格式结果。
'''


# ---------------------------------------------------------------------------
# PR Diff Utilities
# ---------------------------------------------------------------------------
def _extract_changed_files(pr_diff: str) -> list[str]:
    """Extract list of changed files from a git diff.

    Parses diff output to identify all files that have been added,
    modified, or deleted.

    Args:
        pr_diff (`str`):
            Git diff format string.

    Returns:
        `list[str]`:
            List of file paths that were changed in the diff.
    """
    import re

    changed_files: list[str] = []

    # Match diff headers: "--- a/path" or "+++ b/path"
    # Also match: "diff --git a/path b/path"
    patterns = [
        r'^diff --git a/(.+?) b/(.+?)$',  # git diff header
        r'^\+\+\+ b/(.+)$',  # Added/modified file in unified diff
        r'^--- a/(.+)$',  # Original file in unified diff
    ]

    for line in pr_diff.split('\n'):
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                # For git diff header, use the second path (b/path)
                if 'diff --git' in line:
                    file_path = match.group(2)
                else:
                    file_path = match.group(1)

                # Skip /dev/null (indicates file creation/deletion)
                if file_path != '/dev/null' and file_path not in changed_files:
                    changed_files.append(file_path)
                break

    return changed_files


async def _build_pr_context(
    pr_diff: str,
    working_files: dict[str, str],
    max_context_chars: int = 10000,
) -> str:
    """Build PR review context with intelligent truncation.

    For large diffs, this function intelligently selects the most
    relevant portions to include in the context.

    Args:
        pr_diff (`str`):
            Git diff format string.
        working_files (`dict[str, str]`):
            Dict of file paths to their full content in working directory.
        max_context_chars (`int`):
            Maximum characters for the context output.

    Returns:
        `str`:
            Formatted context string for PR review.
    """
    context_parts: list[str] = []
    total_chars = 0

    # If diff is small enough, include it entirely
    if len(pr_diff) <= max_context_chars:
        return pr_diff

    # Parse diff into file-level chunks
    file_diffs: list[tuple[str, str]] = []
    current_file = ""
    current_diff_lines: list[str] = []

    for line in pr_diff.split('\n'):
        # Detect new file diff
        if line.startswith('diff --git') or line.startswith('--- a/'):
            if current_file and current_diff_lines:
                file_diffs.append((current_file, '\n'.join(current_diff_lines)))

            if line.startswith('diff --git'):
                # Extract file name from "diff --git a/path b/path"
                parts = line.split(' ')
                if len(parts) >= 4:
                    current_file = parts[3][2:]  # Remove 'b/' prefix
                current_diff_lines = [line]
            elif line.startswith('--- a/'):
                current_file = line[6:]  # Remove '--- a/' prefix
                current_diff_lines = [line]
        else:
            current_diff_lines.append(line)

    # Don't forget the last file
    if current_file and current_diff_lines:
        file_diffs.append((current_file, '\n'.join(current_diff_lines)))

    # Prioritize files by type (source files first, tests last)
    def file_priority(item: tuple[str, str]) -> int:
        fname = item[0].lower()
        if 'test' in fname or 'spec' in fname:
            return 2  # Tests last
        if fname.endswith(('.md', '.txt', '.json', '.yaml', '.yml')):
            return 1  # Config/docs medium priority
        return 0  # Source files first

    sorted_diffs = sorted(file_diffs, key=file_priority)

    # Build context with budget allocation
    per_file_budget = max_context_chars // max(len(sorted_diffs), 1)

    for file_path, diff_content in sorted_diffs:
        if total_chars >= max_context_chars:
            remaining = len(sorted_diffs) - len(context_parts)
            if remaining > 0:
                context_parts.append(f"\n... ({remaining} 个文件的 diff 已省略)")
            break

        # Truncate if needed
        if len(diff_content) > per_file_budget:
            truncated_diff = diff_content[:per_file_budget]
            # Find last complete line
            last_newline = truncated_diff.rfind('\n')
            if last_newline > 0:
                truncated_diff = truncated_diff[:last_newline]
            truncated_diff += f"\n... (文件 {file_path} 的剩余 diff 已截断)"
            context_parts.append(truncated_diff)
            total_chars += len(truncated_diff)
        else:
            context_parts.append(diff_content)
            total_chars += len(diff_content)

    return '\n'.join(context_parts)


# ---------------------------------------------------------------------------
# Report Normalization
# ---------------------------------------------------------------------------
def _normalize_qa_report(
    qa_report: Any,
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize QA report format from various LLM output formats.

    Args:
        qa_report: Raw QA report from LLM
        criteria: Acceptance criteria list

    Returns:
        dict: Normalized QA report
    """
    # Handle list format
    if isinstance(qa_report, list):
        qa_report = {"criteria": qa_report, "overall_pass": False, "improvements": ""}

    # Handle non-dict
    if not isinstance(qa_report, dict):
        return {
            "criteria": [
                {
                    "id": c.get("id", f"C{i}"),
                    "name": c.get("title", ""),
                    "pass": False,
                    "reason": "无法解析 QA 响应",
                    "recommendation": "",
                }
                for i, c in enumerate(criteria)
            ],
            "overall_pass": False,
            "improvements": "QA 响应格式无效",
        }

    # Extract criteria list (handle various field names)
    raw_criteria = (
        qa_report.get("criteria")
        or qa_report.get("results")
        or qa_report.get("test_cases")
        or qa_report.get("checks")
        or qa_report.get("items")
        or []
    )

    # Handle simple result field
    if not raw_criteria:
        overall_result = qa_report.get("result") or qa_report.get("status") or qa_report.get("pass")
        if overall_result is not None:
            is_pass = overall_result in (True, "pass", "passed", "true", "success", "ok")
            raw_criteria = [
                {
                    "id": c.get("id", f"C{i}"),
                    "name": c.get("title", ""),
                    "result": "pass" if is_pass else "fail",
                }
                for i, c in enumerate(criteria)
            ]

    # Normalize each criterion
    normalized_criteria: list[dict[str, Any]] = []
    for item in raw_criteria:
        if not isinstance(item, dict):
            continue

        item_id = item.get("id") or item.get("criteria_id") or item.get("check_id") or ""
        item_name = item.get("name") or item.get("title") or item.get("description") or ""

        # Determine pass status
        raw_pass = item.get("pass")
        if raw_pass is None:
            raw_result = item.get("result") or item.get("status") or item.get("passed")
            if raw_result is not None:
                raw_pass = raw_result in (True, "pass", "passed", "true", "success", "ok")
            else:
                raw_pass = False
        elif isinstance(raw_pass, str):
            raw_pass = raw_pass.lower() in ("true", "pass", "passed", "yes", "success", "ok")

        reason = item.get("reason") or item.get("message") or item.get("detail") or ""
        recommendation = item.get("recommendation") or item.get("suggestion") or item.get("fix") or ""

        normalized_criteria.append({
            "id": item_id,
            "name": item_name,
            "pass": bool(raw_pass),
            "reason": reason,
            "recommendation": recommendation,
        })

    # Generate default failures if empty
    if not normalized_criteria and criteria:
        normalized_criteria = [
            {
                "id": c.get("id", f"C{i}"),
                "name": c.get("title", ""),
                "pass": False,
                "reason": "LLM 未返回详细判定",
                "recommendation": "",
            }
            for i, c in enumerate(criteria)
        ]

    # Calculate overall pass
    passed_count = sum(1 for c in normalized_criteria if c.get("pass"))
    total_count = max(len(normalized_criteria), 1)
    overall_pass = qa_report.get("overall_pass")
    if overall_pass is None:
        overall_pass = passed_count == total_count and total_count > 0

    improvements = qa_report.get("improvements") or qa_report.get("improvement") or qa_report.get("suggestion") or ""

    return {
        "criteria": normalized_criteria,
        "overall_pass": bool(overall_pass),
        "improvements": improvements,
    }


# ---------------------------------------------------------------------------
# Summary Builders
# ---------------------------------------------------------------------------
def _build_requirement_summary(requirement: dict[str, Any]) -> str:
    """Build requirement summary for QA (reduced tokens).

    Args:
        requirement: Requirement dict

    Returns:
        str: JSON summary string
    """
    return json.dumps(
        {
            "id": requirement.get("id", ""),
            "title": requirement.get("title", ""),
            "summary": requirement.get("summary", requirement.get("description", ""))[:300],
            "category": requirement.get("category", ""),
        },
        ensure_ascii=False,
        indent=2,
    )


def _build_blueprint_summary(blueprint: dict[str, Any]) -> str:
    """Build blueprint summary for QA (reduced tokens).

    Args:
        blueprint: Blueprint dict

    Returns:
        str: JSON summary string
    """
    # Safely convert values to strings before slicing
    deliverable_pitch = str(blueprint.get("deliverable_pitch", "") or "")[:200]
    recommended_stack = blueprint.get("recommended_stack", "")
    if isinstance(recommended_stack, dict):
        recommended_stack = json.dumps(recommended_stack, ensure_ascii=False)
    recommended_stack = str(recommended_stack or "")[:150]

    return json.dumps(
        {
            "artifact_type": str(blueprint.get("artifact_type", "") or ""),
            "deliverable_pitch": deliverable_pitch,
            "recommended_stack": recommended_stack,
            "generation_mode": str(blueprint.get("generation_mode", "") or ""),
            "files_count": len(blueprint.get("files_plan", []) or []),
            "files_list": [f.get("path") for f in (blueprint.get("files_plan", []) or [])[:15]],
        },
        ensure_ascii=False,
        indent=2,
    )


# NOTE: Legacy keyword-based file relevance functions have been removed.
# File selection is now handled by LLM-driven approach in select_relevant_files_for_qa()
# which is language/framework agnostic and handles multilingual content properly.


def _build_files_summary_for_qa(workspace_files: dict[str, str]) -> str:
    """Build detailed files summary for QA evaluation.

    Extracts implementation details (not just structure) so QA can verify
    that requirements are properly implemented.

    Args:
        workspace_files: Dict of file paths to content

    Returns:
        str: Detailed files summary for QA
    """
    from ._validation import extract_file_summary

    summaries: list[str] = []
    total_chars = 0
    max_total_chars = 24000  # Increased for better QA evaluation

    # Sort files by relevance (source files first, tests last)
    # Use blacklist approach instead of whitelist for language agnosticism
    non_source_extensions = (
        ".log", ".lock", ".map", ".min.js", ".min.css",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
        ".woff", ".woff2", ".ttf", ".eot",
        ".pyc", ".pyo", ".class", ".o", ".so",
        ".db", ".sqlite", ".md", ".txt", ".json", ".yaml", ".yml",
    )

    def file_priority(fname: str) -> int:
        fname_lower = fname.lower()
        # Tests get lowest priority
        if "test" in fname_lower or "spec" in fname_lower:
            return 2
        # Non-source files get medium priority
        if fname_lower.endswith(non_source_extensions):
            return 1
        # All other source files get highest priority
        return 0

    sorted_files = sorted(workspace_files.items(), key=lambda x: file_priority(x[0]))

    for fname, content in sorted_files:
        if total_chars > max_total_chars:
            summaries.append(f"\n... (更多 {len(workspace_files) - len(summaries)} 个文件已省略)")
            break

        # Skip node_modules, __pycache__, etc.
        if any(skip in fname for skip in ["node_modules", "__pycache__", ".git"]):
            continue

        summary = extract_file_summary(content, fname)
        if summary.strip():
            file_summary = f"--- {fname} ---\n{summary}"
            summaries.append(file_summary)
            total_chars += len(file_summary)

    return "\n\n".join(summaries)


# ---------------------------------------------------------------------------
# LLM-Driven File Selection
# ---------------------------------------------------------------------------
async def select_relevant_files_for_qa(
    llm: Any,
    workspace_files: dict[str, str],
    criteria: list[dict[str, Any]],
    max_files: int = 15,
    *,
    verbose: bool = False,
    modified_files: list[str] | None = None,
) -> list[tuple[str, float]]:
    """Use LLM to select files most relevant to acceptance criteria.

    This function asks the LLM to analyze acceptance criteria and select
    the most relevant files from the workspace. This approach:
    - Is language/framework agnostic
    - Handles multilingual content (Chinese criteria, English code)
    - Understands semantic relationships
    - Hints about modified files so LLM can prioritize them

    Args:
        llm: LLM model instance
        workspace_files: Dict of file paths to content
        criteria: Acceptance criteria list
        max_files: Maximum number of files to select
        verbose: Whether to print debug info
        modified_files: Files modified by current requirement (hint for LLM)

    Returns:
        List of (file_path, relevance_score) sorted by relevance (descending)
    """
    from ._llm_utils import call_llm_json

    # Skip non-source files
    skip_patterns = ["node_modules", "__pycache__", ".git", ".pyc", ".pyo", "package-lock"]
    filtered_files = {
        k: v for k, v in workspace_files.items()
        if not any(skip in k for skip in skip_patterns)
    }

    if not filtered_files:
        return []

    # Build file list with brief descriptions
    file_descriptions: list[str] = []
    for fname, content in sorted(filtered_files.items()):
        # Get first meaningful lines as description
        lines = [l.strip() for l in content.split('\n') if l.strip()][:5]
        desc = ' '.join(lines)[:150]
        file_descriptions.append(f"- {fname}: {desc}...")

    # Format criteria
    criteria_text = json.dumps(
        [{"id": c.get("id", ""), "title": c.get("title", ""), "description": c.get("description", "")}
         for c in criteria],
        ensure_ascii=False,
        indent=2,
    )

    # Build modified files hint
    modified_hint = ""
    if modified_files:
        normalized_modified = [mf.lstrip("./") for mf in modified_files]
        valid_modified = [mf for mf in normalized_modified if mf in filtered_files]
        if valid_modified:
            modified_hint = f"""
## ⚠️ 本轮被修改的文件（重要提示）
以下文件在本轮实现中被修改，验收时应优先审查：
{chr(10).join(f"- {mf}" for mf in valid_modified[:20])}
{f"... 及其他 {len(valid_modified) - 20} 个文件" if len(valid_modified) > 20 else ""}
"""

    prompt = f"""分析验收标准，从文件列表中选择最相关的文件用于 QA 验收。

## 验收标准
{criteria_text}
{modified_hint}
## 项目文件列表（共 {len(filtered_files)} 个）
{chr(10).join(file_descriptions[:50])}
{f"... 及其他 {len(file_descriptions) - 50} 个文件" if len(file_descriptions) > 50 else ""}

## 任务
选择与验收标准最相关的文件（最多 {max_files} 个）。考虑：
1. **优先选择被修改的文件** - 这些是本轮实现的核心
2. 文件名与验收标准的语义相关性（如"登录"对应 auth.py, LoginView.vue 等）
3. 后端实现文件（路由、模型、验证逻辑）
4. 前端实现文件（视图、组件、验证逻辑）
5. 测试文件（如果验收标准涉及测试）

## 输出格式（严格 JSON）
```json
{{
  "selected_files": [
    {{"path": "文件路径", "relevance": 0.9, "reason": "简短说明为什么相关"}}
  ]
}}
```

只输出 JSON，不要其他内容。"""

    from ._observability import get_qa_observer
    observer = get_qa_observer()

    if verbose:
        observer.on_file_selection_start(len(filtered_files))

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是代码分析专家，擅长识别与需求相关的代码文件。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            label="file_selection",
            verbose=verbose,
        )
    except Exception as exc:
        if verbose:
            observer.on_file_selection_error(exc)
        # Fallback to all files with equal relevance
        return [(f, 0.5) for f in list(filtered_files.keys())[:max_files]]

    selected = result.get("selected_files", [])
    selected_with_scores = [
        (item.get("path", ""), float(item.get("relevance", 0.5)))
        for item in selected
        if item.get("path") in filtered_files
    ]

    # Log selection results
    if verbose:
        observer.on_file_selection_complete(selected_with_scores, len(filtered_files))

    return selected_with_scores


async def build_llm_driven_files_summary(
    llm: Any,
    workspace_files: dict[str, str],
    criteria: list[dict[str, Any]],
    max_total_chars: int = 35000,
    *,
    verbose: bool = False,
    mandatory_files: list[str] | None = None,
) -> str:
    """Build files summary using LLM-driven file selection.

    This function:
    1. Uses LLM to select the most relevant files for the criteria
    2. Allocates more space to highly relevant files
    3. Is language/framework agnostic
    4. ALWAYS includes mandatory_files (files modified by the requirement)

    Args:
        llm: LLM model instance
        workspace_files: Dict of file paths to content
        criteria: Acceptance criteria list
        max_total_chars: Maximum total characters for summary
        verbose: Whether to print debug info
        mandatory_files: Files that MUST be included (e.g., files modified by requirement)

    Returns:
        str: Detailed files summary optimized for QA evaluation
    """
    from ._validation import extract_file_summary
    from ._observability import get_qa_observer

    observer = get_qa_observer()

    # Use LLM to select relevant files
    # Pass modified_files as hint so LLM knows which files were changed
    # This avoids context overflow while ensuring LLM considers modified files
    selected_files = await select_relevant_files_for_qa(
        llm, workspace_files, criteria, max_files=20, verbose=verbose,
        modified_files=mandatory_files,  # Hint, not forced inclusion
    )

    if verbose and mandatory_files:
        observer.ctx.logger.debug(
            f"[QA] 提示 LLM 优先审查 {len(mandatory_files)} 个被修改的文件"
        )

    if not selected_files:
        # Fallback if LLM selection fails
        if verbose:
            observer.ctx.logger.warn("[QA] ⚠️ LLM 文件选择返回空结果，回退到默认摘要")
        return _build_files_summary_for_qa(workspace_files)

    summaries: list[str] = []
    total_chars = 0

    # Process files in order of relevance
    for file_path, relevance in selected_files:
        if file_path not in workspace_files:
            continue
        if total_chars >= max_total_chars:
            break

        content = workspace_files[file_path]

        # Allocate space based on relevance
        # High relevance (>0.7): up to 6000 chars
        # Medium relevance (0.4-0.7): up to 3000 chars
        # Low relevance (<0.4): up to 1500 chars
        if relevance >= 0.7:
            per_file_budget = 6000
        elif relevance >= 0.4:
            per_file_budget = 3000
        else:
            per_file_budget = 1500

        # Adjust budget based on remaining space
        remaining = max_total_chars - total_chars
        per_file_budget = min(per_file_budget, remaining)

        if per_file_budget < 500:
            break

        summary = extract_file_summary(content, file_path, max_chars=per_file_budget)
        if summary.strip():
            relevance_note = f"[相关度: {relevance:.1f}]" if relevance > 0 else ""
            file_summary = f"--- {file_path} {relevance_note} ---\n{summary}"
            summaries.append(file_summary)
            total_chars += len(file_summary)

    # Add note about file selection
    included_count = len(summaries)
    total_count = len(workspace_files)
    if included_count < total_count:
        summaries.append(f"\n... (共 {total_count} 个文件，LLM 选择了最相关的 {included_count} 个)")

    if verbose:
        observer.on_summary_built(included_count, total_count, total_chars)

    return "\n\n".join(summaries)


# ---------------------------------------------------------------------------
# QA Validation
# ---------------------------------------------------------------------------
async def qa_requirement(
    llm: Any,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    artifact_path: Path,
    criteria: list[dict[str, Any]],
    round_index: int,
    workspace_files: dict[str, str] | None = None,
    playwright_mcp: "StatefulClientBase | BrowserSandboxManager | None" = None,
    http_port: int | None = None,  # Deprecated, use http_url
    http_url: str | None = None,  # Full HTTP URL (e.g., http://runtime-xxxx:8080)
    *,
    verbose: bool = False,
    mandatory_files: list[str] | None = None,
    runtime_workspace: Any = None,  # RuntimeWorkspace for runtime validation
    enable_runtime_validation: bool = True,  # Whether to run Claude Code based validation
) -> dict[str, Any]:
    """Perform QA validation on a requirement implementation.

    Args:
        llm: LLM model instance
        requirement: Requirement dict
        blueprint: Blueprint dict
        artifact_path: Path to artifact file
        criteria: Acceptance criteria list
        round_index: Current round number
        workspace_files: Workspace files dict
        playwright_mcp: Playwright test client
        http_port: HTTP server port (deprecated, use http_url)
        http_url: Full HTTP URL for accessing workspace files
        verbose: Whether to print debug info
        mandatory_files: Files that MUST be included in QA review (files modified by this requirement)
        runtime_workspace: RuntimeWorkspace for runtime validation using Claude Code
        enable_runtime_validation: Whether to enable runtime validation (default True)

    Returns:
        dict: Raw QA report (use _normalize_qa_report to normalize)
    """
    from ._llm_utils import call_llm_json
    from ._sandbox import BrowserSandboxManager, run_playwright_test, run_browser_sandbox_test
    from ._observability import get_qa_observer

    observer = get_qa_observer()
    req_id = requirement.get("id", "unknown")
    req_title = requirement.get("title", "")

    # ---------------------------------------------------------------------------
    # NEW: Runtime Validation using Claude Code
    # ---------------------------------------------------------------------------
    runtime_validation_result = None
    runtime_feedback = ""

    if enable_runtime_validation and runtime_workspace:
        from ._qa_runtime import qa_runtime_validation

        if verbose:
            observer.ctx.logger.info(f"[QA] 开始运行时验证 (使用 Claude Code)...")

        try:
            runtime_validation_result = await qa_runtime_validation(
                runtime_workspace=runtime_workspace,
                blueprint=blueprint,
                playwright_mcp=playwright_mcp,
                http_url=http_url or (f"http://127.0.0.1:{http_port}" if http_port else None),
                verbose=verbose,
            )

            if not runtime_validation_result.get("overall_success", True):
                runtime_feedback = runtime_validation_result.get("feedback_for_agent", "")
                if verbose:
                    error_count = len(runtime_validation_result.get("all_errors", []))
                    observer.ctx.logger.warn(f"[QA] 运行时验证发现 {error_count} 个错误")

        except Exception as e:
            if verbose:
                observer.ctx.logger.error(f"[QA] 运行时验证失败: {e}")
            runtime_feedback = f"运行时验证执行失败: {e}"

    if verbose:
        observer.on_qa_start(req_id, req_title, len(criteria))

    # Build artifact description using LLM-driven file selection
    if workspace_files:
        artifact_desc = f"工作区文件摘要 (共 {len(workspace_files)} 个文件):\n"
        # Use LLM to select and prioritize files relevant to criteria
        # CRITICAL: Pass mandatory_files to ensure files modified by this requirement are always reviewed
        artifact_desc += await build_llm_driven_files_summary(
            llm, workspace_files, criteria, verbose=verbose,
            mandatory_files=mandatory_files,
        )
    elif artifact_path is not None:
        artifact_content = artifact_path.read_text(encoding="utf-8")
        artifact_desc = f"交付物 (文件 {artifact_path.name}，截断前 6000 字符):\n{artifact_content[:6000]}"
    else:
        artifact_desc = "无交付物文件可用"

    # Playwright testing
    playwright_results = ""
    # Use http_url if available, otherwise fall back to http_port
    effective_http_url = http_url or (f"http://127.0.0.1:{http_port}" if http_port else None)
    if playwright_mcp and effective_http_url:
        artifact_type = blueprint.get("artifact_type", "")
        if artifact_type == "web" or (workspace_files and any(f.endswith(".html") for f in workspace_files)):
            html_file = "app.html"
            if workspace_files:
                for fname in workspace_files:
                    if fname.endswith(".html"):
                        html_file = fname
                        break
            elif artifact_path and artifact_path.suffix == ".html":
                html_file = artifact_path.name

            page_url = f"{effective_http_url}/{html_file}"
            if verbose:
                observer.on_playwright_test(page_url)

            test_steps = [
                {"name": "页面加载", "action": "check_text", "expected": ""},
                {"name": "截图", "action": "screenshot"},
            ]

            try:
                if isinstance(playwright_mcp, BrowserSandboxManager):
                    pw_result = run_browser_sandbox_test(
                        playwright_mcp, page_url, test_steps, verbose=verbose
                    )
                else:
                    pw_result = await run_playwright_test(
                        playwright_mcp, page_url, test_steps, verbose=verbose
                    )

                playwright_results = f"\n\n【Playwright 自动化测试结果】\n"
                playwright_results += f"整体通过: {pw_result['passed']}\n"
                for r in pw_result.get("results", []):
                    status = "✓" if r.get("passed") else "✗"
                    playwright_results += f"  {status} {r.get('step')}: {r.get('result')}\n"
            except Exception as e:
                playwright_results = f"\n\n【Playwright 测试失败】{e}\n"

    # Build summaries
    requirement_summary = _build_requirement_summary(requirement)
    blueprint_summary = _build_blueprint_summary(blueprint)
    criteria_str = json.dumps(criteria, ensure_ascii=False, indent=2)

    # Build example criteria IDs
    criteria_ids = [c.get("id", f"C{i}") for i, c in enumerate(criteria)]
    example_criteria = []
    for cid in criteria_ids[:2]:
        example_criteria.append(
            f'{{"id": "{cid}", "name": "标准名称", "pass": false, "reason": "未找到相关实现", "recommendation": "需要添加..."}}'
        )
    example_criteria_str = ",\n            ".join(example_criteria) if example_criteria else '{"id": "C1", "name": "示例", "pass": false, "reason": "...", "recommendation": "..."}'

    # Build runtime validation section
    runtime_section = ""
    if runtime_validation_result:
        runtime_section = "\n\n## 【重要】运行时验证结果\n"
        if runtime_validation_result.get("overall_success"):
            runtime_section += "✓ 运行时验证通过\n"
        else:
            runtime_section += "✗ 运行时验证失败\n"
            runtime_section += runtime_feedback
            runtime_section += "\n\n**注意：运行时验证发现的错误必须标记为未通过！**\n"

    prompt = textwrap.dedent(f"""
        ## 需求摘要
        {requirement_summary}

        ## Blueprint 摘要
        {blueprint_summary}

        ## 验收标准（共 {len(criteria)} 条，请逐条验收）
        {criteria_str}

        ## 代码产物
        {artifact_desc}
        {playwright_results}
        {runtime_section}

        ## 任务
        请严格按照上述验收标准逐条检查代码产物，**必须**为每条验收标准输出判定结果。

        **重要**：如果运行时验证发现了错误（如构建失败、导入错误、启动失败等），相关的验收标准必须标记为 pass: false。

        ## 输出格式
        ```json
        {{
          "round": {round_index},
          "criteria": [
            {example_criteria_str}
          ],
          "overall_pass": false,
          "improvements": "需要改进的内容"
        }}
        ```

        ## 要求
        1. criteria 数组必须包含 {len(criteria)} 条记录
        2. 每条记录必须包含：id, name, pass (布尔值), reason, recommendation
        3. pass 字段必须是 true 或 false
        4. 只输出 JSON
    """)

    qa_report, _ = await call_llm_json(
        llm,
        [
            {
                "role": "system",
                "content": "你是资深 QA 工程师，负责验收代码产物。输出严格的 JSON 格式结果。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        label=f"qa:{requirement.get('id', '')}",
        verbose=verbose,
    )

    if verbose:
        # Quick summary of results
        criteria_results = qa_report.get("criteria", [])
        passed_count = sum(1 for c in criteria_results if c.get("pass"))
        total_count = len(criteria_results)
        overall_passed = qa_report.get("overall_pass", False)

        # Log each criterion result
        for c in criteria_results:
            observer.on_criterion_result(
                c.get("id", ""),
                c.get("name", ""),
                c.get("pass", False),
                c.get("reason", ""),
            )

        observer.on_qa_complete(req_id, overall_passed, passed_count, total_count)

    # Attach runtime validation result and feedback to QA report
    if runtime_validation_result:
        qa_report["runtime_validation"] = runtime_validation_result
        qa_report["runtime_feedback"] = runtime_feedback

        # If runtime validation failed, force overall_pass to False
        if not runtime_validation_result.get("overall_success", True):
            qa_report["overall_pass"] = False
            if not qa_report.get("improvements"):
                qa_report["improvements"] = runtime_feedback
            else:
                qa_report["improvements"] = runtime_feedback + "\n\n" + qa_report["improvements"]

    return qa_report


# ---------------------------------------------------------------------------
# PR Mode QA Validation
# ---------------------------------------------------------------------------
async def qa_requirement_pr(
    llm: Any,
    requirement: dict[str, Any],
    criteria: list[dict[str, Any]],
    pr_diff: str,
    delivery_files: list[str],
    working_files: list[str],
    blueprint: dict[str, Any] | None = None,
    runtime_workspace: "RuntimeWorkspaceWithPR | None" = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """PR mode QA validation for reviewing code changes.

    This function performs QA validation in PR (Pull Request) mode,
    where changes are reviewed as incremental diffs rather than
    evaluating the entire codebase.

    Validation flow:
    1. Incremental validation: Check if diff satisfies requirements
    2. Code quality check: Verify new/modified code meets standards
    3. Runtime validation: Run tests in working directory (if workspace provided)

    Args:
        llm (`Any`):
            LLM model instance for generating QA evaluation.
        requirement (`dict[str, Any]`):
            Requirement information dict with 'id', 'title', 'description' etc.
        criteria (`list[dict[str, Any]]`):
            Acceptance criteria list, each with 'id', 'title', 'description'.
        pr_diff (`str`):
            Git diff format string showing changes between delivery and working.
        delivery_files (`list[str]`):
            List of file paths in the delivery directory.
        working_files (`list[str]`):
            List of file paths in the working directory.
        blueprint (`dict[str, Any] | None`):
            Optional design blueprint for additional context.
        runtime_workspace (`RuntimeWorkspaceWithPR | None`):
            Optional runtime workspace for executing validation commands.
        verbose (`bool`):
            Whether to print debug information.

    Returns:
        `dict[str, Any]`:
            QA report containing:
            - overall_pass: bool indicating if all criteria passed
            - criteria: list of individual criterion results
            - improvements: suggested improvements if any criteria failed
            - changed_files: list of files modified in the PR
    """
    from ._llm_utils import call_llm_json
    from ._observability import get_qa_observer

    observer = get_qa_observer()
    req_id = requirement.get("id", "unknown")
    req_title = requirement.get("title", "")

    if verbose:
        observer.on_qa_start(req_id, req_title, len(criteria))
        observer.ctx.logger.info(f"[QA-PR] 开始 PR Review 模式验收")

    # ---------------------------------------------------------------------------
    # Extract changed files from diff
    # ---------------------------------------------------------------------------
    changed_files = _extract_changed_files(pr_diff)
    if verbose:
        observer.ctx.logger.debug(f"[QA-PR] 检测到 {len(changed_files)} 个变更文件")

    # ---------------------------------------------------------------------------
    # Runtime Validation (if workspace provided)
    # ---------------------------------------------------------------------------
    runtime_validation_result = None
    runtime_feedback = ""

    if runtime_workspace:
        from ._qa_runtime import qa_runtime_validation

        if verbose:
            observer.ctx.logger.info("[QA-PR] 开始运行时验证...")

        try:
            runtime_validation_result = await qa_runtime_validation(
                runtime_workspace=runtime_workspace,
                blueprint=blueprint or {},
                playwright_mcp=None,  # PR mode doesn't use browser testing by default
                http_url=runtime_workspace.http_url,
                verbose=verbose,
            )

            if not runtime_validation_result.get("overall_success", True):
                runtime_feedback = runtime_validation_result.get("feedback_for_agent", "")
                if verbose:
                    error_count = len(runtime_validation_result.get("all_errors", []))
                    observer.ctx.logger.warn(f"[QA-PR] 运行时验证发现 {error_count} 个错误")

        except Exception as e:
            if verbose:
                observer.ctx.logger.error(f"[QA-PR] 运行时验证失败: {e}")
            runtime_feedback = f"运行时验证执行失败: {e}"

    # ---------------------------------------------------------------------------
    # Build PR Review Context
    # ---------------------------------------------------------------------------
    # Build optimized diff context for large diffs
    pr_context = await _build_pr_context(pr_diff, {}, max_context_chars=15000)

    # Build requirement description
    requirement_desc = _build_requirement_summary(requirement)

    # Build blueprint summary if available
    blueprint_desc = ""
    if blueprint:
        blueprint_desc = f"\n### 设计蓝图\n{_build_blueprint_summary(blueprint)}"

    # Format criteria
    criteria_str = json.dumps(criteria, ensure_ascii=False, indent=2)

    # Build example criteria format
    criteria_ids = [c.get("id", f"C{i}") for i, c in enumerate(criteria)]
    example_criteria = []
    for cid in criteria_ids[:2]:
        example_criteria.append(
            f'{{"id": "{cid}", "name": "标准名称", "pass": false, '
            f'"reason": "原因说明", "recommendation": "改进建议"}}'
        )
    example_criteria_str = ",\n            ".join(example_criteria) if example_criteria else (
        '{"id": "C1", "name": "示例", "pass": false, "reason": "...", "recommendation": "..."}'
    )

    # Build runtime validation section
    runtime_section = ""
    if runtime_validation_result:
        runtime_section = "\n\n## 【重要】运行时验证结果\n"
        if runtime_validation_result.get("overall_success"):
            runtime_section += "✓ 运行时验证通过\n"
        else:
            runtime_section += "✗ 运行时验证失败\n"
            runtime_section += runtime_feedback
            runtime_section += "\n\n**注意：运行时验证发现的错误必须标记为未通过！**\n"

    # Build the full prompt
    prompt = textwrap.dedent(f"""
        ## PR Review 验收模式

        本次验收采用增量审查模式，仅评估本次变更（PR diff）是否满足需求。

        ### 需求摘要
        {requirement_desc}
        {blueprint_desc}

        ### 变更的文件 ({len(changed_files)} 个)
        {chr(10).join(f"- {f}" for f in changed_files[:20])}
        {f"... 及其他 {len(changed_files) - 20} 个文件" if len(changed_files) > 20 else ""}

        ### 变更差异 (git diff)
        ```diff
        {pr_context}
        ```

        ### 验收标准（共 {len(criteria)} 条）
        {criteria_str}
        {runtime_section}

        ## 任务
        请作为 QA 工程师审查本次 PR：
        1. 检查 diff 是否**完整实现**了需求描述的功能
        2. 检查新增代码是否符合**项目规范**
        3. 检查是否有**潜在的回归风险**（影响其他功能）
        4. 检查**边界条件**和**错误处理**

        **重要**：
        - 仅基于 diff 内容判断，不要假设 diff 之外的实现
        - 如果运行时验证失败，相关验收标准必须标记为 pass: false

        ## 输出格式
        ```json
        {{
          "criteria": [
            {example_criteria_str}
          ],
          "overall_pass": false,
          "improvements": "需要改进的内容"
        }}
        ```

        ## 要求
        1. criteria 数组必须包含 {len(criteria)} 条记录
        2. 每条记录必须包含：id, name, pass (布尔值), reason, recommendation
        3. pass 字段必须是 true 或 false
        4. 只输出 JSON
    """)

    qa_report, _ = await call_llm_json(
        llm,
        [
            {
                "role": "system",
                "content": (
                    "你是资深 QA 工程师，负责审查代码变更（PR）。"
                    "你需要基于 git diff 评估变更是否满足需求。"
                    "输出严格的 JSON 格式结果。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        label=f"qa-pr:{requirement.get('id', '')}",
        verbose=verbose,
    )

    # Normalize the report
    qa_report = _normalize_qa_report(qa_report, criteria)

    # Add PR-specific metadata
    qa_report["mode"] = "pr_review"
    qa_report["changed_files"] = changed_files

    if verbose:
        criteria_results = qa_report.get("criteria", [])
        passed_count = sum(1 for c in criteria_results if c.get("pass"))
        total_count = len(criteria_results)
        overall_passed = qa_report.get("overall_pass", False)

        for c in criteria_results:
            observer.on_criterion_result(
                c.get("id", ""),
                c.get("name", ""),
                c.get("pass", False),
                c.get("reason", ""),
            )

        observer.on_qa_complete(req_id, overall_passed, passed_count, total_count)

    # Attach runtime validation result
    if runtime_validation_result:
        qa_report["runtime_validation"] = runtime_validation_result
        qa_report["runtime_feedback"] = runtime_feedback

        # Force overall_pass to False if runtime validation failed
        if not runtime_validation_result.get("overall_success", True):
            qa_report["overall_pass"] = False
            if not qa_report.get("improvements"):
                qa_report["improvements"] = runtime_feedback
            else:
                qa_report["improvements"] = runtime_feedback + "\n\n" + qa_report["improvements"]

    return qa_report


__all__ = [
    "_normalize_qa_report",
    "_build_requirement_summary",
    "_build_blueprint_summary",
    "_build_files_summary_for_qa",
    "select_relevant_files_for_qa",
    "build_llm_driven_files_summary",
    "qa_requirement",
    "qa_requirement_pr",
    "_extract_changed_files",
    "_build_pr_context",
]
