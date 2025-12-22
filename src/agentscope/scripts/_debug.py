# -*- coding: utf-8 -*-
"""Agent-driven debug utilities.

This module provides language-agnostic debugging capabilities by leveraging
LLM to analyze validation errors and generate fix commands.
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ._sandbox import RuntimeWorkspace


@dataclass
class DebugResult:
    """Result of agent-driven debugging.

    Attributes:
        fixed: Whether errors were fixed
        actions_taken: List of actions taken during debugging
        remaining_errors: List of errors that couldn't be fixed
        commands_executed: List of commands that were executed
        ignored_errors: List of errors that were safely ignored (false positives)
    """

    fixed: bool = False
    actions_taken: list[str] = field(default_factory=list)
    remaining_errors: list[str] = field(default_factory=list)
    commands_executed: list[str] = field(default_factory=list)
    ignored_errors: list[str] = field(default_factory=list)


DEBUG_ANALYSIS_PROMPT = """你是一个代码调试专家。分析以下验证错误，并生成修复命令。

## 项目信息
{project_context}

## 验证错误
{errors}

## 任务
分析这些错误，将它们分为三类：
1. **可忽略的错误（假阳性）**：不是真正的问题，可以安全忽略
2. **可通过命令修复**：通过执行命令可以修复（如安装依赖）
3. **需要修改代码**：必须修改源代码才能解决

### 常见的假阳性错误（应标记为可忽略）
- node_modules、vendor、.git 等依赖目录中的文件问题
- 第三方库内部的空文件、格式问题
- 构建产物目录（dist、build、__pycache__）中的问题
- 测试覆盖率报告等生成文件的问题
- 某些库设计上就是空的占位文件

### 可执行的修复命令类型
- 安装缺失的包（pip install, npm install, go get 等）
- 初始化配置（如创建 __init__.py, 配置环境变量）
- 运行构建命令（npm run build, go build 等）

### 不应该执行的操作
- 修改源代码（这需要重新生成）
- 删除文件
- 执行危险命令

## 输出格式
```json
{{
    "analysis": "错误原因分析",
    "ignorable_errors": [
        {{
            "error": "原始错误信息",
            "reason": "为什么可以忽略"
        }}
    ],
    "fixable_by_command": true/false,
    "fix_commands": [
        {{
            "command": "要执行的命令",
            "description": "命令说明",
            "working_dir": "工作目录（可选，如 backend 或 frontend）"
        }}
    ],
    "code_issues": [
        {{
            "file": "需要修改的文件",
            "issue": "问题描述",
            "suggestion": "修复建议"
        }}
    ],
    "summary": "总结"
}}
```

注意：
- 优先判断错误是否为假阳性，避免不必要的修复操作
- 只生成安全的修复命令
- 如果错误是代码结构问题（如引用了不存在的模块），记录在 code_issues 中
- 优先使用项目已确定的包管理器
"""


async def analyze_and_fix_errors(
    llm: Any,
    runtime_workspace: "RuntimeWorkspace",
    errors: list[str],
    project_context: str = "",
    *,
    max_commands: int = 5,
    verbose: bool = False,
) -> DebugResult:
    """Use LLM to analyze errors and execute fix commands.

    This function:
    1. Sends errors to LLM for analysis
    2. Executes safe fix commands (like installing packages)
    3. Returns results for further handling

    Args:
        llm: LLM model instance
        runtime_workspace: RuntimeWorkspace for command execution
        errors: List of error messages to analyze
        project_context: Project context (tech stack, etc.)
        max_commands: Maximum number of commands to execute
        verbose: Whether to print debug info

    Returns:
        DebugResult with actions taken and remaining errors
    """
    from ._llm_utils import call_llm_json

    if not runtime_workspace or not runtime_workspace.is_initialized:
        return DebugResult(
            fixed=False,
            remaining_errors=["No runtime workspace available"],
        )

    if not errors:
        return DebugResult(fixed=True, actions_taken=["No errors to fix"])

    # Format errors for prompt
    errors_text = "\n".join(f"- {err}" for err in errors[:10])  # Limit to 10 errors

    prompt = DEBUG_ANALYSIS_PROMPT.format(
        project_context=project_context or "（未提供项目上下文）",
        errors=errors_text,
    )

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是代码调试专家，分析错误并生成安全的修复命令。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            label="debug_analysis",
            verbose=verbose,
        )
    except Exception as exc:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Debug] LLM analysis failed: {exc}")
        return DebugResult(
            fixed=False,
            remaining_errors=[f"LLM analysis failed: {exc}"],
        )

    actions: list[str] = []
    commands_executed: list[str] = []
    remaining: list[str] = []
    ignored: list[str] = []

    # Process ignorable errors first
    ignorable_errors = result.get("ignorable_errors", [])
    for item in ignorable_errors:
        error_msg = item.get("error", "")
        reason = item.get("reason", "")
        ignored.append(f"{error_msg}")
        actions.append(f"⊘ 忽略: {error_msg[:50]}... ({reason[:30]})")

    # Check if fixable by command
    if not result.get("fixable_by_command", False):
        # Record code issues as remaining errors
        code_issues = result.get("code_issues", [])
        for issue in code_issues:
            remaining.append(f"{issue.get('file', 'unknown')}: {issue.get('issue', '')}")
        actions.append(f"分析完成: {result.get('summary', '需要修改代码')}")

        # If all errors were ignored, consider it fixed
        all_fixed = len(remaining) == 0 and len(ignored) > 0

        return DebugResult(
            fixed=all_fixed,
            actions_taken=actions,
            remaining_errors=remaining,
            ignored_errors=ignored,
        )

    # Execute fix commands
    fix_commands = result.get("fix_commands", [])[:max_commands]

    for cmd_spec in fix_commands:
        command = cmd_spec.get("command", "")
        description = cmd_spec.get("description", "")
        working_dir = cmd_spec.get("working_dir")

        if not command:
            continue

        # Safety check - skip dangerous commands
        dangerous_patterns = ["rm -rf", "sudo", "chmod 777", "> /dev", "curl | sh", "wget | sh"]
        if any(pattern in command.lower() for pattern in dangerous_patterns):
            remaining.append(f"跳过危险命令: {command}")
            continue

        # Handle working directory by prepending cd command
        full_command = command
        if working_dir:
            full_command = f"cd {working_dir} && {command}"

        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Debug] 执行: {full_command} ({description})")

        try:
            exec_result = runtime_workspace.execute_command(
                full_command,
                timeout=120,
            )

            if exec_result.get("success"):
                actions.append(f"✓ {description}: {command}")
                commands_executed.append(command)
            else:
                error_msg = exec_result.get("error", "")[:100]
                actions.append(f"✗ {description} 失败: {error_msg}")
                remaining.append(f"命令失败: {command}")

        except Exception as exc:
            actions.append(f"✗ 执行异常: {exc}")
            remaining.append(f"命令异常: {command}")

    # Record code issues
    code_issues = result.get("code_issues", [])
    for issue in code_issues:
        remaining.append(f"代码问题 - {issue.get('file', 'unknown')}: {issue.get('issue', '')}")

    # Consider fixed if: commands executed successfully OR all errors were ignored
    fixed = (len(commands_executed) > 0 or len(ignored) > 0) and len(remaining) == 0

    return DebugResult(
        fixed=fixed,
        actions_taken=actions,
        remaining_errors=remaining,
        commands_executed=commands_executed,
        ignored_errors=ignored,
    )


async def debug_validation_errors(
    llm: Any,
    runtime_workspace: "RuntimeWorkspace",
    validation_result: Any,
    project_memory: Any | None = None,
    *,
    verbose: bool = False,
) -> DebugResult:
    """Debug validation errors using LLM analysis.

    High-level wrapper that extracts errors from validation result
    and uses LLM to analyze and fix them.

    Args:
        llm: LLM model instance
        runtime_workspace: RuntimeWorkspace for command execution
        validation_result: CodeValidationResult with errors
        project_memory: Optional ProjectMemory for context
        verbose: Whether to print debug info

    Returns:
        DebugResult with actions taken
    """
    # Extract errors from validation result
    errors = getattr(validation_result, "errors", [])
    if not errors:
        return DebugResult(fixed=True, actions_taken=["No errors to fix"])

    # Build project context
    project_context = ""
    if project_memory and hasattr(project_memory, "get_tech_stack_info"):
        project_context = project_memory.get_tech_stack_info()

    return await analyze_and_fix_errors(
        llm=llm,
        runtime_workspace=runtime_workspace,
        errors=errors,
        project_context=project_context,
        verbose=verbose,
    )


FINALIZATION_ERROR_PROMPT = """你是一个项目整合专家。分析以下文件操作错误，判断如何处理。

## 文件操作错误
{errors}

## 任务
分析这些错误，判断每个错误应该如何处理：
1. **忽略**：这个文件不重要，可以跳过
2. **重命名**：文件路径有冲突，建议重命名
3. **需要人工处理**：问题复杂，需要人工干预

## 输出格式
```json
{{
    "analysis": "错误原因分析",
    "decisions": [
        {{
            "path": "文件路径",
            "action": "ignore|rename|manual",
            "reason": "决策原因",
            "new_path": "新路径（仅当 action=rename 时）"
        }}
    ],
    "summary": "总结"
}}
```

注意：
- 对于依赖目录冲突（如 node_modules、__pycache__），建议忽略
- 对于重要源码文件冲突，建议重命名或人工处理
- 优先保证项目可运行
"""


@dataclass
class FinalizationDecision:
    """Decision for handling a file operation error."""

    path: str
    action: str  # ignore, rename, manual
    reason: str
    new_path: str | None = None


async def analyze_finalization_errors(
    llm: Any,
    file_errors: list[dict[str, Any]],
    *,
    verbose: bool = False,
) -> tuple[list[FinalizationDecision], str]:
    """Use LLM to analyze file operation errors and decide how to handle them.

    Args:
        llm: LLM model instance
        file_errors: List of file error dicts from finalize_project
        verbose: Whether to print debug info

    Returns:
        tuple: (list of decisions, summary string)
    """
    from ._llm_utils import call_llm_json

    if not file_errors:
        return [], "No errors to analyze"

    # Format errors for prompt
    errors_text = "\n".join(
        f"- {err['path']}: {err['error']} (type: {err.get('type', 'unknown')})"
        for err in file_errors[:20]
    )

    prompt = FINALIZATION_ERROR_PROMPT.format(errors=errors_text)

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是项目整合专家，分析文件操作错误并决定处理方式。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            label="finalization_analysis",
            verbose=verbose,
        )
    except Exception as exc:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Finalization] LLM analysis failed: {exc}")
        return [], f"LLM analysis failed: {exc}"

    decisions: list[FinalizationDecision] = []
    for item in result.get("decisions", []):
        decisions.append(FinalizationDecision(
            path=item.get("path", ""),
            action=item.get("action", "manual"),
            reason=item.get("reason", ""),
            new_path=item.get("new_path"),
        ))

    return decisions, result.get("summary", "")


__all__ = [
    "DebugResult",
    "FinalizationDecision",
    "analyze_and_fix_errors",
    "debug_validation_errors",
    "analyze_finalization_errors",
]
