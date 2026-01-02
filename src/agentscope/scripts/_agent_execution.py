# -*- coding: utf-8 -*-
"""Agent-based execution using ReActAgent + Claude Code as limbs.

Architecture Model:
- Agent = Brain (大脑): High-level decision making
- Claude Code = Limbs (四肢): Code execution via claude_code_edit tool
- MCP/Toolkit = Tools (工具): Resources used by Claude Code

This module provides Agent creation with Claude Code as limbs.
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
    """Create a DeveloperReActAgent with Claude Code as limbs.

    The agent uses claude_code_edit tool as its "limbs" to execute
    code-related tasks, while the agent itself acts as the "brain"
    for decision making.

    Args:
        llm: LLM model instance
        formatter: Message formatter
        workspace_dir: Working directory for file operations
        verbose: Whether to print debug info

    Returns:
        DeveloperReActAgent instance with Claude Code limbs
    """
    from agentscope.ones import DeveloperReActAgent
    from agentscope.scripts.hive_toolkit import HiveToolkitManager
    from agentscope.scripts._claude_code import get_container_context

    # Create toolkit with Claude Code tools (the agent's "limbs")
    toolkit_manager = HiveToolkitManager(llm=llm)
    toolkit = toolkit_manager.build_toolkit(
        tools_filter={"claude_code_edit", "claude_code_chat", "task_board_write"}
    )

    # Determine effective workspace path for prompts
    # In container mode, use the container's workspace path, not the host path
    container_id, container_workspace = get_container_context()
    if container_id:
        # Running in container mode - use container workspace path
        effective_workspace = container_workspace  # e.g., "/workspace"
    else:
        # Running locally - use the provided workspace_dir
        effective_workspace = str(workspace_dir)

    # Update tool notes with workspace directory
    if "claude_code" in toolkit.groups:
        toolkit.groups["claude_code"].notes = f"""【Claude Code 四肢使用指南】
工作目录: {effective_workspace}

你拥有 claude_code_edit 工具作为"四肢"，它可以：
- 探索代码库，了解现有结构
- 创建和修改文件
- 编写具体代码实现
- 执行命令和测试

使用方法：
claude_code_edit(prompt="你的指令", workspace="{effective_workspace}")

【重要】所有文件操作都基于工作目录 {effective_workspace}，使用相对路径如：
- frontend/src/components/MyComponent.vue
- frontend/src/views/HomeView.vue
- backend/app/main.py
- backend/app/routers/xxx.py

记住：你是"大脑"，负责分析和决策；claude_code_edit 是你的"四肢"，负责执行。

【任务板工具】
你还可以使用 task_board_write 工具更新任务状态，让用户了解当前进度：
task_board_write(todos=[{{"content": "任务描述", "status": "in_progress", "activeForm": "正在执行..."}}])
状态值: pending（待办）、in_progress（进行中）、completed（已完成）
"""

    agent = DeveloperReActAgent(
        name="Developer",
        model=llm,
        formatter=formatter,
        toolkit=toolkit,
        max_iters=10,  # Allow iterations for complex tasks
    )

    if verbose:
        from ._observability import get_logger
        logger = get_logger()
        logger.debug(f"[AGENT] DeveloperReActAgent 已创建，工作目录: {workspace_dir}")
        logger.debug(f"[AGENT] 可用四肢: {[t['function']['name'] for t in toolkit.get_json_schemas()]}")

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
    runtime_workspace: "RuntimeWorkspace | None" = None,
    skeleton_context: dict[str, Any] | None = None,
    is_first_requirement: bool = False,
) -> dict[str, Any]:
    """Execute requirement using Agent (brain) + Claude Code (limbs).

    The agent acts as the "brain" to analyze the task and make decisions,
    then uses claude_code_edit as its "limbs" to execute the actual coding.

    Args:
        llm: LLM model instance
        formatter: Message formatter
        requirement: Requirement dict
        blueprint: Blueprint dict
        workspace_dir: Working directory
        feedback: QA feedback from previous round
        verbose: Whether to print debug info
        runtime_workspace: Optional RuntimeWorkspace for container file operations
        skeleton_context: Skeleton analysis result with shared file metadata
        is_first_requirement: Whether this is the first requirement (should create skeleton)

    Returns:
        dict: Execution result with summary and file changes
    """
    from agentscope.message import Msg
    from agentscope.scripts._claude_code import get_container_context

    agent = await create_developer_agent(
        llm, formatter, workspace_dir, verbose=verbose
    )

    # Determine effective workspace path for prompts
    # In container mode, use the container's workspace path, not the host path
    container_id, container_workspace = get_container_context()
    if container_id:
        effective_workspace = container_workspace  # e.g., "/workspace"
    else:
        effective_workspace = str(workspace_dir)

    # Get files_plan from blueprint - these are the files Agent should create/modify
    files_plan = blueprint.get("files_plan", [])
    from ._observability import get_logger
    logger = get_logger()

    files_plan_text = ""
    if files_plan:
        files_list = [f"- {f.get('path', '')}" for f in files_plan if f.get("path")]
        if files_list:
            logger.debug(f"[Agent] 收到 files_plan: {files_list}")
            files_plan_text = f"""
## 📋 需要创建/修改的文件（必须严格遵循这些路径）
{chr(10).join(files_list)}

【重要】请严格按照上述路径创建文件，不要使用其他路径！
"""
    else:
        logger.warn(f"[Agent] Blueprint 中 files_plan 为空，Agent 可能无法确定正确的文件路径！")

    # Get existing directory structure from container or host
    existing_structure = ""
    if runtime_workspace and container_id:
        try:
            existing_files = runtime_workspace.list_files()
            # Extract unique directories
            dirs = set()
            for f in existing_files[:100]:  # Limit to first 100 files
                parts = f.split("/")
                for i in range(1, len(parts)):
                    dirs.add("/".join(parts[:i]))
            if dirs:
                # Show top-level directories
                top_dirs = sorted([d for d in dirs if "/" not in d])
                if top_dirs:
                    existing_structure = f"""
## 📁 已有目录结构
工作区已包含以下目录，请在这些目录下创建文件：
{chr(10).join(f"- {d}/" for d in top_dirs)}
"""
        except Exception:
            pass

    # Build the task prompt - guide the agent to use its "limbs"
    task_prompt = f"""# 任务：实现需求

## 需求信息
{json.dumps(requirement, ensure_ascii=False, indent=2)}

## 技术方案
推荐技术栈: {blueprint.get('recommended_stack', '')}
交付物描述: {blueprint.get('deliverable_pitch', '')}

## 工作目录
{effective_workspace}
{files_plan_text}{existing_structure}
【重要】所有文件都在工作目录 {effective_workspace} 下创建，使用相对路径如 backend/app/main.py 或 frontend/src/App.vue

"""

    if feedback:
        task_prompt += f"""
## ⚠️ 上一轮反馈（必须修复）
{feedback}

"""

    # Add scaffold and skeleton creation instructions for first requirement
    init_text = ""
    if is_first_requirement and skeleton_context:
        req_id = requirement.get("id", "")

        # Add scaffold files creation instructions
        scaffold_files = skeleton_context.get("scaffold_files", [])
        if scaffold_files:
            init_text = """
## 🏗️ 项目初始化（首次执行需创建）

这是第一个需求，你需要先创建项目基础结构。

### 后端初始化
创建以下后端基础文件：
"""
            backend_files = [sf for sf in scaffold_files if sf["path"].startswith("backend/")]
            frontend_files = [sf for sf in scaffold_files if sf["path"].startswith("frontend/")]

            for sf in backend_files:
                sf_path = sf["path"]
                sf_desc = sf.get("description", "")
                init_text += f"- `{sf_path}`: {sf_desc}\n"

            init_text += """
### 前端初始化
创建以下前端基础文件：
"""
            for sf in frontend_files:
                sf_path = sf["path"]
                sf_desc = sf.get("description", "")
                init_text += f"- `{sf_path}`: {sf_desc}\n"

            init_text += """
**重要**：创建这些基础文件时，使用标准的项目模板内容。
- 后端：使用 FastAPI + SQLAlchemy 标准结构
- 前端：使用 Vue 3 + TypeScript + Vite 标准结构

创建完基础文件后，运行 `cd /workspace/frontend && npm install` 安装前端依赖。

"""

        # Add skeleton files creation instructions
        skeleton_files = skeleton_context.get("skeleton_files", [])
        if skeleton_files:
            init_text += """
## 🦴 共享骨架文件

以下是跨多个需求共享的骨架文件，你需要先创建它们：
"""
            for sf in skeleton_files:
                sf_path = sf.get("path", "")
                sf_desc = sf.get("description", "")
                shared_by = sf.get("shared_by", [])
                todo_sections = sf.get("todo_sections", [])

                init_text += f"\n### {sf_path}\n"
                init_text += f"- 用途: {sf_desc}\n"
                init_text += f"- 共享于: {', '.join(shared_by)}\n"
                if todo_sections:
                    init_text += f"- TODO 部分:\n"
                    for todo in todo_sections:
                        init_text += f"  - {todo}\n"

            init_text += f"""
【重要】创建骨架文件时：
1. 只实现当前需求 ({req_id}) 相关的部分
2. 其他需求的部分用 `# TODO: [REQ-XXX] 描述` 占位符标记
3. 确保文件语法正确，可以正常导入
"""

    task_prompt += init_text

    task_prompt += """## 执行规范

【强制】你必须使用任务板分步执行：

1. **规划步骤**：开始前，使用 task_board_write 列出 2-5 个具体步骤
   ```
   task_board_write(todos=[
       {"content": "步骤1描述", "status": "pending", "activeForm": "执行步骤1"},
       {"content": "步骤2描述", "status": "pending", "activeForm": "执行步骤2"},
       ...
   ])
   ```

2. **开始执行**：每开始一个步骤，先更新状态为 in_progress
   ```
   task_board_write(todos=[
       {"content": "步骤1描述", "status": "in_progress", "activeForm": "执行步骤1"},
       ...
   ])
   ```

3. **完成步骤**：完成后立即标记为 completed，然后开始下一步
   ```
   task_board_write(todos=[
       {"content": "步骤1描述", "status": "completed", "activeForm": "执行步骤1"},
       {"content": "步骤2描述", "status": "in_progress", "activeForm": "执行步骤2"},
       ...
   ])
   ```

4. **原子操作**：每个步骤调用一次 claude_code_edit，禁止一次调用完成所有工作

【重要】
- 同一时间只有一个任务应该是 in_progress
- 每个 claude_code_edit 调用应该是独立的、可验证的
- 完成一步后再开始下一步

## 你的任务

作为"大脑"，你需要：
1. **分析需求**：理解要实现什么
2. **规划步骤**：使用 task_board_write 列出具体步骤
3. **分步执行**：按顺序执行每个步骤，更新任务板状态
4. **调用四肢**：每个步骤使用 claude_code_edit 让四肢执行

使用四肢的方法：
```
claude_code_edit(
    prompt="详细描述要做什么，使用相对路径如 backend/app/main.py",
    workspace="{effective_workspace}"
)
```

完成后用 generate_response 返回实现总结。开始吧！
""".replace("{effective_workspace}", effective_workspace)

    # Execute agent
    from ._observability import get_logger
    get_logger().info(f"[AGENT-BRAIN] 开始分析需求: {requirement.get('id', 'unknown')}")

    try:
        response_msg = await agent.reply(
            Msg(name="user", role="user", content=task_prompt)
        )
        response_text = response_msg.get_text_content() or ""

        # Collect created/modified files (by the limbs)
        # CRITICAL: In container mode, read files from container, not host!
        written_files = []
        if runtime_workspace and container_id:
            # Container mode: get files from container
            container_files = runtime_workspace.list_files()
            for rel_path in container_files:
                # Skip hidden files and common non-source directories
                if rel_path.startswith("."):
                    continue
                if any(skip in rel_path for skip in ["node_modules", "__pycache__", ".git", "dist", "venv"]):
                    continue
                written_files.append(rel_path)
            logger.debug(f"[Agent] 从容器收集到 {len(written_files)} 个源文件")
        else:
            # Local mode: read from host filesystem
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
            "mode": "agent_with_limbs",
        }

    except Exception as e:
        from ._observability import get_logger
        get_logger().error(f"[AGENT-BRAIN] 执行失败: {e}")
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
    """Edit a specific file using Agent (brain) + Claude Code (limbs).

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
    from agentscope.scripts._claude_code import get_container_context

    agent = await create_developer_agent(
        llm, formatter, workspace_dir, verbose=verbose
    )

    # Determine effective workspace path for prompts
    container_id, container_workspace = get_container_context()
    if container_id:
        effective_workspace = container_workspace
        # Convert file path to be relative to container workspace
        try:
            effective_file_path = str(file_path.relative_to(workspace_dir))
        except ValueError:
            effective_file_path = str(file_path)
    else:
        effective_workspace = str(workspace_dir)
        effective_file_path = str(file_path)

    task_prompt = f"""# 任务：编辑文件

## 目标文件
{effective_file_path}

## 编辑要求
{edit_instruction}

## 工作目录
{effective_workspace}

## 你的任务

作为"大脑"，你需要：
1. 分析编辑要求
2. 调用 claude_code_edit 让四肢执行编辑

使用四肢：
```
claude_code_edit(
    prompt="编辑 {effective_file_path}，{edit_instruction}",
    workspace="{effective_workspace}"
)
```

完成后用 generate_response 返回编辑总结。
""".replace("{effective_file_path}", effective_file_path).replace("{edit_instruction}", edit_instruction).replace("{effective_workspace}", effective_workspace)

    try:
        response_msg = await agent.reply(
            Msg(name="user", role="user", content=task_prompt)
        )
        response_text = response_msg.get_text_content() or ""

        return {
            "success": True,
            "summary": response_text,
            "file_path": str(file_path),
            "mode": "agent_with_limbs",
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
