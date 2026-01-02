# -*- coding: utf-8 -*-
"""File editing tools inspired by Claude Code's Edit mechanism.

This module provides:
- Precise string replacement (old_string -> new_string)
- File reading with caching
- Edit validation (uniqueness check)
- Incremental file modification

Key principles (from Claude Code):
1. MUST read file before editing
2. old_string must be unique in file
3. Preserve existing code, only modify what's needed
4. No full file rewrites - use precise edits
"""
from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.ones.code_guard import CodeGuardManager


# ---------------------------------------------------------------------------
# File State Manager
# ---------------------------------------------------------------------------
class FileStateManager:
    """Manages file state across multiple requirements.

    Tracks which files have been read, modified, and by which requirement.
    Prevents accidental overwrites and enables incremental editing.
    """

    def __init__(self, workspace_dir: Path):
        """Initialize file state manager.

        Args:
            workspace_dir: Root directory for all files
        """
        self.workspace_dir = Path(workspace_dir)
        self._file_cache: dict[str, str] = {}  # path -> content
        self._file_hashes: dict[str, str] = {}  # path -> hash
        self._read_by: dict[str, set[str]] = {}  # path -> set of req_ids
        self._modified_by: dict[str, list[str]] = {}  # path -> list of req_ids (ordered)
        self._locked_files: set[str] = set()  # files locked after passing QA

    def read_file(self, file_path: str, req_id: str | None = None) -> str | None:
        """Read file content and cache it.

        Args:
            file_path: Relative path to file
            req_id: Requirement ID requesting the read

        Returns:
            str: File content, or None if file doesn't exist
        """
        full_path = self.workspace_dir / file_path

        # Return cached content if available and file unchanged
        if file_path in self._file_cache:
            if full_path.exists():
                current_hash = self._compute_hash(full_path.read_text(encoding="utf-8"))
                if current_hash == self._file_hashes.get(file_path):
                    if req_id:
                        self._read_by.setdefault(file_path, set()).add(req_id)
                    return self._file_cache[file_path]

        # Read from disk
        if not full_path.exists():
            return None

        content = full_path.read_text(encoding="utf-8")
        self._file_cache[file_path] = content
        self._file_hashes[file_path] = self._compute_hash(content)

        if req_id:
            self._read_by.setdefault(file_path, set()).add(req_id)

        return content

    def write_file(self, file_path: str, content: str, req_id: str | None = None) -> bool:
        """Write file content and update cache.

        Args:
            file_path: Relative path to file
            content: New file content
            req_id: Requirement ID making the write

        Returns:
            bool: True if write succeeded
        """
        if file_path in self._locked_files:
            from ._observability import get_logger
            get_logger().warn(f"[FileEditor] 文件已锁定，跳过写入: {file_path}")
            return False

        full_path = self.workspace_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

        # Update cache
        self._file_cache[file_path] = content
        self._file_hashes[file_path] = self._compute_hash(content)

        if req_id:
            self._modified_by.setdefault(file_path, []).append(req_id)

        return True

    def lock_file(self, file_path: str) -> None:
        """Lock a file to prevent further modifications.

        Args:
            file_path: Relative path to file
        """
        self._locked_files.add(file_path)

    def unlock_file(self, file_path: str) -> None:
        """Unlock a file to allow modifications.

        Args:
            file_path: Relative path to file
        """
        self._locked_files.discard(file_path)

    def is_locked(self, file_path: str) -> bool:
        """Check if file is locked.

        Args:
            file_path: Relative path to file

        Returns:
            bool: True if locked
        """
        return file_path in self._locked_files

    def refresh_file(self, file_path: str, req_id: str | None = None) -> str | None:
        """Force refresh file content from disk, bypassing cache.

        CRITICAL: Always call this before generating edits to avoid
        using stale content that may have been modified by other requirements.

        Args:
            file_path: Relative path to file
            req_id: Requirement ID requesting the refresh

        Returns:
            str: Fresh file content, or None if file doesn't exist
        """
        full_path = self.workspace_dir / file_path

        if not full_path.exists():
            # File doesn't exist - remove from cache if present
            self._file_cache.pop(file_path, None)
            self._file_hashes.pop(file_path, None)
            return None

        # Always read from disk, update cache
        content = full_path.read_text(encoding="utf-8")
        self._file_cache[file_path] = content
        self._file_hashes[file_path] = self._compute_hash(content)

        if req_id:
            self._read_by.setdefault(file_path, set()).add(req_id)

        return content

    def get_file_history(self, file_path: str) -> dict[str, Any]:
        """Get modification history for a file.

        Args:
            file_path: Relative path to file

        Returns:
            dict: History info with read_by and modified_by
        """
        return {
            "read_by": list(self._read_by.get(file_path, [])),
            "modified_by": self._modified_by.get(file_path, []),
            "is_locked": file_path in self._locked_files,
        }

    def list_directory(self, dir_path: str = "") -> list[str]:
        """List files in a directory (like tree command).

        Args:
            dir_path: Relative directory path (empty for root)

        Returns:
            list: List of file paths relative to workspace
        """
        target = self.workspace_dir / dir_path if dir_path else self.workspace_dir
        if not target.exists():
            return []

        files = []
        for p in sorted(target.rglob("*")):
            if p.is_file() and not any(part.startswith(".") for part in p.parts):
                files.append(str(p.relative_to(self.workspace_dir)))

        return files

    def tree(self, dir_path: str = "", max_depth: int = 3) -> str:
        """Generate tree-like directory listing.

        Args:
            dir_path: Relative directory path
            max_depth: Maximum depth to traverse

        Returns:
            str: Tree-formatted string
        """
        target = self.workspace_dir / dir_path if dir_path else self.workspace_dir
        if not target.exists():
            return f"(directory not found: {dir_path})"

        lines = [str(target.name) + "/"]
        self._tree_recursive(target, "", lines, max_depth, 0)
        return "\n".join(lines)

    def _tree_recursive(
        self,
        path: Path,
        prefix: str,
        lines: list[str],
        max_depth: int,
        current_depth: int
    ) -> None:
        """Recursive helper for tree generation."""
        if current_depth >= max_depth:
            return

        entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        entries = [e for e in entries if not e.name.startswith(".")]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "

            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._tree_recursive(entry, new_prefix, lines, max_depth, current_depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute hash of content for change detection."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get_available_modules(self, tech_stack: str = "") -> dict[str, list[str]]:
        """Extract available modules from project structure.

        Analyzes the workspace to find importable modules based on tech stack.

        Args:
            tech_stack: Technology stack hint (e.g., "python", "fastapi", "react")

        Returns:
            dict: Categorized modules {"python": [...], "javascript": [...]}
        """
        modules: dict[str, list[str]] = {"python": [], "javascript": []}
        tech_lower = tech_stack.lower() if tech_stack else ""

        # Detect project type from files
        is_python = (self.workspace_dir / "requirements.txt").exists() or \
                   (self.workspace_dir / "pyproject.toml").exists() or \
                   "python" in tech_lower or "fastapi" in tech_lower or "django" in tech_lower

        is_js = (self.workspace_dir / "package.json").exists() or \
               "react" in tech_lower or "vue" in tech_lower or "vite" in tech_lower

        if is_python:
            modules["python"] = self._scan_python_modules()

        if is_js:
            modules["javascript"] = self._scan_js_modules()

        return modules

    def _scan_python_modules(self) -> list[str]:
        """Scan for available Python modules in the workspace.

        Returns:
            list: Available Python import paths (e.g., ["app.models", "app.routers.users"])
        """
        python_modules = []
        # Common Python source directories
        src_dirs = ["app", "src", "backend/app", "backend/src", "."]

        for src_dir in src_dirs:
            src_path = self.workspace_dir / src_dir
            if not src_path.exists():
                continue

            for py_file in src_path.rglob("*.py"):
                # Skip __pycache__, venv, etc.
                if any(p.startswith((".", "__pycache__", "venv", "env", ".venv"))
                       for p in py_file.parts):
                    continue

                # Convert file path to module path
                try:
                    rel_path = py_file.relative_to(src_path)
                    # Remove .py extension
                    module_path = str(rel_path)[:-3].replace("/", ".").replace("\\", ".")
                    # Handle __init__.py
                    if module_path.endswith(".__init__"):
                        module_path = module_path[:-9]
                    elif module_path == "__init__":
                        continue

                    if src_dir not in [".", "src"]:
                        # Prepend directory name for subdirectories
                        base = src_dir.split("/")[-1]  # e.g., "app" from "backend/app"
                        if not module_path.startswith(base):
                            module_path = f"{base}.{module_path}" if module_path else base
                    elif src_dir == ".":
                        # Skip if it's just a standalone script
                        if "/" not in str(rel_path) and "\\" not in str(rel_path):
                            continue

                    if module_path and module_path not in python_modules:
                        python_modules.append(module_path)
                except ValueError:
                    continue

        return sorted(python_modules)

    def _scan_js_modules(self) -> list[str]:
        """Scan for available JavaScript/TypeScript modules in the workspace.

        Returns:
            list: Available JS/TS import paths (e.g., ["@/api/users", "@/utils/request"])
        """
        js_modules = []
        # Common frontend source directories
        src_dirs = ["src", "frontend/src", "client/src"]

        for src_dir in src_dirs:
            src_path = self.workspace_dir / src_dir
            if not src_path.exists():
                continue

            for ext in ["*.ts", "*.tsx", "*.js", "*.jsx", "*.vue"]:
                for file in src_path.rglob(ext):
                    # Skip node_modules, dist, etc.
                    if any(p.startswith((".", "node_modules", "dist", "build"))
                           for p in file.parts):
                        continue

                    try:
                        rel_path = file.relative_to(src_path)
                        # Remove extension
                        module_path = str(rel_path)
                        for suffix in [".tsx", ".ts", ".jsx", ".js", ".vue"]:
                            if module_path.endswith(suffix):
                                module_path = module_path[:-len(suffix)]
                                break

                        # Convert to @ alias format (common convention)
                        module_path = "@/" + module_path.replace("\\", "/")

                        # Skip index files (they can be imported by directory)
                        if module_path.endswith("/index"):
                            module_path = module_path[:-6]

                        if module_path and module_path not in js_modules:
                            js_modules.append(module_path)
                    except ValueError:
                        continue

        return sorted(js_modules)


def format_available_modules(modules: dict[str, list[str]]) -> str:
    """Format available modules for inclusion in LLM prompt.

    Args:
        modules: Dict of categorized modules from get_available_modules()

    Returns:
        str: Formatted module list for prompt
    """
    sections = []

    if modules.get("python"):
        py_mods = modules["python"]
        sections.append("【Python 可用模块】\n" + "\n".join(f"  - {m}" for m in py_mods[:50]))
        if len(py_mods) > 50:
            sections[-1] += f"\n  ... 共 {len(py_mods)} 个模块"

    if modules.get("javascript"):
        js_mods = modules["javascript"]
        sections.append("【JavaScript/TypeScript 可用模块】\n" + "\n".join(f"  - {m}" for m in js_mods[:50]))
        if len(js_mods) > 50:
            sections[-1] += f"\n  ... 共 {len(js_mods)} 个模块"

    return "\n\n".join(sections) if sections else ""


# ---------------------------------------------------------------------------
# Edit Operations
# ---------------------------------------------------------------------------
class EditOperation:
    """Represents a single edit operation."""

    def __init__(self, old_string: str, new_string: str, replace_all: bool = False):
        """Initialize edit operation.

        Args:
            old_string: Text to find and replace
            new_string: Replacement text
            replace_all: If True, replace all occurrences
        """
        self.old_string = old_string
        self.new_string = new_string
        self.replace_all = replace_all

    def validate(self, content: str) -> tuple[bool, str]:
        """Validate that edit can be applied.

        Args:
            content: File content to check against

        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.old_string:
            return False, "old_string cannot be empty"

        count = content.count(self.old_string)

        if count == 0:
            return False, f"old_string not found in file"

        if count > 1 and not self.replace_all:
            return False, f"old_string appears {count} times (must be unique or use replace_all)"

        return True, ""

    def apply(self, content: str) -> str:
        """Apply edit to content.

        Args:
            content: Original file content

        Returns:
            str: Modified content
        """
        if self.replace_all:
            return content.replace(self.old_string, self.new_string)
        else:
            return content.replace(self.old_string, self.new_string, 1)


def apply_edits(content: str, edits: list[EditOperation]) -> tuple[str, list[str]]:
    """Apply multiple edits to content.

    Args:
        content: Original file content
        edits: List of edit operations

    Returns:
        tuple: (modified_content, list_of_errors)
    """
    errors = []
    result = content

    for i, edit in enumerate(edits):
        is_valid, error = edit.validate(result)
        if not is_valid:
            errors.append(f"Edit {i + 1}: {error}")
            continue

        result = edit.apply(result)

    return result, errors


# ---------------------------------------------------------------------------
# LLM-Driven Edit Generation
# ---------------------------------------------------------------------------
async def generate_file_edits(
    llm: Any,
    file_path: str,
    existing_content: str,
    requirement: dict[str, Any],
    criteria: list[dict[str, Any]] | None = None,
    failed_criteria: list[dict[str, Any]] | None = None,
    file_manager: "FileStateManager | None" = None,
    blueprint: dict[str, Any] | None = None,
    *,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Generate edit operations for a file using LLM.

    Instead of generating entire file, generate precise edits.

    Args:
        llm: LLM model instance
        file_path: Path to file being edited
        existing_content: Current file content
        requirement: Requirement dict
        criteria: Acceptance criteria to implement
        failed_criteria: Previously failed criteria to fix
        file_manager: File state manager for scanning available modules
        blueprint: Blueprint dict with tech stack info
        verbose: Whether to print debug info

    Returns:
        list: List of edit dicts with 'old', 'new', 'replace_all' keys
    """
    from ._llm_utils import call_llm_json

    # Build criteria context
    criteria_text = ""
    if criteria:
        criteria_text = "\n【需要实现的验收标准】\n"
        for c in criteria:
            criteria_text += f"- {c.get('id', '')}: {c.get('title', c.get('name', ''))}\n"

    if failed_criteria:
        criteria_text += "\n【上轮失败的标准 - 必须修复】\n"
        for c in failed_criteria:
            crit_id = c.get('id', '')
            crit_title = c.get('title', c.get('name', ''))
            # Use enhanced QA failure reason if available
            failure_reason = c.get('qa_failure_reason') or c.get('reason', '未知原因')
            recommendation = c.get('recommendation', '')
            criteria_text += f"- {crit_id}: {crit_title}\n"
            criteria_text += f"  ⚠️ 失败原因: {failure_reason}\n"
            if recommendation:
                criteria_text += f"  💡 修复建议: {recommendation}\n"

    # Build available modules text (CRITICAL: prevents importing non-existent modules)
    modules_text = ""
    if file_manager:
        tech_stack = blueprint.get('recommended_stack', '') if blueprint else ''
        available_modules = file_manager.get_available_modules(tech_stack)
        modules_text = format_available_modules(available_modules)

    prompt = textwrap.dedent(f"""
        【任务】编辑文件: {file_path}

        【当前文件内容】
        ```
        {existing_content[:8000]}
        ```

        【需求】
        {requirement.get('title', '')}: {requirement.get('summary', requirement.get('description', ''))}
        {criteria_text}
        {modules_text}

        【输出格式】
        返回 JSON 格式的编辑指令列表:
        ```json
        {{
            "edits": [
                {{
                    "old": "要替换的原文本（必须在文件中能找到）",
                    "new": "替换后的新文本",
                    "replace_all": false,
                    "reason": "为什么要做这个修改"
                }}
            ],
            "summary": "本次编辑的总结"
        }}
        ```

        【关键规则 - 必须遵守】
        1. old 字段必须是文件中**实际存在**的文本，完全匹配
        2. old 字段应该足够长以确保**唯一性**（至少包含一整行）
        3. 只修改需要改的部分，**保留其他功能代码**
        4. 如果需要添加新代码，找到合适的位置（如函数末尾、import 区域）
        5. 不要删除其他需求已实现的功能
        6. 如果文件是空的或需要创建新内容，使用 old: "" 和 new: "完整内容"

        【模块导入约束 - 严格遵守】
        - 只能导入上述"可用模块"列表中存在的本地模块
        - 禁止导入不存在的模块（如 app.api、app.core 等假设的模块）
        - 第三方库导入不受此限制（如 fastapi、sqlalchemy 等）
        - 如果需要的模块不存在，在文件中定义所需功能或添加 TODO 注释

        【接口调用约束 - 禁止猜测】
        - 只能调用在"当前文件内容"或"相关文件"中明确定义的函数/类/方法
        - 如果需要调用未定义的接口，必须添加 TODO 注释说明需要什么接口
        - 示例: // TODO: 需要 @/api/users 提供 getUserById(id): Promise<User>

        【正确示例】
        old: "def get_member(db, member_id):\\n    pass  # TODO"
        new: "def get_member(db, member_id):\\n    return db.query(Member).filter(Member.id == member_id).first()"

        【错误示例】
        old: "pass" (太短，可能匹配多处)
        old: "# TODO" (太短，不唯一)
    """)

    result, _ = await call_llm_json(
        llm,
        [
            {"role": "system", "content": "你是代码编辑专家，生成精确的文件编辑指令。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        label=f"edit_file:{file_path}",
        verbose=verbose,
    )

    return result.get("edits", [])


async def generate_new_file(
    llm: Any,
    file_path: str,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    criteria: list[dict[str, Any]] | None = None,
    context_files: dict[str, str] | None = None,
    file_manager: "FileStateManager | None" = None,
    *,
    verbose: bool = False,
) -> str:
    """Generate a new file from scratch.

    Only used when file doesn't exist yet.

    Args:
        llm: LLM model instance
        file_path: Path to new file
        requirement: Requirement dict
        blueprint: Blueprint dict with file description
        criteria: Acceptance criteria to implement
        context_files: Related files for context
        file_manager: File state manager for scanning available modules
        verbose: Whether to print debug info

    Returns:
        str: New file content
    """
    from ._llm_utils import call_llm_json

    # Get file description from blueprint
    file_desc = ""
    for fp in blueprint.get("files_plan", []):
        if fp.get("path") == file_path:
            file_desc = fp.get("description", "")
            break

    # Build context from related files
    context_text = ""
    if context_files:
        context_text = "\n【相关文件内容（供参考）】\n"
        for path, content in list(context_files.items())[:5]:
            context_text += f"\n--- {path} ---\n{content[:2000]}\n"

    # Build criteria text
    criteria_text = ""
    if criteria:
        criteria_text = "\n【此文件需实现的验收标准】\n"
        for c in criteria:
            criteria_text += f"- {c.get('id', '')}: {c.get('title', c.get('name', ''))}\n"
            if c.get('description'):
                criteria_text += f"  要求: {c.get('description')}\n"

    # Build available modules text (CRITICAL: prevents importing non-existent modules)
    modules_text = ""
    if file_manager:
        tech_stack = blueprint.get('recommended_stack', '')
        available_modules = file_manager.get_available_modules(tech_stack)
        modules_text = format_available_modules(available_modules)

    prompt = textwrap.dedent(f"""
        【任务】创建新文件: {file_path}

        【文件描述】
        {file_desc}

        【需求】
        {requirement.get('title', '')}: {requirement.get('summary', requirement.get('description', ''))}

        【技术栈】
        {blueprint.get('recommended_stack', '')}
        {context_text}
        {criteria_text}
        {modules_text}

        【输出格式】
        返回 JSON:
        ```json
        {{
            "content": "完整的文件内容",
            "summary": "文件功能说明"
        }}
        ```

        【要求】
        1. 生成完整、可运行的代码
        2. 遵循项目已有的代码风格
        3. 实现所有指定的验收标准

        【模块导入约束 - 严格遵守】
        - 只能导入上述"可用模块"列表中存在的本地模块
        - 禁止导入不存在的模块（如 app.api、app.core 等假设的模块）
        - 第三方库导入不受此限制（如 fastapi、sqlalchemy 等）
        - 如果需要的模块不存在，在文件中定义所需功能或添加 TODO 注释

        【接口调用约束 - 禁止猜测】
        - 只能调用在"相关文件内容"中明确定义的函数/类/方法
        - 如果需要调用的接口不在上下文中，必须添加 TODO 注释说明需要什么接口
        - TODO 格式: // TODO: 需要 [模块路径] 提供 [接口签名]
        - 禁止假设接口的参数类型、返回值类型、同步/异步行为
    """)

    result, _ = await call_llm_json(
        llm,
        [
            {"role": "system", "content": "你是代码生成专家，生成高质量的代码文件。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
        label=f"new_file:{file_path}",
        verbose=verbose,
    )

    return result.get("content", "")


# ---------------------------------------------------------------------------
# High-Level Edit Flow
# ---------------------------------------------------------------------------
async def edit_or_create_file(
    llm: Any,
    file_path: str,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    file_manager: FileStateManager,
    criteria: list[dict[str, Any]] | None = None,
    failed_criteria: list[dict[str, Any]] | None = None,
    *,
    code_guard: "CodeGuardManager | None" = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Edit existing file or create new one.

    Main entry point for file modifications. Follows Claude Code pattern:
    1. Read file first (or determine it's new)
    2. Generate edits (or full content for new files)
    3. Apply and validate edits
    4. Write result

    Args:
        llm: LLM model instance
        file_path: Path to file
        requirement: Requirement dict
        blueprint: Blueprint dict
        file_manager: FileStateManager instance
        criteria: Acceptance criteria to implement
        failed_criteria: Previously failed criteria
        code_guard: CodeGuardManager instance for anti-hallucination validation
        verbose: Whether to print debug info

    Returns:
        dict: Result with 'path', 'content', 'action', 'edits_applied', 'errors'
    """
    from ._observability import get_logger
    logger = get_logger()

    req_id = requirement.get("id", "unknown")
    result = {
        "path": file_path,
        "content": "",
        "action": "create",
        "edits_applied": 0,
        "errors": [],
        "summary": "",
        "code_guard_warnings": "",  # CodeGuard validation warnings
    }

    # Check if file is locked
    if file_manager.is_locked(file_path):
        result["errors"].append(f"文件已锁定: {file_path}")
        result["content"] = file_manager.read_file(file_path, req_id) or ""
        return result

    # Step 1: Read existing file (ALWAYS refresh from disk before edit)
    # This is CRITICAL to avoid edit conflicts when files are modified by other requirements
    existing_content = file_manager.refresh_file(file_path, req_id)

    # CodeGuard: Record the file read
    if code_guard and existing_content is not None:
        code_guard.record_file_read(file_path, existing_content)

    if existing_content is None:
        # New file - generate from scratch
        result["action"] = "create"
        if verbose:
            logger.debug(f"[FileEditor] 创建新文件: {file_path}")

        # Get context from related files
        context_files = {}
        for fp in blueprint.get("files_plan", []):
            dep_path = fp.get("path", "")
            if dep_path != file_path:
                dep_content = file_manager.read_file(dep_path, req_id)
                if dep_content:
                    context_files[dep_path] = dep_content

        content = await generate_new_file(
            llm=llm,
            file_path=file_path,
            requirement=requirement,
            blueprint=blueprint,
            criteria=criteria,
            context_files=context_files if context_files else None,
            file_manager=file_manager,
            verbose=verbose,
        )

        result["content"] = content
        result["summary"] = f"创建新文件 {file_path}"

    else:
        # Existing file - generate edits
        result["action"] = "edit"
        if verbose:
            logger.debug(f"[FileEditor] 编辑现有文件: {file_path} ({len(existing_content)} 字符)")

        edits_data = await generate_file_edits(
            llm=llm,
            file_path=file_path,
            existing_content=existing_content,
            requirement=requirement,
            criteria=criteria,
            failed_criteria=failed_criteria,
            file_manager=file_manager,
            blueprint=blueprint,
            verbose=verbose,
        )

        # Convert to EditOperation objects
        edits = []
        for ed in edits_data:
            edits.append(EditOperation(
                old_string=ed.get("old", ""),
                new_string=ed.get("new", ""),
                replace_all=ed.get("replace_all", False),
            ))

        # Apply edits
        modified_content, errors = apply_edits(existing_content, edits)

        result["content"] = modified_content
        result["edits_applied"] = len(edits) - len(errors)
        result["errors"].extend(errors)
        result["summary"] = f"应用 {result['edits_applied']}/{len(edits)} 个编辑"

        if errors and verbose:
            for err in errors:
                logger.warn(f"[FileEditor] 编辑失败: {err}")

    # Step 2.5: CodeGuard validation (after content is generated, before writing)
    if code_guard and result["content"]:
        is_new_file = existing_content is None
        validation = code_guard.validate_content(
            file_path,
            result["content"],
            is_new_file=is_new_file,
        )

        # Format warnings
        warnings_text = code_guard.format_warnings(validation)
        if warnings_text:
            result["code_guard_warnings"] = warnings_text
            if verbose:
                logger.warn(f"[FileEditor] CodeGuard 检测到问题:\n{warnings_text}")

        # Check if write should be blocked
        if code_guard.should_block_write(validation):
            result["errors"].append("CodeGuard blocked write: file was not read first")
            if verbose:
                logger.error(f"[FileEditor] CodeGuard 阻止写入: {file_path}")
            return result

    # Step 3: Write result
    if result["content"]:
        success = file_manager.write_file(file_path, result["content"], req_id)
        if not success:
            result["errors"].append(f"写入失败: {file_path}")
        else:
            # CodeGuard: Update registries after successful write
            if code_guard:
                code_guard.update_after_write(file_path, result["content"])

    return result


# ---------------------------------------------------------------------------
# Integration Helper
# ---------------------------------------------------------------------------
async def stepwise_edit_files(
    llm: Any,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    file_manager: FileStateManager,
    all_criteria: list[dict[str, Any]] | None = None,
    failed_criteria: list[dict[str, Any]] | None = None,
    *,
    code_guard: "CodeGuardManager | None" = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Edit files step by step, reading before each edit.

    Replacement for stepwise_generate_files that uses edit mode.

    Args:
        llm: LLM model instance
        requirement: Requirement dict
        blueprint: Blueprint dict
        file_manager: FileStateManager instance
        all_criteria: All acceptance criteria for requirement
        failed_criteria: Failed criteria from previous round
        code_guard: CodeGuardManager instance for anti-hallucination validation
        verbose: Whether to print debug info

    Returns:
        dict: Implementation result with files list
    """
    from ._observability import get_logger
    logger = get_logger()

    files_plan = blueprint.get("files_plan", [])
    if not files_plan:
        raise ValueError("Blueprint 缺少 files_plan 字段")

    req_id = requirement.get("id", "")

    # Log directory structure first (like tree command)
    if verbose:
        tree_output = file_manager.tree(max_depth=3)
        logger.debug(f"[FileEditor] 当前目录结构:\n{tree_output}")

    # Build criteria lookup
    criteria_by_id: dict[str, dict[str, Any]] = {}
    if all_criteria:
        for c in all_criteria:
            cid = c.get("id", "")
            if cid:
                criteria_by_id[cid] = c

    results = []
    summaries = []

    for i, file_plan in enumerate(files_plan):
        file_path = file_plan["path"]

        # Get criteria for this file
        file_criteria_ids = file_plan.get("criteria_ids", [])
        file_criteria = [criteria_by_id[cid] for cid in file_criteria_ids if cid in criteria_by_id]

        # Use failed_criteria if no specific criteria
        if not file_criteria and failed_criteria:
            file_criteria = failed_criteria

        logger.info(f"[FileEditor] ({i + 1}/{len(files_plan)}) 处理: {file_path}")

        result = await edit_or_create_file(
            llm=llm,
            file_path=file_path,
            requirement=requirement,
            blueprint=blueprint,
            file_manager=file_manager,
            criteria=file_criteria if file_criteria else None,
            failed_criteria=failed_criteria,
            code_guard=code_guard,
            verbose=verbose,
        )

        results.append(result)
        action_text = "创建" if result["action"] == "create" else f"编辑({result['edits_applied']}处)"
        summaries.append(f"- {file_path}: {action_text} - {result.get('summary', '')[:80]}")

        if result["errors"]:
            for err in result["errors"]:
                logger.warn(f"[FileEditor] {file_path}: {err}")

    # Collect all files
    all_files = []
    code_guard_warnings_list = []
    for r in results:
        if r["content"]:
            all_files.append({"path": r["path"], "content": r["content"]})
        # Collect CodeGuard warnings
        if r.get("code_guard_warnings"):
            code_guard_warnings_list.append(f"[{r['path']}]\n{r['code_guard_warnings']}")

    result_dict = {
        "summary": f"[{req_id}] 处理了 {len(all_files)} 个文件:\n" + "\n".join(summaries),
        "project_type": blueprint.get("artifact_type", "fullstack"),
        "files": all_files,
        "edit_results": results,
        "setup_commands": [],
        "run_command": "",
        "entry_point": "",
    }

    # Add CodeGuard warnings summary if any
    if code_guard_warnings_list:
        result_dict["code_guard_warnings"] = "\n\n".join(code_guard_warnings_list)

    return result_dict


__all__ = [
    "FileStateManager",
    "EditOperation",
    "apply_edits",
    "generate_file_edits",
    "generate_new_file",
    "edit_or_create_file",
    "stepwise_edit_files",
]
