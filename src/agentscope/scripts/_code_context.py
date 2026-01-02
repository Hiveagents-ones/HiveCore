# -*- coding: utf-8 -*-
"""Code context analysis for ensuring import consistency.

This module provides Claude Code-style "read before write" functionality:
- Scan existing files to understand project structure
- Extract module exports (functions, classes, types)
- Validate imports before generating code
- Register new files after creation

The goal is to prevent agents from referencing non-existent modules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.ones.memory import ProjectMemory


# ---------------------------------------------------------------------------
# File Scanning
# ---------------------------------------------------------------------------
def scan_workspace_files(workspace_dir: Path) -> dict[str, str]:
    """Scan workspace and return all source files with their content.

    Args:
        workspace_dir: Workspace directory path

    Returns:
        dict: Mapping of relative path to file content
    """
    files: dict[str, str] = {}

    # Source file extensions to scan
    extensions = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".vue",
        ".json", ".yaml", ".yml", ".toml",
    }

    # Directories to skip
    skip_dirs = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "coverage",
    }

    if not workspace_dir.exists():
        return files

    for file_path in workspace_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in extensions:
            # Check if any parent is in skip_dirs
            if any(skip in file_path.parts for skip in skip_dirs):
                continue

            try:
                rel_path = str(file_path.relative_to(workspace_dir))
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                files[rel_path] = content
            except Exception:
                pass

    return files


def get_file_tree(workspace_dir: Path, max_depth: int = 4) -> str:
    """Generate a tree view of the workspace structure.

    Args:
        workspace_dir: Workspace directory path
        max_depth: Maximum depth to traverse

    Returns:
        str: Tree view string
    """
    lines: list[str] = []
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build"}

    def walk(path: Path, prefix: str = "", depth: int = 0) -> None:
        if depth > max_depth:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and e.name not in skip_dirs]
        files = [e for e in entries if e.is_file()]

        for i, entry in enumerate(dirs + files):
            is_last = i == len(dirs) + len(files) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                walk(entry, prefix + extension, depth + 1)

    lines.append(str(workspace_dir.name) + "/")
    walk(workspace_dir)

    return "\n".join(lines[:100])  # Limit output


# ---------------------------------------------------------------------------
# Export Analysis
# ---------------------------------------------------------------------------
def extract_python_exports(content: str) -> list[dict[str, str]]:
    """Extract exported functions, classes, and variables from Python code.

    Args:
        content: Python file content

    Returns:
        list: List of export info dicts with 'name', 'type', 'signature'
    """
    exports: list[dict[str, str]] = []

    # Class definitions
    for match in re.finditer(r"^class\s+(\w+)(?:\([^)]*\))?:", content, re.MULTILINE):
        exports.append({
            "name": match.group(1),
            "type": "class",
            "signature": match.group(0).strip(),
        })

    # Function definitions
    for match in re.finditer(
        r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]+))?:",
        content,
        re.MULTILINE,
    ):
        func_name = match.group(1)
        if not func_name.startswith("_"):  # Skip private functions
            exports.append({
                "name": func_name,
                "type": "function",
                "signature": match.group(0).strip()[:100],
            })

    # __all__ exports
    all_match = re.search(r"__all__\s*=\s*\[([^\]]+)\]", content)
    if all_match:
        all_names = re.findall(r"['\"](\w+)['\"]", all_match.group(1))
        for name in all_names:
            if not any(e["name"] == name for e in exports):
                exports.append({"name": name, "type": "exported", "signature": name})

    return exports


def extract_typescript_exports(content: str) -> list[dict[str, str]]:
    """Extract exported functions, types, and interfaces from TypeScript/JS.

    Args:
        content: TypeScript/JavaScript file content

    Returns:
        list: List of export info dicts
    """
    exports: list[dict[str, str]] = []

    # Named exports: export function/const/class/interface/type
    patterns = [
        (r"export\s+(?:async\s+)?function\s+(\w+)", "function"),
        (r"export\s+const\s+(\w+)", "const"),
        (r"export\s+class\s+(\w+)", "class"),
        (r"export\s+interface\s+(\w+)", "interface"),
        (r"export\s+type\s+(\w+)", "type"),
        (r"export\s+enum\s+(\w+)", "enum"),
    ]

    for pattern, export_type in patterns:
        for match in re.finditer(pattern, content):
            exports.append({
                "name": match.group(1),
                "type": export_type,
                "signature": match.group(0)[:80],
            })

    # Default export
    default_match = re.search(r"export\s+default\s+(?:function\s+)?(\w+)", content)
    if default_match:
        exports.append({
            "name": "default",
            "type": "default",
            "signature": default_match.group(1),
        })

    # Re-exports: export { x, y } from './module'
    for match in re.finditer(r"export\s*\{([^}]+)\}", content):
        names = re.findall(r"(\w+)(?:\s+as\s+\w+)?", match.group(1))
        for name in names:
            if not any(e["name"] == name for e in exports):
                exports.append({"name": name, "type": "re-export", "signature": name})

    return exports


def extract_vue_exports(content: str) -> list[dict[str, str]]:
    """Extract exports from Vue single file components.

    Args:
        content: Vue file content

    Returns:
        list: List of export info dicts
    """
    exports: list[dict[str, str]] = []

    # Vue components always have a default export
    exports.append({"name": "default", "type": "component", "signature": "Vue Component"})

    # Check for script setup with defineExpose
    expose_match = re.search(r"defineExpose\s*\(\s*\{([^}]+)\}", content)
    if expose_match:
        names = re.findall(r"(\w+)", expose_match.group(1))
        for name in names:
            exports.append({"name": name, "type": "exposed", "signature": name})

    # Extract types defined in script
    script_match = re.search(r"<script[^>]*>(.*?)</script>", content, re.DOTALL)
    if script_match:
        script_content = script_match.group(1)
        exports.extend(extract_typescript_exports(script_content))

    return exports


# ---------------------------------------------------------------------------
# Module Registry
# ---------------------------------------------------------------------------
def build_module_registry(
    files: dict[str, str],
    project_type: str = "fullstack",
) -> dict[str, list[dict[str, str]]]:
    """Build a registry of all module exports.

    Args:
        files: Mapping of file path to content
        project_type: Project type for path alias resolution

    Returns:
        dict: Mapping of module path to list of exports
    """
    registry: dict[str, list[dict[str, str]]] = {}

    for file_path, content in files.items():
        if not content.strip():
            continue

        exports: list[dict[str, str]] = []

        if file_path.endswith(".py"):
            exports = extract_python_exports(content)
        elif file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            exports = extract_typescript_exports(content)
        elif file_path.endswith(".vue"):
            exports = extract_vue_exports(content)

        if exports:
            # Store with multiple path formats for lookup
            registry[file_path] = exports

            # Also store with @ alias for frontend files
            if file_path.startswith("frontend/src/"):
                alias_path = "@/" + file_path[13:]  # Remove "frontend/src/"
                registry[alias_path] = exports
                # Without extension
                if alias_path.endswith((".ts", ".js", ".vue")):
                    registry[alias_path.rsplit(".", 1)[0]] = exports

    return registry


def format_module_registry_for_prompt(
    registry: dict[str, list[dict[str, str]]],
    max_modules: int = 30,
    include_signatures: bool = True,
) -> str:
    """Format module registry for inclusion in agent prompts.

    Args:
        registry: Module registry from build_module_registry
        max_modules: Maximum number of modules to include
        include_signatures: Whether to include function/class signatures

    Returns:
        str: Formatted string for prompt with interface signatures
    """
    if not registry:
        return ""

    lines = ["## 已存在的模块和接口定义\n"]

    # Group by directory, prefer @/ paths over frontend/ paths
    frontend_modules: dict[str, list[dict[str, str]]] = {}
    backend_modules: dict[str, list[dict[str, str]]] = {}

    for path, exports in sorted(registry.items()):
        # Prefer @/ alias paths, skip duplicate frontend/ paths
        if path.startswith("frontend/src/"):
            continue  # Will use @/ version instead

        if path.startswith("@/"):
            if len(frontend_modules) < max_modules // 2:
                frontend_modules[path] = exports
        elif path.startswith("backend/"):
            if len(backend_modules) < max_modules // 2:
                backend_modules[path] = exports

    # Format frontend modules with signatures
    if frontend_modules:
        lines.append("### 前端模块（可引用的接口）")
        lines.append("导入格式: `import { xxx } from '@/path/to/module'`\n")
        for path, exports in frontend_modules.items():
            lines.append(f"\n**`{path}`**")
            for exp in exports[:8]:  # Limit exports per module
                sig = exp.get("signature", exp["name"])
                exp_type = exp.get("type", "")
                if include_signatures and sig and sig != exp["name"]:
                    lines.append(f"  - `{sig}`")
                else:
                    lines.append(f"  - {exp_type}: `{exp['name']}`")

    # Format backend modules with signatures
    # Convert file path to Python import path for clarity
    if backend_modules:
        lines.append("\n### 后端模块（可引用的接口）")
        lines.append("导入格式: `from app.xxx import yyy` (注意: 不要包含 'backend/' 前缀)\n")
        for path, exports in backend_modules.items():
            # Convert backend/app/database.py -> app.database
            python_import_path = _file_path_to_python_import(path)
            lines.append(f"\n**`{python_import_path}`** (文件: `{path}`)")
            for exp in exports[:8]:
                sig = exp.get("signature", exp["name"])
                exp_type = exp.get("type", "")
                if include_signatures and sig and sig != exp["name"]:
                    lines.append(f"  - `{sig}`")
                else:
                    lines.append(f"  - {exp_type}: `{exp['name']}`")

    return "\n".join(lines)


def _file_path_to_python_import(file_path: str) -> str:
    """Convert file path to Python import path.

    Args:
        file_path: File path like 'backend/app/database.py'

    Returns:
        str: Python import path like 'app.database'
    """
    # Remove 'backend/' prefix if present
    if file_path.startswith("backend/"):
        file_path = file_path[8:]

    # Remove .py extension
    if file_path.endswith(".py"):
        file_path = file_path[:-3]

    # Convert / to .
    import_path = file_path.replace("/", ".")

    # Remove __init__ suffix
    if import_path.endswith(".__init__"):
        import_path = import_path[:-9]

    return import_path


def get_interface_constraint_prompt() -> str:
    """Get language-agnostic interface calling constraint prompt.

    This implements Claude Code's "Read Before Write" principle:
    - Only call interfaces that are explicitly defined in context
    - If interface is not found, add TODO comment instead of guessing

    Returns:
        str: Constraint prompt text (language-agnostic)
    """
    return """
## 模块导入约束（严格遵守）

【核心原则】只能导入"已列出的模块"

1. **允许导入**：
   - 标准库模块（os, sys, json, typing 等）
   - 第三方库（fastapi, sqlalchemy, pydantic, axios, vue 等）
   - 上面"已存在的模块"列表中明确列出的项目模块

2. **禁止导入**：
   - 任何不在上述列表中的 `app.xxx` 或 `@/xxx` 路径
   - 例如：如果列表中没有 `app.utils`，就不能 `from app.utils import xxx`

【Python 后端规则】
- 只能使用 `from app.xxx import yyy`，其中 `app.xxx` 必须在"后端模块"列表中
- 如果需要工具函数但没有 `app.utils`，直接在当前文件中定义
- 禁止假设存在 `app.utils`, `app.helpers`, `app.common` 等未列出模块

【前端规则】
- 只能使用 `import xxx from '@/path'`，其中路径必须在"前端模块"列表中
- 如果需要工具函数但没有对应模块，直接在当前文件中定义

【违规处理】
如果你需要一个不存在的模块，有两个选择：
1. 在当前文件中直接实现该功能（推荐）
2. 添加 TODO 注释说明需要创建的模块

【TODO 格式】
```python
# TODO: 需要创建 app.utils 模块，提供 format_phone(phone: str) -> str
```
"""


# ---------------------------------------------------------------------------
# Import Validation
# ---------------------------------------------------------------------------
def extract_imports_from_code(content: str, file_type: str) -> list[str]:
    """Extract import paths from code.

    Args:
        content: Source code content
        file_type: File type (py, ts, vue, etc.)

    Returns:
        list: List of import paths
    """
    imports: list[str] = []

    if file_type == "py":
        # Python imports
        for match in re.finditer(r"^(?:from|import)\s+([^\s]+)", content, re.MULTILINE):
            imports.append(match.group(1).split(".")[0])
    else:
        # JS/TS/Vue imports
        for match in re.finditer(r"(?:import|from)\s+['\"]([^'\"]+)['\"]", content):
            imports.append(match.group(1))
        for match in re.finditer(r"import\s*\(['\"]([^'\"]+)['\"]\)", content):
            imports.append(match.group(1))

    return imports


def validate_imports(
    code_content: str,
    file_path: str,
    registry: dict[str, list[dict[str, str]]],
) -> list[str]:
    """Validate that all imports in code exist in the registry.

    Args:
        code_content: Generated code content
        file_path: Target file path
        registry: Module registry

    Returns:
        list: List of missing import paths
    """
    file_type = "py" if file_path.endswith(".py") else "ts"
    imports = extract_imports_from_code(code_content, file_type)

    missing: list[str] = []

    for imp in imports:
        # Skip standard library and node_modules
        if file_type == "py":
            if imp in {"os", "sys", "json", "re", "typing", "pathlib", "datetime", "asyncio"}:
                continue
            if imp in {"fastapi", "sqlalchemy", "pydantic", "uvicorn", "passlib", "jose"}:
                continue
        else:
            if not imp.startswith("@/") and not imp.startswith("./") and not imp.startswith("../"):
                continue  # External package

        # Check if import exists in registry
        found = False
        for reg_path in registry.keys():
            if imp in reg_path or reg_path.endswith(imp) or reg_path.endswith(imp + ".ts"):
                found = True
                break

        if not found and imp.startswith("@/"):
            missing.append(imp)

    return missing


# ---------------------------------------------------------------------------
# File Registration
# ---------------------------------------------------------------------------
def register_generated_files(
    project_memory: "ProjectMemory",
    files: list[dict[str, Any]],
    requirement_id: str,
) -> None:
    """Register generated files in project memory.

    Args:
        project_memory: ProjectMemory instance
        files: List of file dicts with 'path' and 'content'
        requirement_id: Requirement ID that generated these files
    """
    for file_info in files:
        path = file_info.get("path", "")
        content = file_info.get("content", "")

        if not path or not content:
            continue

        # Generate description based on file type and content
        description = _generate_file_description(path, content)

        project_memory.register_file(
            path=path,
            description=f"[{requirement_id}] {description}",
        )


def _generate_file_description(path: str, content: str) -> str:
    """Generate a brief description of a file based on its content.

    Args:
        path: File path
        content: File content

    Returns:
        str: Brief description
    """
    # Extract first docstring or comment
    if path.endswith(".py"):
        doc_match = re.search(r'"""([^"]+)"""', content)
        if doc_match:
            return doc_match.group(1).strip()[:50]
    elif path.endswith((".ts", ".js", ".vue")):
        comment_match = re.search(r"/\*\*?\s*\n?\s*\*?\s*([^\n*]+)", content)
        if comment_match:
            return comment_match.group(1).strip()[:50]

    # Fallback: describe by path
    if "router" in path.lower():
        return "路由配置"
    elif "store" in path.lower():
        return "状态管理"
    elif "api" in path.lower():
        return "API 接口"
    elif "model" in path.lower():
        return "数据模型"
    elif "view" in path.lower() or "page" in path.lower():
        return "页面组件"
    elif "component" in path.lower():
        return "UI 组件"
    elif "type" in path.lower():
        return "类型定义"
    elif "util" in path.lower():
        return "工具函数"
    else:
        return "源代码文件"


# ---------------------------------------------------------------------------
# Context Builder
# ---------------------------------------------------------------------------
def build_code_context(
    workspace_dir: Path,
    project_memory: "ProjectMemory | None" = None,
    include_file_tree: bool = True,
    include_exports: bool = True,
    max_context_length: int = 8000,
) -> str:
    """Build comprehensive code context for agent prompts.

    This mimics Claude Code's approach of understanding the codebase
    before generating new code.

    Args:
        workspace_dir: Workspace directory
        project_memory: Optional project memory for additional context
        include_file_tree: Whether to include file tree
        include_exports: Whether to include module exports
        max_context_length: Maximum context string length

    Returns:
        str: Formatted context string
    """
    sections: list[str] = []

    # 1. File tree
    if include_file_tree:
        tree = get_file_tree(workspace_dir)
        if tree:
            sections.append(f"## 项目文件结构\n```\n{tree}\n```")

    # 2. Module exports
    if include_exports:
        files = scan_workspace_files(workspace_dir)
        if files:
            registry = build_module_registry(files)
            exports_str = format_module_registry_for_prompt(registry)
            if exports_str:
                sections.append(exports_str)

    # 3. Project memory decisions
    if project_memory:
        memory_ctx = project_memory.get_context_for_prompt(include_instructions=False)
        if memory_ctx:
            sections.append(memory_ctx)

    # Combine and truncate if needed
    context = "\n\n".join(sections)
    if len(context) > max_context_length:
        context = context[:max_context_length] + "\n...(truncated)"

    return context


# ---------------------------------------------------------------------------
# Claude Code Style: Read Before Write + Import Validation
# ---------------------------------------------------------------------------
@dataclass
class ImportValidationResult:
    """Result of import validation."""

    valid: bool
    invalid_imports: list[dict[str, str]]  # [{"import": "...", "reason": "..."}]
    suggested_fixes: dict[str, str]  # {"invalid_path": "correct_path"}


def validate_imports_strict(
    code_content: str,
    file_path: str,
    registry: dict[str, list[dict[str, str]]],
    workspace_files: dict[str, str] | None = None,
) -> ImportValidationResult:
    """Strictly validate all imports in generated code (Claude Code style).

    Unlike soft validation, this checks every import and provides fixes.

    Args:
        code_content: Generated code content
        file_path: Target file path
        registry: Module registry
        workspace_files: All workspace files for additional validation

    Returns:
        ImportValidationResult with validation details and fixes
    """
    invalid_imports: list[dict[str, str]] = []
    suggested_fixes: dict[str, str] = {}

    is_python = file_path.endswith(".py")
    is_frontend = file_path.endswith((".ts", ".tsx", ".js", ".jsx", ".vue"))

    if is_python:
        # Validate Python imports
        invalid, fixes = _validate_python_imports(code_content, registry, workspace_files)
        invalid_imports.extend(invalid)
        suggested_fixes.update(fixes)
    elif is_frontend:
        # Validate frontend imports
        invalid, fixes = _validate_frontend_imports(code_content, registry)
        invalid_imports.extend(invalid)
        suggested_fixes.update(fixes)

    return ImportValidationResult(
        valid=len(invalid_imports) == 0,
        invalid_imports=invalid_imports,
        suggested_fixes=suggested_fixes,
    )


def _validate_python_imports(
    content: str,
    registry: dict[str, list[dict[str, str]]],
    workspace_files: dict[str, str] | None = None,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Validate Python imports and suggest fixes.

    Args:
        content: Python code content
        registry: Module registry
        workspace_files: All workspace files

    Returns:
        Tuple of (invalid_imports, suggested_fixes)
    """
    invalid: list[dict[str, str]] = []
    fixes: dict[str, str] = {}

    # Standard library and common third-party modules to skip
    stdlib_and_common = {
        "os", "sys", "json", "re", "typing", "pathlib", "datetime", "asyncio",
        "collections", "itertools", "functools", "dataclasses", "enum", "abc",
        "logging", "time", "uuid", "hashlib", "base64", "copy", "io",
        # Common third-party
        "fastapi", "sqlalchemy", "pydantic", "uvicorn", "passlib", "jose",
        "starlette", "redis", "celery", "pytest", "httpx", "aiohttp",
    }

    # Build a set of valid Python import paths from registry
    valid_paths: set[str] = set()
    for path in registry.keys():
        if path.startswith("backend/"):
            # Convert backend/app/database.py -> app.database
            py_path = _file_path_to_python_import(path)
            valid_paths.add(py_path)
            # Also add parent packages
            parts = py_path.split(".")
            for i in range(1, len(parts)):
                valid_paths.add(".".join(parts[:i]))

    # Also check workspace files
    if workspace_files:
        for path in workspace_files.keys():
            if path.startswith("backend/") and path.endswith(".py"):
                py_path = _file_path_to_python_import(path)
                valid_paths.add(py_path)
                parts = py_path.split(".")
                for i in range(1, len(parts)):
                    valid_paths.add(".".join(parts[:i]))

    # Extract and validate imports
    # Pattern: from xxx.yyy import zzz
    for match in re.finditer(r"^from\s+(\S+)\s+import", content, re.MULTILINE):
        import_path = match.group(1)

        # Skip stdlib and third-party
        root_module = import_path.split(".")[0]
        if root_module in stdlib_and_common:
            continue

        # Check if it's a project import (starts with app.)
        if import_path.startswith("app."):
            if import_path not in valid_paths:
                # Try to find the correct path
                correct_path = _find_correct_python_import(import_path, valid_paths)
                if correct_path:
                    invalid.append({
                        "import": import_path,
                        "reason": f"Module not found, did you mean '{correct_path}'?",
                    })
                    fixes[import_path] = correct_path
                else:
                    invalid.append({
                        "import": import_path,
                        "reason": "Module does not exist in the project",
                    })

    return invalid, fixes


def _validate_frontend_imports(
    content: str,
    registry: dict[str, list[dict[str, str]]],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Validate frontend imports and suggest fixes.

    Args:
        content: Frontend code content
        registry: Module registry

    Returns:
        Tuple of (invalid_imports, suggested_fixes)
    """
    invalid: list[dict[str, str]] = []
    fixes: dict[str, str] = {}

    # Build set of valid frontend paths
    valid_paths: set[str] = set()
    for path in registry.keys():
        if path.startswith("@/"):
            valid_paths.add(path)
            # Also add without extension
            for ext in (".ts", ".js", ".vue", ".tsx", ".jsx"):
                if path.endswith(ext):
                    valid_paths.add(path[:-len(ext)])

    # Extract imports: import xxx from '@/path' or import('@/path')
    for match in re.finditer(r"['\"](@/[^'\"]+)['\"]", content):
        import_path = match.group(1)

        # Normalize path (remove extension for comparison)
        normalized = import_path
        for ext in (".ts", ".js", ".vue", ".tsx", ".jsx"):
            if normalized.endswith(ext):
                normalized = normalized[:-len(ext)]
                break

        if normalized not in valid_paths and import_path not in valid_paths:
            # Try to find correct path
            correct_path = _find_correct_frontend_import(normalized, valid_paths)
            if correct_path:
                invalid.append({
                    "import": import_path,
                    "reason": f"Module not found, did you mean '{correct_path}'?",
                })
                fixes[import_path] = correct_path
            else:
                invalid.append({
                    "import": import_path,
                    "reason": "Module does not exist in the project",
                })

    return invalid, fixes


def _find_correct_python_import(
    invalid_path: str,
    valid_paths: set[str],
) -> str | None:
    """Find the correct Python import path for an invalid one.

    Args:
        invalid_path: Invalid import path like 'app.models.database'
        valid_paths: Set of valid import paths

    Returns:
        Correct path if found, None otherwise
    """
    # Strategy 1: Check if removing a segment makes it valid
    # app.models.database -> app.database
    parts = invalid_path.split(".")
    for i in range(1, len(parts)):
        for j in range(i + 1, len(parts) + 1):
            candidate = ".".join(parts[:i] + parts[j:])
            if candidate in valid_paths:
                return candidate

    # Strategy 2: Check if the last segment exists elsewhere
    # app.models.database -> app.database (if 'database' exists in app)
    target_name = parts[-1]
    for path in valid_paths:
        if path.endswith(f".{target_name}"):
            return path

    # Strategy 3: Fuzzy match on module name
    for path in valid_paths:
        path_parts = path.split(".")
        if path_parts[-1] == target_name:
            return path

    return None


def _find_correct_frontend_import(
    invalid_path: str,
    valid_paths: set[str],
) -> str | None:
    """Find the correct frontend import path for an invalid one.

    Args:
        invalid_path: Invalid import path like '@/api/users'
        valid_paths: Set of valid import paths

    Returns:
        Correct path if found, None otherwise
    """
    # Get the filename part
    parts = invalid_path.split("/")
    target_name = parts[-1]

    # Look for paths ending with the same filename
    for path in valid_paths:
        if path.endswith(f"/{target_name}"):
            return path

    return None


def fix_invalid_imports(
    code_content: str,
    validation_result: ImportValidationResult,
) -> str:
    """Fix invalid imports in code using suggested fixes.

    This function handles two cases:
    1. Replace invalid import paths with correct ones (when fix is available)
    2. Comment out imports that have no valid replacement

    Args:
        code_content: Original code content
        validation_result: Validation result with fixes

    Returns:
        Fixed code content
    """
    if validation_result.valid:
        return code_content

    fixed_content = code_content

    # First, apply path replacements
    for invalid_path, correct_path in validation_result.suggested_fixes.items():
        fixed_content = fixed_content.replace(invalid_path, correct_path)

    # Then, comment out imports that have no fix
    for invalid_import in validation_result.invalid_imports:
        import_path = invalid_import["import"]

        # Skip if already fixed
        if import_path in validation_result.suggested_fixes:
            continue

        # Comment out the invalid import line
        if import_path.startswith("app."):
            # Python import: comment out the line
            pattern = rf"^(from\s+{re.escape(import_path)}\s+import\s+.*)$"
            fixed_content = re.sub(
                pattern,
                r"# REMOVED: \1  # Module does not exist",
                fixed_content,
                flags=re.MULTILINE,
            )
        elif import_path.startswith("@/"):
            # Frontend import: comment out the line
            # Match: import xxx from '@/invalid/path'
            escaped_path = re.escape(import_path)
            pattern = rf"^(import\s+.+\s+from\s+['\"]){escaped_path}(['\"].*)$"
            fixed_content = re.sub(
                pattern,
                r"// REMOVED: \1\2  // Module does not exist",
                fixed_content,
                flags=re.MULTILINE,
            )

    return fixed_content


def read_related_modules(
    target_file: str,
    workspace_files: dict[str, str],
    registry: dict[str, list[dict[str, str]]],
    max_modules: int = 5,
    max_content_per_module: int = 2000,
) -> str:
    """Read related module contents before generating code (Claude Code style).

    This implements "Read Before Write" - understanding existing code before
    generating new code that depends on it.

    Args:
        target_file: File path being generated
        workspace_files: All workspace files
        registry: Module registry
        max_modules: Maximum number of related modules to read
        max_content_per_module: Maximum content length per module

    Returns:
        Formatted string with related module contents
    """
    related_modules: list[tuple[str, str]] = []

    is_python = target_file.endswith(".py")
    is_frontend = target_file.endswith((".ts", ".tsx", ".js", ".jsx", ".vue"))

    if is_python:
        # For Python backend files, read related app.* modules
        # Priority: database, models, schemas, routers
        priority_patterns = ["database", "models", "schemas", "routers", "auth", "deps"]

        for pattern in priority_patterns:
            if len(related_modules) >= max_modules:
                break

            for file_path, content in workspace_files.items():
                if len(related_modules) >= max_modules:
                    break

                if file_path.startswith("backend/") and pattern in file_path.lower():
                    if file_path.endswith(".py") and "__pycache__" not in file_path:
                        import_path = _file_path_to_python_import(file_path)
                        truncated = content[:max_content_per_module]
                        if len(content) > max_content_per_module:
                            truncated += "\n# ... (truncated)"
                        related_modules.append((import_path, truncated))

    elif is_frontend:
        # For frontend files, read related @/ modules
        # Priority: api, stores, types, composables
        priority_patterns = ["api/", "stores/", "types/", "composables/", "utils/"]

        for pattern in priority_patterns:
            if len(related_modules) >= max_modules:
                break

            for file_path, content in workspace_files.items():
                if len(related_modules) >= max_modules:
                    break

                if file_path.startswith("frontend/src/") and pattern in file_path:
                    alias_path = "@/" + file_path[13:]
                    truncated = content[:max_content_per_module]
                    if len(content) > max_content_per_module:
                        truncated += "\n// ... (truncated)"
                    related_modules.append((alias_path, truncated))

    if not related_modules:
        return ""

    lines = [
        "## 相关模块内容（Read Before Write）",
        "以下是项目中已存在的相关模块，请仔细阅读后再生成代码：\n",
    ]

    for module_path, content in related_modules:
        lines.append(f"### `{module_path}`")
        lines.append(f"```\n{content}\n```\n")

    return "\n".join(lines)


__all__ = [
    "scan_workspace_files",
    "get_file_tree",
    "extract_python_exports",
    "extract_typescript_exports",
    "extract_vue_exports",
    "build_module_registry",
    "format_module_registry_for_prompt",
    "get_interface_constraint_prompt",
    "validate_imports",
    "validate_imports_strict",
    "fix_invalid_imports",
    "read_related_modules",
    "register_generated_files",
    "build_code_context",
    "ImportValidationResult",
]
