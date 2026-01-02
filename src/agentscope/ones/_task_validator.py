# -*- coding: utf-8 -*-
"""Task-level immediate validation for execution loop.

This module provides language-agnostic validation by checking:
1. Whether expected files were created
2. Whether Claude Code reported any errors
3. Active validation by calling Claude Code to verify the task

Language-specific validation (syntax, imports, etc.) is handled
by Claude Code itself during the active validation step.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import time as _time_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..aa import Requirement

logger = logging.getLogger(__name__)


def _log_validation(
    msg: str,
    *,
    level: str = "info",
    prefix: str = "[TaskValidator]",
) -> None:
    """Log validation message with real-time output.

    Args:
        msg: Message to log.
        level: Log level (info, warning, error).
        prefix: Prefix for the message.
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


@dataclass
class TaskValidationResult:
    """Result of task-level validation."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error_summary: str = ""
    files_checked: list[str] = field(default_factory=list)
    validation_type: str = "basic"

    def __post_init__(self) -> None:
        if not self.error_summary and self.errors:
            self.error_summary = "; ".join(self.errors[:3])
            if len(self.errors) > 3:
                self.error_summary += f" (还有 {len(self.errors) - 3} 个错误)"


class TaskLevelValidator:
    """Validates each task immediately after completion.

    This is a language-agnostic validator that:
    1. Checks if Claude Code reported errors in the output
    2. Verifies that files were created/modified

    Language-specific validation (syntax, imports, tests) should be
    performed by Claude Code itself during task execution.
    """

    def __init__(
        self,
        workspace_dir: str | Path,
        *,
        container_id: str | None = None,
        container_workspace: str = "/workspace/working",
        validation_timeout: float = 30.0,
    ) -> None:
        """Initialize the validator.

        Args:
            workspace_dir: Local workspace directory (used when not in container mode).
            container_id: Docker container ID for container mode.
            container_workspace: Workspace path inside the container.
            validation_timeout: Timeout for validation commands.
        """
        self.workspace_dir = Path(workspace_dir)
        self.container_id = container_id
        self.container_workspace = container_workspace
        self.validation_timeout = validation_timeout

        # Track which validations have passed for incremental checks
        self._passed_validations: dict[str, TaskValidationResult] = {}

    @property
    def is_container_mode(self) -> bool:
        """Check if running in container mode."""
        return self.container_id is not None

    async def validate_task(
        self,
        node_id: str,
        requirement: Requirement | None,
        output_content: str | None,
    ) -> TaskValidationResult:
        """Validate a single task immediately after completion.

        This performs language-agnostic validation:
        1. Check if the output contains error indicators
        2. Verify files were created (if applicable)

        Args:
            node_id: Task identifier (e.g., 'REQ-001')
            requirement: The requirement being fulfilled
            output_content: The agent's output content

        Returns:
            TaskValidationResult with pass/fail status and errors
        """
        if requirement is None:
            return TaskValidationResult(passed=True, validation_type="skipped")

        errors: list[str] = []
        warnings: list[str] = []

        logger.info(
            "[%s] 开始任务级验收 (容器模式: %s)",
            node_id,
            self.is_container_mode,
        )

        # Check for different error/timeout types from Claude Code output
        # 1. [ERROR] - definitive error, trigger repair
        # 2. [TIMEOUT:STALLED] - timeout with no progress, trigger repair
        # 3. [TIMEOUT:PROGRESS] - timeout but has progress, don't trigger repair
        if output_content:
            if "[ERROR]" in output_content:
                idx = output_content.find("[ERROR]")
                snippet = output_content[idx : idx + 300].split("\n")[0]
                errors.append(f"Claude Code 报告错误: {snippet}")
            elif "[TIMEOUT:STALLED]" in output_content:
                idx = output_content.find("[TIMEOUT:STALLED]")
                snippet = output_content[idx : idx + 300].split("\n")[0]
                errors.append(f"任务卡住: {snippet}")
            elif "[TIMEOUT:PROGRESS]" in output_content:
                # Task made progress but timed out - not an error, just a warning
                idx = output_content.find("[TIMEOUT:PROGRESS]")
                snippet = output_content[idx : idx + 300].split("\n")[0]
                warnings.append(f"任务超时但有进展: {snippet}")
                logger.info(
                    "[%s] 任务超时但有进展，不触发修复流程",
                    node_id,
                )

        result = TaskValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validation_type="output_check",
        )

        # Log result
        if result.passed:
            logger.info("[%s] ✓ 任务验收通过", node_id)
            self._passed_validations[node_id] = result
        else:
            logger.warning(
                "[%s] ✗ 任务验收失败: %s",
                node_id,
                result.error_summary,
            )

        return result

    async def _check_files_created(self, output_content: str) -> bool | None:
        """Check if files mentioned in output were actually created.

        This is a best-effort check that looks for file paths in the output
        and verifies they exist.

        Args:
            output_content: The output to parse for file paths.

        Returns:
            True if files exist, False if not, None if cannot determine.
        """
        # Simple heuristic: look for "Files Changed" or similar patterns
        if "Files Changed" not in output_content and "创建的文件" not in output_content:
            return None

        # For now, just return None (cannot determine)
        # A more sophisticated implementation could parse file paths
        # and verify their existence
        return None

    async def _run_command(
        self,
        cmd: list[str],
        cwd: str | None = None,
    ) -> tuple[int, str, str]:
        """Run a command either locally or in container.

        Args:
            cmd: Command to run.
            cwd: Working directory.

        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        if self.is_container_mode:
            docker_cmd = ["docker", "exec"]
            if cwd:
                docker_cmd.extend(["-w", cwd])
            docker_cmd.append(self.container_id)
            docker_cmd.extend(cmd)
            final_cmd = docker_cmd
            final_cwd = None
        else:
            final_cmd = cmd
            final_cwd = cwd

        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        final_cmd,
                        cwd=final_cwd,
                        capture_output=True,
                        timeout=int(self.validation_timeout),
                    ),
                ),
                timeout=self.validation_timeout + 5,
            )
            return (
                result.returncode,
                result.stdout.decode("utf-8", errors="replace"),
                result.stderr.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            return -1, "", "命令超时"
        except Exception as e:
            return -1, "", str(e)[:200]

    def generate_fix_prompt(
        self,
        node_id: str,
        requirement: Requirement | None,
        validation_result: TaskValidationResult,
        original_output: str | None,
    ) -> str:
        """Generate a targeted fix prompt for the agent.

        Args:
            node_id: Task identifier
            requirement: Original requirement
            validation_result: The failed validation result
            original_output: What the agent produced

        Returns:
            A prompt focused on fixing the specific errors
        """
        title = getattr(requirement, "title", node_id) if requirement else node_id

        prompt = f"""## 任务修复请求

**任务**: {node_id} - {title}

### 验收失败原因

{chr(10).join(f'- ❌ {e}' for e in validation_result.errors)}

### 修复要求

请针对上述错误进行修复：

1. 分析错误原因
2. 修复具体问题
3. **必须**运行验证命令确认修复成功

### 验证要求（重要）

修复完成后，你**必须**主动验证代码的正确性：
1. 运行适当的命令验证代码可以被正确加载/编译
2. 如果项目有测试框架，运行相关测试
3. 如果验证失败，继续修复直到验证通过
4. 只有验证通过后才算修复完成

验证方式由你根据项目类型自行决定。

### 重要提示

- 只修复上述错误，不要修改其他功能
- 如果需要创建缺失的文件或目录，请一并创建
"""

        return prompt

    def get_validation_summary(self) -> dict[str, bool]:
        """Get summary of all passed validations."""
        return {
            node_id: result.passed
            for node_id, result in self._passed_validations.items()
        }

    async def validate_with_agent(
        self,
        node_id: str,
        requirement: "Requirement | None",
        output_content: str | None,
        *,
        validation_timeout: float = 120.0,
    ) -> TaskValidationResult:
        """Actively validate task by calling Claude Code to verify.

        This method calls Claude Code to let it verify the task result
        by running appropriate validation commands (build, test, import, etc.)
        based on the project type.

        Args:
            node_id: Task identifier (e.g., 'REQ-001')
            requirement: The requirement being fulfilled
            output_content: The agent's output content (for context)
            validation_timeout: Timeout for validation (default 120s)

        Returns:
            TaskValidationResult with pass/fail status and errors
        """
        if requirement is None:
            return TaskValidationResult(passed=True, validation_type="skipped")

        _log_validation(f"[{node_id}] 🔍 开始主动验证...")

        try:
            from agentscope.scripts._claude_code import claude_code_edit
        except ImportError:
            _log_validation(
                f"[{node_id}] ⚠ claude_code_edit 不可用，跳过主动验证",
                level="warning",
            )
            return TaskValidationResult(passed=True, validation_type="skipped")

        # Build validation prompt
        title = getattr(requirement, "title", node_id) if requirement else node_id
        validation_prompt = f"""## 任务验证请求

**任务**: {node_id} - {title}

请验证此任务的代码是否可以正常运行。你需要：

1. **检查关键文件是否存在**：
   - 如果是 Python 项目：检查 requirements.txt 或 pyproject.toml 是否存在
   - 如果是 Node.js 项目：检查 package.json 是否存在
   - 检查任务相关的代码文件是否存在

2. **验证代码可以正常运行**：
   - Python: 尝试导入主要模块 (`python -c "import ..."`)
   - Node.js:
     * 首先检查 node_modules 是否存在，如不存在则运行 `npm install`
     * 然后运行 `npm run build` 或 `npm run lint`（假设依赖已安装）
   - 其他语言: 运行适当的编译/构建命令

   **注意**: npm install 可能需要较长时间，请耐心等待。如果构建失败，
   请仔细分析错误信息（如 TypeScript 类型错误、导入错误等）。

3. **输出验证结果**：
   - 如果所有验证通过，输出: `[VALIDATION_PASSED]`
   - 如果任何验证失败，输出: `[VALIDATION_FAILED] 具体失败原因`

**重要**：
- 只做验证，不要修改任何代码
- 验证超时限制: {validation_timeout}秒
- 如果发现缺失的关键文件（如 requirements.txt），必须报告为失败
"""

        try:
            _log_validation(f"[{node_id}] 调用 Claude Code 执行验证...")
            result = await asyncio.wait_for(
                claude_code_edit(prompt=validation_prompt),
                timeout=validation_timeout,
            )

            # Extract result text
            result_text = ""
            if result and result.content:
                for block in result.content:
                    if hasattr(block, "text"):
                        result_text += block.text
                    elif isinstance(block, dict) and "text" in block:
                        result_text += block["text"]

            # Parse validation result
            errors: list[str] = []
            warnings: list[str] = []

            if "[VALIDATION_FAILED]" in result_text:
                # Extract failure reason
                idx = result_text.find("[VALIDATION_FAILED]")
                failure_msg = result_text[idx + len("[VALIDATION_FAILED]"):].strip()
                # Take first line or first 200 chars
                failure_msg = failure_msg.split("\n")[0][:200]
                errors.append(f"验证失败: {failure_msg}")
                _log_validation(
                    f"[{node_id}] ✗ 主动验证失败: {failure_msg}",
                    level="error",
                )
            elif "[VALIDATION_PASSED]" in result_text:
                _log_validation(f"[{node_id}] ✓ 主动验证通过")
            elif "[ERROR]" in result_text:
                idx = result_text.find("[ERROR]")
                snippet = result_text[idx : idx + 300].split("\n")[0]
                errors.append(f"验证过程出错: {snippet}")
                _log_validation(
                    f"[{node_id}] ✗ 验证过程出错: {snippet}",
                    level="error",
                )
            else:
                # No explicit marker - assume passed with warning
                warnings.append("验证完成但未返回明确结果")
                _log_validation(
                    f"[{node_id}] ⚠ 验证完成但未返回明确结果",
                    level="warning",
                )

            validation_result = TaskValidationResult(
                passed=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validation_type="active_validation",
            )

            if validation_result.passed:
                self._passed_validations[node_id] = validation_result

            return validation_result

        except asyncio.TimeoutError:
            _log_validation(
                f"[{node_id}] ✗ 主动验证超时 ({validation_timeout}s)",
                level="error",
            )
            return TaskValidationResult(
                passed=False,
                errors=[f"验证超时 ({validation_timeout}s)"],
                validation_type="active_validation",
            )
        except Exception as e:
            _log_validation(
                f"[{node_id}] ✗ 主动验证异常: {e}",
                level="error",
            )
            return TaskValidationResult(
                passed=False,
                errors=[f"验证异常: {str(e)[:200]}"],
                validation_type="active_validation",
            )
