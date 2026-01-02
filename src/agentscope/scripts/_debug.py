# -*- coding: utf-8 -*-
"""Agent-driven debug utilities.

This module provides language-agnostic debugging capabilities by leveraging
LLM to analyze validation errors and generate fix commands.

Enhanced with limited code fix capability for common issues like:
- Import path errors
- Missing package imports
- API migration (e.g., Pydantic v2)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
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
        files_modified: List of files that were modified during code fix
    """

    fixed: bool = False
    actions_taken: list[str] = field(default_factory=list)
    remaining_errors: list[str] = field(default_factory=list)
    commands_executed: list[str] = field(default_factory=list)
    ignored_errors: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)


@dataclass
class CodeFix:
    """A single code fix operation.

    Attributes:
        file_path: Path to the file to modify
        fix_type: Type of fix (import_path, add_import, replace_line, etc.)
        old_content: Content to replace (for replace operations)
        new_content: New content to insert
        line_number: Optional line number for targeted fixes
        description: Human-readable description of the fix
    """

    file_path: str
    fix_type: str
    old_content: str
    new_content: str
    line_number: int | None = None
    description: str = ""


# ---------------------------------------------------------------------------
# Code Fix Prompt - For limited, safe code modifications
# ---------------------------------------------------------------------------
CODE_FIX_PROMPT = """你是一个代码修复专家。根据错误信息，生成精确的代码修复操作。

## 错误信息
{errors}

## 相关文件内容
{file_contents}

## 项目已存在的模块
{existing_modules}

## 任务
分析错误，生成**最小化、精确**的代码修复。只修复导入错误和简单的 API 问题。

### 允许的修复类型
1. **import_path**: 修正错误的导入路径
   - 例: `from app.core.config import Settings` → `from app.config import Settings`
2. **add_import**: 添加缺失的导入语句
   - 例: 添加 `import jwt` 或 `from typing import Optional`
3. **replace_line**: 替换单行代码
   - 例: Pydantic v2 迁移 `from pydantic import BaseSettings` → `from pydantic_settings import BaseSettings`
4. **remove_import**: 移除无效的导入（注释掉）
   - 例: 注释掉 `from app.utils import xxx`（当模块不存在时）

### 不允许的修复
- 大规模代码重构
- 修改业务逻辑
- 删除或重写整个函数/类

## 输出格式
```json
{{
    "analysis": "错误分析",
    "fixes": [
        {{
            "file_path": "backend/app/xxx.py",
            "fix_type": "import_path|add_import|replace_line|remove_import",
            "old_content": "原始内容（必须精确匹配文件中的内容）",
            "new_content": "修复后的内容",
            "description": "修复说明"
        }}
    ],
    "unfixable": [
        {{
            "error": "无法自动修复的错误",
            "reason": "原因"
        }}
    ]
}}
```

注意：
- old_content 必须与文件中的内容**完全匹配**，包括空格和缩进
- 修复应该是最小化的，只改变必要的部分
- 如果不确定正确的导入路径，宁可注释掉也不要猜测
- 优先使用项目中已存在的模块
"""


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
    enable_code_fix: bool = True,
    verbose: bool = False,
) -> DebugResult:
    """Use LLM to analyze errors and execute fix commands.

    This function:
    1. Sends errors to LLM for analysis
    2. Executes safe fix commands (like installing packages)
    3. Attempts limited code fixes for import/API issues (if enabled)
    4. Returns results for further handling

    Args:
        llm: LLM model instance
        runtime_workspace: RuntimeWorkspace for command execution
        errors: List of error messages to analyze
        project_context: Project context (tech stack, etc.)
        max_commands: Maximum number of commands to execute
        enable_code_fix: Whether to enable limited code fix capability
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
    files_modified: list[str] = []
    code_issues = result.get("code_issues", [])

    if not result.get("fixable_by_command", False):
        # Try code fix if enabled and there are code issues
        if enable_code_fix and code_issues:
            if verbose:
                from ._observability import get_logger
                get_logger().debug(f"[Debug] 尝试代码修复: {len(code_issues)} 个问题")

            fix_actions, fix_remaining, fix_modified = await fix_code_issues(
                llm=llm,
                runtime_workspace=runtime_workspace,
                code_issues=code_issues,
                errors=errors,
                verbose=verbose,
            )

            actions.extend(fix_actions)
            remaining.extend(fix_remaining)
            files_modified.extend(fix_modified)
        else:
            # Record code issues as remaining errors
            for issue in code_issues:
                remaining.append(f"{issue.get('file', 'unknown')}: {issue.get('issue', '')}")

        actions.append(f"分析完成: {result.get('summary', '需要修改代码')}")

        # If all errors were ignored or fixed, consider it fixed
        all_fixed = (len(remaining) == 0 and len(ignored) > 0) or len(files_modified) > 0

        return DebugResult(
            fixed=all_fixed,
            actions_taken=actions,
            remaining_errors=remaining,
            ignored_errors=ignored,
            files_modified=files_modified,
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

    # Handle code issues - try code fix if enabled
    if enable_code_fix and code_issues:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Debug] 尝试代码修复: {len(code_issues)} 个问题")

        fix_actions, fix_remaining, fix_modified = await fix_code_issues(
            llm=llm,
            runtime_workspace=runtime_workspace,
            code_issues=code_issues,
            errors=errors,
            verbose=verbose,
        )

        actions.extend(fix_actions)
        remaining.extend(fix_remaining)
        files_modified.extend(fix_modified)
    else:
        # Just record code issues as remaining errors
        for issue in code_issues:
            remaining.append(f"代码问题 - {issue.get('file', 'unknown')}: {issue.get('issue', '')}")

    # Consider fixed if: commands executed OR files modified OR all ignored, with no remaining
    fixed = (
        len(commands_executed) > 0 or len(ignored) > 0 or len(files_modified) > 0
    ) and len(remaining) == 0

    return DebugResult(
        fixed=fixed,
        actions_taken=actions,
        remaining_errors=remaining,
        commands_executed=commands_executed,
        ignored_errors=ignored,
        files_modified=files_modified,
    )


async def debug_validation_errors(
    llm: Any,
    runtime_workspace: "RuntimeWorkspace",
    validation_result: Any,
    project_memory: Any | None = None,
    *,
    enable_code_fix: bool = True,
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
        enable_code_fix: Whether to enable limited code fix capability
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
        enable_code_fix=enable_code_fix,
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


# ---------------------------------------------------------------------------
# Code Fix Functions - Limited, safe code modifications
# ---------------------------------------------------------------------------


def _extract_file_from_error(error: str) -> str | None:
    """Extract file path from error message.

    Args:
        error: Error message string

    Returns:
        File path if found, None otherwise
    """
    # Common patterns for file paths in error messages
    patterns = [
        r'File "([^"]+\.py)"',  # Python traceback
        r"(\S+\.py):\d+",  # Python syntax error
        r"(\S+\.(ts|tsx|js|jsx|vue)):\d+",  # TypeScript/JavaScript
        r"in (\S+\.py)",  # Import error
        r"module '([^']+)'",  # Module name (convert to path)
    ]

    for pattern in patterns:
        match = re.search(pattern, error)
        if match:
            path = match.group(1)
            # Convert module path to file path if needed
            if "." in path and "/" not in path and not path.endswith(".py"):
                path = path.replace(".", "/") + ".py"
            return path

    return None


def _clean_file_path(file_path: str) -> str | None:
    """Clean up file path by removing annotations and normalizing format.

    Args:
        file_path: Raw file path potentially with annotations

    Returns:
        Cleaned file path or None if invalid
    """
    if not file_path:
        return None

    # Remove parenthetical annotations like "(或类似路径)"
    cleaned = re.sub(r"\s*\([^)]*\)\s*", "", file_path).strip()

    # Remove suffix annotations like "或类似文件", "或类似路径"
    cleaned = re.sub(r"\s+(或|及|和|等).*$", "", cleaned).strip()

    # Remove quotes
    cleaned = cleaned.strip("'\"")

    # Skip if it looks like descriptive text, not a path
    if not cleaned or len(cleaned) > 200:
        return None

    # Must contain a file extension
    valid_extensions = [".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".json"]
    if not any(cleaned.endswith(ext) for ext in valid_extensions):
        return None

    # Must not contain Chinese characters (descriptive text)
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        return None

    return cleaned


def _fuzzy_find_file(workspace_dir: "Path", file_path: str) -> "Path | None":
    """Find file using fuzzy matching when exact path doesn't exist.

    Args:
        workspace_dir: Workspace directory path
        file_path: Relative file path to find

    Returns:
        Path object if found, None otherwise
    """
    from pathlib import Path

    workspace = Path(workspace_dir)

    # Get the filename from the path
    filename = Path(file_path).name

    # Search for files with the same name
    candidates = list(workspace.rglob(filename))

    # Filter out __pycache__ and node_modules
    candidates = [
        p for p in candidates
        if "__pycache__" not in str(p) and "node_modules" not in str(p)
    ]

    if not candidates:
        return None

    # If only one candidate, return it
    if len(candidates) == 1:
        return candidates[0]

    # Try to find the best match based on path similarity
    path_parts = Path(file_path).parts

    best_match = None
    best_score = 0

    for candidate in candidates:
        rel_path = candidate.relative_to(workspace)
        candidate_parts = rel_path.parts

        # Count matching parts from the end (filename and parent dirs)
        score = 0
        for i in range(1, min(len(path_parts), len(candidate_parts)) + 1):
            if path_parts[-i] == candidate_parts[-i]:
                score += 1
            else:
                break

        if score > best_score:
            best_score = score
            best_match = candidate

    return best_match


def _read_file_content(workspace_dir: "Path", file_path: str) -> str | None:
    """Read file content from workspace.

    Args:
        workspace_dir: Workspace directory path
        file_path: Relative file path

    Returns:
        File content if exists, None otherwise
    """
    from pathlib import Path

    # Clean up the file path first
    cleaned_path = _clean_file_path(file_path)
    if not cleaned_path:
        return None

    file_path = cleaned_path

    # Normalize path - remove leading slashes and /workspace prefix
    file_path = file_path.lstrip("/")
    if file_path.startswith("workspace/"):
        file_path = file_path[10:]

    full_path = Path(workspace_dir) / file_path
    if full_path.exists():
        try:
            return full_path.read_text(encoding="utf-8")
        except Exception:
            return None

    # Try common subdirectories
    for subdir in ["backend", "frontend", "src", "app"]:
        alt_path = Path(workspace_dir) / subdir / file_path
        if alt_path.exists():
            try:
                return alt_path.read_text(encoding="utf-8")
            except Exception:
                pass

    # Try stripping common prefixes from file_path
    for prefix in ["app/", "src/", "backend/app/", "frontend/src/"]:
        if file_path.startswith(prefix):
            stripped = file_path[len(prefix):]
            for subdir in ["backend/app", "frontend/src", "src", "app"]:
                alt_path = Path(workspace_dir) / subdir / stripped
                if alt_path.exists():
                    try:
                        return alt_path.read_text(encoding="utf-8")
                    except Exception:
                        pass

    # Last resort: fuzzy match by filename
    fuzzy_match = _fuzzy_find_file(workspace_dir, file_path)
    if fuzzy_match:
        try:
            return fuzzy_match.read_text(encoding="utf-8")
        except Exception:
            pass

    return None


def _get_existing_modules(workspace_dir: "Path") -> list[str]:
    """Get list of existing Python and frontend modules.

    Args:
        workspace_dir: Workspace directory path

    Returns:
        List of module paths
    """
    from pathlib import Path

    modules = []
    workspace = Path(workspace_dir)

    # Python modules
    for py_file in workspace.rglob("*.py"):
        if "__pycache__" in str(py_file) or "node_modules" in str(py_file):
            continue
        rel_path = py_file.relative_to(workspace)
        # Convert to import path
        import_path = str(rel_path).replace("/", ".").replace(".py", "")
        # Remove leading 'backend.' if present
        if import_path.startswith("backend."):
            import_path = import_path[8:]  # Remove 'backend.'
        modules.append(import_path)

    # Frontend modules
    for ext in ["*.ts", "*.tsx", "*.js", "*.jsx", "*.vue"]:
        for fe_file in workspace.rglob(ext):
            if "node_modules" in str(fe_file):
                continue
            rel_path = fe_file.relative_to(workspace)
            modules.append(f"@/{rel_path}")

    return modules


async def fix_code_issues(
    llm: Any,
    runtime_workspace: "RuntimeWorkspace",
    code_issues: list[dict[str, Any]],
    errors: list[str],
    *,
    verbose: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """Fix code issues using LLM-generated fixes.

    This function performs limited, safe code modifications to fix common issues
    like import errors and API migration.

    Args:
        llm: LLM model instance
        runtime_workspace: RuntimeWorkspace for file access
        code_issues: List of code issues from debug analysis
        errors: Original error messages
        verbose: Whether to print debug info

    Returns:
        Tuple of (actions_taken, remaining_errors, files_modified)
    """
    from pathlib import Path
    from ._llm_utils import call_llm_json

    actions: list[str] = []
    remaining: list[str] = []
    files_modified: list[str] = []

    if not runtime_workspace or not runtime_workspace.is_initialized:
        return actions, ["No runtime workspace available"], files_modified

    if not code_issues and not errors:
        return ["No code issues to fix"], [], files_modified

    workspace_dir = Path(runtime_workspace.workspace_dir)

    if verbose:
        from ._observability import get_logger
        get_logger().debug(
            f"[CodeFix] 开始: {len(code_issues)} 个 code_issues, {len(errors)} 个 errors"
        )

    # Extract files from errors and code issues
    files_to_check: set[str] = set()
    import_errors: list[tuple[str, str]] = []  # (module, name) pairs
    skipped_paths: list[str] = []  # Track invalid paths for debugging

    for issue in code_issues:
        raw_path = issue.get("file")
        if raw_path:
            # Clean up the path first
            cleaned = _clean_file_path(raw_path)
            if cleaned:
                files_to_check.add(cleaned)
            else:
                skipped_paths.append(raw_path)

    for error in errors:
        file_path = _extract_file_from_error(error)
        if file_path:
            files_to_check.add(file_path)

        # Extract import error pattern: cannot import name 'xxx' from 'yyy'
        import_match = re.search(
            r"cannot import name ['\"](\w+)['\"] from ['\"]([^'\"]+)['\"]",
            error,
        )
        if import_match:
            name, module = import_match.groups()
            import_errors.append((module, name))

    # For import errors, search all Python files that might contain the bad import
    # Also check __init__.py files that might need to export the missing name
    # We read file contents here directly to avoid path resolution issues
    file_contents: dict[str, str] = {}

    if import_errors:
        for py_file in workspace_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "node_modules" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                rel_path = str(py_file.relative_to(workspace_dir))

                for module, name in import_errors:
                    should_add = False

                    # Check if file contains the problematic import
                    patterns = [
                        f"from {module} import",
                        f"from {module.replace('.', '/')} import",
                    ]
                    if any(p in content for p in patterns) and name in content:
                        should_add = True
                        if verbose:
                            from ._observability import get_logger
                            get_logger().debug(
                                f"[CodeFix] 找到调用方: {rel_path}"
                            )

                    # Also check if this is the __init__.py that should export the name
                    # e.g., for 'app.routers', check backend/app/routers/__init__.py
                    module_path = module.replace(".", "/")
                    if rel_path.endswith(f"{module_path}/__init__.py"):
                        should_add = True
                        if verbose:
                            from ._observability import get_logger
                            get_logger().debug(
                                f"[CodeFix] 找到模块入口: {rel_path}"
                            )

                    if should_add:
                        files_to_check.add(rel_path)
                        # Store content directly (already read)
                        if rel_path not in file_contents:
                            if len(content) > 3000:
                                content = content[:3000] + "\n... (truncated)"
                            file_contents[rel_path] = content
            except Exception:
                pass

    # Read remaining files from code_issues that weren't found via import search
    for file_path in files_to_check:
        if file_path not in file_contents:
            content = _read_file_content(workspace_dir, file_path)
            if content:
                if len(content) > 3000:
                    content = content[:3000] + "\n... (truncated)"
                file_contents[file_path] = content

    if verbose:
        from ._observability import get_logger
        logger = get_logger()
        logger.debug(
            f"[CodeFix] 找到 {len(files_to_check)} 个文件待检查, "
            f"{len(import_errors)} 个导入错误, 读取了 {len(file_contents)} 个文件"
        )
        if skipped_paths:
            logger.debug(
                f"[CodeFix] 跳过 {len(skipped_paths)} 个无效路径: "
                f"{skipped_paths[:3]}"
            )

    if not file_contents:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(
                f"[CodeFix] 无法读取文件，待检查列表: {list(files_to_check)[:5]}"
            )
        return actions, ["Could not read any related files"], files_modified

    # Get existing modules
    existing_modules = _get_existing_modules(workspace_dir)

    # Format errors and file contents for prompt
    errors_text = "\n".join(f"- {err}" for err in errors[:10])
    for issue in code_issues:
        errors_text += f"\n- {issue.get('file', 'unknown')}: {issue.get('issue', '')}"

    files_text = ""
    for path, content in file_contents.items():
        files_text += f"\n### {path}\n```\n{content}\n```\n"

    modules_text = "\n".join(f"- {m}" for m in existing_modules[:50])

    prompt = CODE_FIX_PROMPT.format(
        errors=errors_text,
        file_contents=files_text,
        existing_modules=modules_text or "（未扫描到模块）",
    )

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是代码修复专家，生成精确的代码修复操作。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            label="code_fix",
            verbose=verbose,
        )
    except Exception as exc:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[CodeFix] LLM analysis failed: {exc}")
        return actions, [f"Code fix LLM analysis failed: {exc}"], files_modified

    # Log LLM result
    if verbose:
        from ._observability import get_logger
        logger = get_logger()
        analysis = result.get("analysis", "")
        logger.debug(f"[CodeFix] 分析: {analysis[:100]}")
        fixes = result.get("fixes", [])
        unfixable = result.get("unfixable", [])
        logger.debug(f"[CodeFix] 生成 {len(fixes)} 个修复, {len(unfixable)} 个无法修复")
        for i, fix in enumerate(fixes[:5]):
            logger.debug(
                f"[CodeFix] 修复 {i+1}: {fix.get('fix_type')} - {fix.get('file_path')}"
            )

    # Apply fixes
    fixes = result.get("fixes", [])
    for fix_spec in fixes:
        file_path = fix_spec.get("file_path", "")
        fix_type = fix_spec.get("fix_type", "")
        old_content = fix_spec.get("old_content", "")
        new_content = fix_spec.get("new_content", "")
        description = fix_spec.get("description", "")

        if not file_path or not fix_type:
            continue

        # Read current file content
        full_path = workspace_dir / file_path
        if not full_path.exists():
            # Try with backend/ prefix
            full_path = workspace_dir / "backend" / file_path
            if not full_path.exists():
                remaining.append(f"File not found: {file_path}")
                continue

        try:
            current_content = full_path.read_text(encoding="utf-8")
        except Exception as exc:
            remaining.append(f"Failed to read {file_path}: {exc}")
            continue

        # Apply fix based on type
        new_file_content = None

        if fix_type == "import_path":
            # Replace import path
            if old_content in current_content:
                new_file_content = current_content.replace(old_content, new_content)
            else:
                remaining.append(f"[{file_path}] old_content not found: {old_content[:50]}")
                continue

        elif fix_type == "add_import":
            # Add import at the beginning (after existing imports)
            lines = current_content.split("\n")
            import_section_end = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    import_section_end = i + 1
                elif stripped and not stripped.startswith("#") and import_section_end > 0:
                    break

            # Insert new import
            lines.insert(import_section_end, new_content)
            new_file_content = "\n".join(lines)

        elif fix_type == "replace_line":
            # Replace specific line
            if old_content in current_content:
                new_file_content = current_content.replace(old_content, new_content)
            else:
                remaining.append(f"[{file_path}] old_content not found: {old_content[:50]}")
                continue

        elif fix_type == "remove_import":
            # Comment out import
            if old_content in current_content:
                commented = f"# REMOVED: {old_content}"
                new_file_content = current_content.replace(old_content, commented)
            else:
                remaining.append(f"[{file_path}] old_content not found: {old_content[:50]}")
                continue

        else:
            remaining.append(f"Unknown fix type: {fix_type}")
            continue

        # Write fixed content
        if new_file_content and new_file_content != current_content:
            try:
                full_path.write_text(new_file_content, encoding="utf-8")
                actions.append(f"✓ [{fix_type}] {file_path}: {description}")
                files_modified.append(str(file_path))
                if verbose:
                    from ._observability import get_logger
                    get_logger().debug(f"[CodeFix] Fixed {file_path}: {description}")
            except Exception as exc:
                remaining.append(f"Failed to write {file_path}: {exc}")

    # Record unfixable issues
    unfixable = result.get("unfixable", [])
    for item in unfixable:
        remaining.append(f"无法自动修复: {item.get('error', '')} - {item.get('reason', '')}")

    return actions, remaining, files_modified


__all__ = [
    "DebugResult",
    "CodeFix",
    "FinalizationDecision",
    "analyze_and_fix_errors",
    "debug_validation_errors",
    "analyze_finalization_errors",
    "fix_code_issues",
]
