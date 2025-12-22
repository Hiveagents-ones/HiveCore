# -*- coding: utf-8 -*-
"""Agent-based execution using ReActAgent + Toolkit for file operations.

This module provides Claude Code style file editing capabilities using
the DeveloperReActAgent with file operation tools.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.model import ChatModelBase
    from agentscope.formatter import FormatterBase
    from ._sandbox import RuntimeWorkspace


async def create_developer_agent(
    llm: "ChatModelBase",
    formatter: "FormatterBase",
    workspace_dir: Path,
    *,
    verbose: bool = False,
) -> Any:
    """Create a DeveloperReActAgent with file operation tools.

    Args:
        llm: LLM model instance
        formatter: Message formatter
        workspace_dir: Working directory for file operations
        verbose: Whether to print debug info

    Returns:
        DeveloperReActAgent instance with file tools
    """
    from agentscope.ones import DeveloperReActAgent
    from agentscope.scripts.hive_toolkit import HiveToolkitManager

    # Create toolkit with file operation tools
    toolkit_manager = HiveToolkitManager(llm=llm)
    toolkit = toolkit_manager.build_toolkit(
        tools_filter={"view_text_file", "write_text_file", "insert_text_file"}
    )

    # Update tool notes with workspace directory
    if "file_ops" in toolkit.groups:
        toolkit.groups["file_ops"].notes = f"""【文件操作工具使用指南】
工作目录: {workspace_dir}

- view_text_file: 查看文件内容，支持指定行号范围 [start, end]
- write_text_file: 创建新文件或覆盖现有文件，支持部分替换（指定 ranges=[start, end] 只替换指定行）
- insert_text_file: 在指定行号处插入新内容

【编辑最佳实践】
1. 修改代码前，先用 view_text_file 查看相关代码段
2. 使用 write_text_file 的 ranges 参数进行精确替换，避免破坏其他代码
3. 确保替换内容包含完整的代码单元（完整的函数、类、语句等）
4. 编辑后再次使用 view_text_file 验证修改结果
"""

    agent = DeveloperReActAgent(
        name="Developer",
        model=llm,
        formatter=formatter,
        toolkit=toolkit,
        max_iters=15,  # Allow more iterations for complex edits
    )

    if verbose:
        from ._observability import get_logger
        logger = get_logger()
        logger.debug(f"[AGENT] DeveloperReActAgent 已创建，工作目录: {workspace_dir}")
        logger.debug(f"[AGENT] 可用工具: {[t['function']['name'] for t in toolkit.get_json_schemas()]}")

    return agent


async def execute_with_agent(
    llm: Any,
    formatter: Any,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    workspace_dir: Path,
    feedback: str = "",
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute requirement implementation using ReActAgent with file tools.

    Args:
        llm: LLM model instance
        formatter: Message formatter
        requirement: Requirement dict
        blueprint: Blueprint dict
        workspace_dir: Working directory
        feedback: QA feedback from previous round
        verbose: Whether to print debug info

    Returns:
        dict: Execution result with summary and file changes
    """
    from agentscope.message import Msg

    agent = await create_developer_agent(
        llm, formatter, workspace_dir, verbose=verbose
    )

    # Build the task prompt
    files_plan = blueprint.get("files_plan", [])
    files_desc = "\n".join(
        f"- {f['path']}: {f.get('description', '')} (action: {f.get('action', 'create')})"
        for f in files_plan
    )

    task_prompt = f"""请根据以下需求和设计方案，使用文件操作工具实现代码。

## 需求
{json.dumps(requirement, ensure_ascii=False, indent=2)}

## 设计方案 (Blueprint)
推荐技术栈: {blueprint.get('recommended_stack', '')}
交付物描述: {blueprint.get('deliverable_pitch', '')}

## 文件计划
{files_desc}

## 工作目录
{workspace_dir}

"""

    if feedback:
        task_prompt += f"""
## 上一轮 QA 反馈
{feedback}

请根据反馈修复问题。
"""

    task_prompt += """
## 任务要求
1. 按照文件计划创建/修改文件
2. 确保代码完整可运行
3. 遵循编辑最佳实践，避免语法错误
4. 完成后用 generate_response 工具返回实现总结

开始工作吧！
"""

    # Execute agent
    from ._observability import get_logger
    get_logger().info(f"[AGENT] 开始执行需求: {requirement.get('id', 'unknown')}")

    try:
        response_msg = await agent.reply(
            Msg(name="user", role="user", content=task_prompt)
        )
        response_text = response_msg.get_text_content() or ""

        # Collect created/modified files
        written_files = []
        for fpath in workspace_dir.rglob("*"):
            if fpath.is_file() and not fpath.name.startswith("."):
                rel_path = str(fpath.relative_to(workspace_dir))
                if "node_modules" not in rel_path and "__pycache__" not in rel_path:
                    written_files.append(rel_path)

        return {
            "success": True,
            "summary": response_text,
            "files": [{"path": p} for p in written_files],
            "project_type": blueprint.get("artifact_type", "fullstack"),
        }

    except Exception as e:
        from ._observability import get_logger
        get_logger().error(f"[AGENT] 执行失败: {e}")
        return {
            "success": False,
            "summary": f"Agent 执行失败: {e}",
            "files": [],
            "error": str(e),
        }


async def edit_file_with_agent(
    llm: Any,
    formatter: Any,
    file_path: Path,
    edit_instruction: str,
    workspace_dir: Path,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Edit a specific file using ReActAgent.

    Args:
        llm: LLM model instance
        formatter: Message formatter
        file_path: Path to the file to edit
        edit_instruction: Description of the edit to make
        workspace_dir: Working directory
        verbose: Whether to print debug info

    Returns:
        dict: Edit result
    """
    from agentscope.message import Msg

    agent = await create_developer_agent(
        llm, formatter, workspace_dir, verbose=verbose
    )

    task_prompt = f"""请编辑文件: {file_path}

## 编辑要求
{edit_instruction}

## 工作流程
1. 先用 view_text_file 查看文件当前内容
2. 分析需要修改的位置
3. 使用 write_text_file 的 ranges 参数进行精确编辑
4. 用 view_text_file 验证修改结果
5. 用 generate_response 返回修改总结
"""

    try:
        response_msg = await agent.reply(
            Msg(name="user", role="user", content=task_prompt)
        )
        response_text = response_msg.get_text_content() or ""

        return {
            "success": True,
            "summary": response_text,
            "file_path": str(file_path),
        }

    except Exception as e:
        return {
            "success": False,
            "summary": f"编辑失败: {e}",
            "file_path": str(file_path),
            "error": str(e),
        }


__all__ = [
    "create_developer_agent",
    "execute_with_agent",
    "edit_file_with_agent",
]
