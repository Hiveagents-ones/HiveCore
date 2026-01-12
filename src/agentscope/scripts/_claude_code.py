# -*- coding: utf-8 -*-
"""Claude Code integration for HiveCore.

This module provides a wrapper to invoke Claude Code CLI for code editing tasks,
using Zhipu GLM-4.7 as the backend model.

Supports two execution modes:
1. Local mode: Claude Code CLI runs on host machine
2. Container mode: Claude Code CLI runs inside Docker container via `docker exec`
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _filter_ecs_exec_output(output: str) -> str:
    """Filter out ECS Exec session manager messages from command output.

    Args:
        output: Raw output from ecs execute-command

    Returns:
        Filtered output with only the actual command result
    """
    lines = []
    for line in output.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip session manager messages
        if (stripped.startswith("The Session Manager plugin") or
            stripped.startswith("Starting session with") or
            stripped.startswith("Exiting session with") or
            stripped.startswith("Cannot perform start session") or
            "SessionId:" in stripped or
            "session with SessionId:" in stripped.lower()):
            continue
        lines.append(line)
    return "\n".join(lines).strip()

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

logger = logging.getLogger(__name__)

# Default Zhipu API configuration
DEFAULT_ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/anthropic"

# Container execution context (Docker)
_container_id: str | None = None
_container_workspace: str = "/workspace"

# ECS execution context (AWS Fargate)
_ecs_task_arn: str | None = None
_ecs_cluster: str = "hivecore-cluster"
_ecs_region: str = "ap-northeast-1"
_ecs_container_name: str = "sandbox"
_ecs_mode: bool = False

# Current agent context for observability
_current_agent_id: str | None = None

# Default workspace for code execution (can be set via set_default_workspace)
_default_workspace: str | None = None


def set_current_agent_id(agent_id: str | None) -> None:
    """Set current agent ID for Claude Code observability.

    Args:
        agent_id: Agent ID, or None to clear.
    """
    global _current_agent_id
    _current_agent_id = agent_id


def get_current_agent_id() -> str | None:
    """Get current agent ID.

    Returns:
        Current agent ID or None.
    """
    return _current_agent_id


def set_default_workspace(workspace: str | None) -> None:
    """Set default workspace directory for Claude Code execution.

    When set, all Claude Code tool calls will use this workspace by default
    (unless explicitly overridden via the workspace parameter).

    Args:
        workspace: Path to the workspace directory, or None to clear.
    """
    global _default_workspace
    _default_workspace = workspace


def get_default_workspace() -> str | None:
    """Get default workspace directory.

    Returns:
        Default workspace path or None.
    """
    return _default_workspace


def set_container_context(
    container_id: str | None,
    container_workspace: str = "/workspace",
) -> None:
    """Set container context for Claude Code execution.

    When container_id is set, Claude Code CLI will be executed inside
    the container via `docker exec` instead of on the host machine.

    Args:
        container_id: Docker container ID. Set to None to disable container mode.
        container_workspace: Working directory inside container.
    """
    global _container_id, _container_workspace, _ecs_mode
    _container_id = container_id
    _container_workspace = container_workspace
    _ecs_mode = False


def set_ecs_context(
    task_arn: str,
    cluster: str = "hivecore-cluster",
    region: str = "ap-northeast-1",
    container_name: str = "sandbox",
    workspace: str = "/workspace",
) -> None:
    """Set ECS Fargate context for Claude Code execution.

    When ECS context is set, Claude Code CLI will be executed inside
    the ECS container via `aws ecs execute-command` instead of on the host machine.

    Args:
        task_arn: ECS task ARN (e.g., "arn:aws:ecs:...:task/...")
        cluster: ECS cluster name. Defaults to "hivecore-cluster".
        region: AWS region. Defaults to "ap-northeast-1".
        container_name: Container name in task. Defaults to "sandbox".
        workspace: Working directory inside container.
    """
    global _ecs_task_arn, _ecs_cluster, _ecs_region, _ecs_container_name
    global _container_workspace, _ecs_mode
    _ecs_task_arn = task_arn
    _ecs_cluster = cluster
    _ecs_region = region
    _ecs_container_name = container_name
    _container_workspace = workspace
    _ecs_mode = True


def clear_container_context() -> None:
    """Clear all container/Docker/ECS context."""
    global _container_id, _container_workspace, _ecs_mode
    global _ecs_task_arn, _ecs_cluster, _ecs_region, _ecs_container_name
    _container_id = None
    _container_workspace = "/workspace"
    _ecs_task_arn = None
    _ecs_cluster = "hivecore-cluster"
    _ecs_region = "ap-northeast-1"
    _ecs_container_name = "sandbox"
    _ecs_mode = False


def get_container_context() -> tuple[str | None, str, bool]:
    """Get current container context.

    Returns:
        Tuple of (container_id_or_task_arn, container_workspace, is_ecs_mode).
        is_ecs_mode is True when using ECS Fargate, False for Docker or local.
    """
    if _ecs_mode:
        return _ecs_task_arn, _container_workspace, True
    return _container_id, _container_workspace, False


async def _get_container_file_snapshot(
    container_id: str,
    workspace: str,
) -> set[str]:
    """Get a snapshot of files in container workspace.

    Args:
        container_id: Docker container ID.
        workspace: Workspace directory to scan.

    Returns:
        Set of file paths with modification times.
    """
    try:
        # Use find to get all files with their modification times
        cmd = [
            "docker", "exec", container_id,
            "find", workspace, "-type", "f",
            "-printf", "%p|%T@\\n",
        ]
        result = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=10,
        )
        stdout, _ = await asyncio.wait_for(result.communicate(), timeout=10)
        # Return set of "path|mtime" strings
        lines = stdout.decode("utf-8", errors="replace").strip().split("\n")
        return {line for line in lines if line and "|" in line}
    except Exception:
        return set()


def _check_file_activity(
    before_snapshot: set[str],
    after_snapshot: set[str],
) -> tuple[bool, int, int]:
    """Check if there was file activity between two snapshots.

    Args:
        before_snapshot: File snapshot before execution.
        after_snapshot: File snapshot after execution.

    Returns:
        Tuple of (has_activity, new_files_count, modified_files_count).
    """
    # Extract file paths (without mtime) for comparison
    before_files = {s.split("|")[0] for s in before_snapshot if "|" in s}
    after_files = {s.split("|")[0] for s in after_snapshot if "|" in s}

    # New files created
    new_files = after_files - before_files

    # Check for modified files (same path, different mtime)
    before_dict = {s.split("|")[0]: s for s in before_snapshot if "|" in s}
    after_dict = {s.split("|")[0]: s for s in after_snapshot if "|" in s}

    modified_files = 0
    for path in before_files & after_files:
        if before_dict.get(path) != after_dict.get(path):
            modified_files += 1

    has_activity = len(new_files) > 0 or modified_files > 0
    return has_activity, len(new_files), modified_files


def _build_workspace_constraint_prompt(workspace: str) -> str:
    """Build a prompt that constrains Claude Code to work within the specified workspace.

    This is critical for PR-mode isolation where each agent has its own worktree.
    Without this constraint, agents may accidentally modify files in other directories.

    Args:
        workspace: The allowed workspace directory path.

    Returns:
        A constraint prompt to prepend to user prompts.
    """
    return f"""【工作目录约束 - 必须严格遵守】

你的工作目录是: {workspace}

🚫 禁止操作（违反将导致任务失败）：
1. 禁止使用 cp、mv、rsync 等命令将文件复制/移动到其他目录
2. 禁止直接修改 /workspace/delivery/ 目录中的任何文件
3. 禁止修改其他 agent 的工作目录（/workspace/working/其他目录/）
4. 禁止使用 cd 切换到其他 agent 的目录后进行写操作

✅ 正确做法：
1. 所有代码创建和修改都在 {workspace} 内完成
2. 如需参考其他目录的代码，使用 cat/read 只读查看，但不能复制或修改
3. 代码合并到 delivery 由系统自动通过 git cherry-pick 完成
4. 完成工作后，使用 git add 和 git commit 提交你的修改

⚠️ 重要：你不需要手动将代码复制到 delivery 目录，系统会自动处理合并！

---

"""


async def claude_code_edit(
    prompt: str,
    workspace: str | None = None,
    api_key: str | None = None,
    timeout: int = 480,
    agent_id: str | None = None,
) -> ToolResponse:
    """Execute a code editing task using Claude Code CLI.

    This function invokes the Claude Code CLI with the given prompt,
    using Zhipu GLM-4.7 as the backend model.

    Execution modes:
    - If container context is set (via set_container_context), runs inside container
    - Otherwise, runs on host machine

    Args:
        prompt (`str`):
            The editing instruction/prompt for Claude Code.
            Should describe what code changes to make.
        workspace (`str | None`, optional):
            The working directory for Claude Code.
        agent_id (`str | None`, optional):
            Agent ID for observability. If provided, enables real-time logging.
            Defaults to current directory (or container workspace in container mode).
        api_key (`str | None`, optional):
            Zhipu API key. If not provided, uses ZHIPU_API_KEY
            environment variable.
        timeout (`int`, optional):
            Timeout in seconds. Defaults to 480 (8 minutes).

    Returns:
        `ToolResponse`:
            The result of the Claude Code execution.
    """
    # Check if we should run in container mode
    container_id, container_workspace, is_ecs_mode = get_container_context()

    # Use global agent_id if not provided as argument
    effective_agent_id = agent_id or get_current_agent_id()

    # Create observer for real-time logging if agent_id is available
    on_progress_callback = None
    if effective_agent_id:
        try:
            from ._observability import get_claude_code_observer
            observer = get_claude_code_observer()
            observer.set_agent(effective_agent_id)
            on_progress_callback = observer.on_progress
        except ImportError:
            pass  # Observability not available

    if is_ecs_mode:
        # ECS Fargate mode - execute in remote ECS container
        constrained_prompt = _build_workspace_constraint_prompt(container_workspace) + prompt
        return await _claude_code_edit_in_ecs(
            prompt=constrained_prompt,
            task_arn=container_id,  # task_arn stored in container_id
            container_workspace=container_workspace,
            api_key=api_key,
            timeout=timeout,
            on_progress=on_progress_callback,
        )
    elif container_id:
        # [PR-MODE] Inject workspace constraint to prevent cross-directory operations
        # This is critical for multi-agent isolation in PR mode
        constrained_prompt = _build_workspace_constraint_prompt(container_workspace) + prompt

        return await _claude_code_edit_in_container(
            prompt=constrained_prompt,
            container_id=container_id,
            container_workspace=container_workspace,
            api_key=api_key,
            timeout=timeout,
            on_progress=on_progress_callback,
        )
    else:
        # Use global default workspace if workspace parameter is not provided
        effective_workspace = workspace or get_default_workspace()
        return await _claude_code_edit_local(
            prompt=prompt,
            workspace=effective_workspace,
            api_key=api_key,
            timeout=timeout,
        )


async def _claude_code_edit_in_ecs(
    prompt: str,
    task_arn: str,
    container_workspace: str,
    api_key: str | None = None,
    timeout: int | None = None,
    on_progress: Any | None = None,
) -> ToolResponse:
    """Execute Claude Code CLI inside an ECS Fargate container.

    Uses AWS ECS execute-command to run commands in the remote ECS task.

    Args:
        prompt: The editing instruction/prompt.
        task_arn: ECS task ARN.
        container_workspace: Working directory inside container.
        api_key: Zhipu API key.
        timeout: Total timeout in seconds.
        on_progress: Optional async callback for progress updates.

    Returns:
        ToolResponse with execution result.
    """
    import time
    import subprocess

    # Log the start of Claude Code execution
    prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
    logger.info(
        "[ClaudeCode] 开始执行 (ECS task=%s, workspace=%s)",
        task_arn.split("/")[-1],
        container_workspace,
    )
    logger.info("[ClaudeCode] 任务: %s", prompt_preview)

    # Get ECS context
    global _ecs_cluster, _ecs_region, _ecs_container_name

    # Enhance prompt with directory structure guidance
    enhanced_prompt = f"""【重要 - 文件路径规范】
当前工作目录: {container_workspace}
这是项目的根目录，你必须在此目录下创建所有文件。

**核心约束：**
1. 使用相对路径，禁止使用绝对路径（如 /workspace/...）
2. 不要创建额外的项目根目录（如 my-project/），当前目录就是项目根
3. 禁止使用 ../ 向上跳转目录

【任务】
{prompt}"""

    # Resolve API key
    resolved_api_key = api_key or os.environ.get("ZHIPU_API_KEY", "")
    logger.info("[ClaudeCode] Resolved API key: %s... (length: %d)",
               resolved_api_key[:8] if resolved_api_key else "None",
               len(resolved_api_key) if resolved_api_key else 0)
    if not resolved_api_key:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text="[ERROR] No API key provided. Set ZHIPU_API_KEY in .env file.",
            )]
        )

    # Use base64 encoding to avoid quote escaping issues
    import base64
    prompt_b64 = base64.b64encode(enhanced_prompt.encode("utf-8")).decode("ascii")

    # Build ECS execute command
    # Note: This uses synchronous subprocess since AWS CLI doesn't have async interface
    # IMPORTANT: Run claude as 'node' user because --dangerously-skip-permissions
    # cannot be used with root/sudo privileges (security restriction in Claude Code CLI)
    # Use sudo -H to preserve environment variables for the node user
    #
    # Strategy: Write command to a script file first to avoid complex quoting issues
    # Then execute the script - this is more reliable than passing complex commands
    # via --command with nested quotes
    escaped_command = (
        f"echo {prompt_b64} | base64 -d > /tmp/prompt.txt && "
        f"cd {container_workspace} && "
        f"sudo -H -u node env "
        f"ANTHROPIC_BASE_URL={DEFAULT_ZHIPU_BASE_URL} "
        f"ANTHROPIC_API_KEY={resolved_api_key} "
        f"ANTHROPIC_AUTH_TOKEN={resolved_api_key} "
        f"HOME=/home/node "
        f"claude -p \"$(cat /tmp/prompt.txt)\" --output-format stream-json --verbose --dangerously-skip-permissions"
    )

    aws_cmd = [
        "aws", "ecs", "execute-command",
        "--cluster", _ecs_cluster,
        "--task", task_arn,
        "--container", _ecs_container_name,
        "--command", f"/bin/bash -c '{escaped_command}'",
        "--interactive",
        "--region", _ecs_region,
    ]

    start_time = time.time()

    try:
        # Execute command using pty to simulate TTY for AWS CLI --interactive mode
        # AWS CLI's --interactive flag expects a TTY; without it, output gets truncated
        loop = asyncio.get_event_loop()

        def run_command():
            import pty
            import os
            import select

            # Create pseudo-terminal
            master_fd, slave_fd = pty.openpty()

            # Start process with pseudo-terminal as stdout/stderr
            proc = subprocess.Popen(
                aws_cmd,
                stdout=slave_fd,
                stderr=slave_fd,
                stdin=slave_fd,
                text=True,
                close_fds=True,
            )
            os.close(slave_fd)

            logger.info("[ClaudeCode] Process started with PID: %s (pty mode)", proc.pid)

            # Read output from master_fd with timeout
            stdout_buffer = []
            stderr_buffer = []

            # Set master_fd to non-blocking
            import fcntl
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            start_read = time.time()
            read_timeout = timeout or 300

            while True:
                # Check if process has exited
                ret = proc.poll()
                if ret is not None:
                    # Process finished, do final reads with delay to allow buffer flush
                    logger.info("[ClaudeCode] Process exited (rc=%s), reading remaining data...", ret)
                    # Read multiple times with small delays to catch all buffered data
                    for _ in range(5):
                        try:
                            remaining = os.read(master_fd, 65536).decode('utf-8', errors='replace')
                            if remaining:
                                logger.info("[ClaudeCode] Read %d more bytes after exit", len(remaining))
                                stdout_buffer.append(remaining)
                            time.sleep(0.1)
                        except OSError:
                            break
                    break

                # Use select to wait for data with timeout
                try:
                    rlist, _, _ = select.select([master_fd], [], [], 1.0)
                    if rlist:
                        try:
                            data = os.read(master_fd, 4096).decode('utf-8', errors='replace')
                            if data:
                                stdout_buffer.append(data)
                                start_read = time.time()  # Reset timeout on activity
                        except OSError:
                            pass
                except (select.error, ValueError):
                    # select.error can happen in gevent environment
                    pass

                # Check timeout
                if time.time() - start_read > read_timeout:
                    logger.warning("[ClaudeCode] Timeout reading from pty")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break

            os.close(master_fd)

            stdout_text = ''.join(stdout_buffer)
            stderr_text = ''.join(stderr_buffer)

            logger.info("[ClaudeCode] PTY read complete: %d chunks, %d bytes total",
                       len(stdout_buffer), len(stdout_text))
            # Log first 500 chars of output for debugging
            if stdout_text:
                logger.info("[ClaudeCode] First 500 chars: %s", repr(stdout_text[:500]))

            return proc, stdout_text, stderr_text

        process, stdout_text, stderr_text = await loop.run_in_executor(None, run_command)

        logger.info("[ClaudeCode] Process finished with returncode: %s", process.returncode)

        # Process output
        output_lines: list[str] = []
        stderr_lines: list[str] = []
        final_result: dict | None = None
        import json

        # Parse stdout
        for line in stdout_text.split("\n"):
            line = line.strip()
            if line:
                output_lines.append(line)
                try:
                    msg = json.loads(line)
                    msg_type = msg.get("type", "")
                    subtype = msg.get("subtype", "")
                    logger.info("[ClaudeCode] Stream JSON: type=%s, subtype=%s", msg_type, subtype)
                    if msg_type == "result":
                        final_result = msg
                        logger.info("[ClaudeCode] Found result message!")
                except json.JSONDecodeError:
                    pass

        # Parse stderr
        if stderr_text:
            stderr_lines.extend(stderr_text.split("\n"))

        logger.info("[ClaudeCode] Total stdout_lines: %d, stderr_lines: %d, final_result: %s",
                   len(output_lines), len(stderr_lines),
                   "set" if final_result else "None")
        if stderr_lines and any(l for l in stderr_lines if l.strip()):
            logger.warning("[ClaudeCode] Stderr output: %s", "\n".join(stderr_lines[-10:]))

        # Log raw output for debugging (last 10 lines, limited to 500 chars)
        raw_output = "\n".join(output_lines[-10:]) if output_lines else ""
        if raw_output:
            logger.info("[ClaudeCode] Raw stdout (last 10 lines): %s", raw_output[:500])

        # Process result
        if final_result:
            result_type = final_result.get("resultType", "success")
            if result_type == "success":
                content = final_result.get("output", "Code editing completed")
                logger.info("[ClaudeCode] Success result: %s...", content[:100] if content else "empty")
                return ToolResponse(
                    content=[TextBlock(type="text", text=content)]
                )
            else:
                error_msg = final_result.get("error", "Unknown error")
                logger.info("[ClaudeCode] Error result: %s", error_msg)
                return ToolResponse(
                    content=[TextBlock(
                        type="text",
                        text=f"[ERROR] {error_msg}",
                    )]
                )

        # Fallback: return last line of output (after filtering)
        if output_lines:
            # Filter out Session Manager messages
            raw_output = "\n".join(output_lines)
            filtered_output = _filter_ecs_exec_output(raw_output)
            logger.info("[ClaudeCode] Fallback - raw_lines: %d, filtered_length: %d",
                       len(output_lines), len(filtered_output) if filtered_output else 0)
            if filtered_output:
                return ToolResponse(
                    content=[TextBlock(type="text", text=filtered_output)]
                )
            else:
                # No actual output after filtering (only Session Manager messages)
                return ToolResponse(
                    content=[TextBlock(type="text", text="Code editing completed")]
                )

        return ToolResponse(
            content=[TextBlock(type="text", text="Code editing completed (no output)")]
        )

    except Exception as e:
        logger.exception("[ClaudeCode] ECS execution failed: %s", e)
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text=f"[ERROR] ECS execution failed: {e}",
            )]
        )


async def _claude_code_edit_in_container(
    prompt: str,
    container_id: str,
    container_workspace: str,
    api_key: str | None = None,
    timeout: int | None = None,
    activity_timeout: int | None = None,
    on_progress: Any | None = None,
) -> ToolResponse:
    """Execute Claude Code CLI inside a Docker container with streaming output.

    Uses stream-json format for real-time output monitoring and better timeout detection.

    Args:
        prompt: The editing instruction/prompt.
        container_id: Docker container ID.
        container_workspace: Working directory inside container.
        api_key: Zhipu API key.
        timeout: Total timeout in seconds. None means no timeout (default).
        activity_timeout: Timeout for no output activity. None means no timeout (default).
        on_progress: Optional async callback for progress updates.

    Returns:
        ToolResponse with execution result.
    """
    import time

    # Log the start of Claude Code execution for observability
    prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
    logger.info(
        "[ClaudeCode] 开始执行 (container=%s, workspace=%s, 流式模式)",
        container_id[:12],
        container_workspace,
    )
    logger.info("[ClaudeCode] 任务: %s", prompt_preview)

    # Enhance prompt with directory structure guidance
    enhanced_prompt = f"""【重要 - 文件路径规范】
当前工作目录: {container_workspace}
这是项目的根目录，你必须在此目录下创建所有文件。

**核心约束：**
1. 使用相对路径，禁止使用绝对路径（如 /workspace/...）
2. 不要创建额外的项目根目录（如 my-project/），当前目录就是项目根
3. 禁止使用 ../ 向上跳转目录

**推荐目录结构：**
- 后端代码: backend/app/, backend/tests/
- 前端代码: frontend/src/, frontend/public/
- 数据库: database/, migrations/
- 文档: docs/
- 设计: design/
- 配置: config/, 或根目录的配置文件
- 其他合理的目录结构都可以

**正确示例：**
- backend/app/main.py ✓
- frontend/src/App.vue ✓
- docs/api.md ✓
- design/wireframes.md ✓
- README.md ✓

**错误示例：**
- /workspace/working/project/file.py ✗（绝对路径）
- my-project/backend/main.py ✗（额外项目目录）
- ../other/file.py ✗（向上跳转）

【任务】
{prompt}"""

    # Resolve API key
    resolved_api_key = api_key or os.environ.get("ZHIPU_API_KEY", "")
    if not resolved_api_key:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text="[ERROR] No API key provided. Set ZHIPU_API_KEY in .env file.",
            )]
        )

    # Use base64 encoding to avoid quote escaping issues
    import base64
    prompt_b64 = base64.b64encode(enhanced_prompt.encode("utf-8")).decode("ascii")

    # Build docker exec command with stream-json format
    # Write prompt to temp file, then use $(cat file) to pass it as positional argument
    # This allows stream-json format which requires --verbose
    docker_cmd = [
        "docker", "exec",
        "--user", "node",
        "-w", container_workspace,
        "-e", "HOME=/home/node",
        "-e", f"ANTHROPIC_BASE_URL={DEFAULT_ZHIPU_BASE_URL}",
        "-e", f"ANTHROPIC_API_KEY={resolved_api_key}",
        "-e", f"ANTHROPIC_AUTH_TOKEN={resolved_api_key}",
        container_id,
        "bash", "-c",
        f"echo '{prompt_b64}' | base64 -d > /home/node/prompt.txt && "
        f"claude -p \"$(cat /home/node/prompt.txt)\" "
        f"--output-format stream-json --verbose --dangerously-skip-permissions",
    ]

    start_time = time.time()
    last_activity_time = start_time
    output_lines: list[str] = []
    final_result: dict | None = None

    try:
        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            # Stream output using chunked read instead of readline()
            # This avoids the 64KB line limit that causes LimitOverrunError
            # when Claude Code outputs large tool results (e.g., reading files)
            read_buffer = b""
            chunk_size = 65536  # 64KB chunks

            while True:
                # Read next chunk (with optional activity timeout)
                try:
                    if activity_timeout is not None:
                        chunk = await asyncio.wait_for(
                            process.stdout.read(chunk_size),
                            timeout=activity_timeout,
                        )
                    else:
                        # No timeout - wait indefinitely
                        chunk = await process.stdout.read(chunk_size)
                except asyncio.TimeoutError:
                    # No output for activity_timeout seconds - likely stalled
                    process.kill()
                    await process.wait()
                    logger.warning(
                        "[ClaudeCode] 静默超时 (%ds 无输出)，任务可能卡住",
                        activity_timeout,
                    )
                    return ToolResponse(
                        content=[TextBlock(
                            type="text",
                            text=f"[TIMEOUT:STALLED] Claude Code 静默超时 "
                                 f"({activity_timeout}s 无输出)，任务可能卡住。",
                        )]
                    )

                if not chunk:
                    # EOF - process finished
                    # Process any remaining data in buffer
                    if read_buffer:
                        line = read_buffer.decode("utf-8", errors="replace").strip()
                        if line:
                            output_lines.append(line)
                            try:
                                msg = json.loads(line)
                                if msg.get("type") == "result":
                                    final_result = msg
                            except json.JSONDecodeError:
                                pass
                    break

                last_activity_time = time.time()
                read_buffer += chunk

                # Process all complete lines in buffer
                while b"\n" in read_buffer:
                    line_bytes, read_buffer = read_buffer.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    output_lines.append(line)

                    # Parse NDJSON message
                    try:
                        msg = json.loads(line)
                        msg_type = msg.get("type", "")

                        # Call progress callback if provided
                        if on_progress:
                            try:
                                if asyncio.iscoroutinefunction(on_progress):
                                    await on_progress(msg)
                                else:
                                    on_progress(msg)
                            except Exception as e:
                                logger.warning("[ClaudeCode] on_progress 回调错误: %s", e)

                        # Capture final result
                        if msg_type == "result":
                            final_result = msg

                    except json.JSONDecodeError:
                        # Not JSON, skip (e.g., very long tool result lines)
                        pass

            # Wait for process to finish
            await process.wait()

        except Exception as e:
            process.kill()
            await process.wait()
            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text=f"[ERROR] Claude Code 执行异常: {str(e)[:500]}",
                )]
            )

        # Check return code
        if process.returncode != 0:
            stderr_bytes = await process.stderr.read()
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            error_preview = stderr_text[:500] if stderr_text else "Unknown error"
            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text=f"[ERROR] Claude Code failed (exit {process.returncode}): {error_preview}",
                )]
            )

        # Format result from stream-json output
        if final_result:
            result_text = final_result.get("result", "")
            is_error = final_result.get("is_error", False)
            if is_error:
                return ToolResponse(
                    content=[TextBlock(
                        type="text",
                        text=f"[ERROR] {result_text}",
                    )]
                )
            return ToolResponse(
                content=[TextBlock(type="text", text=f"**Result:** {result_text}")]
            )
        else:
            # No result message, return raw output
            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text="\n".join(output_lines[-10:]) if output_lines else "No output",
                )]
            )

    except FileNotFoundError:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text="[ERROR] Docker not found. Please install Docker.",
            )]
        )
    except Exception as exc:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text=f"[ERROR] Failed to execute Claude Code in container: {exc}",
            )]
        )


async def _claude_code_edit_local(
    prompt: str,
    workspace: str | None = None,
    api_key: str | None = None,
    timeout: int = 480,
) -> ToolResponse:
    """Execute Claude Code CLI on the host machine.

    Args:
        prompt: The editing instruction/prompt.
        workspace: Working directory.
        api_key: Zhipu API key.
        timeout: Timeout in seconds.

    Returns:
        ToolResponse with execution result.
    """
    # Resolve workspace
    cwd = Path(workspace).resolve() if workspace else Path.cwd()
    if not cwd.exists():
        cwd.mkdir(parents=True, exist_ok=True)

    # Resolve API key - prioritize ZHIPU_API_KEY from .env
    resolved_api_key = api_key or os.environ.get("ZHIPU_API_KEY", "")
    if not resolved_api_key:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text="[ERROR] No API key provided. Set ZHIPU_API_KEY in .env file.",
            )]
        )

    # Build a CLEAN environment for Claude Code subprocess
    # IMPORTANT: We must NOT inherit the parent's ANTHROPIC_AUTH_TOKEN
    # because it might be a 'cr_' token from the current Claude Code session
    env = {}

    # Copy essential environment variables
    essential_vars = [
        "PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL", "TERM",
        "TMPDIR", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME",
    ]
    for var in essential_vars:
        if var in os.environ:
            env[var] = os.environ[var]

    # Set Zhipu configuration - this OVERRIDES any inherited values
    env["ANTHROPIC_BASE_URL"] = DEFAULT_ZHIPU_BASE_URL
    env["ANTHROPIC_API_KEY"] = resolved_api_key
    # Claude Code uses ANTHROPIC_AUTH_TOKEN for authentication
    env["ANTHROPIC_AUTH_TOKEN"] = resolved_api_key

    # Build command
    # Using -p for prompt mode, --output-format json for structured output
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "json",
        "--dangerously-skip-permissions",  # Skip permission prompts for automation
    ]

    try:
        # Build the command string for shell execution
        # Escape quotes in prompt properly
        escaped_prompt = prompt.replace('"', '\\"').replace("'", "'\"'\"'")
        cmd_str = f"claude -p '{escaped_prompt}' --output-format json --dangerously-skip-permissions"

        process = await asyncio.create_subprocess_shell(
            cmd_str,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text=f"[ERROR] Claude Code timed out after {timeout} seconds.",
                )]
            )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if process.returncode != 0:
            return ToolResponse(
                content=[TextBlock(
                    type="text",
                    text=f"[ERROR] Claude Code failed (exit {process.returncode}):\n{stderr_text}\n{stdout_text}",
                )]
            )

        # Try to parse JSON output
        try:
            output_data = json.loads(stdout_text)
            # Format the response nicely
            formatted = _format_claude_code_output(output_data)
            return ToolResponse(
                content=[TextBlock(type="text", text=formatted)]
            )
        except json.JSONDecodeError:
            # Return raw output if not JSON
            return ToolResponse(
                content=[TextBlock(type="text", text=stdout_text)]
            )

    except FileNotFoundError:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text="[ERROR] Claude Code CLI not found. Please install with: npm install -g @anthropic-ai/claude-code",
            )]
        )
    except Exception as exc:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text=f"[ERROR] Failed to execute Claude Code: {exc}",
            )]
        )


async def claude_code_chat(
    message: str,
    workspace: str | None = None,
    api_key: str | None = None,
    timeout: int = 120,
) -> ToolResponse:
    """Send a chat message to Claude Code for code-related questions.

    Unlike claude_code_edit, this is for asking questions about code
    without necessarily making changes.

    Args:
        message (`str`):
            The question or message to send.
        workspace (`str | None`, optional):
            The working directory context.
        api_key (`str | None`, optional):
            Zhipu API key.
        timeout (`int`, optional):
            Timeout in seconds. Defaults to 120.

    Returns:
        `ToolResponse`:
            Claude Code's response.
    """
    return await claude_code_edit(
        prompt=message,
        workspace=workspace,
        api_key=api_key,
        timeout=timeout,
    )


def _log_stream_event(event: dict[str, Any]) -> None:
    """Log a streaming event from Claude Code in real-time.

    This provides visibility into what Claude Code is doing as it happens.

    Args:
        event: A single streaming JSON event from Claude Code.
    """
    event_type = event.get("type", "")

    # Tool use events - show what tools are being called
    if event_type == "tool_use":
        tool_name = event.get("name", "unknown")
        tool_input = event.get("input", {})

        # Format tool-specific output
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            logger.info("[ClaudeCode] 📖 读取文件: %s", file_path)

        elif tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            content_len = len(tool_input.get("content", ""))
            logger.info("[ClaudeCode] ✏️ 写入文件: %s (%d 字符)", file_path, content_len)

        elif tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            old_str = tool_input.get("old_string", "")[:30]
            logger.info("[ClaudeCode] 🔧 编辑文件: %s (替换: '%s...')", file_path, old_str)

        elif tool_name == "Bash":
            command = tool_input.get("command", "")[:80]
            logger.info("[ClaudeCode] 💻 执行命令: %s", command)

        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            logger.info("[ClaudeCode] 🔍 搜索文件: %s", pattern)

        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            logger.info("[ClaudeCode] 🔍 搜索内容: %s", pattern)

        else:
            logger.info("[ClaudeCode] 🔧 调用工具: %s", tool_name)

    # Tool result events
    elif event_type == "tool_result":
        tool_name = event.get("name", "unknown")
        success = not event.get("is_error", False)
        status = "✓" if success else "✗"
        logger.info("[ClaudeCode]   %s %s 完成", status, tool_name)

    # Text/thinking events - show Claude's thinking
    elif event_type == "text" or event_type == "content_block_delta":
        text = event.get("text", "") or event.get("delta", {}).get("text", "")
        if text and len(text.strip()) > 0:
            # Only log substantial text (skip fragments)
            text_preview = text[:100] + "..." if len(text) > 100 else text
            logger.debug("[ClaudeCode] 💭 %s", text_preview.replace("\n", " "))

    # Message events
    elif event_type == "message":
        content = event.get("content", "")
        if content:
            content_preview = str(content)[:100]
            logger.info("[ClaudeCode] 📝 %s...", content_preview)

    # Final result event
    elif event_type == "result":
        logger.info("[ClaudeCode] ✅ 执行完成")


def _log_claude_code_result(output: dict[str, Any]) -> None:
    """Log Claude Code execution result for observability.

    Args:
        output: The parsed JSON output from Claude Code.
    """
    # Log files changed with details
    files_changed = output.get("files_changed", [])
    if files_changed:
        logger.info("[ClaudeCode] ✓ 修改了 %d 个文件:", len(files_changed))
        for f in files_changed[:10]:  # Show more files
            logger.info("[ClaudeCode]   📄 %s", f)
        if len(files_changed) > 10:
            logger.info("[ClaudeCode]   ... 还有 %d 个文件", len(files_changed) - 10)
    else:
        logger.info("[ClaudeCode] ⚠ 未修改任何文件")

    # Log cost if available
    cost = output.get("cost")
    if cost:
        logger.info("[ClaudeCode] 💰 消耗: %s", cost)

    # Log FULL result summary (not truncated) - use INFO level
    result = output.get("result") or output.get("response") or output.get("message")
    if result:
        result_str = str(result)
        # Show full result for transparency (up to 1000 chars)
        if len(result_str) > 1000:
            result_preview = result_str[:1000] + f"\n... (共 {len(result_str)} 字符)"
        else:
            result_preview = result_str
        logger.info("[ClaudeCode] 📋 结果:\n%s", result_preview)


def _format_claude_code_output(output: dict[str, Any]) -> str:
    """Format Claude Code JSON output into readable text.

    Args:
        output (`dict[str, Any]`):
            The parsed JSON output from Claude Code.

    Returns:
        `str`:
            Formatted text representation.
    """
    parts = []

    # Extract result/response
    if "result" in output:
        parts.append(f"**Result:**\n{output['result']}")
    elif "response" in output:
        parts.append(f"**Response:**\n{output['response']}")
    elif "message" in output:
        parts.append(f"**Message:**\n{output['message']}")

    # Extract files changed
    if "files_changed" in output:
        files = output["files_changed"]
        if files:
            parts.append(f"\n**Files Changed:** {', '.join(files)}")

    # Extract cost info if available
    if "cost" in output:
        parts.append(f"\n**Cost:** {output['cost']}")

    if not parts:
        # Fallback to JSON dump
        return json.dumps(output, ensure_ascii=False, indent=2)

    return "\n".join(parts)


def check_claude_code_installed() -> bool:
    """Check if Claude Code CLI is installed and available.

    Returns:
        `bool`:
            True if Claude Code is available.
    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_claude_code_version() -> str | None:
    """Get the installed Claude Code version.

    Returns:
        `str | None`:
            Version string or None if not installed.
    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
