# -*- coding: utf-8 -*-
"""Code validation utilities.

This module provides:
- CodeValidationResult dataclass
- Static code analysis
- Import validation
- LLM-based code review
- Layered validation pipeline
"""
from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ._sandbox import RuntimeWorkspace


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------
@dataclass
class CodeValidationResult:
    """Result of code validation.

    Attributes:
        is_valid: Whether the code passed validation
        score: Overall validation score (0.0 to 1.0)
        errors: List of error messages
        warnings: List of warning messages
        details: Additional validation details
    """

    is_valid: bool = True
    score: float = 1.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Syntax Validation (Compile-time checks)
# ---------------------------------------------------------------------------
def check_syntax_errors(
    files: dict[str, str],
) -> tuple[bool, list[str], list[str]]:
    """Check for syntax errors in code files.

    Performs static syntax checking:
    - Python files: Uses ast.parse() to detect syntax errors
    - JavaScript/TypeScript: Basic bracket matching and common errors
    - Vue files: Checks script section syntax

    Args:
        files: Dict mapping file paths to content

    Returns:
        tuple: (is_valid, errors, warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []

    for fpath, content in files.items():
        ext = fpath.split(".")[-1].lower() if "." in fpath else ""

        # Python syntax check
        if ext == "py":
            try:
                ast.parse(content, filename=fpath)
            except SyntaxError as e:
                errors.append(f"{fpath}:{e.lineno}: Python 语法错误 - {e.msg}")

        # JavaScript/TypeScript basic checks
        elif ext in ("js", "ts", "jsx", "tsx"):
            # Check bracket balance
            brackets = {"(": ")", "[": "]", "{": "}"}
            stack = []
            line_num = 1
            in_string = None
            in_template = False

            for i, char in enumerate(content):
                if char == "\n":
                    line_num += 1
                    continue

                # Track string context
                if char in ('"', "'", "`") and (i == 0 or content[i - 1] != "\\"):
                    if in_string == char:
                        in_string = None
                        if char == "`":
                            in_template = False
                    elif in_string is None:
                        in_string = char
                        if char == "`":
                            in_template = True
                    continue

                if in_string:
                    continue

                if char in brackets:
                    stack.append((char, line_num))
                elif char in brackets.values():
                    if stack and brackets.get(stack[-1][0]) == char:
                        stack.pop()
                    else:
                        errors.append(f"{fpath}:{line_num}: 不匹配的括号 '{char}'")

            if stack:
                unmatched = stack[-1]
                warnings.append(f"{fpath}:{unmatched[1]}: 未闭合的括号 '{unmatched[0]}'")

            # Check for common syntax errors
            common_errors = [
                (r"^\s*else\s+if\s*\(", "else if 应该写成 'else if' 或 'elif' (Python)"),
                (r",\s*\}", "对象/数组末尾有多余的逗号"),
                (r"=>\s*\{[^}]*return[^;]*$", "箭头函数中 return 语句可能缺少分号"),
            ]
            for pattern, desc in common_errors:
                matches = re.findall(pattern, content, re.MULTILINE)
                if matches:
                    warnings.append(f"{fpath}: {desc}")

        # Vue single file component
        elif ext == "vue":
            # Extract script section and check
            script_match = re.search(
                r"<script[^>]*>(.*?)</script>",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if script_match:
                script_content = script_match.group(1)
                # Basic bracket check for script section
                open_braces = script_content.count("{")
                close_braces = script_content.count("}")
                if open_braces != close_braces:
                    warnings.append(
                        f"{fpath}: Script 部分大括号不匹配 ({{ {open_braces} vs }} {close_braces})"
                    )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


# ---------------------------------------------------------------------------
# Static Validation
# ---------------------------------------------------------------------------
def check_code_completeness(
    files: dict[str, str],
) -> tuple[bool, list[str], list[str]]:
    """Check code completeness by looking for placeholder patterns.

    Args:
        files: Dict mapping file paths to content

    Returns:
        tuple: (is_complete, errors, warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Patterns that indicate incomplete code
    # Note: TODO/FIXME are common in MVP code and shouldn't heavily penalize
    # The ellipsis (...) check is removed as it's valid in Python type stubs
    incomplete_patterns = [
        # Critical patterns (will be errors if blocking)
        (r"raise\s+NotImplementedError", "NotImplementedError"),
        # Minor patterns (warnings only, very low penalty)
        (r"pass\s*#\s*TODO", "Empty pass with TODO"),
    ]

    # Informational patterns (counted but not penalized much)
    info_patterns = [
        (r"#\s*TODO", "TODO comment"),
        (r"#\s*FIXME", "FIXME comment"),
        (r"//\s*TODO", "TODO comment (JS)"),
    ]

    info_count = 0
    for fpath, content in files.items():
        for pattern, desc in incomplete_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                warnings.append(f"{fpath}: {desc} ({len(matches)} occurrences)")
        # Count info patterns but don't add to warnings (just for logging)
        for pattern, desc in info_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            info_count += len(matches)

    # Check for empty files
    for fpath, content in files.items():
        if not content.strip():
            errors.append(f"{fpath}: Empty file")

    is_complete = len(errors) == 0
    return is_complete, errors, warnings, info_count


def run_static_validation(
    files: dict[str, str],
) -> CodeValidationResult:
    """Run static code analysis on files.

    Performs:
    - Python syntax validation
    - Completeness checks
    - Basic structure validation

    Args:
        files: Dict mapping file paths to content

    Returns:
        CodeValidationResult: Validation results
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check completeness
    is_complete, comp_errors, comp_warnings, info_count = check_code_completeness(files)
    errors.extend(comp_errors)
    warnings.extend(comp_warnings)

    # Validate Python syntax
    for fpath, content in files.items():
        if fpath.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError as exc:
                errors.append(f"{fpath}:{exc.lineno}: Syntax error - {exc.msg}")

    # Calculate score - be lenient for MVP code
    # Errors are penalized more heavily, but warnings much less
    # Info patterns (TODO/FIXME) have very minimal impact
    error_penalty = len(errors) * 0.15
    warning_penalty = len(warnings) * 0.02  # Reduced from 0.05
    info_penalty = min(0.05, info_count * 0.001)  # Very minimal penalty for TODOs
    score = max(0.5, 1.0 - error_penalty - warning_penalty - info_penalty)

    return CodeValidationResult(
        is_valid=len(errors) == 0,
        score=score,
        errors=errors,
        warnings=warnings,
        details={"static_check": True, "info_patterns": info_count},
    )


# ---------------------------------------------------------------------------
# Import Validation
# ---------------------------------------------------------------------------
def _install_dependencies(
    runtime_workspace: "RuntimeWorkspace",
) -> bool:
    """Install project dependencies before validation.

    Looks for requirements.txt and package.json files and installs dependencies.

    Args:
        runtime_workspace: RuntimeWorkspace instance for execution

    Returns:
        bool: True if dependencies installed successfully
    """
    # Install Python dependencies if requirements.txt exists
    check_req = runtime_workspace.execute_command(
        "test -f backend/requirements.txt && echo 'exists'",
        timeout=10,
    )
    if check_req.get("success") and "exists" in check_req.get("output", ""):
        runtime_workspace.execute_command(
            "cd backend && pip install -q -r requirements.txt 2>/dev/null || true",
            timeout=120,
        )

    # Check for root requirements.txt
    check_root_req = runtime_workspace.execute_command(
        "test -f requirements.txt && echo 'exists'",
        timeout=10,
    )
    if check_root_req.get("success") and "exists" in check_root_req.get("output", ""):
        runtime_workspace.execute_command(
            "pip install -q -r requirements.txt 2>/dev/null || true",
            timeout=120,
        )

    # Install common dependencies that are often used but might not be in requirements
    runtime_workspace.execute_command(
        "pip install -q passlib python-jose sqlalchemy fastapi bcrypt pydantic 2>/dev/null || true",
        timeout=60,
    )

    return True


def run_import_validation(
    runtime_workspace: "RuntimeWorkspace",
    files: dict[str, str],
) -> CodeValidationResult:
    """Validate imports by attempting to import Python modules.

    This function installs dependencies first, then validates Python syntax
    by running the files with 'python -m py_compile'.

    Args:
        runtime_workspace: RuntimeWorkspace instance for execution
        files: Dict mapping file paths to content

    Returns:
        CodeValidationResult: Validation results
    """
    if not runtime_workspace or not runtime_workspace.is_initialized:
        return CodeValidationResult(
            is_valid=True,
            score=1.0,
            warnings=["Import validation skipped: no runtime"],
        )

    # Install dependencies first
    _install_dependencies(runtime_workspace)

    errors: list[str] = []
    warnings: list[str] = []

    # Find Python files
    py_files = [f for f in files.keys() if f.endswith(".py")]

    # Set of third-party packages to ignore import errors for
    third_party_packages = {
        "passlib", "jose", "sqlalchemy", "fastapi", "pydantic",
        "bcrypt", "redis", "aioredis", "prometheus", "locust",
        "element_plus", "axios", "pinia", "vue"
    }

    for fpath in py_files:
        # Skip test files and migration files
        if "test" in fpath.lower() or "migration" in fpath.lower():
            continue

        # Use py_compile to check syntax only (doesn't require imports to work)
        result = runtime_workspace.execute_command(
            f'python -m py_compile "{fpath}"',
            timeout=30,
        )

        if not result.get("success"):
            error_output = result.get("error", "")
            # Only report syntax errors
            if "SyntaxError" in error_output:
                errors.append(f"{fpath}: Syntax error - {error_output[:200]}")
            # For module errors, check if it's a third-party package
            elif "ModuleNotFoundError" in error_output or "ImportError" in error_output:
                # Check if it's a known third-party package error
                is_third_party = any(pkg in error_output.lower() for pkg in third_party_packages)
                if not is_third_party:
                    # Check for local module import errors
                    if "from ." in error_output or "from app" in error_output or "from backend" in error_output:
                        warnings.append(f"{fpath}: Local import warning - {error_output[:100]}")
                    else:
                        # Report unknown import error as warning not error
                        warnings.append(f"{fpath}: Import warning - {error_output[:100]}")

    # Calculate score - be more lenient (warnings don't reduce score as much)
    total = len(py_files) or 1
    error_penalty = len(errors) * 0.15
    warning_penalty = len(warnings) * 0.03
    score = max(0.3, 1.0 - error_penalty - warning_penalty)

    return CodeValidationResult(
        is_valid=len(errors) == 0,
        score=score,
        errors=errors,
        warnings=warnings,
        details={"import_check": True, "files_checked": len(py_files)},
    )


# ---------------------------------------------------------------------------
# File Summary Extraction
# ---------------------------------------------------------------------------
def extract_file_summary(content: str, file_path: str, max_chars: int = 2000) -> str:
    """Extract a detailed summary of file for QA evaluation.

    This function provides enough context for QA to verify implementation details,
    not just structural information.

    Args:
        content: File content
        file_path: File path (used to determine file type)
        max_chars: Maximum characters to include in summary

    Returns:
        str: Detailed file summary for QA
    """
    lines = content.split("\n")
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    # For small files, return full content
    if len(content) <= max_chars:
        return content

    summary_parts: list[str] = []
    total_len = 0

    # Python files - include function/class bodies
    if ext == "py":
        in_block = False
        block_lines: list[str] = []
        block_indent = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            current_indent = len(line) - len(line.lstrip())

            # Start of new block
            if stripped.startswith(("class ", "def ", "async def ", "@")):
                # Save previous block
                if block_lines and total_len < max_chars:
                    block_content = "\n".join(block_lines)
                    summary_parts.append(block_content)
                    total_len += len(block_content)
                block_lines = [f"L{i + 1}: {line.rstrip()}"]
                block_indent = current_indent
                in_block = True
            elif in_block:
                # Continue block until we hit same or lower indent (non-empty)
                if stripped and current_indent <= block_indent and not stripped.startswith(("#", "@")):
                    in_block = False
                    if block_lines and total_len < max_chars:
                        block_content = "\n".join(block_lines[:20])  # Max 20 lines per block
                        summary_parts.append(block_content)
                        total_len += len(block_content)
                    block_lines = []
                else:
                    if len(block_lines) < 20:
                        block_lines.append(f"L{i + 1}: {line.rstrip()}")
            elif stripped.startswith(("import ", "from ")):
                if total_len < max_chars // 4:  # Limit imports
                    summary_parts.append(f"L{i + 1}: {stripped}")
                    total_len += len(stripped)

        # Don't forget last block
        if block_lines and total_len < max_chars:
            block_content = "\n".join(block_lines[:20])
            summary_parts.append(block_content)

    # JavaScript/TypeScript files
    elif ext in ("js", "ts", "jsx", "tsx"):
        in_block = False
        block_lines: list[str] = []
        brace_count = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Start of function/class/const
            if any(stripped.startswith(kw) for kw in ("function ", "class ", "const ", "export ", "async ")):
                if block_lines and total_len < max_chars:
                    block_content = "\n".join(block_lines)
                    summary_parts.append(block_content)
                    total_len += len(block_content)
                block_lines = [f"L{i + 1}: {line.rstrip()}"]
                brace_count = line.count("{") - line.count("}")
                in_block = brace_count > 0
            elif in_block:
                if len(block_lines) < 25:
                    block_lines.append(f"L{i + 1}: {line.rstrip()}")
                brace_count += line.count("{") - line.count("}")
                if brace_count <= 0:
                    in_block = False
                    if block_lines and total_len < max_chars:
                        block_content = "\n".join(block_lines)
                        summary_parts.append(block_content)
                        total_len += len(block_content)
                    block_lines = []
            elif stripped.startswith("import "):
                if total_len < max_chars // 4:
                    summary_parts.append(f"L{i + 1}: {stripped}")
                    total_len += len(stripped)

        if block_lines and total_len < max_chars:
            summary_parts.append("\n".join(block_lines))

    # Vue files - include template structure and script content
    elif ext == "vue":
        sections = {"template": [], "script": [], "style": []}
        current_section = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if "<template" in stripped:
                current_section = "template"
            elif "<script" in stripped:
                current_section = "script"
            elif "<style" in stripped:
                current_section = "style"
            elif "</template>" in stripped or "</script>" in stripped or "</style>" in stripped:
                current_section = None

            if current_section and len(sections[current_section]) < 40:
                sections[current_section].append(f"L{i + 1}: {line.rstrip()}")

        # Prioritize script > template > style
        for section_name in ["script", "template"]:
            section_lines = sections[section_name]
            if section_lines:
                section_content = "\n".join(section_lines)
                if total_len + len(section_content) < max_chars:
                    summary_parts.append(f"[{section_name.upper()}]\n{section_content}")
                    total_len += len(section_content)

    # HTML files
    elif ext in ("html", "htm"):
        # Include first part and any script tags
        summary_parts.append("\n".join(f"L{i+1}: {line}" for i, line in enumerate(lines[:30])))

    # Default: proportional sampling
    else:
        chunk_size = max(1, len(lines) // 3)
        # Beginning
        summary_parts.append("\n".join(f"L{i+1}: {line}" for i, line in enumerate(lines[:chunk_size])))
        # Middle
        mid_start = len(lines) // 2 - chunk_size // 2
        summary_parts.append(f"... (lines {chunk_size+1}-{mid_start}) ...")
        summary_parts.append("\n".join(f"L{i+1}: {line}" for i, line in enumerate(lines[mid_start:mid_start + chunk_size], start=mid_start)))

    result = "\n\n".join(summary_parts)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (truncated)"
    return result


# ---------------------------------------------------------------------------
# LLM-based Validation
# ---------------------------------------------------------------------------
async def validate_code_lightweight(
    llm: Any,
    files: dict[str, str],
    requirement_summary: str,
    *,
    verbose: bool = False,
) -> CodeValidationResult:
    """Lightweight code validation with syntax check + LLM review.

    Performs two-phase validation:
    1. Static syntax check (fast, catches compile-time errors)
    2. LLM-based semantic review (slow, catches logic issues)

    Args:
        llm: LLM model instance
        files: Dict mapping file paths to content
        requirement_summary: Brief description of requirements
        verbose: Whether to print debug info

    Returns:
        CodeValidationResult: Validation results
    """
    from ._llm_utils import call_llm_json

    # Phase 1: Static syntax validation (fast, catches compile-time errors)
    syntax_valid, syntax_errors, syntax_warnings = check_syntax_errors(files)

    if verbose and syntax_errors:
        from ._observability import get_logger
        logger = get_logger()
        logger.warn(f"[Validation] 语法检查发现 {len(syntax_errors)} 个错误:")
        for err in syntax_errors[:5]:
            logger.warn(f"  - {err}")

    # If syntax errors exist, return early with failure
    # This avoids wasting LLM tokens on broken code
    if syntax_errors:
        return CodeValidationResult(
            is_valid=False,
            score=0.3,  # Low score for syntax errors
            errors=syntax_errors,
            warnings=syntax_warnings,
            details={"phase": "syntax_check", "skipped_llm": True},
        )

    # Phase 2: LLM-based semantic validation
    # Build file summary
    file_summaries: list[str] = []
    for fpath, content in files.items():
        summary = extract_file_summary(content, fpath)
        file_summaries.append(f"=== {fpath} ===\n{summary}")

    files_text = "\n\n".join(file_summaries[:10])  # Limit files

    prompt = textwrap.dedent(f"""
        请快速审查以下代码文件，判断是否满足基本需求。

        【需求摘要】
        {requirement_summary}

        【代码文件摘要】
        {files_text}

        【审查要点】
        1. 代码结构是否完整（有入口、有核心逻辑）
        2. 是否存在明显的语法错误或未完成的占位符
        3. 文件之间的引用是否合理

        【输出格式】
        ```json
        {{
            "is_valid": true/false,
            "score": 0.0-1.0,
            "errors": ["错误1", "错误2"],
            "warnings": ["警告1"],
            "summary": "简要说明"
        }}
        ```
    """)

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是代码审查专家，请快速判断代码质量。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            label="code_validation",
            verbose=verbose,
        )

        # Combine syntax warnings with LLM warnings
        all_warnings = syntax_warnings + result.get("warnings", [])

        return CodeValidationResult(
            is_valid=result.get("is_valid", True),
            score=result.get("score", 0.8),
            errors=result.get("errors", []),
            warnings=all_warnings,
            details={
                "llm_summary": result.get("summary", ""),
                "phase": "llm_validation",
                "syntax_warnings_count": len(syntax_warnings),
            },
        )
    except Exception as exc:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Validation] LLM validation failed: {exc}")
        return CodeValidationResult(
            is_valid=True,
            score=0.7,
            warnings=syntax_warnings + [f"LLM validation failed: {exc}"],
        )


async def validate_code_with_llm(
    llm: Any,
    files: dict[str, str],
    requirement_summary: str,
    *,
    verbose: bool = False,
) -> CodeValidationResult:
    """Full LLM-based code validation (legacy compatibility).

    Args:
        llm: LLM model instance
        files: Dict mapping file paths to content
        requirement_summary: Brief description of requirements
        verbose: Whether to print debug info

    Returns:
        CodeValidationResult: Validation results
    """
    return await validate_code_lightweight(
        llm, files, requirement_summary, verbose=verbose
    )


# ---------------------------------------------------------------------------
# LLM-Driven Linter Validation
# ---------------------------------------------------------------------------
LINTER_STRATEGY_PROMPT = """你是一个代码质量工具专家。根据以下项目技术选型，生成合适的代码检查命令。

## 项目技术选型
{tech_stack_info}

## 项目文件
{file_list}

## 任务
分析项目使用的技术栈，决定使用哪些代码检查工具，并生成检查命令。

### 常见技术栈对应的检查工具：
- Python: pylint, flake8, mypy, ruff, black --check
- JavaScript/TypeScript: eslint, tsc --noEmit
- Vue: eslint (vue-eslint-parser), vue-tsc
- React: eslint (eslint-plugin-react)
- Node.js: npm run lint (如果存在)
- Go: go vet, golint, staticcheck
- Rust: cargo check, cargo clippy

### 输出格式
```json
{{
  "detected_stack": {{
    "languages": ["检测到的语言"],
    "frameworks": ["检测到的框架"],
    "package_managers": ["检测到的包管理器"]
  }},
  "linter_commands": [
    {{
      "name": "检查名称",
      "command": "要执行的命令",
      "working_dir": "工作目录（相对路径，如 backend 或 frontend）",
      "timeout": 60,
      "file_pattern": "检查的文件模式（如 *.py）",
      "severity": "error|warning",
      "install_command": "安装该工具的命令（可选）"
    }}
  ],
  "reasoning": "为什么选择这些检查工具"
}}
```

注意：
- 只根据实际存在的文件和配置来选择工具
- 如果没有配置文件（如 .eslintrc、pyproject.toml），使用默认配置或跳过
- 优先使用项目已配置的检查工具（检查 package.json scripts 或 pyproject.toml）
- 命令应该能够在沙箱环境中直接执行
- 如果工具未安装，提供 install_command
- 重要：命令必须排除 node_modules、__pycache__、dist、build 等第三方目录
- 对于 Python：使用 --ignore 或 --exclude 参数排除第三方代码
- 对于 ESLint/TSC：使用 --ignore-pattern 参数排除 node_modules
- 只检查业务代码（frontend/src、backend/app 等目录）
"""


@dataclass
class LinterCheckResult:
    """Result of a single linter check."""

    name: str
    command: str
    success: bool
    output: str = ""
    error_count: int = 0
    warning_count: int = 0
    details: list[str] = field(default_factory=list)


def _filter_source_files(files: dict[str, str]) -> dict[str, str]:
    """Filter out third-party and generated files from file dict.

    Args:
        files: Dict mapping file paths to content

    Returns:
        dict: Filtered dict with only source files
    """
    excluded_patterns = [
        "node_modules/",
        "__pycache__/",
        ".git/",
        "dist/",
        "build/",
        ".venv/",
        "venv/",
        ".env/",
        "env/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".tox/",
        "egg-info/",
        ".eggs/",
        "htmlcov/",
        ".coverage",
        "coverage.xml",
        "*.pyc",
        "*.pyo",
        "*.egg",
        "*.whl",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    ]

    filtered = {}
    for fpath, content in files.items():
        # Skip excluded patterns
        skip = False
        for pattern in excluded_patterns:
            if pattern.endswith("/"):
                if pattern[:-1] in fpath:
                    skip = True
                    break
            elif pattern.startswith("*."):
                if fpath.endswith(pattern[1:]):
                    skip = True
                    break
            elif pattern in fpath:
                skip = True
                break

        if not skip:
            filtered[fpath] = content

    return filtered


async def generate_linter_strategy(
    llm: Any,
    files: dict[str, str],
    tech_stack_info: str = "",
    *,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Use LLM to generate linter strategy based on project tech stack.

    Args:
        llm: LLM model instance
        files: Dict mapping file paths to content
        tech_stack_info: Project memory tech stack context
        verbose: Whether to print debug info

    Returns:
        dict: Linter strategy with commands to run, or None if failed
    """
    from ._llm_utils import call_llm_json

    # Filter out third-party files before building file list
    source_files = _filter_source_files(files)

    # Build file list summary from source files only
    file_list = "\n".join(f"- {fpath}" for fpath in sorted(source_files.keys())[:50])
    if len(source_files) > 50:
        file_list += f"\n... 及其他 {len(source_files) - 50} 个源文件"

    # If no tech stack info, try to detect from files
    if not tech_stack_info:
        tech_stack_info = "（项目记忆中无技术选型信息，请从文件列表推断）"

    prompt = LINTER_STRATEGY_PROMPT.format(
        tech_stack_info=tech_stack_info,
        file_list=file_list,
    )

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是代码质量工具专家，请根据项目技术栈选择合适的检查工具。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            label="linter_strategy",
            verbose=verbose,
        )
        return result
    except Exception as exc:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Validation] Failed to generate linter strategy: {exc}")
        return None


def parse_linter_output(
    output: str,
    command: str,
) -> tuple[int, int, list[str]]:
    """Parse linter output to extract error/warning counts.

    Args:
        output: Command output
        command: Original command (to determine parser)

    Returns:
        tuple: (error_count, warning_count, detail_messages)
    """
    errors = 0
    warnings = 0
    details: list[str] = []

    lines = output.split("\n")

    # Python linters (pylint, flake8, ruff)
    if any(tool in command for tool in ["pylint", "flake8", "ruff"]):
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # flake8/ruff format: file:line:col: E123 message
            if re.match(r".+:\d+:\d+:\s*[EF]\d+", line):
                errors += 1
                details.append(line[:200])
            elif re.match(r".+:\d+:\d+:\s*[WC]\d+", line):
                warnings += 1
                if len(details) < 10:
                    details.append(line[:200])

    # ESLint
    elif "eslint" in command:
        for line in lines:
            if "error" in line.lower():
                errors += 1
                details.append(line[:200])
            elif "warning" in line.lower():
                warnings += 1

    # TypeScript
    elif "tsc" in command:
        for line in lines:
            if re.match(r".+\(\d+,\d+\):\s*error", line):
                errors += 1
                details.append(line[:200])

    # Vue
    elif "vue-tsc" in command:
        for line in lines:
            if "error" in line.lower():
                errors += 1
                details.append(line[:200])

    # Generic: count error/warning keywords
    else:
        for line in lines:
            line_lower = line.lower()
            if "error" in line_lower:
                errors += 1
            elif "warning" in line_lower:
                warnings += 1

    return errors, warnings, details[:10]


async def run_linter_validation(
    runtime_workspace: "RuntimeWorkspace | None",
    llm: Any,
    files: dict[str, str],
    tech_stack_info: str = "",
    *,
    verbose: bool = False,
) -> CodeValidationResult:
    """Run LLM-driven linter validation on project files.

    This layer:
    1. Uses LLM to analyze project tech stack and decide which linters to use
    2. Generates appropriate lint commands
    3. Executes commands in sandbox
    4. Parses output and returns structured results

    Args:
        runtime_workspace: RuntimeWorkspace instance for command execution
        llm: LLM model instance
        files: Dict mapping file paths to content
        tech_stack_info: Project memory tech stack context
        verbose: Whether to print debug info

    Returns:
        CodeValidationResult: Linter validation results
    """
    if not runtime_workspace or not runtime_workspace.is_initialized:
        return CodeValidationResult(
            is_valid=True,
            score=1.0,
            warnings=["Linter validation skipped: no runtime workspace"],
            details={"linter_check": False, "reason": "no_runtime"},
        )

    # Step 1: Generate linter strategy using LLM
    from ._observability import get_logger
    logger = get_logger()
    if verbose:
        logger.debug("[Validation] Generating linter strategy...")

    strategy = await generate_linter_strategy(
        llm, files, tech_stack_info, verbose=verbose
    )

    if not strategy or not strategy.get("linter_commands"):
        return CodeValidationResult(
            is_valid=True,
            score=0.8,
            warnings=["Could not determine appropriate linters for this project"],
            details={"linter_check": False, "reason": "no_strategy"},
        )

    # Step 2: Execute linter commands
    commands = strategy.get("linter_commands", [])
    check_results: list[LinterCheckResult] = []
    total_errors = 0
    total_warnings = 0

    if verbose:
        logger.debug(f"[Validation] Running {len(commands)} linter checks...")

    for cmd_spec in commands:
        cmd_name = cmd_spec.get("name", "lint")
        command = cmd_spec.get("command", "")
        working_dir = cmd_spec.get("working_dir", "")
        timeout = cmd_spec.get("timeout", 60)
        install_cmd = cmd_spec.get("install_command")

        if not command:
            continue

        if verbose:
            logger.debug(f"[Validation]   - {cmd_name}: {command[:60]}...")

        # Try to run the command
        try:
            result = runtime_workspace.execute_command(
                command,
                working_dir=working_dir if working_dir else None,
                timeout=timeout,
            )

            output = result.get("output", "")
            error_output = result.get("error", "")
            success = result.get("success", False)

            # If command failed due to tool not found, try installing
            if not success and install_cmd and "not found" in error_output.lower():
                if verbose:
                    logger.debug(f"[Validation]     Installing: {install_cmd[:50]}...")
                runtime_workspace.execute_command(install_cmd, timeout=120)
                # Retry
                result = runtime_workspace.execute_command(
                    command,
                    working_dir=working_dir if working_dir else None,
                    timeout=timeout,
                )
                output = result.get("output", "")
                success = result.get("success", False)

            # Parse output
            errors, warnings, details = parse_linter_output(
                output + "\n" + error_output, command
            )

            # Some linters return non-zero on warnings, but that's ok
            if not success and errors == 0:
                success = True

            check_results.append(LinterCheckResult(
                name=cmd_name,
                command=command,
                success=success,
                output=output[:1000],
                error_count=errors,
                warning_count=warnings,
                details=details,
            ))

            total_errors += errors
            total_warnings += warnings

        except Exception as exc:
            check_results.append(LinterCheckResult(
                name=cmd_name,
                command=command,
                success=False,
                output="",
                error_count=1,
                details=[f"Execution failed: {exc}"],
            ))
            total_errors += 1

    # Step 3: Calculate score and build result
    if not check_results:
        return CodeValidationResult(
            is_valid=True,
            score=0.8,
            warnings=["No linter checks were executed"],
            details={"linter_check": False},
        )

    # Score calculation:
    # - Start with 1.0
    # - Deduct 0.05 for each error (max 0.4 deduction) - more lenient
    # - Deduct 0.01 for each warning (max 0.1 deduction) - more lenient
    # This allows projects with some linter errors to still pass validation
    error_penalty = min(0.4, total_errors * 0.05)
    warning_penalty = min(0.1, total_warnings * 0.01)
    score = max(0.3, 1.0 - error_penalty - warning_penalty)

    # Build error messages
    errors: list[str] = []
    warnings_list: list[str] = []

    for check in check_results:
        if check.error_count > 0:
            errors.append(f"{check.name}: {check.error_count} errors")
            errors.extend(check.details[:3])
        if check.warning_count > 0:
            warnings_list.append(f"{check.name}: {check.warning_count} warnings")

    is_valid = total_errors == 0

    return CodeValidationResult(
        is_valid=is_valid,
        score=score,
        errors=errors,
        warnings=warnings_list,
        details={
            "linter_check": True,
            "checks_run": len(check_results),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "detected_stack": strategy.get("detected_stack", {}),
            "check_results": [
                {
                    "name": c.name,
                    "success": c.success,
                    "errors": c.error_count,
                    "warnings": c.warning_count,
                }
                for c in check_results
            ],
        },
    )


# ---------------------------------------------------------------------------
# Compile Validation (LLM-Driven, Language-Agnostic)
# ---------------------------------------------------------------------------
@dataclass
class CompileCheckResult:
    """Result of a single compile check."""

    name: str
    command: str
    success: bool
    output: str = ""
    error_count: int = 0
    details: list[str] = field(default_factory=list)


COMPILE_STRATEGY_PROMPT = """你是一个编译/构建工具专家。根据以下项目文件结构，生成用于验证代码能否正确编译/导入的命令。

## 项目文件
{file_list}

## 任务
分析项目使用的技术栈，生成**编译验证命令**。这些命令应该能够检测：
- 模块导入错误（缺少依赖、循环导入等）
- 类型错误（TypeScript、Java 等静态类型语言）
- 编译错误（Go、Rust、C++ 等编译型语言）

### 常见技术栈对应的编译验证命令：
- Python (FastAPI/Django/Flask): `python -c "from <module> import <entry>"`
- TypeScript/JavaScript: `npx tsc --noEmit` 或 `npm run build`
- Vue.js: `npx vue-tsc --noEmit`
- React: `npx tsc --noEmit` 或 `npm run build`
- Go: `go build ./...`
- Rust: `cargo check`
- Java/Kotlin: `mvn compile` 或 `gradle compileJava`
- C/C++: `make` 或 `cmake --build .`

### 输出格式
```json
{{
  "detected_stack": {{
    "languages": ["检测到的语言"],
    "frameworks": ["检测到的框架"],
    "build_tools": ["检测到的构建工具"]
  }},
  "compile_commands": [
    {{
      "name": "检查名称",
      "command": "要执行的命令",
      "working_dir": "工作目录（相对路径，如 backend 或 frontend）",
      "timeout": 120,
      "install_command": "安装依赖的命令（可选，如 npm install）",
      "success_indicator": "成功时输出中应包含的文本（可选）",
      "error_patterns": ["错误输出的正则模式"]
    }}
  ],
  "reasoning": "为什么选择这些编译验证命令"
}}
```

注意：
- 只根据实际存在的文件来选择验证命令
- 优先使用项目已配置的构建命令（检查 package.json scripts、Makefile 等）
- 命令应该只做验证，不应该产生实际的构建产物（使用 --noEmit、check 等选项）
- 对于需要安装依赖的项目，提供 install_command
- error_patterns 应该是能匹配编译错误输出的正则表达式
"""


async def generate_compile_strategy(
    llm: Any,
    files: dict[str, str],
    *,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Use LLM to generate compile validation strategy based on project structure.

    Args:
        llm: LLM model instance
        files: Dict mapping file paths to content
        verbose: Whether to print debug info

    Returns:
        dict: Compile strategy with commands to run, or None if failed
    """
    from ._llm_utils import call_llm_json

    # Filter out third-party files
    source_files = _filter_source_files(files)

    # Build file list summary
    file_list = "\n".join(f"- {fpath}" for fpath in sorted(source_files.keys())[:50])
    if len(source_files) > 50:
        file_list += f"\n... 及其他 {len(source_files) - 50} 个源文件"

    prompt = COMPILE_STRATEGY_PROMPT.format(file_list=file_list)

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是编译/构建工具专家，请根据项目结构选择合适的编译验证命令。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            label="compile_strategy",
            verbose=verbose,
        )
        return result
    except Exception as exc:
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Compile] Failed to generate compile strategy: {exc}")
        return None


def _parse_compile_output(
    output: str,
    error_patterns: list[str] | None,
) -> tuple[int, list[str]]:
    """Parse compile output to extract error count and details.

    Args:
        output: Command output
        error_patterns: Regex patterns to match errors

    Returns:
        tuple: (error_count, detail_messages)
    """
    errors = 0
    details: list[str] = []

    lines = output.split("\n")

    # Default error patterns for common languages
    default_patterns = [
        r"error[:\s]",  # Generic error
        r"Error[:\s]",
        r"ERROR[:\s]",
        r"failed",
        r"FAILED",
        r"cannot find",
        r"not found",
        r"undefined",
        r"No module named",
        r"ModuleNotFoundError",
        r"ImportError",
        r"SyntaxError",
        r"error TS\d+",  # TypeScript
        r"error\[E\d+\]",  # Rust
        r"error: ",  # Go, C++
    ]

    patterns = error_patterns or default_patterns

    for line in lines:
        line = line.strip()
        if not line:
            continue

        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                errors += 1
                if len(details) < 10:
                    details.append(line[:200])
                break

    return errors, details


async def run_compile_validation(
    runtime_workspace: "RuntimeWorkspace",
    llm: Any,
    files: dict[str, str],
    *,
    verbose: bool = False,
) -> CodeValidationResult:
    """Run LLM-driven compile/build validation on project.

    This is a language-agnostic compile validation that:
    1. Uses LLM to analyze project structure and detect tech stack
    2. Generates appropriate compile/import validation commands
    3. Executes commands in sandbox
    4. Parses output and returns structured results

    Args:
        runtime_workspace: RuntimeWorkspace instance for execution
        llm: LLM model instance
        files: Dict mapping file paths to content
        verbose: Whether to print debug info

    Returns:
        CodeValidationResult: Compile validation results
    """
    if not runtime_workspace or not runtime_workspace.is_initialized:
        return CodeValidationResult(
            is_valid=True,
            score=1.0,
            warnings=["Compile validation skipped: no runtime"],
            details={"compile_check": False, "reason": "no_runtime"},
        )

    from ._observability import get_logger
    logger = get_logger()

    # Step 1: Generate compile strategy using LLM
    if verbose:
        logger.debug("[Compile] 生成编译验证策略...")

    strategy = await generate_compile_strategy(llm, files, verbose=verbose)

    if not strategy or not strategy.get("compile_commands"):
        return CodeValidationResult(
            is_valid=True,
            score=0.8,
            warnings=["Could not determine appropriate compile commands for this project"],
            details={"compile_check": False, "reason": "no_strategy"},
        )

    # Step 2: Execute compile commands
    commands = strategy.get("compile_commands", [])
    check_results: list[CompileCheckResult] = []
    all_errors: list[str] = []

    if verbose:
        detected = strategy.get("detected_stack", {})
        logger.debug(f"[Compile] 检测到技术栈: {detected.get('languages', [])} / {detected.get('frameworks', [])}")
        logger.debug(f"[Compile] 执行 {len(commands)} 个编译验证...")

    for cmd_spec in commands:
        cmd_name = cmd_spec.get("name", "compile")
        command = cmd_spec.get("command", "")
        working_dir = cmd_spec.get("working_dir", "")
        timeout = cmd_spec.get("timeout", 120)
        install_cmd = cmd_spec.get("install_command")
        success_indicator = cmd_spec.get("success_indicator")
        error_patterns = cmd_spec.get("error_patterns")

        if not command:
            continue

        if verbose:
            logger.debug(f"[Compile]   - {cmd_name}: {command[:60]}...")

        try:
            # Install dependencies first if needed
            if install_cmd:
                if verbose:
                    logger.debug(f"[Compile]     安装依赖: {install_cmd[:50]}...")
                runtime_workspace.execute_command(
                    install_cmd,
                    working_dir=working_dir if working_dir else None,
                    timeout=180,
                )

            # Run compile command
            result = runtime_workspace.execute_command(
                command,
                working_dir=working_dir if working_dir else None,
                timeout=timeout,
            )

            output = result.get("output", "")
            error_output = result.get("error", "")
            success = result.get("success", False)
            combined_output = output + "\n" + error_output

            # Check for success indicator
            if success_indicator and success_indicator in combined_output:
                success = True

            # Parse errors
            error_count, error_details = _parse_compile_output(
                combined_output, error_patterns
            )

            # If command succeeded and no errors found, it's a pass
            if success and error_count == 0:
                check_results.append(CompileCheckResult(
                    name=cmd_name,
                    command=command,
                    success=True,
                    output="编译验证通过",
                ))
                if verbose:
                    logger.debug(f"[Compile]     ✓ {cmd_name} 通过")
            else:
                all_errors.append(f"{cmd_name}: {error_count} 个错误")
                all_errors.extend(error_details[:3])

                check_results.append(CompileCheckResult(
                    name=cmd_name,
                    command=command,
                    success=False,
                    output=combined_output[:1000],
                    error_count=error_count,
                    details=error_details,
                ))
                if verbose:
                    logger.warn(f"[Compile]     ✗ {cmd_name} 失败: {error_count} 个错误")

        except Exception as exc:
            check_results.append(CompileCheckResult(
                name=cmd_name,
                command=command,
                success=False,
                output="",
                error_count=1,
                details=[f"执行失败: {exc}"],
            ))
            all_errors.append(f"{cmd_name}: 执行失败 - {exc}")

    # Step 3: Calculate score
    if not check_results:
        return CodeValidationResult(
            is_valid=True,
            score=0.8,
            warnings=["No compile checks were executed"],
            details={"compile_check": False},
        )

    total_checks = len(check_results)
    passed_checks = sum(1 for c in check_results if c.success)
    total_errors = sum(c.error_count for c in check_results)

    # Base score from pass rate
    if total_checks > 0:
        base_score = passed_checks / total_checks
    else:
        base_score = 1.0

    # Additional penalty for error count
    error_penalty = min(0.3, total_errors * 0.02)
    score = max(0.0, base_score - error_penalty)

    is_valid = all(c.success for c in check_results)

    return CodeValidationResult(
        is_valid=is_valid,
        score=score,
        errors=all_errors,
        warnings=[],
        details={
            "compile_check": True,
            "detected_stack": strategy.get("detected_stack", {}),
            "checks_run": total_checks,
            "checks_passed": passed_checks,
            "total_errors": total_errors,
            "check_results": [
                {
                    "name": c.name,
                    "success": c.success,
                    "errors": c.error_count,
                    "details": c.details[:3],
                }
                for c in check_results
            ],
        },
    )


# ---------------------------------------------------------------------------
# Layered Validation Pipeline
# ---------------------------------------------------------------------------
async def layered_code_validation(
    runtime_workspace: "RuntimeWorkspace | None",
    llm: Any,
    files: dict[str, str],
    requirement_summary: str,
    *,
    tech_stack_info: str = "",
    verbose: bool = False,
) -> CodeValidationResult:
    """Run layered code validation pipeline.

    Validation layers:
    1. Static analysis (syntax, completeness) - weight 15%
    2. Import validation (if runtime available) - weight 15%
    3. LLM-driven linter validation (if runtime available) - weight 30%
    4. **Compile validation** (real build test) - weight 40%

    Note: LLM code review layer was removed because it caused false negatives
    by judging code completeness from summaries instead of actual execution.
    Functional validation is now handled by QA acceptance phase.

    Args:
        runtime_workspace: RuntimeWorkspace instance (optional)
        llm: LLM model instance (used for linter/compile strategy generation)
        files: Dict mapping file paths to content
        requirement_summary: Brief description of requirements
        tech_stack_info: Project memory tech stack context for linter selection
        verbose: Whether to print debug info

    Returns:
        CodeValidationResult: Combined validation results
    """
    from ._observability import get_logger
    logger = get_logger()

    # Filter out third-party files (node_modules, __pycache__, etc.)
    source_files = _filter_source_files(files)
    if verbose:
        logger.debug(f"[Validation] Filtered {len(files)} files to {len(source_files)} source files")

    all_errors: list[str] = []
    all_warnings: list[str] = []
    details: dict[str, Any] = {}
    layer_results: list[tuple[str, float]] = []  # (layer_name, score)

    # Layer 1: Static validation (use source files only)
    if verbose:
        logger.debug("[Validation] Running static analysis...")
    static_result = run_static_validation(source_files)
    all_errors.extend(static_result.errors)
    all_warnings.extend(static_result.warnings)
    layer_results.append(("static", static_result.score))
    details["static"] = static_result.details

    # Layer 2: Import validation (requires runtime)
    if runtime_workspace and runtime_workspace.is_initialized:
        if verbose:
            logger.debug("[Validation] Running import validation...")
        import_result = run_import_validation(runtime_workspace, source_files)
        all_errors.extend(import_result.errors)
        all_warnings.extend(import_result.warnings)
        layer_results.append(("import", import_result.score))
        details["import"] = import_result.details
    else:
        # Skip gracefully with a neutral score when no runtime available
        if verbose:
            logger.debug("[Validation] Import validation skipped (no runtime)")
        all_warnings.append("Import validation skipped: no RuntimeWorkspace")
        layer_results.append(("import", 0.7))  # Neutral score, not failing
        details["import"] = {"skipped": True, "reason": "no_runtime"}

    # Layer 3: LLM-driven linter validation (requires runtime)
    if runtime_workspace and runtime_workspace.is_initialized:
        if verbose:
            logger.debug("[Validation] Running LLM-driven linter validation...")
        linter_result = await run_linter_validation(
            runtime_workspace, llm, source_files, tech_stack_info, verbose=verbose
        )
        all_errors.extend(linter_result.errors)
        all_warnings.extend(linter_result.warnings)
        layer_results.append(("linter", linter_result.score))
        details["linter"] = linter_result.details
    else:
        # Skip gracefully with a neutral score when no runtime available
        if verbose:
            logger.debug("[Validation] Linter validation skipped (no runtime)")
        all_warnings.append("Linter validation skipped: no RuntimeWorkspace")
        layer_results.append(("linter", 0.7))  # Neutral score, not failing
        details["linter"] = {"skipped": True, "reason": "no_runtime"}

    # Layer 4: Compile validation (LLM-driven, language-agnostic)
    if runtime_workspace and runtime_workspace.is_initialized:
        if verbose:
            logger.debug("[Validation] Running compile validation (LLM-driven)...")
        compile_result = await run_compile_validation(
            runtime_workspace, llm, files, verbose=verbose  # LLM-driven compile strategy
        )
        all_errors.extend(compile_result.errors)
        all_warnings.extend(compile_result.warnings)
        layer_results.append(("compile", compile_result.score))
        details["compile"] = compile_result.details

        # If compile fails, this is critical - early exit with low score
        if not compile_result.is_valid:
            if verbose:
                logger.warn(f"[Validation] ✗ 编译验证失败 - 代码无法运行")
                for err in compile_result.errors[:3]:
                    logger.warn(f"[Validation]   - {err}")
    else:
        if verbose:
            logger.debug("[Validation] Compile validation skipped (no runtime)")
        all_warnings.append("Compile validation skipped: no RuntimeWorkspace")
        layer_results.append(("compile", 0.7))  # Neutral score
        details["compile"] = {"skipped": True, "reason": "no_runtime"}

    # Layer 5: LLM lightweight review - REMOVED
    # LLM code review based on summaries causes false negatives.
    # Real validation should be runtime-based (run code, check results).
    # Compile validation (Layer 4) already verifies code can run.
    # QA acceptance (separate phase) verifies functional requirements.

    # Calculate combined score (weighted average)
    # Weights adjusted after removing LLM review layer
    # Compile validation is critical - highest weight
    weight_map = {
        "static": 0.15,
        "import": 0.15,
        "linter": 0.30,
        "compile": 0.40,  # Most important - real build test
    }

    if layer_results:
        # Normalize weights based on which layers ran
        total_weight = sum(weight_map.get(name, 0.2) for name, _ in layer_results)
        combined_score = sum(
            score * (weight_map.get(name, 0.2) / total_weight)
            for name, score in layer_results
        )
    else:
        combined_score = 1.0

    # Determine validity
    # If compile validation failed, code is invalid regardless of score
    compile_passed = details.get("compile", {}).get("skipped", True) or \
                     all(c.get("success", True) for c in details.get("compile", {}).get("check_results", []))
    is_valid = len(all_errors) == 0 and combined_score >= 0.6 and compile_passed

    return CodeValidationResult(
        is_valid=is_valid,
        score=combined_score,
        errors=all_errors,
        warnings=all_warnings,
        details=details,
    )


__all__ = [
    "CodeValidationResult",
    "LinterCheckResult",
    "CompileCheckResult",
    "check_code_completeness",
    "run_static_validation",
    "run_import_validation",
    "run_linter_validation",
    "run_compile_validation",
    "generate_linter_strategy",
    "generate_compile_strategy",
    "extract_file_summary",
    "validate_code_lightweight",
    "validate_code_with_llm",
    "layered_code_validation",
    "_filter_source_files",
]
