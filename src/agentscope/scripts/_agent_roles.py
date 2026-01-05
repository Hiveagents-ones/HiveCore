# -*- coding: utf-8 -*-
"""Agent role implementations for requirement design and implementation.

This module provides:
- Blueprint design (design_requirement)
- Requirement implementation (implement_requirement)
- File generation utilities
- Edit operations
- Scaffold execution
- Claude Code integration for code generation
"""
from __future__ import annotations

import ast
import json
import re
import textwrap
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ._sandbox import RuntimeWorkspace

# Claude Code integration configuration
USE_CLAUDE_CODE = False  # Set to False to use traditional LLM generation (Claude CLI not available in Worker)

# Claude Code execution mode:
# - "stepwise": Agent decides file list, Claude Code generates each file (legacy)
# - "autonomous": Claude Code has full control over implementation (direct call)
# - "agent_with_limbs": Agent (brain) calls claude_code_edit (limbs) via toolkit
#
# Recommended: "agent_with_limbs" - proper brain/limbs separation
CLAUDE_CODE_MODE = "agent_with_limbs"


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
    skeleton_context: dict[str, Any] | None = None,
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
        skeleton_context: Skeleton context with file_ownership and shared_files
        verbose: Whether to print debug info

    Returns:
        dict: Blueprint JSON
    """
    from ._llm_utils import call_llm_json

    # Build criteria guidance for code generation
    criteria_guidance = ""
    if failed_criteria:
        criteria_guidance = "\n【必须实现的验收标准】\n"
        for i, criterion in enumerate(failed_criteria, 1):
            crit_id = criterion.get("id", f"AC-{i}")
            crit_name = criterion.get("name", criterion.get("title", ""))
            crit_desc = criterion.get("description", "")
            criteria_guidance += f"{i}. [{crit_id}] {crit_name}\n"
            if crit_desc:
                criteria_guidance += f"   描述: {crit_desc}\n"
            # Add QA failure reason if available (explains WHY previous attempt failed)
            if criterion.get("qa_failure_reason"):
                criteria_guidance += f"   ⚠️ 上次失败原因: {criterion.get('qa_failure_reason')}\n"
            # Add recommendation if available (explains HOW to fix)
            if criterion.get("recommendation"):
                criteria_guidance += f"   💡 修复建议: {criterion.get('recommendation')}\n"
        criteria_guidance += "\n【重要】files_plan 中的每个文件必须标注它实现哪些验收标准！\n"

    prompt = textwrap.dedent(f"""
        需求对象:
        {json.dumps(requirement, ensure_ascii=False, indent=2)}

        已通过的标准:
        {sorted(passed_ids) if passed_ids else "无"}
        {criteria_guidance}

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
            {{"path": "frontend/src/views/HomeView.vue", "description": "首页视图", "action": "create", "priority": 1, "criteria_ids": ["AC-1"]}},
            {{"path": "frontend/src/components/TaskItem.vue", "description": "任务项组件", "action": "create", "priority": 2, "criteria_ids": ["AC-2"]}},
            {{"path": "backend/app/main.py", "description": "后端入口", "action": "modify", "priority": 1, "criteria_ids": ["AC-3"]}}
          ]
        }}

        【关键 - 文件路径规范】
        1. files_plan.path 必须使用完整的相对路径，包含目录结构！
        2. 前端文件必须以 frontend/ 开头，如: frontend/src/views/XXX.vue, frontend/src/components/XXX.vue
        3. 后端文件必须以 backend/ 开头，如: backend/app/main.py, backend/app/routers/xxx.py
        4. 禁止使用简短路径如 src/XXX.vue 或 main.py，必须使用完整路径！
        5. files_plan.criteria_ids 必须标注该文件需要满足哪些验收标准ID！

        【生成模式说明】
        - single: 简单项目（单文件）
        - stepwise: 复杂项目（多文件分步生成）
        - scaffold: 使用脚手架初始化后生成业务代码

        【scaffold 配置说明】
        - init_command: 项目初始化命令（只执行一次，如 npm create、django-admin startproject）
        - install_template: 增量安装依赖的命令模板，{{packages}} 会被替换为包列表
        - packages: 本需求所需的依赖包列表（会与已安装的包合并，只安装新增的）

        【依赖管理 - 重要】
        如果代码需要使用第三方库（如 PyJWT, bcrypt, axios 等），必须：
        1. 在 scaffold.packages 中列出所需的第三方依赖
        2. 或在 files_plan 中包含 requirements.txt（Python）或 package.json（Node.js）
        否则代码将因缺少依赖而无法运行！

        输出合法 JSON。
    """)

    if existing_workspace_files:
        prompt += f"\n\n【当前工作区已有文件】\n{existing_workspace_files}\n"
        prompt += "如果有框架文件，请使用 stepwise 而非 scaffold 模式。\n"

    # Add skeleton context information
    if skeleton_context and skeleton_context.get("skeleton_generated"):
        req_id = requirement.get("id", "")
        file_ownership = skeleton_context.get("file_ownership", {})
        shared_files = skeleton_context.get("shared_files", [])

        # Find files owned by this requirement
        owned_files = [f for f, owner in file_ownership.items() if owner == req_id]
        # Find shared files this requirement can modify
        modifiable_shared = [f for f in shared_files if req_id in file_ownership.get(f, "")]

        prompt += "\n\n【统一代码骨架信息】\n"
        prompt += "项目已生成统一代码骨架，请基于骨架进行增量填充，不要覆盖整个文件。\n"

        if owned_files:
            prompt += f"\n此需求负责填充的文件:\n{json.dumps(owned_files, ensure_ascii=False, indent=2)}\n"
            prompt += "对于这些文件，请使用 action: 'modify' 填充 TODO 标记的部分。\n"

        if modifiable_shared:
            prompt += f"\n此需求可修改的共享文件:\n{json.dumps(modifiable_shared, ensure_ascii=False, indent=2)}\n"
            prompt += "对于共享文件，只填充标记为本需求的 TODO 部分，保留其他需求的 TODO 标记。\n"

        if shared_files:
            prompt += f"\n所有共享文件列表:\n{json.dumps(shared_files, ensure_ascii=False, indent=2)}\n"
            prompt += "【重要】不要删除或完全重写共享文件，只能增量修改。\n"

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

    # Validate and fix files_plan paths
    files_plan = blueprint.get("files_plan", [])
    from ._observability import get_logger
    logger = get_logger()

    if files_plan:
        logger.debug(f"[Blueprint] files_plan 原始路径: {[f.get('path', '') for f in files_plan]}")
        fixed_files_plan = []
        for f in files_plan:
            path = f.get("path", "")
            # Fix paths that don't start with frontend/ or backend/
            if path and not path.startswith(("frontend/", "backend/")):
                # Try to infer the correct prefix
                if any(path.endswith(ext) for ext in [".vue", ".jsx", ".tsx", ".css", ".scss"]):
                    # Frontend file
                    if path.startswith("src/"):
                        path = "frontend/" + path
                    elif not "/" in path or path.startswith("components/") or path.startswith("views/"):
                        path = "frontend/src/" + path
                    else:
                        path = "frontend/src/" + path
                elif any(path.endswith(ext) for ext in [".py"]):
                    # Backend file
                    if path.startswith("app/"):
                        path = "backend/" + path
                    elif not "/" in path:
                        path = "backend/app/" + path
                    else:
                        path = "backend/" + path
                logger.debug(f"[Blueprint] 修正路径: {f.get('path')} -> {path}")
                f = {**f, "path": path}
            fixed_files_plan.append(f)
        blueprint["files_plan"] = fixed_files_plan
        logger.debug(f"[Blueprint] files_plan 修正后路径: {[f.get('path', '') for f in fixed_files_plan]}")
    else:
        logger.warn(f"[Blueprint] files_plan 为空！")

    # NOTE: Scaffold files are now pre-written BEFORE skeleton generation
    # in _execution.py, no need to add them to files_plan here

    return blueprint


def validate_blueprint_criteria_coverage(
    blueprint: dict[str, Any],
    failed_criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate that Blueprint's files_plan covers all failed acceptance criteria.

    This function checks if every failed criterion is assigned to at least one
    file in the files_plan. If not, it returns the uncovered criteria IDs.

    Args:
        blueprint: Blueprint dict with files_plan
        failed_criteria: List of failed criteria that must be implemented

    Returns:
        dict: Validation result with 'is_valid', 'covered_ids', 'uncovered_ids'
    """
    files_plan = blueprint.get("files_plan", [])
    failed_ids = {c.get("id", "") for c in failed_criteria if c.get("id")}

    # Collect all criteria IDs covered by files_plan
    covered_ids: set[str] = set()
    for fp in files_plan:
        criteria_ids = fp.get("criteria_ids", [])
        if isinstance(criteria_ids, list):
            covered_ids.update(criteria_ids)

    # Find uncovered criteria
    uncovered_ids = failed_ids - covered_ids

    return {
        "is_valid": len(uncovered_ids) == 0,
        "covered_ids": list(covered_ids),
        "uncovered_ids": list(uncovered_ids),
        "coverage_ratio": len(covered_ids) / len(failed_ids) if failed_ids else 1.0,
    }


async def fix_blueprint_coverage(
    llm: Any,
    blueprint: dict[str, Any],
    uncovered_criteria: list[dict[str, Any]],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Fix Blueprint to cover uncovered acceptance criteria.

    Args:
        llm: LLM model instance
        blueprint: Original Blueprint
        uncovered_criteria: List of criteria not covered in files_plan
        verbose: Whether to print debug info

    Returns:
        dict: Fixed Blueprint with updated files_plan
    """
    from ._llm_utils import call_llm_json

    criteria_text = json.dumps(uncovered_criteria, ensure_ascii=False, indent=2)

    prompt = textwrap.dedent(f"""
        当前 Blueprint 的 files_plan 未覆盖以下验收标准:
        {criteria_text}

        当前 Blueprint:
        {json.dumps(blueprint, ensure_ascii=False, indent=2)}

        请更新 Blueprint，确保所有验收标准都分配给至少一个文件。

        选项:
        1. 在现有文件的 criteria_ids 中添加遗漏的标准 ID
        2. 添加新文件来实现遗漏的标准

        输出完整的更新后 Blueprint JSON。
    """)

    fixed_blueprint, _ = await call_llm_json(
        llm,
        [
            {"role": "system", "content": "你是架构师，负责确保 Blueprint 覆盖所有验收标准。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        label="fix_blueprint_coverage",
        verbose=verbose,
    )

    return fixed_blueprint


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
    skeleton_context: dict[str, Any] | None = None,
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
        skeleton_context: Skeleton context with file_ownership and shared_files
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

    # Build detailed criteria implementation guide
    criteria_impl_guide = ""
    if failed_criteria:
        criteria_impl_guide = "\n\n【必须实现的验收标准 - 请逐条确保满足】\n"
        for i, criterion in enumerate(failed_criteria, 1):
            crit_id = criterion.get("id", f"AC-{i}")
            crit_name = criterion.get("name", criterion.get("title", ""))
            crit_desc = criterion.get("description", "")
            criteria_impl_guide += f"\n{i}. [{crit_id}] {crit_name}\n"
            if crit_desc:
                criteria_impl_guide += f"   要求: {crit_desc}\n"
            if criterion.get("recommendation"):
                criteria_impl_guide += f"   实现建议: {criterion.get('recommendation')}\n"
            if criterion.get("reason"):
                criteria_impl_guide += f"   上次失败原因: {criterion.get('reason')}\n"
        criteria_impl_guide += "\n【警告】如果验收标准涉及性能测试，必须在代码中添加性能验证逻辑！\n"
        criteria_impl_guide += "【警告】如果验收标准涉及特定功能，必须实现完整的接口和逻辑！\n"

    prompt = textwrap.dedent(f"""
        需求:
        {json.dumps(requirement, ensure_ascii=False, indent=2)}

        Blueprint:
        {json.dumps(blueprint, ensure_ascii=False, indent=2)}
        {workspace_context}
        {criteria_impl_guide}

        已通过的标准: {sorted(passed_ids) if passed_ids else "无"}
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

    # Add skeleton context for incremental filling
    if skeleton_context and skeleton_context.get("skeleton_generated"):
        req_id = requirement.get("id", "")
        file_ownership = skeleton_context.get("file_ownership", {})
        shared_files = skeleton_context.get("shared_files", [])

        prompt += "\n\n【增量填充模式】\n"
        prompt += "项目使用统一代码骨架，你需要增量填充而非覆盖整个文件。\n"

        # Find files owned by this requirement
        owned_files = [f for f, owner in file_ownership.items() if owner == req_id]
        if owned_files:
            prompt += f"\n你负责填充的文件: {json.dumps(owned_files, ensure_ascii=False)}\n"
            prompt += "对于这些文件中的 TODO 标记，请生成完整实现代码。\n"

        if shared_files:
            prompt += f"\n共享文件（只能增量修改，不能覆盖）: {json.dumps(shared_files, ensure_ascii=False)}\n"
            prompt += f"在共享文件中，只填充标记为 `# TODO: [{req_id}]` 的部分。\n"
            prompt += "保留其他需求的 TODO 标记和现有代码。\n"

        prompt += "\n【重要】对于已存在的文件，你的 content 应该是修改后的完整内容，"
        prompt += "但要保留其他需求的占位符和实现。\n"

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
    skeleton_context: dict[str, Any] | None = None,
    file_criteria: list[dict[str, Any]] | None = None,
    module_registry: dict[str, list[dict[str, str]]] | None = None,
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
        skeleton_context: Skeleton context with file_ownership and shared_files
        file_criteria: Acceptance criteria this file should implement
        module_registry: Registry of existing modules and their exports
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

    # Claude Code style: Read Before Write
    # 1. Read related modules before generating code
    workspace_files: dict[str, str] | None = None
    if runtime_workspace and module_registry:
        from ._code_context import (
            format_module_registry_for_prompt,
            get_interface_constraint_prompt,
            read_related_modules,
            scan_workspace_files,
        )
        from pathlib import Path

        # Scan workspace files for Read Before Write
        workspace_path = Path(runtime_workspace.workspace_dir)
        workspace_files = scan_workspace_files(workspace_path)

        # Add related module contents (Read Before Write)
        related_content = read_related_modules(
            file_path, workspace_files, module_registry, max_modules=3
        )
        if related_content:
            prompt += f"\n\n{related_content}"

        # Add module registry
        registry_str = format_module_registry_for_prompt(module_registry, max_modules=20)
        if registry_str:
            prompt += f"\n\n{registry_str}"
            # Add language-agnostic interface constraint
            prompt += f"\n{get_interface_constraint_prompt()}"
    elif module_registry:
        from ._code_context import format_module_registry_for_prompt, get_interface_constraint_prompt
        registry_str = format_module_registry_for_prompt(module_registry, max_modules=20)
        if registry_str:
            prompt += f"\n\n{registry_str}"
            prompt += f"\n{get_interface_constraint_prompt()}"

    # Add skeleton context for shared files
    if skeleton_context and skeleton_context.get("skeleton_generated"):
        req_id = requirement.get("id", "")
        shared_files = skeleton_context.get("shared_files", [])

        if file_path in shared_files:
            prompt += f"\n\n【共享文件注意事项】\n"
            prompt += f"此文件 ({file_path}) 是共享文件，被多个需求使用。\n"
            prompt += f"只填充标记为 `# TODO: [{req_id}]` 的部分。\n"
            prompt += "保留其他需求的 TODO 标记和现有代码，不要删除或覆盖。\n"

    # Add acceptance criteria that this file must implement
    if file_criteria:
        prompt += "\n\n【此文件必须实现的验收标准】\n"
        for i, criterion in enumerate(file_criteria, 1):
            crit_id = criterion.get("id", f"AC-{i}")
            crit_name = criterion.get("name", criterion.get("title", ""))
            crit_desc = criterion.get("description", "")
            prompt += f"{i}. [{crit_id}] {crit_name}\n"
            if crit_desc:
                prompt += f"   要求: {crit_desc}\n"
        prompt += "\n【关键】生成的代码必须完整实现上述每个验收标准的功能！\n"

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

    # Claude Code style: Validate and fix imports after generation
    if result and module_registry:
        from ._code_context import (
            validate_imports_strict,
            fix_invalid_imports,
        )

        content = result.get("content", "")
        if content:
            validation = validate_imports_strict(
                content,
                file_path,
                module_registry,
                workspace_files=workspace_files,
            )

            if not validation.valid:
                # Auto-fix invalid imports
                fixed_content = fix_invalid_imports(content, validation)
                result["content"] = fixed_content

                # Log the fixes
                if verbose:
                    for inv in validation.invalid_imports:
                        fix = validation.suggested_fixes.get(inv["import"])
                        if fix:
                            print(f"  [AutoFix] {inv['import']} -> {fix}")
                        else:
                            print(f"  [Warning] Invalid import: {inv['import']} - {inv['reason']}")

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
            # Fix permissions after frontend initialization
            # This ensures Claude Code (node user) can modify the files
            await execute_cmd(
                "chown -R node:node /workspace/frontend 2>/dev/null || true",
                "前端权限修复"
            )

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
            # Fix permissions after backend initialization
            # This ensures Claude Code (node user) can modify the files
            await execute_cmd(
                "chown -R node:node /workspace/backend 2>/dev/null || true",
                "后端权限修复"
            )

        # Post-init commands only run on first initialization
        if not is_init:
            for post_cmd in backend_cfg.get("post_init", []):
                await execute_cmd(post_cmd, "后端 post_init", timeout=600)

    return result


# ---------------------------------------------------------------------------
# Claude Code File Generation
# ---------------------------------------------------------------------------
async def generate_file_with_claude_code(
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    file_plan: dict[str, Any],
    workspace_dir: str,
    generated_files: dict[str, str],
    file_criteria: list[dict[str, Any]] | None = None,
    contextual_notes: str | None = None,
    *,
    runtime_workspace: Any | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Generate a single file using Claude Code CLI.

    Args:
        requirement: Requirement dict
        blueprint: Blueprint dict
        file_plan: File plan dict with path, description, action
        workspace_dir: Workspace directory path
        generated_files: Already generated files for context
        file_criteria: Acceptance criteria this file should implement
        contextual_notes: Additional context notes
        runtime_workspace: RuntimeWorkspace for reading files from container
        verbose: Whether to print debug info

    Returns:
        dict: File result with path and content
    """
    from ._claude_code import claude_code_edit
    from pathlib import Path

    file_path = file_plan.get("path", "")
    file_desc = file_plan.get("description", "")
    action = file_plan.get("action", "create")

    # Build the prompt for Claude Code
    prompt_parts = []

    # Task description
    if action == "modify":
        prompt_parts.append(f"修改文件 {file_path}:")
    else:
        prompt_parts.append(f"创建文件 {file_path}:")

    prompt_parts.append(f"\n文件描述: {file_desc}")

    # Requirement context
    prompt_parts.append(f"\n\n需求: {requirement.get('title', '')}")
    if requirement.get("description"):
        prompt_parts.append(f"\n{requirement.get('description')[:500]}")

    # Blueprint context
    if blueprint.get("recommended_stack"):
        prompt_parts.append(f"\n\n技术栈: {blueprint.get('recommended_stack')}")
    if blueprint.get("deliverable_pitch"):
        prompt_parts.append(f"\n目标: {blueprint.get('deliverable_pitch')}")

    # Acceptance criteria
    if file_criteria:
        prompt_parts.append("\n\n必须满足的验收标准:")
        for i, criterion in enumerate(file_criteria, 1):
            crit_id = criterion.get("id", f"AC-{i}")
            crit_name = criterion.get("name", criterion.get("title", ""))
            crit_desc = criterion.get("description", "")
            prompt_parts.append(f"\n{i}. [{crit_id}] {crit_name}")
            if crit_desc:
                prompt_parts.append(f"\n   要求: {crit_desc}")

    # Dependencies context
    dependencies = file_plan.get("dependencies", [])
    if dependencies and generated_files:
        prompt_parts.append("\n\n相关依赖文件:")
        for dep in dependencies[:3]:
            if dep in generated_files:
                content = generated_files[dep]
                prompt_parts.append(f"\n--- {dep} ---\n{content[:2000]}")

    # Additional context
    if contextual_notes:
        prompt_parts.append(f"\n\n上下文:\n{contextual_notes[:1000]}")

    prompt = "".join(prompt_parts)

    # Call Claude Code
    try:
        result = await claude_code_edit(
            prompt=prompt,
            workspace=workspace_dir,
            timeout=120,  # 2 minutes per file
        )

        # Parse the response
        response_text = ""
        if result.content:
            for block in result.content:
                if hasattr(block, "get"):
                    response_text += block.get("text", "")
                elif hasattr(block, "text"):
                    response_text += block.text

        # Read the generated file content
        # Priority: 1) runtime_workspace (container), 2) local path, 3) extract from response
        content = ""

        # Try reading from container via runtime_workspace
        if runtime_workspace:
            try:
                content = await runtime_workspace.read_file(file_path)
                if content:
                    return {
                        "path": file_path,
                        "content": content,
                        "summary": f"Claude Code 生成 (容器): {response_text[:100]}",
                    }
            except Exception as read_err:
                if verbose:
                    logger.debug(f"[ClaudeCode] 从容器读取失败 {file_path}: {read_err}")

        # Fallback: try local path
        full_path = Path(workspace_dir) / file_path
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8")
            return {
                "path": file_path,
                "content": content,
                "summary": f"Claude Code 生成: {response_text[:100]}",
            }

        # Fallback: try to extract code from the response
        if "```" in response_text:
            import re
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", response_text, re.DOTALL)
            if code_match:
                content = code_match.group(1)
                # Write to container if runtime_workspace available
                if runtime_workspace:
                    try:
                        await runtime_workspace.write_file(file_path, content)
                    except Exception:
                        pass  # Ignore write errors
                else:
                    # Fallback: write locally
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                return {
                    "path": file_path,
                    "content": content,
                    "summary": f"从响应提取: {response_text[:100]}",
                }

        return {
            "path": file_path,
            "content": "",
            "summary": f"Claude Code 未生成文件: {response_text[:200]}",
        }

    except Exception as e:
        if verbose:
            from ._observability import get_logger
            get_logger().warn(f"[ClaudeCode] 生成 {file_path} 失败: {e}")
        return {
            "path": file_path,
            "content": "",
            "summary": f"生成失败: {str(e)}",
        }


# ---------------------------------------------------------------------------
# Autonomous Claude Code Implementation (NEW - Recommended)
# ---------------------------------------------------------------------------
async def implement_requirement_autonomous(
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    all_criteria: list[dict[str, Any]] | None = None,
    workspace_dir: str | None = None,
    contextual_notes: str | None = None,
    feedback: str = "",
    failed_criteria: list[dict[str, Any]] | None = None,
    previous_errors: list[str] | None = None,
    architecture_contract: dict[str, Any] | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Implement a requirement by delegating full control to Claude Code.

    Unlike stepwise mode, this gives Claude Code complete autonomy to:
    - Explore the existing codebase
    - Decide which files to create or modify
    - Implement the solution holistically

    Args:
        requirement: Requirement dict with id, title, description
        blueprint: Blueprint with recommended_stack, deliverable_pitch
        all_criteria: Acceptance criteria to satisfy
        workspace_dir: Workspace directory path
        contextual_notes: Additional context
        feedback: Feedback from previous round
        failed_criteria: List of failed acceptance criteria
        previous_errors: List of validation errors from previous round
        architecture_contract: Architecture contract with API endpoints
        verbose: Whether to print debug info

    Returns:
        dict: Implementation result with files and developer_summary
    """
    from ._claude_code import claude_code_edit
    from ._observability import get_logger
    from pathlib import Path

    logger = get_logger()
    req_id = requirement.get("id", "REQ-???")

    if verbose:
        logger.info(f"[{req_id}] 🤖 自主模式: Claude Code 全权负责实现")

    # Build comprehensive prompt for Claude Code
    prompt_parts = []

    # 1. Task header
    prompt_parts.append(f"# 任务: 实现需求 {req_id}")
    prompt_parts.append(f"\n## 需求: {requirement.get('title', '')}")
    if requirement.get("description"):
        prompt_parts.append(f"\n{requirement.get('description')}")

    # 2. Technology stack
    if blueprint.get("recommended_stack"):
        prompt_parts.append(f"\n\n## 技术栈\n{blueprint.get('recommended_stack')}")

    # 3. Goal
    if blueprint.get("deliverable_pitch"):
        prompt_parts.append(f"\n\n## 目标\n{blueprint.get('deliverable_pitch')}")

    # 4. Acceptance criteria (CRITICAL)
    if all_criteria:
        prompt_parts.append("\n\n## 验收标准 (必须全部满足)")
        for i, criterion in enumerate(all_criteria, 1):
            crit_id = criterion.get("id", f"AC-{i}")
            crit_name = criterion.get("name", criterion.get("title", ""))
            crit_desc = criterion.get("description", "")
            prompt_parts.append(f"\n{i}. **[{crit_id}]** {crit_name}")
            if crit_desc:
                prompt_parts.append(f"\n   - {crit_desc}")

    # 5. Architecture contract (if available)
    if architecture_contract:
        endpoints = architecture_contract.get("api_endpoints", [])
        if endpoints:
            prompt_parts.append("\n\n## API 架构契约")
            for ep in endpoints[:10]:  # Limit to first 10
                method = ep.get("method", "GET")
                path = ep.get("path", "")
                desc = ep.get("description", "")
                prompt_parts.append(f"\n- `{method} {path}`: {desc}")

    # 6. Previous round feedback (if any)
    if feedback or failed_criteria or previous_errors:
        prompt_parts.append("\n\n## ⚠️ 上一轮问题 (必须修复)")
        if feedback:
            prompt_parts.append(f"\n反馈: {feedback}")
        if failed_criteria:
            prompt_parts.append("\n未通过的验收标准:")
            for fc in failed_criteria:
                prompt_parts.append(f"\n- {fc.get('name', '')}: {fc.get('reason', '')}")
        if previous_errors:
            prompt_parts.append("\n代码错误:")
            for err in previous_errors[:5]:
                prompt_parts.append(f"\n- {err}")

    # 7. Additional context
    if contextual_notes:
        prompt_parts.append(f"\n\n## 上下文\n{contextual_notes[:2000]}")

    # 8. Instructions
    prompt_parts.append("""

## 实现指南

请你：
1. **首先探索代码库**，了解现有结构和模式
2. **自主决定**需要创建或修改哪些文件
3. **完整实现**需求，确保所有验收标准都能通过
4. **遵循现有代码风格**和项目约定
5. **确保导入正确**，避免循环导入

你有完全的自主权来决定最佳实现方案。开始吧！
""")

    prompt = "".join(prompt_parts)

    if verbose:
        logger.debug(f"[{req_id}] Prompt 长度: {len(prompt)} 字符")

    # Call Claude Code with extended timeout
    try:
        result = await claude_code_edit(
            prompt=prompt,
            workspace=workspace_dir,
            timeout=600,  # 10 minutes for full requirement
        )

        # Parse the response
        response_text = ""
        if result.content:
            for block in result.content:
                if hasattr(block, "get"):
                    response_text += block.get("text", "")
                elif hasattr(block, "text"):
                    response_text += block.text

        if verbose:
            logger.info(f"[{req_id}] Claude Code 完成: {response_text[:200]}...")

        # Scan workspace for generated/modified files
        files_output = []
        if workspace_dir:
            ws_path = Path(workspace_dir)
            # Get all source files
            for ext in ["py", "ts", "js", "vue", "tsx", "jsx", "json"]:
                for f in ws_path.rglob(f"*.{ext}"):
                    if "node_modules" in str(f) or "__pycache__" in str(f):
                        continue
                    rel_path = str(f.relative_to(ws_path))
                    try:
                        content = f.read_text(encoding="utf-8")
                        files_output.append({
                            "path": rel_path,
                            "content": content,
                        })
                    except Exception:
                        pass

        return {
            "files": files_output,
            "developer_summary": f"Claude Code 自主实现: {response_text[:500]}",
            "mode": "autonomous",
        }

    except Exception as e:
        logger.error(f"[{req_id}] Claude Code 执行失败: {e}")
        return {
            "files": [],
            "developer_summary": f"实现失败: {str(e)}",
            "mode": "autonomous",
        }


# ---------------------------------------------------------------------------
# Stepwise Generation (Legacy)
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
    skeleton_context: dict[str, Any] | None = None,
    all_criteria: list[dict[str, Any]] | None = None,
    workspace_dir: "Any | None" = None,
    code_guard: "Any | None" = None,
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
        skeleton_context: Skeleton context with file_ownership and shared_files
        all_criteria: All acceptance criteria for the requirement
        workspace_dir: Workspace directory for module scanning
        code_guard: CodeGuardManager instance for real-time validation
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

    # Build module registry for import validation (Claude Code style)
    module_registry: dict[str, list[dict[str, str]]] = {}
    if workspace_dir:
        from pathlib import Path
        from ._code_context import scan_workspace_files, build_module_registry
        ws_path = Path(workspace_dir) if not isinstance(workspace_dir, Path) else workspace_dir
        if ws_path.exists():
            existing_files = scan_workspace_files(ws_path)
            module_registry = build_module_registry(existing_files)
            if verbose and module_registry:
                logger.debug(f"[STEPWISE] 扫描到 {len(module_registry)} 个现有模块")

    # Build feedback context from previous round errors
    # Using structured error classification (框架普适化 + Agent特化)
    feedback_context = ""
    if feedback:
        feedback_context += f"\n【上一轮反馈】\n{feedback}\n"
    if failed_criteria:
        feedback_context += "\n【未通过的验收标准】\n"
        for criterion in failed_criteria:
            feedback_context += f"- {criterion.get('name', '')}: {criterion.get('reason', '')}\n"
    if previous_errors:
        # Use the framework's error classification system
        from ._execution import _classify_errors, ErrorCategory

        classified = _classify_errors(previous_errors)

        # Show raw errors first (limited)
        feedback_context += "\n【上一轮代码错误 - 必须修复】\n"
        for err in previous_errors[:10]:
            feedback_context += f"- {err}\n"

        # ===================================================================
        # Agent Specialization Layer (Agent特化)
        # Provide domain-specific guidance based on error categories
        # ===================================================================

        # 1. CIRCULAR IMPORT - Most critical, blocks everything
        if classified[ErrorCategory.CIRCULAR_IMPORT]:
            feedback_context += (
                "\n【严重：循环导入错误】\n"
                "这是导致项目无法运行的根本原因！\n"
                "\n修复策略（选择其一）：\n"
                "策略A - 最小化 __init__.py：\n"
                "```python\n"
                "# app/__init__.py\n"
                "__all__ = ['models', 'schemas', 'routers']\n"
                "# 不要导入具体类！让用户从子模块导入\n"
                "```\n"
                "\n策略B - 使用 TYPE_CHECKING：\n"
                "```python\n"
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    from .models.member import Member  # 只用于类型提示\n"
                "```\n"
            )

        # 2. TYPE CHECK ERRORS - Common with mypy/tsc
        elif classified[ErrorCategory.TYPE_CHECK]:
            type_errors = classified[ErrorCategory.TYPE_CHECK]
            feedback_context += (
                f"\n【类型检查错误】检测到 {len(type_errors)} 个类型错误\n"
                "\n常见问题和修复方法：\n"
                "\n1. SQLAlchemy 模型类型注解：\n"
                "```python\n"
                "# ❌ 错误\n"
                "class User(Base):\n"
                "    name: str = Column(String)  # Column 不是 str\n"
                "\n"
                "# ✅ 正确 - 使用 Mapped\n"
                "from sqlalchemy.orm import Mapped, mapped_column\n"
                "class User(Base):\n"
                "    name: Mapped[str] = mapped_column(String)\n"
                "```\n"
                "\n2. Optional 类型处理：\n"
                "```python\n"
                "# ❌ 错误\n"
                "def get_user(id: int) -> User:  # 可能返回 None\n"
                "\n"
                "# ✅ 正确\n"
                "def get_user(id: int) -> User | None:\n"
                "```\n"
                "\n3. Pydantic v2 迁移：\n"
                "```python\n"
                "# ❌ 错误 - Pydantic v1 语法\n"
                "from pydantic import BaseSettings\n"
                "\n"
                "# ✅ 正确 - Pydantic v2 语法\n"
                "from pydantic_settings import BaseSettings\n"
                "```\n"
            )

        # 3. IMPORT MISSING - Symbol not exported
        elif classified[ErrorCategory.IMPORT_MISSING]:
            import_errors = classified[ErrorCategory.IMPORT_MISSING]
            feedback_context += "\n【导入缺失错误】\n"
            for err_info in import_errors[:3]:  # Show first 3
                symbol = err_info.get("symbol", "Unknown")
                package = err_info.get("package", "Unknown")
                feedback_context += (
                    f"\n无法从 `{package}` 导入 `{symbol}`\n"
                    f"\n修复方法（选择其一）：\n"
                    f"1. 在 `{package.replace('.', '/')}/__init__.py` 添加导出：\n"
                    f"   ```python\n"
                    f"   from .模块名 import {symbol}\n"
                    f"   ```\n"
                    f"2. 修改导入语句使用完整路径：\n"
                    f"   ```python\n"
                    f"   from {package}.模块名 import {symbol}\n"
                    f"   ```\n"
                )

        # 4. MODULE NOT FOUND - Missing dependency
        elif classified[ErrorCategory.MODULE_NOT_FOUND]:
            module_errors = classified[ErrorCategory.MODULE_NOT_FOUND]
            feedback_context += "\n【缺失依赖错误】\n"
            for err_info in module_errors[:3]:
                module = err_info.get("module", "Unknown")
                feedback_context += f"- 缺失模块: {module}\n"
            feedback_context += (
                "\n必须更新依赖文件：\n"
                "- Python: 在 requirements.txt 添加依赖\n"
                "- Node.js: 在 package.json 的 dependencies 添加\n"
                "- 将依赖文件加入待修改文件列表！\n"
            )

        # 5. SYNTAX ERRORS
        elif classified[ErrorCategory.SYNTAX]:
            feedback_context += (
                "\n【语法错误】\n"
                "代码生成不完整，请检查：\n"
                "1. 字符串引号是否成对\n"
                "2. 括号 () [] {} 是否配对\n"
                "3. 代码是否被截断\n"
            )

        # 6. INIT MISSING - Database/file not initialized
        elif classified[ErrorCategory.INIT_MISSING]:
            init_errors = classified[ErrorCategory.INIT_MISSING]
            feedback_context += "\n【初始化缺失错误】\n"
            for err_info in init_errors:
                file_path = err_info.get("file", "")
                if "db" in file_path.lower() or "database" in file_path.lower():
                    feedback_context += (
                        "\n数据库未初始化！\n"
                        "\n修复方法 - 在应用启动时创建表：\n"
                        "```python\n"
                        "# FastAPI with lifespan\n"
                        "from contextlib import asynccontextmanager\n"
                        "from .database import engine, Base\n"
                        "\n"
                        "@asynccontextmanager\n"
                        "async def lifespan(app: FastAPI):\n"
                        "    Base.metadata.create_all(bind=engine)\n"
                        "    yield\n"
                        "\n"
                        "app = FastAPI(lifespan=lifespan)\n"
                        "```\n"
                        "\n或在 main.py 顶部直接调用：\n"
                        "```python\n"
                        "from .database import engine, Base\n"
                        "Base.metadata.create_all(bind=engine)\n"
                        "```\n"
                    )
                    break

    generated_files: dict[str, str] = {}
    summaries: list[str] = []

    # Build criteria lookup by ID
    criteria_by_id: dict[str, dict[str, Any]] = {}
    if all_criteria:
        for c in all_criteria:
            cid = c.get("id", "")
            if cid:
                criteria_by_id[cid] = c

    for i, file_plan in enumerate(sorted_files):
        file_path = file_plan["path"]
        action = file_plan.get("action", "create")
        is_scaffold = file_plan.get("is_scaffold", False)

        # Handle scaffold files - use template content directly
        if is_scaffold and file_plan.get("content_template"):
            logger.info(f"[STEPWISE] ({i + 1}/{len(sorted_files)}) [Scaffold] 创建基础文件: {file_path}")
            content = file_plan["content_template"]
            generated_files[file_path] = content

            # Write to workspace
            if runtime_workspace and runtime_workspace.is_initialized:
                try:
                    runtime_workspace.write_file(file_path, content)
                    logger.debug(f"[STEPWISE] Scaffold 文件写入容器: {file_path}")
                except Exception as e:
                    logger.warn(f"[STEPWISE] Scaffold 写入失败: {file_path} - {e}")
            elif workspace_dir:
                full_path = workspace_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                logger.debug(f"[STEPWISE] Scaffold 文件写入主机: {file_path}")

            continue  # Skip LLM generation for scaffold files

        logger.info(f"[STEPWISE] ({i + 1}/{len(sorted_files)}) {'修改' if action == 'modify' else '生成'}: {file_path}")

        # Get criteria for this specific file
        file_criteria_ids = file_plan.get("criteria_ids", [])
        file_criteria = [criteria_by_id[cid] for cid in file_criteria_ids if cid in criteria_by_id]
        # If no specific criteria assigned, use failed criteria
        if not file_criteria and failed_criteria:
            file_criteria = failed_criteria

        # Combine contextual notes with feedback
        combined_context = contextual_notes or ""
        if feedback_context:
            combined_context += feedback_context

        # CodeGuard real-time validation with retry
        max_retries = 2 if code_guard else 1
        code_guard_feedback = ""

        for retry in range(max_retries):
            # Add CodeGuard feedback to context for retry
            retry_context = combined_context if combined_context else ""
            if code_guard_feedback:
                retry_context += f"\n\n[CodeGuard 检测到问题，请修复]\n{code_guard_feedback}"

            # Choose generation method based on USE_CLAUDE_CODE flag
            if USE_CLAUDE_CODE and workspace_dir:
                # Use Claude Code for file generation
                if verbose:
                    logger.info(f"[ClaudeCode] 使用 Claude Code 生成: {file_path}")
                result = await generate_file_with_claude_code(
                    requirement=requirement,
                    blueprint=blueprint,
                    file_plan=file_plan,
                    workspace_dir=str(workspace_dir),
                    generated_files=generated_files,
                    file_criteria=file_criteria if file_criteria else None,
                    contextual_notes=retry_context if retry_context else None,
                    runtime_workspace=runtime_workspace,
                    verbose=verbose,
                )
            else:
                # Use traditional LLM generation
                result = await generate_single_file(
                    llm=llm,
                    requirement=requirement,
                    blueprint=blueprint,
                    file_plan=file_plan,
                    generated_files=generated_files,
                    contextual_notes=retry_context if retry_context else None,
                    runtime_workspace=runtime_workspace,
                    skeleton_context=skeleton_context,
                    file_criteria=file_criteria if file_criteria else None,
                    module_registry=module_registry if module_registry else None,
                    verbose=verbose,
                )

            content = result.get("content", "")
            if not content:
                break

            # CodeGuard real-time validation
            if code_guard and code_guard.config.should_validate_file(file_path):
                cg_result = code_guard.validate_content(file_path, content, is_new_file=True)
                # Check for ERROR level issues
                has_errors = any(
                    issue.severity.name == "ERROR"
                    for issue in cg_result.issues
                )
                if has_errors and retry < max_retries - 1:
                    # Format errors for retry
                    code_guard_feedback = code_guard.format_warnings(cg_result)
                    if verbose:
                        logger.warn(f"[STEPWISE] CodeGuard 检测到错误，重试 {file_path}")
                    continue  # Retry with feedback
                elif cg_result.issues and verbose:
                    # Log warnings even if not retrying
                    warnings = code_guard.format_warnings(cg_result)
                    if warnings:
                        logger.warn(f"[STEPWISE] CodeGuard ({file_path}):\n{warnings}")

            # Validation passed or max retries reached
            break

        content = result.get("content", "")
        if content:
            generated_files[file_path] = content
            summaries.append(f"- {file_path}: {result.get('summary', '')[:100]}")

            # Update module registry with newly generated file (for subsequent files to reference)
            if module_registry is not None:
                from ._code_context import (
                    extract_python_exports,
                    extract_typescript_exports,
                    extract_vue_exports,
                )
                exports: list[dict[str, str]] = []
                if file_path.endswith(".py"):
                    exports = extract_python_exports(content)
                elif file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
                    exports = extract_typescript_exports(content)
                elif file_path.endswith(".vue"):
                    exports = extract_vue_exports(content)
                if exports:
                    module_registry[file_path] = exports
                    # Add @ alias for frontend files
                    if file_path.startswith("frontend/src/"):
                        alias_path = "@/" + file_path[13:]
                        module_registry[alias_path] = exports
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


# ---------------------------------------------------------------------------
# LLM-Driven Unified Skeleton Analysis (metadata only, no content generation)
# ---------------------------------------------------------------------------
SKELETON_ANALYSIS_PROMPT = """分析以下项目需求，识别需要预先创建的共享代码骨架文件。

【重要】只分析并返回文件元信息，不要生成具体代码内容。代码将由 Claude Code 在容器中生成。

## 项目需求列表
{requirements_json}

## 架构契约（如有）
{architecture_contract}

## 任务
分析所有需求，识别：
1. 共享的数据实体（多个需求都需要的）
2. 共享的API模块/路由（多个需求都需要的）
3. 共享的工具函数或服务

## 输出格式
```json
{{
  "analysis": {{
    "shared_entities": [
      {{"name": "实体名", "used_by": ["REQ-001", "REQ-002"], "fields": ["字段1", "字段2"]}}
    ],
    "shared_modules": [
      {{"name": "模块名", "type": "router|service|util", "used_by": ["REQ-001"], "description": "模块描述"}}
    ]
  }},
  "skeleton_files": [
    {{
      "path": "文件路径（相对于项目根目录）",
      "description": "文件用途说明",
      "shared_by": ["REQ-001", "REQ-002"],
      "todo_sections": ["需要实现的功能1", "需要实现的功能2"]
    }}
  ],
  "file_ownership": {{
    "REQ-001": ["文件路径1", "文件路径2"],
    "REQ-002": ["文件路径3"]
  }},
  "reasoning": "为什么这样划分骨架"
}}
```

## 重要原则
1. 只识别被多个需求共享的骨架文件
2. 每个需求独有的文件不需要预定义骨架
3. 不要生成具体代码内容（template字段），只描述文件用途和需要实现的功能
4. todo_sections 列出每个需求需要在该文件中实现的功能点
5. 不要假设特定的编程语言或框架，根据需求推断
"""


async def analyze_skeleton_requirements(
    llm: Any,
    requirements: list[dict[str, Any]],
    architecture_contract: dict[str, Any] | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Use LLM to analyze requirements and determine skeleton structure.

    Args:
        llm: LLM model instance
        requirements: List of requirement dicts
        architecture_contract: Architecture contract (optional)
        verbose: Whether to print debug info

    Returns:
        dict: Skeleton analysis result, or None if failed
    """
    from ._llm_utils import call_llm_json
    from ._observability import get_logger

    logger = get_logger()

    # Build requirements summary
    req_summary = []
    for req in requirements:
        req_summary.append({
            "id": req.get("id", ""),
            "title": req.get("title", ""),
            "type": req.get("type", ""),
            "description": req.get("description", "")[:500],
        })

    # Format architecture contract
    contract_str = "无"
    if architecture_contract:
        contract_str = json.dumps(architecture_contract, ensure_ascii=False, indent=2)

    prompt = SKELETON_ANALYSIS_PROMPT.format(
        requirements_json=json.dumps(req_summary, ensure_ascii=False, indent=2),
        architecture_contract=contract_str,
    )

    try:
        result, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是软件架构师，善于分析需求并设计代码骨架结构。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            label="skeleton_analysis",
            verbose=verbose,
        )
        return result
    except Exception as exc:
        if verbose:
            logger.debug(f"[SKELETON] Failed to analyze skeleton: {exc}")
        return None


async def analyze_unified_skeleton(
    llm: Any,
    requirements: list[dict[str, Any]],
    architecture_contract: dict[str, Any] | None = None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Analyze requirements to identify shared skeleton files.

    NOTE: This function only analyzes and returns metadata.
    Actual file creation is done by Claude Code in the container.

    This function:
    1. Uses LLM to analyze all requirements
    2. Identifies shared entities and modules
    3. Returns skeleton file metadata for Claude Code to create

    Args:
        llm: LLM model instance
        requirements: List of all requirement dicts
        architecture_contract: Architecture contract (optional)
        verbose: Whether to print debug info

    Returns:
        dict: {
            "skeleton_files": list of file metadata (path, description, shared_by, todo_sections),
            "file_ownership": mapping of req_id to owned files,
            "shared_files": list of files shared by multiple requirements,
            "analysis": shared entities and modules analysis
        }
    """
    from ._observability import get_logger

    logger = get_logger()

    # Skip if only one requirement
    if len(requirements) <= 1:
        if verbose:
            logger.debug("[SKELETON] Skipped: only one requirement")
        return {"skeleton_files": [], "file_ownership": {}, "shared_files": [], "analysis": {}}

    # Analyze skeleton requirements (metadata only, no content generation)
    if verbose:
        logger.info("[SKELETON] 分析需求，识别共享骨架...")

    analysis = await analyze_skeleton_requirements(
        llm, requirements, architecture_contract, verbose=verbose
    )

    if not analysis or not analysis.get("skeleton_files"):
        if verbose:
            logger.debug("[SKELETON] No shared skeleton needed")
        return {"skeleton_files": [], "file_ownership": {}, "shared_files": [], "analysis": {}}

    # Extract skeleton file metadata (no file writing here)
    skeleton_files = analysis.get("skeleton_files", [])
    file_ownership = analysis.get("file_ownership", {})
    shared_files: list[str] = []

    # Collect shared files
    for file_spec in skeleton_files:
        file_path = file_spec.get("path", "")
        shared_by = file_spec.get("shared_by", [])
        if file_path and len(shared_by) > 1:
            shared_files.append(file_path)

    result = {
        "skeleton_files": skeleton_files,  # Metadata only: path, description, shared_by, todo_sections
        "file_ownership": file_ownership,
        "shared_files": shared_files,
        "analysis": analysis.get("analysis", {}),
    }

    if verbose:
        logger.info(f"[SKELETON] 识别了 {len(skeleton_files)} 个骨架文件, {len(shared_files)} 个共享文件")
        for sf in skeleton_files:
            logger.debug(f"[SKELETON]   - {sf.get('path')}: {sf.get('description', '')[:50]}")

    return result


# Keep old function name as alias for compatibility
async def generate_unified_skeleton(
    llm: Any,
    requirements: list[dict[str, Any]],
    workspace_dir: "Any",  # Path - now ignored
    architecture_contract: dict[str, Any] | None = None,
    runtime_workspace: "Any | None" = None,  # RuntimeWorkspace - now ignored
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Deprecated: Use analyze_unified_skeleton instead.

    This function now only analyzes and returns metadata.
    workspace_dir and runtime_workspace parameters are ignored.
    """
    return await analyze_unified_skeleton(
        llm, requirements, architecture_contract, verbose=verbose
    )


def get_owned_files(
    file_ownership: dict[str, list[str]],
    requirement_id: str,
) -> list[str]:
    """Get list of files owned by a specific requirement.

    Args:
        file_ownership: Mapping of requirement ID to owned file paths
        requirement_id: The requirement ID to look up

    Returns:
        list: File paths owned by this requirement
    """
    return file_ownership.get(requirement_id, [])


def is_shared_file(
    shared_files: list[str],
    file_path: str,
) -> bool:
    """Check if a file is shared by multiple requirements.

    Args:
        shared_files: List of shared file paths
        file_path: File path to check

    Returns:
        bool: True if the file is shared
    """
    # Normalize paths for comparison
    normalized = file_path.lstrip("./")
    return normalized in shared_files or file_path in shared_files


__all__ = [
    "extract_file_structure",
    "find_similar_text",
    "validate_python_syntax",
    "apply_edits",
    "design_requirement",
    "implement_requirement",
    "implement_requirement_autonomous",
    "generate_single_file",
    "sort_files_by_dependency",
    "run_scaffold_commands",
    "stepwise_generate_files",
    "analyze_skeleton_requirements",
    "generate_unified_skeleton",
    "get_owned_files",
    "is_shared_file",
    # Claude Code configuration
    "USE_CLAUDE_CODE",
    "CLAUDE_CODE_MODE",
]
