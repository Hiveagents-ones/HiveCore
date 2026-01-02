# -*- coding: utf-8 -*-
"""Multi-agent collaborative execution with git worktree isolation.

This module implements parallel execution of multiple agents on the same task,
with each agent working in their own git worktree and PRs merged by size.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Awaitable

from ..message import Msg
from ..pipeline import MsgHub
from .._logging import logger
import time as _time_module

if TYPE_CHECKING:
    from .execution import AgentOutput, ExecutionContext


def _log_collaborative(
    msg: str,
    *,
    level: str = "info",
    prefix: str = "[Collaborative]",
) -> None:
    """Log collaborative execution message with real-time output.

    Args:
        msg: Message to log.
        level: Log level (info, warning, error).
        prefix: Log prefix.
    """
    timestamp = _time_module.strftime("%H:%M:%S")
    formatted = f"{timestamp} | {prefix} {msg}"
    print(formatted, flush=True)

    if level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.info(msg)


class CollaborativeExecutor:
    """Executes tasks with multiple agents working in parallel.

    This executor:
    1. Creates isolated git worktrees for each agent
    2. Runs agents in parallel with MsgHub for communication
    3. Collects PR stats and sorts by size (largest first)
    4. Merges PRs sequentially, handling conflicts via agent resolution
    """

    def __init__(
        self,
        workspace: Any,
        invoke_agent_async: Callable[
            [str, str, "ExecutionContext", str],
            Coroutine[Any, Any, "AgentOutput | None"],
        ],
        get_runtime_agents: Callable[[], dict[str, Any]],
    ) -> None:
        """Initialize the collaborative executor.

        Args:
            workspace: RuntimeWorkspaceWithPR instance with git worktree support.
            invoke_agent_async: Async function to invoke an agent.
            get_runtime_agents: Function to get registered runtime agents.
        """
        self.workspace = workspace
        self._invoke_agent_async = invoke_agent_async
        self._get_runtime_agents = get_runtime_agents

    async def execute(
        self,
        node: Any,
        context: "ExecutionContext",
    ) -> list["AgentOutput"]:
        """Execute a task with multiple agents collaborating in parallel.

        This method implements the multi-agent collaboration pattern:
        1. Create git worktree for each agent
        2. Execute all agents in parallel with MsgHub communication
        3. Collect PRs and sort by size (largest first)
        4. Merge PRs sequentially, handling conflicts

        Args:
            node: The task node with multiple assigned agents.
            context: Execution context.

        Returns:
            List of AgentOutput from all agents.
        """
        from agentscope.scripts._runtime_workspace import AgentPRStats

        node_id = node.node_id
        agent_ids = node.assigned_agent_ids
        outputs: list["AgentOutput"] = []

        _log_collaborative(
            f"[{node_id}] 🤝 开始协作执行: {len(agent_ids)} 个 Agent",
        )

        # Step 1: Initialize git repo if needed
        await self.workspace.init_git_repo()

        # Step 2: Create worktree for each agent
        for agent_id in agent_ids:
            success = await self.workspace.create_agent_worktree(agent_id)
            if not success:
                _log_collaborative(
                    f"[{node_id}] ⚠️ 无法为 {agent_id} 创建 worktree",
                    level="warning",
                )

        # Step 3: Get agent instances
        runtime_agents = self._get_runtime_agents()
        agent_instances = []
        for agent_id in agent_ids:
            if agent_id in runtime_agents:
                agent_instances.append(runtime_agents[agent_id])

        if not agent_instances:
            _log_collaborative(
                f"[{node_id}] ❌ 无可用 Agent 实例",
                level="error",
            )
            return outputs

        # Step 4: Execute agents in parallel with MsgHub
        outputs = await self._execute_agents_parallel(
            node_id=node_id,
            agent_ids=agent_ids,
            agent_instances=agent_instances,
            context=context,
        )

        # Step 5: Commit changes for each agent
        for agent_id in agent_ids:
            await self.workspace.commit_agent_changes(
                agent_id,
                f"{node_id}: {agent_id} changes",
            )

        # Step 6: Collect PR stats and merge
        await self._collect_and_merge_prs(
            node_id=node_id,
            agent_ids=agent_ids,
            context=context,
        )

        # Step 7: Track worktrees for deferred cleanup
        # NOTE: We no longer cleanup worktrees here because agents may be
        # reused in subsequent rounds. Instead, worktrees are cleaned up
        # at the end of each Round in ExecutionLoop.
        # See: ExecutionLoop._cleanup_round_worktrees()
        if not hasattr(self.workspace, "_active_agent_worktrees"):
            self.workspace._active_agent_worktrees = set()
        for agent_id in agent_ids:
            self.workspace._active_agent_worktrees.add(agent_id)

        _log_collaborative(
            f"[{node_id}] ✅ 协作执行完成",
        )

        return outputs

    async def _execute_agents_parallel(
        self,
        node_id: str,
        agent_ids: list[str],
        agent_instances: list[Any],
        context: "ExecutionContext",
    ) -> list["AgentOutput"]:
        """Execute agents sequentially with correct worktree directories.

        Note: Changed from parallel to sequential execution because
        Claude Code uses a global container_workspace which would conflict
        when agents run in parallel with different worktree directories.

        Args:
            node_id: Task identifier.
            agent_ids: List of agent IDs.
            agent_instances: List of agent instances.
            context: Execution context.

        Returns:
            List of successful AgentOutput.
        """
        outputs: list["AgentOutput"] = []

        announcement = Msg(
            name="Coordinator",
            role="system",
            content=f"## 协作任务: {node_id}\n\n"
            f"需求: {context.intent_utterance}\n\n"
            f"参与 Agent: {', '.join(agent_ids)}\n\n"
            f"请各自完成自己的部分，并通过消息沟通协调。\n"
            f"如需其他 Agent 的信息，请发送 [需要协助: @角色名] 消息。",
        )

        async with MsgHub(
            participants=agent_instances,
            announcement=announcement,
            enable_auto_broadcast=True,
        ):
            # Execute agents sequentially to avoid container_workspace conflict
            _log_collaborative(
                f"[{node_id}] ⚡ 顺序执行 {len(agent_ids)} 个 Agent (worktree 隔离)...",
            )

            for agent_id in agent_ids:
                agent_dir = await self.workspace.get_agent_working_dir(agent_id)

                # Set container workspace to agent's worktree directory
                try:
                    from agentscope.scripts._claude_code import set_container_context
                    container_id = getattr(self.workspace, "container_id", None)
                    if container_id:
                        set_container_context(container_id, agent_dir)
                        _log_collaborative(
                            f"[{node_id}] 📁 {agent_id} 工作目录: {agent_dir}",
                        )
                except ImportError:
                    pass

                task_prompt = (
                    f"## 协作任务\n\n"
                    f"**任务ID**: {node_id}\n"
                    f"**需求**: {context.intent_utterance}\n"
                    f"**你的角色**: {agent_id}\n"
                    f"**工作目录**: {agent_dir}\n\n"
                    f"**重要**: 你必须在 `{agent_dir}` 目录下创建和修改文件。\n"
                    f"所有文件操作都必须使用这个目录作为根目录。\n\n"
                    f"如果需要其他 Agent 的信息（如接口定义），请通过消息询问。"
                )

                try:
                    result = await self._invoke_agent_async(
                        agent_id,
                        task_prompt,
                        context=context,
                        node_id=node_id,
                    )
                    if result:
                        outputs.append(result)
                        context.add_output(result)
                        _log_collaborative(
                            f"[{node_id}] ✓ {agent_id} 执行完成",
                        )
                except Exception as e:
                    _log_collaborative(
                        f"[{node_id}] ❌ {agent_id} 执行异常: {e}",
                        level="error",
                    )

        return outputs

    async def _collect_and_merge_prs(
        self,
        node_id: str,
        agent_ids: list[str],
        context: "ExecutionContext",
        validate_fn: Callable[[str, str], Coroutine[Any, Any, bool]] | None = None,
    ) -> None:
        """Collect PR stats and cherry-pick to delivery in order (largest first).

        This implements the cherry-pick validation flow:
        1. Cherry-pick each agent's commit to delivery
        2. If conflict, sync delivery to worktree and let agent re-implement
        3. Validate in delivery directory
        4. If validation fails, reset delivery and let agent fix

        Args:
            node_id: Task identifier.
            agent_ids: List of agent IDs.
            context: Execution context.
            validate_fn: Optional validation function (node_id, agent_id) -> passed.
        """
        from agentscope.scripts._runtime_workspace import AgentPRStats

        # Collect PR stats
        pr_stats: list[AgentPRStats] = []
        for agent_id in agent_ids:
            stats = await self.workspace.get_agent_pr_stats(agent_id)
            pr_stats.append(stats)
            _log_collaborative(
                f"[{node_id}] 📊 {agent_id} PR: +{stats.additions}/-{stats.deletions} ({stats.files_changed} files)",
            )

        # Sort by total changes (largest first)
        pr_stats.sort(key=lambda s: s.total_changes, reverse=True)

        _log_collaborative(
            f"[{node_id}] 📋 Cherry-pick 顺序: {[s.agent_id for s in pr_stats]}",
        )

        # Cherry-pick and validate in order (largest first)
        for idx, stats in enumerate(pr_stats):
            agent_id = stats.agent_id
            max_retries = 2

            for retry in range(max_retries + 1):
                # Save delivery HEAD for potential rollback
                delivery_head = await self.workspace.get_delivery_head()

                # Cherry-pick to delivery
                _log_collaborative(
                    f"[{node_id}] 🍒 Cherry-pick {agent_id} 到 delivery...",
                )
                pick_result = await self.workspace.cherry_pick_to_delivery(agent_id)

                if not pick_result.success:
                    if pick_result.conflicts:
                        # Conflict - sync delivery to worktree and let agent re-implement
                        _log_collaborative(
                            f"[{node_id}] ⚠️ {agent_id} cherry-pick 冲突: {pick_result.conflicts}",
                            level="warning",
                        )

                        # Sync delivery state to agent's worktree
                        synced = await self.workspace.sync_delivery_to_agent_worktree(
                            agent_id
                        )
                        if not synced:
                            _log_collaborative(
                                f"[{node_id}] ❌ {agent_id} sync 失败",
                                level="error",
                            )
                            break

                        # Let agent re-implement based on new state
                        resolved = await self._reimpl_after_conflict(
                            agent_id=agent_id,
                            node_id=node_id,
                            conflicts=pick_result.conflicts,
                            context=context,
                        )

                        if resolved:
                            # Agent made new commit, retry cherry-pick
                            continue
                        else:
                            _log_collaborative(
                                f"[{node_id}] ❌ {agent_id} 重新实现失败",
                                level="error",
                            )
                            break
                    else:
                        _log_collaborative(
                            f"[{node_id}] ❌ {agent_id} cherry-pick 失败: {pick_result.message}",
                            level="error",
                        )
                        break

                # Cherry-pick succeeded, now validate in delivery
                _log_collaborative(
                    f"[{node_id}] 🔍 在 delivery 目录验收 {agent_id}...",
                )

                if validate_fn:
                    passed = await validate_fn(node_id, agent_id)
                else:
                    # No validation function, assume passed
                    passed = True

                if passed:
                    _log_collaborative(
                        f"[{node_id}] ✓ {agent_id} 验收通过",
                    )
                    break
                else:
                    # Validation failed - reset delivery and let agent fix
                    _log_collaborative(
                        f"[{node_id}] ⚠️ {agent_id} 验收失败 (尝试 {retry + 1}/{max_retries + 1})",
                        level="warning",
                    )

                    if retry < max_retries:
                        # Reset delivery and sync to agent if in fallback mode
                        reset_ok, sync_performed = (
                            await self.workspace.reset_delivery_for_retry(
                                agent_id, delivery_head
                            )
                        )
                        if sync_performed:
                            _log_collaborative(
                                f"[{node_id}] 📥 已同步 delivery 状态到 {agent_id} (fallback mode)",
                            )

                        # Let agent fix the issue
                        fixed = await self._fix_validation_failure(
                            agent_id=agent_id,
                            node_id=node_id,
                            context=context,
                            state_reset=sync_performed,
                        )

                        if not fixed:
                            _log_collaborative(
                                f"[{node_id}] ❌ {agent_id} 修复失败",
                                level="error",
                            )
                            break
                    else:
                        _log_collaborative(
                            f"[{node_id}] ❌ {agent_id} 验收失败 (已达最大重试)",
                            level="error",
                        )

    async def _reimpl_after_conflict(
        self,
        agent_id: str,
        node_id: str,
        conflicts: list[str],
        context: "ExecutionContext",
    ) -> bool:
        """Let agent re-implement after cherry-pick conflict.

        The agent's worktree has been synced with delivery state.
        Agent should re-implement their changes on top of this state.

        Args:
            agent_id: The agent to re-implement.
            node_id: Task identifier.
            conflicts: List of conflicting file paths.
            context: Execution context.

        Returns:
            True if agent made a new commit.
        """
        _log_collaborative(
            f"[{node_id}] 🔧 让 {agent_id} 基于最新状态重新实现...",
        )

        prompt = f"""## 需要重新实现

你的修改与其他 Agent 的修改冲突。你的工作目录已更新为包含其他 Agent 修改的最新状态。

冲突的文件：
{chr(10).join(f'- {f}' for f in conflicts)}

**你需要做的：**
1. 查看当前工作目录中的最新代码（已包含其他 Agent 的修改）
2. 重新实现你的修改，确保与现有代码兼容
3. 确保功能完整性

**注意：** 你不需要处理冲突标记，因为你的工作目录已经是干净的最新状态。
你只需要在此基础上添加你的实现。
"""

        output = await self._invoke_agent_async(
            agent_id,
            prompt,
            context=context,
            node_id=node_id,
        )

        if output:
            context.add_output(output)

        # Commit the new changes
        committed = await self.workspace.commit_agent_changes(
            agent_id,
            f"{node_id}: {agent_id} re-implementation after conflict",
        )

        return committed

    async def _fix_validation_failure(
        self,
        agent_id: str,
        node_id: str,
        context: "ExecutionContext",
        state_reset: bool = False,
    ) -> bool:
        """Let agent fix validation failure.

        Args:
            agent_id: The agent to fix.
            node_id: Task identifier.
            context: Execution context.
            state_reset: Whether the agent's working directory was reset
                (fallback mode only).

        Returns:
            True if agent made a fix commit.
        """
        _log_collaborative(
            f"[{node_id}] 🔧 让 {agent_id} 修复验收失败...",
        )

        if state_reset:
            prompt = """## ⚠️ 状态重置通知

你之前的修改验证失败，工作目录已被重置到初始状态。
**请基于当前干净的代码状态重新实现功能。**

---

## 验收失败，需要修复

你的代码在验收阶段未通过。请检查并修复问题：

1. 检查代码是否有语法错误
2. 检查依赖是否完整（如 requirements.txt）
3. 检查导入是否正确
4. 运行测试或验证命令确认修复有效

请修复问题并确保代码可以正常运行。
"""
        else:
            prompt = """## 验收失败，需要修复

你的代码在验收阶段未通过。请检查并修复问题：

1. 检查代码是否有语法错误
2. 检查依赖是否完整（如 requirements.txt）
3. 检查导入是否正确
4. 运行测试或验证命令确认修复有效

请修复问题并确保代码可以正常运行。
"""

        output = await self._invoke_agent_async(
            agent_id,
            prompt,
            context=context,
            node_id=node_id,
        )

        if output:
            context.add_output(output)

        # Commit the fix
        committed = await self.workspace.commit_agent_changes(
            agent_id,
            f"{node_id}: {agent_id} validation fix",
        )

        return committed

    async def _sync_and_resolve_conflicts(
        self,
        node_id: str,
        agent_id: str,
        context: "ExecutionContext",
    ) -> bool:
        """Sync agent branch from main and resolve conflicts if any.

        Args:
            node_id: Task identifier.
            agent_id: Agent to sync.
            context: Execution context.

        Returns:
            True if sync successful (with or without conflict resolution).
        """
        _log_collaborative(
            f"[{node_id}] 🔄 {agent_id} 同步 main 分支...",
        )
        sync_result = await self.workspace.update_agent_from_main(agent_id)

        if sync_result.success:
            return True

        if not sync_result.conflicts:
            return True

        # Has conflicts - let agent resolve
        _log_collaborative(
            f"[{node_id}] ⚠️ {agent_id} 有冲突: {sync_result.conflicts}",
            level="warning",
        )

        # Get conflict details
        conflict_details = await self.workspace.get_conflict_details(agent_id)

        # Let agent resolve conflicts
        resolved = await self._resolve_agent_conflicts(
            agent_id=agent_id,
            node_id=node_id,
            conflicts=sync_result.conflicts,
            conflict_details=conflict_details,
            context=context,
        )

        if not resolved:
            _log_collaborative(
                f"[{node_id}] ❌ {agent_id} 冲突解决失败",
                level="error",
            )

        return resolved

    async def _resolve_agent_conflicts(
        self,
        agent_id: str,
        node_id: str,
        conflicts: list[str],
        conflict_details: dict[str, str],
        context: "ExecutionContext",
    ) -> bool:
        """Let an agent resolve merge conflicts.

        Args:
            agent_id: The agent to resolve conflicts.
            node_id: Task identifier.
            conflicts: List of conflicting file paths.
            conflict_details: Map of filename to content with conflict markers.
            context: Execution context.

        Returns:
            True if conflicts were resolved successfully.
        """
        _log_collaborative(
            f"[{node_id}] 🔧 让 {agent_id} 解决冲突...",
        )

        # Build conflict resolution prompt
        conflict_info = []
        for filename, content in conflict_details.items():
            # Extract just the conflicting section for context
            conflict_info.append(f"### {filename}\n```\n{content[:2000]}\n```")

        prompt = f"""## 合并冲突需要处理

你的分支在合并 main 时发现以下文件有冲突：

{chr(10).join(f'- {f}' for f in conflicts)}

### 冲突标记说明

文件中包含如下标记：
```
<<<<<<< HEAD
你的修改
=======
其他 Agent 的修改（已合并到 main）
>>>>>>> main
```

### 冲突文件内容

{chr(10).join(conflict_info)}

### 你需要做的

1. 编辑冲突文件，合并双方的修改
2. 删除所有 `<<<<<<<`、`=======`、`>>>>>>>` 标记
3. 确保代码逻辑正确，功能完整
4. 保存文件

**注意**：你应该保留双方的有效修改，而不是简单地选择一方。
"""

        # Let agent resolve
        output = await self._invoke_agent_async(
            agent_id,
            prompt,
            context=context,
            node_id=node_id,
        )

        if output:
            context.add_output(output)

        # Check if conflicts are resolved
        resolved = await self.workspace.mark_conflicts_resolved(agent_id)

        if resolved:
            _log_collaborative(
                f"[{node_id}] ✓ {agent_id} 冲突解决成功",
            )
        else:
            _log_collaborative(
                f"[{node_id}] ❌ {agent_id} 仍有未解决的冲突标记",
                level="error",
            )

        return resolved


def get_workspace_for_collaborative(
    orchestrator: Any,
    workspace_dir: str,
) -> Any | None:
    """Get RuntimeWorkspaceWithPR instance for collaborative execution.

    Collaborative execution requires a workspace with git worktree support.
    This function tries to find an existing workspace or create one.

    Args:
        orchestrator: The orchestrator instance.
        workspace_dir: Base workspace directory.

    Returns:
        RuntimeWorkspaceWithPR instance or None if not available.
    """
    # Try to get workspace from orchestrator
    workspace = getattr(orchestrator, "_workspace", None)

    if workspace is not None:
        # Check if it's a RuntimeWorkspaceWithPR with git support
        if hasattr(workspace, "init_git_repo") and hasattr(
            workspace, "create_agent_worktree"
        ):
            return workspace

    # Try to create one if we have the necessary info
    try:
        from agentscope.scripts._runtime_workspace import RuntimeWorkspaceWithPR

        # Check if there's a container_id available
        container_id = getattr(orchestrator, "_container_id", None)
        if container_id:
            workspace = RuntimeWorkspaceWithPR(
                base_workspace_dir=workspace_dir,
                enable_pr_mode=True,
            )
            workspace.container_id = container_id
            return workspace
    except ImportError:
        pass

    return None
