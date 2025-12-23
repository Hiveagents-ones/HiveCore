# -*- coding: utf-8 -*-
"""Agent role implementations for requirement design and implementation.

This module provides:
- Blueprint design (design_requirement)
- Requirement implementation (implement_requirement)
- File generation utilities
- Edit operations
- Scaffold execution
"""
from __future__ import annotations

import ast
import json
import re
import textwrap
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ._sandbox import RuntimeWorkspace


# ---------------------------------------------------------------------------
# Text Utilities
# ---------------------------------------------------------------------------
def extract_file_structure(content: str, file_path: str) -> str:
    """Extract structure information from a file.

    Args:
        content: File content
        file_path: File path

    Returns:
        str: Structure description
    """
    lines = content.split("\n")
    structure_lines: list[str] = []

    ext = file_path.split(".")[-1].lower() if "." in file_path else ""

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Python
        if ext == "py":
            if stripped.startswith(("class ", "def ", "async def ")):
                structure_lines.append(f"L{i + 1}: {stripped[:80]}")
        # JavaScript/TypeScript/Vue
        elif ext in ("js", "ts", "jsx", "tsx", "vue"):
            if any(stripped.startswith(kw) for kw in ["function ", "class ", "const ", "export ", "async function "]):
                if "=" in stripped and "function" not in stripped and "class" not in stripped:
                    if any(k in stripped for k in ["Component", "Router", "Store"]):
                        structure_lines.append(f"L{i + 1}: {stripped[:80]}")
                else:
                    structure_lines.append(f"L{i + 1}: {stripped[:80]}")
            elif any(tag in stripped for tag in ["<script", "<template", "<style"]):
                structure_lines.append(f"L{i + 1}: {stripped[:80]}")
        # Other
        else:
            if stripped.startswith(("class ", "def ", "function ")):
                structure_lines.append(f"L{i + 1}: {stripped[:80]}")

    if structure_lines:
        return "文件结构:\n" + "\n".join(structure_lines[:30])
    return ""


def find_similar_text(content: str, target: str, context_lines: int = 3) -> str:
    """Find similar text in content and return context.

    Args:
        content: File content
        target: Target text to find
        context_lines: Number of context lines

    Returns:
        str: Context information
    """
    if not target or len(target) < 10:
        return ""

    lines = content.split("\n")

    # Extract keywords
    keywords = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b", target)
    keyword_counts: dict[str, int] = {}
    for kw in keywords:
        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

    # Find unique keywords
    unique_keywords = sorted(keyword_counts.keys(), key=lambda k: keyword_counts[k])[:5]

    # Search for lines with keywords
    matches: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        score = sum(1 for kw in unique_keywords if kw in line)
        if score >= 2:
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            context = "\n".join(f"L{j + 1}: {lines[j]}" for j in range(start, end))
            matches.append((score, i + 1, context))

    if matches:
        matches.sort(key=lambda x: -x[0])
        best = matches[0]
        return f"可能匹配位置 (L{best[1]}, 相似度={best[0]}):\n{best[2]}"

    return ""


def validate_python_syntax(content: str) -> tuple[bool, str]:
    """Validate Python code syntax.

    Args:
        content: Python code

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        msg = f"语法错误 (行 {e.lineno}): {e.msg}"
        if e.text:
            msg += f" | 代码: {e.text.strip()[:50]}"
        return False, msg
    except Exception as e:
        return False, f"解析错误: {str(e)}"


# ---------------------------------------------------------------------------
# Edit Operations
# ---------------------------------------------------------------------------
def apply_edits(
    existing_content: str,
    edits: list[dict[str, Any]],
    verbose: bool = False,
) -> tuple[str, bool, list[dict[str, Any]]]:
    """Apply edit operations to file content.

    Args:
        existing_content: Original content
        edits: List of edit operations
        verbose: Whether to print debug info

    Returns:
        tuple: (modified_content, all_success, failed_edits)
    """
    content = existing_content
    all_success = True
    failed_edits: list[dict[str, Any]] = []

    for i, edit in enumerate(edits):
        edit_type = edit.get("type", "")
        success = False
        failure_reason = ""

        try:
            if edit_type == "replace":
                old_text = edit.get("old", "")
                new_text = edit.get("new", "")
                if old_text and old_text in content:
                    content = content.replace(old_text, new_text, 1)
                    success = True
                else:
                    failure_reason = f"未找到目标文本: '{old_text[:100]}...'" if len(old_text) > 100 else f"未找到目标文本: '{old_text}'"

            elif edit_type == "insert_after":
                anchor = edit.get("anchor", "")
                new_content = edit.get("content", "")
                if anchor and anchor in content:
                    lines = content.split("\n")
                    for j, line in enumerate(lines):
                        if anchor in line:
                            lines.insert(j + 1, new_content)
                            content = "\n".join(lines)
                            success = True
                            break
                else:
                    failure_reason = f"未找到锚点: '{anchor[:100]}...'" if len(anchor) > 100 else f"未找到锚点: '{anchor}'"

            elif edit_type == "insert_before":
                anchor = edit.get("anchor", "")
                new_content = edit.get("content", "")
                if anchor and anchor in content:
                    lines = content.split("\n")
                    for j, line in enumerate(lines):
                        if anchor in line:
                            lines.insert(j, new_content)
                            content = "\n".join(lines)
                            success = True
                            break
                else:
                    failure_reason = f"未找到锚点: '{anchor[:100]}...'" if len(anchor) > 100 else f"未找到锚点: '{anchor}'"

            elif edit_type == "delete":
                target = edit.get("target", "")
                if target and target in content:
                    content = content.replace(target, "", 1)
                    success = True
                else:
                    failure_reason = f"未找到目标文本"

            elif edit_type == "append":
                new_content = edit.get("content", "")
                if new_content:
                    if not content.endswith("\n"):
                        content += "\n"
                    content += new_content
                    success = True

            elif edit_type == "prepend":
                new_content = edit.get("content", "")
                if new_content:
                    content = new_content + ("\n" if not new_content.endswith("\n") else "") + content
                    success = True

            else:
                failure_reason = f"未知编辑类型: {edit_type}"

        except Exception as e:
            failure_reason = f"执行出错: {e}"

        if success:
            if verbose:
                from ._observability import get_logger
                get_logger().debug(f"[EDIT] #{i + 1} {edit_type}: 成功")
        else:
            all_success = False
            failed_edits.append({
                "index": i + 1,
                "edit": edit,
                "reason": failure_reason,
            })
            if verbose:
                from ._observability import get_logger
                get_logger().debug(f"[EDIT] #{i + 1} {edit_type}: {failure_reason}")

    return content, all_success, failed_edits


# ---------------------------------------------------------------------------
# Blueprint Design
# ---------------------------------------------------------------------------
async def design_requirement(
    llm: Any,
    requirement: dict[str, Any],
    feedback: str,
    passed_ids: set[str],
    failed_criteria: list[dict[str, Any]],
    prev_blueprint: dict[str, Any] | None,
    contextual_notes: str | None = None,
    existing_workspace_files: list[str] | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Design blueprint for a requirement.

    Args:
        llm: LLM model instance
        requirement: Requirement dict
        feedback: Previous QA feedback
        passed_ids: Set of passed criteria IDs
        failed_criteria: List of failed criteria
        prev_blueprint: Previous blueprint (if any)
        contextual_notes: Context notes
        existing_workspace_files: List of existing files in workspace
        verbose: Whether to print debug info

    Returns:
        dict: Blueprint JSON
    """
    from ._llm_utils import call_llm_json

    prompt = textwrap.dedent(f"""
        需求对象:
        {json.dumps(requirement, ensure_ascii=False, indent=2)}

        已通过的标准:
        {sorted(passed_ids) if passed_ids else "无"}

        仍需改进的标准:
        {json.dumps(failed_criteria, ensure_ascii=False, indent=2) if failed_criteria else "无"}

        上一版 Blueprint (如有):
        {json.dumps(prev_blueprint, ensure_ascii=False, indent=2) if prev_blueprint else "无"}

        之前 QA 的反馈 (如有):
        {feedback or "无"}

        请输出 Blueprint（JSON），字段包括:
        {{
          "requirement_id": "{requirement.get('id', '')}",
          "artifact_type": "web|api|script|document",
          "deliverable_pitch": "...",
          "recommended_stack": "...",
          "generation_mode": "single|stepwise|scaffold",
          "scaffold": {{
            "frontend": {{
              "init_command": "npm create vite@latest frontend --template vue",
              "install_template": "cd frontend && npm install {{packages}}",
              "packages": ["element-plus", "axios", "vue-router"]
            }},
            "backend": {{
              "init_command": null,
              "install_template": "pip install {{packages}}",
              "packages": ["fastapi", "sqlalchemy", "passlib[bcrypt]"]
            }}
          }},
          "files_plan": [
            {{"path": "...", "description": "...", "action": "create|modify", "priority": 1}}
          ]
        }}

        【生成模式说明】
        - single: 简单项目（单文件）
        - stepwise: 复杂项目（多文件分步生成）
        - scaffold: 使用脚手架初始化后生成业务代码

        【scaffold 配置说明】
        - init_command: 项目初始化命令（只执行一次，如 npm create、django-admin startproject）
        - install_template: 增量安装依赖的命令模板，{{packages}} 会被替换为包列表
        - packages: 本需求所需的依赖包列表（会与已安装的包合并，只安装新增的）

        输出合法 JSON。
    """)

    if existing_workspace_files:
        prompt += f"\n\n【当前工作区已有文件】\n{existing_workspace_files}\n"
        prompt += "如果有框架文件，请使用 stepwise 而非 scaffold 模式。\n"
    if contextual_notes:
        prompt += "\n共享上下文:\n" + contextual_notes

    blueprint, _ = await call_llm_json(
        llm,
        [
            {"role": "system", "content": "你是资深架构/体验设计师，输出 Blueprint JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.35,
        label=f"blueprint:{requirement.get('id', '')}",
        verbose=verbose,
    )

    return blueprint


# ---------------------------------------------------------------------------
# Requirement Implementation
# ---------------------------------------------------------------------------
async def implement_requirement(
    llm: Any,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    feedback: str,
    passed_ids: set[str],
    failed_criteria: list[dict[str, Any]],
    previous_artifact: str,
    contextual_notes: str | None = None,
    workspace_files: dict[str, str] | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Implement a requirement based on blueprint.

    Args:
        llm: LLM model instance
        requirement: Requirement dict
        blueprint: Blueprint dict
        feedback: QA feedback
        passed_ids: Set of passed criteria IDs
        failed_criteria: List of failed criteria
        previous_artifact: Previous artifact content
        contextual_notes: Context notes
        workspace_files: Existing workspace files
        verbose: Whether to print debug info

    Returns:
        dict: Implementation result with files
    """
    from ._llm_utils import call_llm_json

    workspace_context = ""
    if workspace_files:
        workspace_context = "\n当前工作区文件:\n"
        for fname, content in workspace_files.items():
            workspace_context += f"\n--- {fname} (前 2000 字符) ---\n{content[:2000]}\n"

    prompt = textwrap.dedent(f"""
        需求:
        {json.dumps(requirement, ensure_ascii=False, indent=2)}

        Blueprint:
        {json.dumps(blueprint, ensure_ascii=False, indent=2)}
        {workspace_context}

        已通过的标准: {sorted(passed_ids) if passed_ids else "无"}
        需修复的标准: {json.dumps(failed_criteria, ensure_ascii=False, indent=2) if failed_criteria else "无"}
        上一版交付片段: {previous_artifact[:1200] if previous_artifact else "无"}
        QA 反馈: {feedback or "无"}

        请输出 JSON:
        {{
          "summary": "...",
          "project_type": "fullstack|frontend|backend",
          "files": [
            {{"path": "backend/app.py", "content": "..."}}
          ],
          "setup_commands": ["pip install -r requirements.txt"],
          "run_command": "...",
          "entry_point": "http://localhost:3000"
        }}
    """)

    if contextual_notes:
        prompt += "\n可引用的上下文:\n" + contextual_notes

    impl, _ = await call_llm_json(
        llm,
        [
            {"role": "system", "content": "你是交付工程师，需要生成最终产物。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
        label=f"implement:{requirement.get('id', '')}",
        verbose=verbose,
    )

    return impl


# ---------------------------------------------------------------------------
# Single File Generation
# ---------------------------------------------------------------------------
async def generate_single_file(
    llm: Any,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    file_plan: dict[str, Any],
    generated_files: dict[str, str],
    contextual_notes: str | None = None,
    runtime_workspace: "RuntimeWorkspace | None" = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Generate a single file based on file plan.

    Args:
        llm: LLM model instance
        requirement: Requirement dict
        blueprint: Blueprint dict
        file_plan: File plan dict
        generated_files: Already generated files
        contextual_notes: Context notes
        runtime_workspace: RuntimeWorkspace instance
        verbose: Whether to print debug info

    Returns:
        dict: File result with path and content
    """
    from ._llm_utils import call_llm_json

    file_path = file_plan.get("path", "")
    file_desc = file_plan.get("description", "")
    action = file_plan.get("action", "create")
    dependencies = file_plan.get("dependencies", [])

    # Read existing content for modify action
    existing_content = ""
    if action == "modify" and runtime_workspace:
        try:
            existing_content = runtime_workspace.read_file(file_path)
        except Exception:
            pass

    # Build dependencies context
    deps_context = ""
    if dependencies and generated_files:
        deps_context = "\n【依赖文件内容】\n"
        for dep in dependencies:
            if dep in generated_files:
                content = generated_files[dep]
                deps_context += f"\n--- {dep} ---\n{content[:3000]}\n"

    # Build prompt
    if action == "modify" and existing_content:
        prompt = textwrap.dedent(f"""
            【任务】修改文件: {file_path}

            【当前内容】
            ```
            {existing_content[:6000]}
            ```

            【修改说明】
            {file_desc}

            【项目需求】
            {json.dumps(requirement, ensure_ascii=False, indent=2)}
            {deps_context}

            请输出修改后的完整文件:
            {{"path": "{file_path}", "content": "...", "summary": "..."}}
        """)
    else:
        prompt = textwrap.dedent(f"""
            【任务】生成文件: {file_path}

            【文件描述】
            {file_desc}

            【项目需求】
            {json.dumps(requirement, ensure_ascii=False, indent=2)}

            【Blueprint】
            推荐技术栈: {blueprint.get('recommended_stack', '')}
            {deps_context}

            请输出完整文件:
            {{"path": "{file_path}", "content": "...", "summary": "..."}}
        """)

    if contextual_notes:
        prompt += "\n上下文:\n" + contextual_notes

    result, _ = await call_llm_json(
        llm,
        [
            {"role": "system", "content": "你是交付工程师，生成单个代码文件。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
        label=f"generate_file:{file_path}",
        verbose=verbose,
    )

    return result


# ---------------------------------------------------------------------------
# File Sorting
# ---------------------------------------------------------------------------
def sort_files_by_dependency(files_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort files by dependency order using topological sort.

    Args:
        files_plan: List of file plans

    Returns:
        list: Sorted file plans
    """
    if not files_plan:
        return []

    # Build dependency graph
    path_to_file = {f["path"]: f for f in files_plan}
    in_degree = {f["path"]: 0 for f in files_plan}
    dependents: dict[str, list[str]] = {f["path"]: [] for f in files_plan}

    for f in files_plan:
        for dep in f.get("dependencies", []):
            if dep in path_to_file:
                in_degree[f["path"]] += 1
                dependents[dep].append(f["path"])

    # Topological sort with priority
    result: list[dict[str, Any]] = []
    queue = sorted(
        [p for p, d in in_degree.items() if d == 0],
        key=lambda p: path_to_file[p].get("priority", 99),
    )

    while queue:
        path = queue.pop(0)
        result.append(path_to_file[path])

        for dep_path in dependents[path]:
            in_degree[dep_path] -= 1
            if in_degree[dep_path] == 0:
                priority = path_to_file[dep_path].get("priority", 99)
                insert_idx = len(queue)
                for i, p in enumerate(queue):
                    if path_to_file[p].get("priority", 99) > priority:
                        insert_idx = i
                        break
                queue.insert(insert_idx, dep_path)

    # Add remaining files (cycles)
    remaining = [f for f in files_plan if f["path"] not in [r["path"] for r in result]]
    result.extend(sorted(remaining, key=lambda f: f.get("priority", 99)))

    return result


# ---------------------------------------------------------------------------
# Scaffold Commands - LLM-driven package management
# ---------------------------------------------------------------------------
def _build_scaffold_commands(
    config: dict[str, Any],
    scaffold_type: str,
    is_initialized: bool,
    installed_packages: set[str],
) -> tuple[list[str], set[str]]:
    """Build scaffold commands based on LLM-provided configuration.

    The LLM provides:
    - init_command: Project initialization (run once)
    - install_template: Template for installing packages ({packages} placeholder)
    - packages: List of required packages

    Args:
        config: Scaffold config from blueprint (e.g., frontend or backend section)
        scaffold_type: "frontend" or "backend" (for logging)
        is_initialized: Whether project is already initialized
        installed_packages: Set of already installed packages

    Returns:
        Tuple of (list of commands to execute, set of packages to track)
    """
    commands: list[str] = []
    packages_to_track: set[str] = set()

    if not config:
        return commands, packages_to_track

    # Handle legacy format (single "command" field)
    if "command" in config and "packages" not in config:
        # Legacy: just run the command if not initialized
        if not is_initialized:
            commands.append(config["command"])
        return commands, packages_to_track

    # New format with explicit init_command, install_template, packages
    init_cmd = config.get("init_command")
    install_template = config.get("install_template")
    packages = config.get("packages", [])

    # Convert packages to set for tracking
    required_packages = set(packages) if isinstance(packages, list) else set()
    packages_to_track = required_packages

    if not is_initialized:
        # First time: run init command if provided
        if init_cmd:
            commands.append(init_cmd)

        # Install all packages
        if install_template and required_packages:
            install_cmd = install_template.replace("{packages}", ' '.join(sorted(required_packages)))
            commands.append(install_cmd)
    else:
        # Already initialized: only install new packages
        new_packages = required_packages - installed_packages
        if install_template and new_packages:
            install_cmd = install_template.replace("{packages}", ' '.join(sorted(new_packages)))
            commands.append(install_cmd)

    return commands, packages_to_track


async def run_scaffold_commands(
    runtime_workspace: "RuntimeWorkspace",
    scaffold_config: dict[str, Any],
    llm: Any,
    *,
    scaffold_initialized: dict[str, bool] | None = None,
    installed_packages: dict[str, set[str]] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute scaffold initialization commands with incremental package installation.

    Args:
        runtime_workspace: RuntimeWorkspace instance
        scaffold_config: Scaffold configuration
        llm: LLM for result judgment
        scaffold_initialized: Dict tracking which scaffold types are initialized
        installed_packages: Dict tracking installed packages per scaffold type
        verbose: Whether to print debug info

    Returns:
        dict: Execution result with new_packages info
    """
    result = {
        "success": True,
        "commands_executed": [],
        "outputs": [],
        "errors": [],
        "new_packages": {"frontend": set(), "backend": set()},
        "initialized": {"frontend": False, "backend": False},
    }

    scaffold_initialized = scaffold_initialized or {}
    installed_packages = installed_packages or {"frontend": set(), "backend": set()}

    async def execute_cmd(cmd: str, description: str, timeout: int = 300) -> bool:
        from ._observability import get_logger
        logger = get_logger()
        logger.info(f"[SCAFFOLD] {description}: {cmd}")
        result["commands_executed"].append(cmd)

        try:
            exec_result = runtime_workspace.execute_command(cmd, timeout=timeout)
            output = exec_result.get("output", "")
            error = exec_result.get("error", "")
            result["outputs"].append(output)

            if exec_result.get("success"):
                logger.info(f"[SCAFFOLD] ✓ {description}完成")
                return True
            else:
                result["errors"].append(f"{description}失败: {error[:100]}")
                logger.warn(f"[SCAFFOLD] ⚠ {description}失败")
                return False
        except Exception as e:
            result["errors"].append(str(e))
            return False

    # Frontend scaffold
    frontend_cfg = scaffold_config.get("frontend")
    if frontend_cfg:
        is_init = scaffold_initialized.get("frontend", False)
        commands, new_pkgs = _build_scaffold_commands(
            frontend_cfg,
            "frontend",
            is_init,
            installed_packages.get("frontend", set()),
        )
        for cmd in commands:
            desc = "前端增量安装" if is_init else "前端初始化"
            await execute_cmd(cmd, desc)
        if new_pkgs:
            result["new_packages"]["frontend"] = new_pkgs
        if not is_init and commands:
            result["initialized"]["frontend"] = True

        # Post-init commands only run on first initialization
        if not is_init:
            for post_cmd in frontend_cfg.get("post_init", []):
                await execute_cmd(post_cmd, "前端 post_init", timeout=600)

    # Backend scaffold
    backend_cfg = scaffold_config.get("backend")
    if backend_cfg:
        is_init = scaffold_initialized.get("backend", False)
        commands, new_pkgs = _build_scaffold_commands(
            backend_cfg,
            "backend",
            is_init,
            installed_packages.get("backend", set()),
        )
        for cmd in commands:
            desc = "后端增量安装" if is_init else "后端初始化"
            await execute_cmd(cmd, desc)
        if new_pkgs:
            result["new_packages"]["backend"] = new_pkgs
        if not is_init and commands:
            result["initialized"]["backend"] = True

        # Post-init commands only run on first initialization
        if not is_init:
            for post_cmd in backend_cfg.get("post_init", []):
                await execute_cmd(post_cmd, "后端 post_init", timeout=600)

    return result


# ---------------------------------------------------------------------------
# Stepwise Generation
# ---------------------------------------------------------------------------
async def stepwise_generate_files(
    llm: Any,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    contextual_notes: str | None = None,
    runtime_workspace: "RuntimeWorkspace | None" = None,
    feedback: str = "",
    failed_criteria: list[dict[str, Any]] | None = None,
    previous_errors: list[str] | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Generate files step by step based on blueprint.

    Args:
        llm: LLM model instance
        requirement: Requirement dict
        blueprint: Blueprint dict
        contextual_notes: Context notes
        runtime_workspace: RuntimeWorkspace instance
        feedback: Feedback from previous round (QA/validation issues)
        failed_criteria: List of failed acceptance criteria
        previous_errors: List of validation errors from previous round
        verbose: Whether to print debug info

    Returns:
        dict: Implementation result compatible with implement_requirement
    """
    files_plan = blueprint.get("files_plan", [])
    if not files_plan:
        raise ValueError("Blueprint 缺少 files_plan 字段")

    from ._observability import get_logger
    logger = get_logger()

    sorted_files = sort_files_by_dependency(files_plan)
    if verbose:
        logger.debug(f"[STEPWISE] 文件生成顺序: {[f['path'] for f in sorted_files]}")

    # Build feedback context from previous round errors
    feedback_context = ""
    if feedback:
        feedback_context += f"\n【上一轮反馈】\n{feedback}\n"
    if failed_criteria:
        feedback_context += "\n【未通过的验收标准】\n"
        for criterion in failed_criteria:
            feedback_context += f"- {criterion.get('name', '')}: {criterion.get('reason', '')}\n"
    if previous_errors:
        feedback_context += "\n【上一轮代码错误 - 必须修复】\n"
        for err in previous_errors[:10]:  # Limit to top 10 errors
            feedback_context += f"- {err}\n"

    generated_files: dict[str, str] = {}
    summaries: list[str] = []

    for i, file_plan in enumerate(sorted_files):
        file_path = file_plan["path"]
        action = file_plan.get("action", "create")
        logger.info(f"[STEPWISE] ({i + 1}/{len(sorted_files)}) {'修改' if action == 'modify' else '生成'}: {file_path}")

        # Combine contextual notes with feedback
        combined_context = contextual_notes or ""
        if feedback_context:
            combined_context += feedback_context

        result = await generate_single_file(
            llm=llm,
            requirement=requirement,
            blueprint=blueprint,
            file_plan=file_plan,
            generated_files=generated_files,
            contextual_notes=combined_context if combined_context else None,
            runtime_workspace=runtime_workspace,
            verbose=verbose,
        )

        content = result.get("content", "")
        if content:
            generated_files[file_path] = content
            summaries.append(f"- {file_path}: {result.get('summary', '')[:100]}")
        else:
            logger.warn(f"[STEPWISE] 警告: {file_path} 生成内容为空")

    return {
        "summary": f"分步生成了 {len(generated_files)} 个文件:\n" + "\n".join(summaries),
        "project_type": blueprint.get("artifact_type", "fullstack"),
        "files": [{"path": p, "content": c} for p, c in generated_files.items()],
        "setup_commands": [],
        "run_command": "",
        "entry_point": "",
    }


__all__ = [
    "extract_file_structure",
    "find_similar_text",
    "validate_python_syntax",
    "apply_edits",
    "design_requirement",
    "implement_requirement",
    "generate_single_file",
    "sort_files_by_dependency",
    "run_scaffold_commands",
    "stepwise_generate_files",
]
