# -*- coding: utf-8 -*-
"""QA Runtime Validation using Claude Code.

This module provides framework-agnostic runtime validation for QA:
1. Uses blueprint's tech_stack info (from project memory) to know project type
2. Claude Code runs appropriate tests based on tech_stack
3. Collects errors without fixing - passes them to next iteration
4. Performs Playwright e2e testing if frontend is detected

Key Design Principles:
- Uses project memory (blueprint.tech_stack) for project info
- NO hardcoded framework logic - Claude Code decides how to test
- Errors are collected, not fixed
- Feedback goes to next round's Agent
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ._sandbox import RuntimeWorkspace, BrowserSandboxManager
    from agentscope.mcp import StatefulClientBase


# ---------------------------------------------------------------------------
# Project Analysis (Using Blueprint Info)
# ---------------------------------------------------------------------------
async def analyze_and_test_project(
    runtime_workspace: "RuntimeWorkspace",
    blueprint: dict[str, Any],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Use Claude Code to run tests based on blueprint's tech_stack.

    This function uses project memory (blueprint.tech_stack) to know
    what type of project this is, then asks Claude Code to run
    appropriate tests.

    Args:
        runtime_workspace: RuntimeWorkspace for container operations
        blueprint: Blueprint dict containing tech_stack info
        verbose: Whether to print debug info

    Returns:
        dict with:
        - success: bool
        - project_info: detected project information
        - backend_result: backend test result (if applicable)
        - frontend_result: frontend test result (if applicable)
        - all_errors: list of all errors found
        - suggestions: list of fix suggestions
    """
    from ._claude_code import claude_code_edit, set_container_context
    from ._observability import get_logger

    logger = get_logger()

    # Get container context
    container_id = getattr(runtime_workspace, "container_id", None)
    if not container_id:
        if verbose:
            logger.warn("[QA-Runtime] No container context, skipping runtime analysis")
        return {
            "success": True,
            "skipped": True,
            "reason": "No container context",
            "all_errors": [],
        }

    # Set container context for Claude Code
    set_container_context(container_id, "/workspace")

    # Extract tech_stack from blueprint
    tech_stack = blueprint.get("tech_stack", {})
    project_type = blueprint.get("project_type", "unknown")
    backend_tech = tech_stack.get("backend", "")
    frontend_tech = tech_stack.get("frontend", "")
    database_tech = tech_stack.get("database", "")

    # Determine what needs testing
    has_backend = bool(backend_tech and backend_tech.lower() not in ["无", "none", "null", "", "n/a"])
    has_frontend = bool(frontend_tech and frontend_tech.lower() not in ["无", "none", "null", "", "n/a"])

    # Non-code project types that don't need runtime testing
    non_code_types = ["docs", "documentation", "design", "config", "other", "文档", "设计", "配置"]
    is_non_code = project_type.lower() in non_code_types

    # Skip if no code to test
    if not has_backend and not has_frontend:
        if verbose:
            logger.info(f"[QA-Runtime] 项目类型: {project_type} - 无代码需要验证，跳过运行时测试")
        return {
            "success": True,
            "skipped": True,
            "reason": "Non-code project (no backend/frontend in tech_stack)",
            "all_errors": [],
            "project_info": {
                "type": project_type,
                "has_backend": False,
                "has_frontend": False,
                "needs_runtime_test": False,
            },
        }

    if is_non_code:
        if verbose:
            logger.info(f"[QA-Runtime] 项目类型: {project_type} - 非代码项目，跳过运行时测试")
        return {
            "success": True,
            "skipped": True,
            "reason": f"Non-code project type: {project_type}",
            "all_errors": [],
            "project_info": {
                "type": project_type,
                "has_backend": has_backend,
                "has_frontend": has_frontend,
                "needs_runtime_test": False,
            },
        }

    if verbose:
        logger.info(f"[QA-Runtime] 项目类型: {project_type}")
        logger.info(f"[QA-Runtime] 技术栈 - 后端: {backend_tech}, 前端: {frontend_tech}, 数据库: {database_tech}")

    # Build prompt with project info from blueprint
    prompt = f"""你是一个 QA 工程师，需要验证当前项目能否正常运行。

## 项目信息（来自项目记忆）

- **项目类型**: {project_type}
- **后端技术**: {backend_tech or "无"}
- **前端技术**: {frontend_tech or "无"}
- **数据库**: {database_tech or "无"}

## 第一步：确认项目结构

快速检查项目目录，确认实际的文件结构：
```bash
ls -la
```

根据上面的项目信息，找到对应的入口文件。

## 第二步：验证项目

{"### 后端验证（" + backend_tech + "）" if has_backend else ""}
{'''
1. 进入后端目录（如果有独立目录）
2. 检查/安装依赖
3. 验证代码能否正常导入（不要实际启动长期运行的服务）
4. 记录所有错误

常见验证命令：
- Python/FastAPI/Django/Flask: `pip install -r requirements.txt && python -c "from app.main import app"` 或类似
- Node.js/Express: `npm install && node -e "require('./app')"`
- Go: `go build ./...`
- Rust: `cargo check`
''' if has_backend else ""}

{"### 前端验证（" + frontend_tech + "）" if has_frontend else ""}
{'''
1. 进入前端目录（如果有独立目录）
2. 安装依赖：`npm install`
3. 运行构建测试：`npm run build`
4. 记录所有错误
''' if has_frontend else ""}

## 第三步：输出结果

严格按以下 JSON 格式输出结果：
```json
{{
  "project_info": {{
    "type": "{project_type}",
    "backend_lang": "检测到的后端语言",
    "backend_framework": "{backend_tech or 'null'}",
    "frontend_framework": "{frontend_tech or 'null'}",
    "has_backend": {str(has_backend).lower()},
    "has_frontend": {str(has_frontend).lower()},
    "needs_runtime_test": true
  }},
  "backend_result": {{
    "tested": true/false,
    "success": true/false,
    "commands_run": ["执行的命令列表"],
    "errors": ["错误1", "错误2"],
    "warnings": ["警告1"]
  }},
  "frontend_result": {{
    "tested": true/false,
    "success": true/false,
    "commands_run": ["执行的命令列表"],
    "errors": ["错误1", "错误2"],
    "warnings": ["警告1"]
  }},
  "overall_success": true/false,
  "all_errors": ["所有错误的汇总列表"],
  "suggestions": ["修复建议1", "修复建议2"]
}}
```

## 重要规则：
1. **不要修复任何错误**，只收集和报告
2. **不要启动长期运行的服务**，只做导入/编译检查
3. 如果遇到 ModuleNotFoundError、ImportError、Cannot find module 等，完整记录错误信息
4. 只输出最终的 JSON 结果，不要输出中间过程"""

    try:
        result = await claude_code_edit(prompt=prompt, timeout=300)
        # TextBlock is a TypedDict, so access via ["text"] not .text
        result_text = result.content[0]["text"] if result.content else ""

        # Parse JSON from result
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                test_result = json.loads(json_match.group())
                if verbose:
                    project_type = test_result.get("project_info", {}).get("type", "unknown")
                    success = test_result.get("overall_success", False)
                    status = "✓" if success else "✗"
                    logger.info(f"[QA-Runtime] 项目类型: {project_type}, 结果: {status}")

                    for err in test_result.get("all_errors", [])[:5]:
                        logger.error(f"[QA-Runtime] 错误: {err[:100]}")

                return test_result
            except json.JSONDecodeError as e:
                if verbose:
                    logger.warn(f"[QA-Runtime] JSON 解析失败: {e}")
                return {
                    "success": False,
                    "all_errors": [f"JSON parse error: {e}"],
                    "raw_output": result_text[:1000],
                }
        else:
            if verbose:
                logger.warn(f"[QA-Runtime] 无法从输出中提取 JSON")
            return {
                "success": False,
                "all_errors": ["No JSON found in output"],
                "raw_output": result_text[:1000],
            }

    except Exception as e:
        if verbose:
            logger.error(f"[QA-Runtime] 执行失败: {e}")
        return {
            "success": False,
            "all_errors": [f"Execution error: {str(e)}"],
        }


# ---------------------------------------------------------------------------
# E2E Test with Playwright (Framework Agnostic)
# ---------------------------------------------------------------------------
async def run_e2e_test(
    runtime_workspace: "RuntimeWorkspace",
    playwright_mcp: "StatefulClientBase | BrowserSandboxManager | None",
    http_url: str,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run end-to-end tests using Playwright.

    This test is framework-agnostic - it simply:
    1. Navigates to the URL
    2. Checks if the page loads
    3. Looks for console errors
    4. Takes screenshots

    Args:
        runtime_workspace: RuntimeWorkspace for container operations
        playwright_mcp: Playwright MCP client or BrowserSandboxManager
        http_url: URL to access the frontend
        verbose: Whether to print debug info

    Returns:
        dict with test results
    """
    from ._sandbox import BrowserSandboxManager, run_playwright_test, run_browser_sandbox_test
    from ._observability import get_logger

    logger = get_logger()

    if not playwright_mcp or not http_url:
        return {
            "tested": False,
            "success": True,
            "reason": "No Playwright or HTTP URL configured",
            "errors": [],
        }

    if verbose:
        logger.info(f"[QA-E2E] 执行页面测试: {http_url}")

    test_steps = [
        {"name": "页面加载", "action": "check_text", "expected": ""},
        {"name": "截图", "action": "screenshot"},
    ]

    results = {
        "tested": True,
        "success": True,
        "errors": [],
        "screenshots": [],
        "console_errors": [],
    }

    try:
        if isinstance(playwright_mcp, BrowserSandboxManager):
            pw_result = run_browser_sandbox_test(
                playwright_mcp, http_url, test_steps, verbose=verbose
            )
        else:
            pw_result = await run_playwright_test(
                playwright_mcp, http_url, test_steps, verbose=verbose
            )

        results["success"] = pw_result.get("passed", False)

        if not results["success"]:
            results["errors"].append(pw_result.get("error", "Page load failed"))

        # Collect screenshots
        for r in pw_result.get("results", []):
            if "screenshot" in r.get("step", "").lower():
                results["screenshots"].append(r.get("result", ""))

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"E2E test error: {str(e)}")

    if verbose:
        status = "✓" if results["success"] else "✗"
        logger.info(f"[QA-E2E] 测试结果: {status}")

    return results


# ---------------------------------------------------------------------------
# Main QA Runtime Validation
# ---------------------------------------------------------------------------
async def qa_runtime_validation(
    runtime_workspace: "RuntimeWorkspace",
    blueprint: dict[str, Any],
    playwright_mcp: "StatefulClientBase | BrowserSandboxManager | None" = None,
    http_url: str | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Perform complete runtime validation for QA.

    This is the main entry point for runtime QA validation.
    Uses blueprint's tech_stack info from project memory to know
    what type of project this is, then Claude Code runs appropriate tests.

    Args:
        runtime_workspace: RuntimeWorkspace for container operations
        blueprint: Blueprint dict containing tech_stack info from project memory
        playwright_mcp: Playwright client for e2e testing
        http_url: HTTP URL for accessing frontend
        verbose: Whether to print debug info

    Returns:
        dict with:
        - overall_success: bool
        - project_analysis: project structure analysis
        - backend_result: backend test result (if applicable)
        - frontend_result: frontend test result (if applicable)
        - e2e_result: e2e test result (if applicable)
        - all_errors: combined list of all errors
        - feedback_for_agent: formatted feedback for next iteration
    """
    from ._observability import get_logger

    logger = get_logger()

    if verbose:
        logger.info("[QA-Runtime] 开始运行时验证...")

    # Step 1: Use Claude Code to test the project (using blueprint's tech_stack)
    test_result = await analyze_and_test_project(
        runtime_workspace, blueprint, verbose=verbose
    )

    # Handle skipped case
    if test_result.get("skipped"):
        return {
            "overall_success": True,
            "skipped": True,
            "reason": test_result.get("reason", "Skipped"),
            "all_errors": [],
            "feedback_for_agent": "",
        }

    # Build result structure
    result = {
        "overall_success": test_result.get("overall_success", False),
        "project_info": test_result.get("project_info", {}),
        "backend_result": test_result.get("backend_result"),
        "frontend_result": test_result.get("frontend_result"),
        "e2e_result": None,
        "all_errors": test_result.get("all_errors", []),
        "suggestions": test_result.get("suggestions", []),
        "feedback_for_agent": "",
    }

    # Step 2: Run E2E tests if frontend exists and we have playwright
    project_info = test_result.get("project_info", {})
    has_frontend = project_info.get("has_frontend", False)

    if has_frontend and playwright_mcp and http_url:
        # Only run E2E if frontend build succeeded (or wasn't tested)
        frontend_result = test_result.get("frontend_result", {})
        frontend_ok = not frontend_result.get("tested") or frontend_result.get("success", False)

        if frontend_ok:
            e2e_result = await run_e2e_test(
                runtime_workspace, playwright_mcp, http_url, verbose=verbose
            )
            result["e2e_result"] = e2e_result

            if e2e_result.get("tested") and not e2e_result.get("success"):
                result["overall_success"] = False
                result["all_errors"].extend(e2e_result.get("errors", []))

    # Step 3: Generate feedback for agent
    result["feedback_for_agent"] = _generate_feedback(result)

    if verbose:
        status = "✓ 通过" if result["overall_success"] else "✗ 失败"
        error_count = len(result["all_errors"])
        logger.info(f"[QA-Runtime] 运行时验证完成: {status} ({error_count} 个错误)")

    return result


def _generate_feedback(result: dict[str, Any]) -> str:
    """Generate feedback message for the next agent iteration.

    Args:
        result: Runtime validation result

    Returns:
        Formatted feedback string
    """
    if result.get("overall_success"):
        return ""

    feedback_parts = ["## 运行时验证发现以下问题，请修复：\n"]

    # Project info
    project_info = result.get("project_info", {})
    if project_info:
        feedback_parts.append(f"项目类型: {project_info.get('type', 'unknown')}")
        if project_info.get("backend_framework"):
            feedback_parts.append(f"后端: {project_info.get('backend_lang', '')} / {project_info.get('backend_framework', '')}")
        if project_info.get("frontend_framework"):
            feedback_parts.append(f"前端: {project_info.get('frontend_framework', '')}")
        feedback_parts.append("")

    # Backend errors
    backend = result.get("backend_result", {})
    if backend and backend.get("tested") and not backend.get("success"):
        feedback_parts.append("### 后端错误")
        for cmd in backend.get("commands_run", []):
            feedback_parts.append(f"- 执行: `{cmd}`")
        for err in backend.get("errors", []):
            feedback_parts.append(f"- ❌ {err}")
        feedback_parts.append("")

    # Frontend errors
    frontend = result.get("frontend_result", {})
    if frontend and frontend.get("tested") and not frontend.get("success"):
        feedback_parts.append("### 前端错误")
        for cmd in frontend.get("commands_run", []):
            feedback_parts.append(f"- 执行: `{cmd}`")
        for err in frontend.get("errors", []):
            feedback_parts.append(f"- ❌ {err}")
        feedback_parts.append("")

    # E2E errors
    e2e = result.get("e2e_result", {})
    if e2e and e2e.get("tested") and not e2e.get("success"):
        feedback_parts.append("### E2E 测试错误")
        for err in e2e.get("errors", []):
            feedback_parts.append(f"- ❌ {err}")
        feedback_parts.append("")

    # Suggestions
    suggestions = result.get("suggestions", [])
    if suggestions:
        feedback_parts.append("### 修复建议")
        for s in suggestions:
            feedback_parts.append(f"- 💡 {s}")
        feedback_parts.append("")

    return "\n".join(feedback_parts)


__all__ = [
    "analyze_and_test_project",
    "run_e2e_test",
    "qa_runtime_validation",
]
