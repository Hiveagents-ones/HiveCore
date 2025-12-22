# -*- coding: utf-8 -*-
"""Acceptance Agent for dynamic project validation.

This module provides an LLM-driven acceptance agent that:
1. Analyzes deliverables to determine validation strategy
2. Selects appropriate sandbox environments (browser, CLI, API, etc.)
3. Executes validation dynamically based on LLM decisions
4. Verifies deliverables meet acceptance criteria

Key design principles:
- NO hardcoded validation methods - LLM decides everything
- Multi-sandbox support: browser for web, CLI for backend, etc.
- Deliverable-aware: validates against actual acceptance criteria
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    from ..model import ChatModelBase
    from .sandbox_orchestrator import SandboxOrchestrator, SandboxTypeEnum

    # Forward reference for RuntimeWorkspace (defined in full_user_flow_cli.py)
    class RuntimeWorkspace:
        """Type stub for RuntimeWorkspace."""

        sandbox_id: str | None
        is_initialized: bool

        def execute_command(
            self, command: str, *, working_dir: str | None = None, timeout: int = 300
        ) -> dict: ...

        def read_file(self, path: str) -> str: ...

        def list_directory(self, path: str = "") -> list[str]: ...


class AcceptanceStatus(str, Enum):
    """Status of acceptance validation."""

    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some checks passed, some failed
    ERROR = "error"  # Validation itself failed to run


class ValidationEnvironment(str, Enum):
    """Environment type for validation execution."""

    CLI = "cli"  # Command line execution
    BROWSER = "browser"  # Browser automation (Playwright)
    API = "api"  # HTTP API testing
    GUI = "gui"  # Desktop GUI automation
    MOBILE = "mobile"  # Mobile app testing
    VISUAL = "visual"  # Screenshot comparison


@dataclass
class ValidationCheck:
    """A single validation check result."""

    name: str
    description: str
    environment: ValidationEnvironment
    action: dict[str, Any]  # LLM-defined action to execute
    passed: bool
    output: str = ""
    error: str | None = None
    screenshot: str | None = None  # Path to screenshot if applicable


@dataclass
class AcceptanceResult:
    """Result of acceptance validation."""

    status: AcceptanceStatus
    score: float  # 0.0 to 1.0
    checks: list[ValidationCheck] = field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)
    deliverable_assessment: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Whether acceptance passed."""
        return self.status == AcceptanceStatus.PASSED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "score": self.score,
            "passed": self.passed,
            "summary": self.summary,
            "checks": [
                {
                    "name": c.name,
                    "description": c.description,
                    "environment": c.environment.value,
                    "passed": c.passed,
                    "output": c.output[:500] if c.output else "",
                    "error": c.error,
                    "screenshot": c.screenshot,
                }
                for c in self.checks
            ],
            "recommendations": self.recommendations,
            "deliverable_assessment": self.deliverable_assessment,
        }


# Prompt for LLM to generate validation strategy
VALIDATION_STRATEGY_PROMPT = '''你是一个智能验收专家。根据以下信息，生成验收策略。

## 用户原始需求
{user_requirement}

## 交付标准
{acceptance_criteria}

## 产物类型
{artifact_type}

## 工作区文件
{file_list}

## 可用验收环境
{available_environments}

## 任务
分析产物和交付标准，生成验收策略。你需要：
1. 根据产物类型选择合适的验收环境
2. 设计验收步骤来验证是否满足交付标准
3. 不要假设任何特定框架 - 根据实际文件判断

输出JSON格式：
```json
{{
  "artifact_analysis": {{
    "detected_type": "检测到的产物类型",
    "main_components": ["主要组件列表"],
    "entry_points": ["入口点，如URL、命令等"]
  }},
  "validation_strategy": {{
    "approach": "验收方法总述",
    "environments_needed": ["需要的验收环境"]
  }},
  "validation_checks": [
    {{
      "name": "检查名称",
      "description": "检查什么，为什么重要",
      "acceptance_criterion": "对应哪条交付标准",
      "environment": "cli/browser/api/gui/mobile/visual",
      "action": {{
        "type": "动作类型",
        ... 动作参数
      }},
      "expected_result": "期望结果描述",
      "required": true/false
    }}
  ],
  "reasoning": "为什么选择这个验收策略"
}}
```

## 动作类型说明

### CLI动作 (environment: "cli")
```json
{{"type": "shell", "command": "要执行的命令", "timeout": 60}}
{{"type": "file_check", "paths": ["检查的文件路径"], "check": "exists/not_empty/contains"}}
```

### Browser动作 (environment: "browser")

**【重要】browser_snapshot 返回的是无障碍树（Accessibility Tree）格式，不是 HTML DOM！**

无障碍树格式示例：
```
- document [FOCUSED]
  - banner
    - heading "页面标题" [level=1]
    - navigation
      - link "首页"
      - link "关于"
  - main
    - region "内容区域"
      - paragraph
        - text "这是正文内容"
      - button "点击我"
```

因此：
- 【禁止】使用 CSS 选择器（如 "#id", ".class", "div > p"）- 不会工作
- 【推荐】使用 check_text 检查页面是否包含特定文本
- 【推荐】使用 check_title 检查页面标题
- 【可用】check_element 的 selector 应该填写无障碍树中的角色名或文本片段

```json
{{"type": "navigate", "url": "http://localhost:3000"}}
{{"type": "screenshot", "name": "截图名称"}}
{{"type": "check_text", "text": "期望在页面中出现的文本"}}
{{"type": "check_title", "title": "期望的页面标题"}}
{{"type": "check_element", "selector": "button/link/heading等角色或文本片段", "check": "exists/text_contains", "value": "期望值"}}
{{"type": "click", "element": "按钮或链接的文本/角色描述"}}
{{"type": "input", "element": "输入框的文本/角色描述", "value": "输入值"}}
{{"type": "wait", "timeout": 5000}}
```

验证示例（正确方式）：
- 验证页面有标题 → {{"type": "check_text", "text": "新品发布"}}
- 验证有导航链接 → {{"type": "check_text", "text": "首页"}}
- 验证有按钮 → {{"type": "check_element", "selector": "button", "check": "exists"}}
- 验证特定文本存在 → {{"type": "check_text", "text": "欢迎使用"}}

### API动作 (environment: "api")
```json
{{"type": "request", "method": "GET/POST/PUT/DELETE", "url": "API地址", "headers": {{}}, "body": {{}}}}
{{"type": "check_response", "status": 200, "body_contains": "期望内容"}}
```

注意：
- 根据产物类型选择合适的验收环境
- Web应用必须用浏览器环境验收UI
- API服务用API环境验收
- 后端代码用CLI环境验收
- 验收步骤要能验证交付标准是否满足
- 【重要】浏览器环境使用无障碍树，不支持 CSS 选择器！请用 check_text 和 check_title 验证
- 【重要】验证页面内容时，使用 check_text 检查具体文本是否存在
'''

# Prompt for analyzing validation results
RESULT_ANALYSIS_PROMPT = '''你是一个验收专家。根据以下验收结果，判断产物是否满足交付标准。

## 用户原始需求
{user_requirement}

## 交付标准
{acceptance_criteria}

## 验收结果
{results}

## 任务
分析验收结果，对照交付标准给出判断：
1. 每条交付标准是否满足
2. 总体是否通过验收
3. 具体问题和改进建议

输出JSON格式：
```json
{{
  "deliverable_assessment": {{
    "criterion_1": {{"met": true/false, "evidence": "依据", "issues": []}},
    "criterion_2": {{"met": true/false, "evidence": "依据", "issues": []}}
  }},
  "status": "passed/failed/partial",
  "score": 0-100,
  "summary": "验收总结，说明产物是否满足需求",
  "critical_issues": ["严重问题列表"],
  "recommendations": ["改进建议"]
}}
```
'''


class AcceptanceAgent:
    """LLM-driven acceptance agent for multi-environment validation.

    This agent:
    1. Analyzes deliverables to understand what needs validation
    2. Uses LLM to decide which sandbox environments to use
    3. Executes validation in appropriate environments
    4. Verifies deliverables meet acceptance criteria

    Supported environments:
    - CLI: Shell commands, file checks, test execution
    - Browser: Web UI testing with Playwright
    - API: HTTP endpoint testing
    - GUI: Desktop application testing
    - Mobile: Mobile app testing

    Example:
        >>> agent = AcceptanceAgent(model=model, orchestrator=orchestrator)
        >>> result = await agent.validate(
        ...     workspace_dir="/workspace",
        ...     user_requirement="创建一个健身系统",
        ...     acceptance_criteria=["后端API可访问", "前端页面可正常显示"],
        ...     artifact_type="web",
        ... )
        >>> if result.passed:
        ...     print("验收通过")
        ... else:
        ...     for issue in result.recommendations:
        ...         print(f"问题: {issue}")
    """

    def __init__(
        self,
        *,
        model: "ChatModelBase",
        sandbox_orchestrator: "SandboxOrchestrator | None" = None,
        runtime_workspace: "RuntimeWorkspace | None" = None,
        playwright_mcp: "Any | None" = None,
        http_port: int | None = None,
        default_timeout: int = 120,
    ) -> None:
        """Initialize acceptance agent.

        Args:
            model: LLM model for generating validation strategies.
            sandbox_orchestrator: Orchestrator for multi-sandbox execution.
            runtime_workspace: RuntimeWorkspace instance for executing in same Docker sandbox.
                If provided, will be used instead of creating new sandboxes.
            playwright_mcp: Playwright MCP client for browser testing.
                Can be StatefulClientBase or BrowserSandboxManager.
            http_port: HTTP server port for serving web content to browser.
            default_timeout: Default timeout for validation actions.
        """
        self._model = model
        self._orchestrator = sandbox_orchestrator
        self._runtime_workspace = runtime_workspace
        self._playwright_mcp = playwright_mcp
        self._http_port = http_port
        self._default_timeout = default_timeout

    async def validate(
        self,
        *,
        workspace_dir: str = "/workspace",
        user_requirement: str = "",
        acceptance_criteria: list[str] | None = None,
        artifact_type: str = "web",
        file_list: list[str] | None = None,
        serve_url: str | None = None,
    ) -> AcceptanceResult:
        """Run acceptance validation on deliverables.

        Args:
            workspace_dir: Directory containing project files.
            user_requirement: Original user requirement.
            acceptance_criteria: List of acceptance criteria to verify.
            artifact_type: Type of artifact (web, api, cli, mobile, etc.).
            file_list: List of files in workspace (auto-detected if None).
            serve_url: URL where the app is served (for browser validation).

        Returns:
            AcceptanceResult with validation status and details.
        """
        # Step 1: Get file list if not provided
        if file_list is None:
            file_list = await self._list_workspace_files(workspace_dir)

        if not file_list:
            return AcceptanceResult(
                status=AcceptanceStatus.ERROR,
                score=0.0,
                summary="工作区为空，没有找到任何文件",
                recommendations=["请先生成项目文件"],
            )

        # Step 2: Generate validation strategy using LLM
        criteria_str = "\n".join(
            f"- {i+1}. {c}" for i, c in enumerate(acceptance_criteria or [])
        )
        if not criteria_str:
            criteria_str = "- 项目文件完整\n- 代码可运行\n- 基本功能正常"

        available_envs = self._get_available_environments()

        strategy = await self._generate_validation_strategy(
            user_requirement=user_requirement,
            acceptance_criteria=criteria_str,
            artifact_type=artifact_type,
            file_list=file_list,
            available_environments=available_envs,
        )

        if strategy is None:
            return AcceptanceResult(
                status=AcceptanceStatus.ERROR,
                score=0.0,
                summary="无法生成验收策略",
                recommendations=["请检查LLM配置"],
            )

        # Step 2.5: Prepare services (install deps & start services) if needed
        needs_api = any(
            c.get("environment") == "api"
            for c in strategy.get("validation_checks", [])
        )
        service_info = None
        service_prep_failed = False
        service_prep_errors: list[str] = []
        if needs_api:
            logger.info("Detected API validation checks, preparing services...")
            prep_result = await self._prepare_services(
                workspace_dir=workspace_dir,
                file_list=file_list,
                artifact_type=artifact_type,
            )
            if prep_result.get("services"):
                service_info = prep_result
            if not prep_result.get("success"):
                service_prep_failed = True
                service_prep_errors = prep_result.get("errors", [])
                logger.warning(
                    "Service preparation failed: %s",
                    "; ".join(service_prep_errors),
                )

        # Step 3: Execute validation checks in appropriate environments
        checks = await self._execute_validation_checks(
            strategy=strategy,
            workspace_dir=workspace_dir,
            serve_url=serve_url,
            skip_api_if_service_failed=service_prep_failed,
            service_prep_errors=service_prep_errors,
        )

        # Step 4: Analyze results using LLM
        result = await self._analyze_results(
            checks=checks,
            user_requirement=user_requirement,
            acceptance_criteria=criteria_str,
        )

        return result

    async def _call_model(self, prompt: str) -> Any:
        """Call the LLM model with proper format.

        Handles different model types (OpenAIChatModel, etc.) with their
        expected input formats.
        """
        from ..message import Msg

        msg = Msg(name="acceptance_agent", role="user", content=prompt)

        # OpenAIChatModel 使用 __call__ 方法，期望 list[dict]
        if hasattr(self._model, "__call__") and not hasattr(self._model, "reply"):
            messages = [{"role": "user", "content": prompt}]
            return await self._model(messages)

        # 其他模型使用 reply 方法
        if hasattr(self._model, "reply"):
            return await self._model.reply(msg)

        raise AttributeError("Model has no reply or __call__ method")

    def _extract_text_content(self, response: Any) -> str:
        """Extract text content from model response.

        Handles different response formats:
        - ChatResponse with content list of TextBlock/TypedDict
        - Dict with content field
        - Msg with content attribute
        - Plain string
        """
        # Handle None
        if response is None:
            return ""

        # Handle string directly
        if isinstance(response, str):
            return response

        # Handle ChatResponse or dict-like with 'content' field
        content = None
        if hasattr(response, "content"):
            content = response.content
        elif isinstance(response, dict) and "content" in response:
            content = response["content"]

        if content is None:
            return str(response)

        # Handle list of blocks (TextBlock, etc.)
        if isinstance(content, (list, tuple)):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    # TextBlock is TypedDict, access via ["text"]
                    if block.get("type") == "text" and "text" in block:
                        text_parts.append(block["text"])
                    elif "text" in block:
                        text_parts.append(block["text"])
                elif hasattr(block, "text"):
                    # Object with text attribute
                    text_parts.append(block.text)
            return "\n".join(text_parts) if text_parts else str(content)

        # Handle string content
        if isinstance(content, str):
            return content

        return str(content)

    def _get_available_environments(self) -> str:
        """Get description of available validation environments."""
        envs = []

        # Always available
        envs.append("- cli: 命令行执行（shell命令、文件检查、测试运行）")

        # Check sandbox capabilities
        from .sandbox_orchestrator import SandboxTypeEnum

        envs.append("- browser: 浏览器自动化（Playwright，用于Web UI测试）")
        envs.append("- api: HTTP API测试（请求发送、响应验证）")

        # Optional based on orchestrator config
        envs.append("- gui: 桌面应用测试（Computer Use）")
        envs.append("- mobile: 移动应用测试")
        envs.append("- visual: 视觉对比（截图对比）")

        return "\n".join(envs)

    async def _list_workspace_files(self, workspace_dir: str) -> list[str]:
        """List files in workspace directory."""
        # Prefer RuntimeWorkspace if available (uses same Docker sandbox)
        if self._runtime_workspace and self._runtime_workspace.is_initialized:
            try:
                # RuntimeWorkspace uses /workspace as base, so we list from root
                files = self._runtime_workspace.list_directory("")
                if files:
                    # Recursively get all files
                    all_files = []
                    self._collect_files_recursive(all_files, "", files)
                    return all_files[:100]
            except Exception as exc:
                logger.warning("Failed to list files via RuntimeWorkspace: %s", exc)

        # Fallback to SandboxOrchestrator
        if self._orchestrator:
            try:
                result = self._orchestrator.execute_command(
                    f"find {workspace_dir} -type f -name '*' | head -100",
                    timeout=30,
                )
                if result.success:
                    files = [
                        f.replace(workspace_dir + "/", "")
                        for f in result.output.strip().split("\n")
                        if f
                    ]
                    return files
            except Exception as exc:
                logger.warning("Failed to list workspace files: %s", exc)

        return []

    def _collect_files_recursive(
        self, all_files: list[str], prefix: str, entries: list[str]
    ) -> None:
        """Recursively collect files from directory listing."""
        for entry in entries:
            if entry.startswith(".") or entry.startswith("_"):
                continue
            full_path = f"{prefix}/{entry}" if prefix else entry
            try:
                # Try to list as directory
                sub_entries = self._runtime_workspace.list_directory(full_path)
                if sub_entries:
                    self._collect_files_recursive(all_files, full_path, sub_entries)
                else:
                    all_files.append(full_path)
            except Exception:
                # Probably a file, not a directory
                all_files.append(full_path)

    async def _generate_validation_strategy(
        self,
        *,
        user_requirement: str,
        acceptance_criteria: str,
        artifact_type: str,
        file_list: list[str],
        available_environments: str,
    ) -> dict[str, Any] | None:
        """Use LLM to generate validation strategy."""
        prompt = VALIDATION_STRATEGY_PROMPT.format(
            user_requirement=user_requirement or "未指定",
            acceptance_criteria=acceptance_criteria,
            artifact_type=artifact_type,
            file_list="\n".join(f"- {f}" for f in file_list[:50]),
            available_environments=available_environments,
        )

        try:
            response = await self._call_model(prompt)
            content = self._extract_text_content(response)

            strategy = self._extract_json(content)
            if strategy and "validation_checks" in strategy:
                logger.info(
                    "Generated validation strategy with %d checks",
                    len(strategy["validation_checks"]),
                )
                return strategy
        except Exception as exc:
            logger.error("Failed to generate validation strategy: %s", exc)

        return None

    async def _prepare_services(
        self,
        *,
        workspace_dir: str,
        file_list: list[str],
        artifact_type: str,
    ) -> dict[str, Any]:
        """Prepare services using framework-specific agents.

        This method:
        1. Uses FrameworkDetector to identify frameworks in the project
        2. Gets startup strategy from framework-specific agents
        3. Falls back to LLM if no framework is detected
        4. Executes commands to install deps and start services

        Returns:
            dict with keys: success, services, errors
        """
        result = {
            "success": False,
            "services": [],
            "errors": [],
        }

        # Use LLM to generate startup strategy
        startup_strategy = await self._generate_startup_strategy(
            workspace_dir=workspace_dir,
            file_list=file_list,
            artifact_type=artifact_type,
        )

        if not startup_strategy:
            result["errors"].append("Failed to generate startup strategy")
            return result

        commands = startup_strategy.get("commands", [])

        # Execute startup commands
        for cmd_spec in commands:
            cmd = cmd_spec.get("command", "")
            desc = cmd_spec.get("description", cmd[:50])
            cmd_working_dir = cmd_spec.get("working_dir", "")
            timeout = cmd_spec.get("timeout", 120)
            background = cmd_spec.get("background", False)

            # Handle working_dir: RuntimeWorkspace.execute_command expects
            # a path RELATIVE to workspace_dir (it will prepend workspace_dir)
            # So we need to extract just the relative part

            # Strip /workspace prefix if LLM returned absolute path
            if cmd_working_dir.startswith("/workspace/"):
                cmd_working_dir = cmd_working_dir[len("/workspace/"):]
            elif cmd_working_dir == "/workspace":
                cmd_working_dir = ""

            # Also strip workspace_dir prefix if it was included
            if cmd_working_dir.startswith(workspace_dir + "/"):
                cmd_working_dir = cmd_working_dir[len(workspace_dir) + 1:]
            elif cmd_working_dir == workspace_dir:
                cmd_working_dir = ""

            # Now cmd_working_dir should be relative (e.g., "backend", "frontend")
            # or empty string for workspace root
            # Pass it directly - RuntimeWorkspace will prepend workspace_dir
            effective_working_dir = cmd_working_dir if cmd_working_dir else None

            if not cmd:
                continue

            logger.info("Executing: %s", desc)

            # For background commands, wrap with nohup
            if background:
                cmd = f"nohup {cmd} > /tmp/service_{len(result['services'])}.log 2>&1 & echo $!"

            exec_result = self._execute_command_in_workspace(
                cmd,
                working_dir=effective_working_dir,
                timeout=timeout,
            )

            if exec_result["success"]:
                logger.info("Success: %s", desc)
                if background and exec_result["output"].strip():
                    result["services"].append({
                        "description": desc,
                        "pid": exec_result["output"].strip(),
                    })
            else:
                error_msg = f"{desc}: {exec_result['error'][:200]}"
                result["errors"].append(error_msg)
                logger.warning("Failed: %s", error_msg)

                # Check if this is a critical command
                if cmd_spec.get("critical", False):
                    return result

        # Wait for services to initialize if any were started
        if result["services"]:
            wait_time = startup_strategy.get("wait_after_start", 3)
            logger.info("Waiting %ds for services to initialize...", wait_time)
            await asyncio.sleep(wait_time)

        result["success"] = len(result["errors"]) == 0
        return result

    async def _generate_startup_strategy(
        self,
        *,
        workspace_dir: str,
        file_list: list[str],
        artifact_type: str,
    ) -> dict[str, Any] | None:
        """Use LLM to generate service startup strategy."""
        # Show first 50 files to avoid token overflow
        files_str = "\n".join(file_list[:50])
        if len(file_list) > 50:
            files_str += f"\n... and {len(file_list) - 50} more files"

        prompt = f'''你是一个 DevOps 专家。分析以下项目文件，生成启动服务所需的命令。

## 工作区目录
{workspace_dir}

## 项目文件
{files_str}

## 产物类型
{artifact_type}

## 任务
分析项目结构，生成启动服务所需的命令序列。你需要：
1. 识别项目类型（Python/Node.js/Go/Java 等）
2. 确定依赖安装命令
3. 确定服务启动命令
4. 确定服务运行的端口

输出JSON格式：
```json
{{
  "project_analysis": {{
    "type": "项目类型",
    "framework": "使用的框架",
    "entry_point": "入口文件"
  }},
  "commands": [
    {{
      "description": "命令描述",
      "command": "要执行的命令",
      "working_dir": "相对路径，如 backend 或 frontend，或留空表示根目录",
      "timeout": 120,
      "background": false,
      "critical": true
    }}
  ],
  "services": [
    {{
      "name": "服务名称",
      "port": 8000,
      "health_check": "http://localhost:8000/health"
    }}
  ],
  "wait_after_start": 3
}}
```

【重要】working_dir 使用规则：
- 使用**相对路径**，如 "backend" 或 "frontend"，不要使用绝对路径
- 如果命令需要在根目录执行，working_dir 设为空字符串 ""
- 错误示例："/workspace/backend"（不要这样写）
- 正确示例："backend"（这样写）

注意：
- 【重要】只根据上面列出的实际文件来生成命令，不要假设文件存在
- 如果没有 requirements.txt，不要执行 pip install -r requirements.txt
- 如果没有 package.json，不要执行 npm install
- 依赖安装命令应该在服务启动命令之前
- 后台服务需要设置 "background": true
- critical 表示如果命令失败是否应该中止后续命令
- 根据实际项目配置确定端口号，不要假设固定端口
- 如果是 Python FastAPI 项目，使用 uvicorn 启动
- 如果是 Node.js 项目，使用 npm run dev 或 npm start
- 对于简单的静态 HTML 页面，不需要启动任何服务，返回空的 commands 列表
'''

        try:
            response = await self._call_model(prompt)
            content = self._extract_text_content(response)
            strategy = self._extract_json(content)

            if strategy and "commands" in strategy:
                logger.info(
                    "Generated startup strategy with %d commands",
                    len(strategy["commands"]),
                )
                return strategy
        except Exception as exc:
            logger.error("Failed to generate startup strategy: %s", exc)

        return None

    async def _execute_validation_checks(
        self,
        *,
        strategy: dict[str, Any],
        workspace_dir: str,
        serve_url: str | None,
        skip_api_if_service_failed: bool = False,
        service_prep_errors: list[str] | None = None,
    ) -> list[ValidationCheck]:
        """Execute validation checks in appropriate environments.

        Args:
            strategy: Validation strategy with checks to execute.
            workspace_dir: Workspace directory path.
            serve_url: URL for browser tests.
            skip_api_if_service_failed: If True, skip API checks and mark as failed.
            service_prep_errors: Error messages from service preparation.
        """
        checks: list[ValidationCheck] = []

        for check_spec in strategy.get("validation_checks", []):
            name = check_spec.get("name", "Unknown")
            description = check_spec.get("description", "")
            env_str = check_spec.get("environment", "cli")
            action = check_spec.get("action", {})

            try:
                env = ValidationEnvironment(env_str)
            except ValueError:
                env = ValidationEnvironment.CLI

            logger.info("Running validation: %s (env=%s)", name, env.value)

            try:
                if env == ValidationEnvironment.CLI:
                    check = await self._execute_cli_check(
                        name=name,
                        description=description,
                        action=action,
                        workspace_dir=workspace_dir,
                    )
                elif env == ValidationEnvironment.BROWSER:
                    check = await self._execute_browser_check(
                        name=name,
                        description=description,
                        action=action,
                        serve_url=serve_url,
                    )
                elif env == ValidationEnvironment.API:
                    # Skip API checks if service preparation failed
                    if skip_api_if_service_failed:
                        error_msg = "服务启动失败，跳过 API 验证"
                        if service_prep_errors:
                            error_msg += f": {'; '.join(service_prep_errors[:2])}"
                        check = ValidationCheck(
                            name=name,
                            description=description,
                            environment=env,
                            action=action,
                            passed=False,
                            error=error_msg,
                        )
                    else:
                        check = await self._execute_api_check(
                            name=name,
                            description=description,
                            action=action,
                        )
                else:
                    # Unsupported environment - try CLI fallback
                    check = ValidationCheck(
                        name=name,
                        description=description,
                        environment=env,
                        action=action,
                        passed=False,
                        error=f"Environment {env.value} not yet implemented",
                    )
            except Exception as exc:
                check = ValidationCheck(
                    name=name,
                    description=description,
                    environment=env,
                    action=action,
                    passed=False,
                    error=str(exc),
                )

            checks.append(check)
            logger.info(
                "Validation '%s': %s",
                name,
                "PASSED" if check.passed else "FAILED",
            )

        return checks

    def _execute_command_in_workspace(
        self, command: str, *, working_dir: str | None = None, timeout: int = 300
    ) -> dict[str, Any]:
        """Execute command using RuntimeWorkspace or SandboxOrchestrator.

        Returns dict with keys: success, output, error
        """
        # Prefer RuntimeWorkspace if available (same Docker sandbox)
        if self._runtime_workspace and self._runtime_workspace.is_initialized:
            result = self._runtime_workspace.execute_command(
                command, working_dir=working_dir, timeout=timeout
            )
            return {
                "success": result.get("success", False),
                "output": result.get("output", ""),
                "error": result.get("error", ""),
            }

        # Fallback to SandboxOrchestrator
        if self._orchestrator:
            result = self._orchestrator.execute_command(
                command, working_dir=working_dir, timeout=timeout
            )
            return {
                "success": result.success,
                "output": result.output or "",
                "error": result.error or "",
            }

        return {"success": False, "output": "", "error": "No execution backend available"}

    async def _execute_cli_check(
        self,
        *,
        name: str,
        description: str,
        action: dict[str, Any],
        workspace_dir: str,
    ) -> ValidationCheck:
        """Execute a CLI validation check."""
        action_type = action.get("type", "shell")

        if action_type == "shell":
            command = action.get("command", "echo 'no command'")
            timeout = action.get("timeout", self._default_timeout)

            # Use unified execution method (prefers RuntimeWorkspace)
            result = self._execute_command_in_workspace(
                command, working_dir=workspace_dir, timeout=timeout
            )

            return ValidationCheck(
                name=name,
                description=description,
                environment=ValidationEnvironment.CLI,
                action=action,
                passed=result["success"],
                output=result["output"][:2000] if result["output"] else "",
                error=result["error"] if not result["success"] else None,
            )

        elif action_type == "file_check":
            paths = action.get("paths", [])
            check_type = action.get("check", "exists")

            all_passed = True
            outputs = []

            for path in paths:
                full_path = f"{workspace_dir}/{path}"
                if check_type == "exists":
                    result = self._execute_command_in_workspace(
                        f"test -e {full_path} && echo 'EXISTS' || echo 'NOT_FOUND'",
                        timeout=10,
                    )
                    passed = "EXISTS" in result["output"]
                elif check_type == "not_empty":
                    result = self._execute_command_in_workspace(
                        f"test -s {full_path} && echo 'NOT_EMPTY' || echo 'EMPTY'",
                        timeout=10,
                    )
                    passed = "NOT_EMPTY" in result["output"]
                else:
                    passed = False

                outputs.append(f"{path}: {'OK' if passed else 'FAILED'}")
                if not passed:
                    all_passed = False

            return ValidationCheck(
                name=name,
                description=description,
                environment=ValidationEnvironment.CLI,
                action=action,
                passed=all_passed,
                output="\n".join(outputs),
            )

        return ValidationCheck(
            name=name,
            description=description,
            environment=ValidationEnvironment.CLI,
            action=action,
            passed=False,
            error=f"Unknown CLI action type: {action_type}",
        )

    async def _execute_browser_check(
        self,
        *,
        name: str,
        description: str,
        action: dict[str, Any],
        serve_url: str | None,
    ) -> ValidationCheck:
        """Execute a browser validation check using Playwright MCP or BrowserSandbox.

        Supports two backends:
        1. BrowserSandboxManager (sync): Uses agentscope-runtime's BrowserSandbox
        2. StatefulClientBase (async): Uses Playwright MCP via stdio

        The backend is determined by self._playwright_mcp type.
        """
        action_type = action.get("type", "navigate")

        # Check if playwright_mcp is available
        if self._playwright_mcp is None:
            return ValidationCheck(
                name=name,
                description=description,
                environment=ValidationEnvironment.BROWSER,
                action=action,
                passed=False,
                error="Browser testing not available: playwright_mcp not configured",
            )

        # Determine URL - prefer serve_url (for Docker), then http_port, then default
        if serve_url:
            default_url = serve_url
        elif self._http_port:
            default_url = f"http://localhost:{self._http_port}"
        else:
            default_url = "http://localhost:3000"

        try:
            # Check if using BrowserSandboxManager (sync) or StatefulClientBase (async)
            is_browser_sandbox = hasattr(self._playwright_mcp, "browser_navigate")

            if action_type == "navigate":
                url = action.get("url", default_url)
                # For BrowserSandbox (Docker), replace localhost with host.docker.internal
                if is_browser_sandbox and serve_url and "host.docker.internal" in serve_url:
                    # Extract port from serve_url and replace localhost URLs
                    import re
                    port_match = re.search(r":(\d+)", serve_url)
                    if port_match:
                        port = port_match.group(1)
                        # Replace localhost:any_port or localhost (without port) with serve_url base
                        url = re.sub(
                            r"http://localhost(:\d+)?",
                            f"http://host.docker.internal:{port}",
                            url,
                        )
                if is_browser_sandbox:
                    result = self._playwright_mcp.browser_navigate(url)
                    # Wait for page load
                    self._playwright_mcp.browser_wait_for(time=1.0)
                else:
                    result = await self._playwright_mcp.session.call_tool(
                        "browser_navigate",
                        arguments={"url": url}
                    )
                    await asyncio.sleep(1)

                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=True,  # Navigation success if no exception
                    output=str(result)[:1000],
                )

            elif action_type == "screenshot":
                screenshot_name = action.get("name", "screenshot")
                if is_browser_sandbox:
                    result = self._playwright_mcp.browser_take_screenshot(filename=screenshot_name)
                else:
                    result = await self._playwright_mcp.session.call_tool(
                        "browser_take_screenshot",
                        arguments={}
                    )
                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=True,
                    output="Screenshot taken",
                    screenshot=str(result)[:500] if result else None,
                )

            elif action_type == "check_element":
                selector = action.get("selector", "body")
                check = action.get("check", "exists")
                value = action.get("value", "")

                # Get page snapshot to check elements
                if is_browser_sandbox:
                    snapshot = self._playwright_mcp.browser_snapshot()
                else:
                    snapshot = await self._playwright_mcp.session.call_tool(
                        "browser_snapshot",
                        arguments={}
                    )

                snapshot_str = str(snapshot)
                passed = False
                output = ""

                if check == "exists":
                    # Check if selector appears in snapshot
                    passed = selector in snapshot_str
                    output = f"Element '{selector}' {'found' if passed else 'not found'} in page"
                elif check == "visible":
                    # For visibility, we check if it's in snapshot (simplification)
                    passed = selector in snapshot_str
                    output = f"Element '{selector}' visibility: {passed}"
                elif check == "text_contains" and value:
                    passed = value in snapshot_str
                    output = f"Text '{value}' {'found' if passed else 'not found'} in page"

                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=passed,
                    output=output,
                )

            elif action_type == "click":
                # 支持 element (新) 和 selector (兼容旧)
                element = action.get("element") or action.get("selector", "")
                if is_browser_sandbox:
                    result = self._playwright_mcp.browser_click(element=element)
                else:
                    result = await self._playwright_mcp.session.call_tool(
                        "browser_click",
                        arguments={"element": element}
                    )
                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=True,  # Success if no exception
                    output=str(result)[:500],
                )

            elif action_type == "input":
                # 支持 element (新) 和 selector (兼容旧)
                element = action.get("element") or action.get("selector", "")
                value = action.get("value", "")
                if is_browser_sandbox:
                    result = self._playwright_mcp.browser_type(element=element, text=value)
                else:
                    result = await self._playwright_mcp.session.call_tool(
                        "browser_type",
                        arguments={"element": element, "text": value}
                    )
                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=True,  # Success if no exception
                    output=str(result)[:500],
                )

            elif action_type == "wait":
                # timeout 单位为毫秒，转换为秒
                wait_time = action.get("timeout", 1000) / 1000.0
                if is_browser_sandbox:
                    try:
                        self._playwright_mcp.browser_wait_for(time=wait_time)
                    except Exception:
                        # 如果 wait_for 不支持，使用 sleep
                        await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(wait_time)
                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=True,
                    output=f"Waited {wait_time}s",
                )

            elif action_type == "check_title":
                expected_title = action.get("title", "")
                if is_browser_sandbox:
                    snapshot = self._playwright_mcp.browser_snapshot()
                else:
                    snapshot = await self._playwright_mcp.session.call_tool(
                        "browser_snapshot",
                        arguments={}
                    )
                snapshot_str = str(snapshot)
                passed = expected_title in snapshot_str if expected_title else True
                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=passed,
                    output=f"Title check: expected '{expected_title}', found: {passed}",
                )

            elif action_type == "check_text":
                expected_text = action.get("text", "")
                if is_browser_sandbox:
                    snapshot = self._playwright_mcp.browser_snapshot()
                else:
                    snapshot = await self._playwright_mcp.session.call_tool(
                        "browser_snapshot",
                        arguments={}
                    )
                snapshot_str = str(snapshot)
                passed = expected_text in snapshot_str if expected_text else True
                return ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.BROWSER,
                    action=action,
                    passed=passed,
                    output=f"Text '{expected_text}' {'found' if passed else 'not found'} in page",
                )

        except Exception as exc:
            logger.warning("Browser check '%s' failed: %s", name, exc)
            return ValidationCheck(
                name=name,
                description=description,
                environment=ValidationEnvironment.BROWSER,
                action=action,
                passed=False,
                error=str(exc),
            )

        return ValidationCheck(
            name=name,
            description=description,
            environment=ValidationEnvironment.BROWSER,
            action=action,
            passed=False,
            error=f"Unknown browser action type: {action_type}",
        )

    async def _execute_api_check(
        self,
        *,
        name: str,
        description: str,
        action: dict[str, Any],
    ) -> ValidationCheck:
        """Execute an API validation check."""
        action_type = action.get("type", "request")

        if action_type == "request":
            method = action.get("method", "GET")
            url = action.get("url", "")
            headers = action.get("headers", {})
            body = action.get("body", {})
            expected_status = action.get("expected_status", 200)

            # Use curl in CLI for API testing
            # --connect-timeout: 连接超时（秒）
            # -m/--max-time: 总超时（秒）
            header_args = " ".join(f'-H "{k}: {v}"' for k, v in headers.items())
            body_arg = f"-d '{json.dumps(body)}'" if body else ""

            cmd = f"curl --connect-timeout 5 -m 15 -s -o /dev/null -w '%{{http_code}}' -X {method} {header_args} {body_arg} '{url}'"

            # Use unified execution method (prefers RuntimeWorkspace)
            result = self._execute_command_in_workspace(cmd, timeout=30)

            status_code = result["output"].strip() if result["output"] else "0"
            passed = status_code == str(expected_status)

            return ValidationCheck(
                name=name,
                description=description,
                environment=ValidationEnvironment.API,
                action=action,
                passed=passed,
                output=f"Status: {status_code} (expected: {expected_status})",
                error=result["error"] if not passed else None,
            )

        return ValidationCheck(
            name=name,
            description=description,
            environment=ValidationEnvironment.API,
            action=action,
            passed=False,
            error=f"Unknown API action type: {action_type}",
        )

    async def _analyze_results(
        self,
        *,
        checks: list[ValidationCheck],
        user_requirement: str,
        acceptance_criteria: str,
    ) -> AcceptanceResult:
        """Use LLM to analyze validation results against acceptance criteria."""
        if not checks:
            return AcceptanceResult(
                status=AcceptanceStatus.ERROR,
                score=0.0,
                summary="没有执行任何验收检查",
            )

        # Format results for LLM
        results_str = json.dumps(
            [
                {
                    "name": c.name,
                    "description": c.description,
                    "environment": c.environment.value,
                    "passed": c.passed,
                    "output": c.output[:500] if c.output else "",
                    "error": c.error,
                }
                for c in checks
            ],
            ensure_ascii=False,
            indent=2,
        )

        prompt = RESULT_ANALYSIS_PROMPT.format(
            user_requirement=user_requirement or "未指定",
            acceptance_criteria=acceptance_criteria,
            results=results_str,
        )

        try:
            response = await self._call_model(prompt)
            content = self._extract_text_content(response)

            analysis = self._extract_json(content)
            if analysis:
                status_str = analysis.get("status", "failed")
                status = AcceptanceStatus(status_str) if status_str in [
                    s.value for s in AcceptanceStatus
                ] else AcceptanceStatus.FAILED

                return AcceptanceResult(
                    status=status,
                    score=float(analysis.get("score", 0)) / 100.0,
                    checks=checks,
                    summary=analysis.get("summary", ""),
                    recommendations=analysis.get("recommendations", []),
                    deliverable_assessment=analysis.get("deliverable_assessment", {}),
                )
        except Exception as exc:
            logger.error("Failed to analyze results: %s", exc)

        # Fallback: simple pass ratio calculation
        passed_count = sum(1 for c in checks if c.passed)
        total_count = len(checks)
        score = passed_count / total_count if total_count > 0 else 0.0

        if score >= 0.8:
            status = AcceptanceStatus.PASSED
        elif score >= 0.5:
            status = AcceptanceStatus.PARTIAL
        else:
            status = AcceptanceStatus.FAILED

        return AcceptanceResult(
            status=status,
            score=score,
            checks=checks,
            summary=f"通过 {passed_count}/{total_count} 项检查",
        )

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        """Extract JSON from LLM response text."""
        import re

        # Try to find JSON in code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find bare JSON object
        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try parsing entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        return None

    def validate_sync(
        self,
        *,
        workspace_dir: str = "/workspace",
        user_requirement: str = "",
        acceptance_criteria: list[str] | None = None,
        artifact_type: str = "web",
        file_list: list[str] | None = None,
        serve_url: str | None = None,
    ) -> AcceptanceResult:
        """Synchronous wrapper for validate().

        For use in non-async contexts.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.validate(
                workspace_dir=workspace_dir,
                user_requirement=user_requirement,
                acceptance_criteria=acceptance_criteria,
                artifact_type=artifact_type,
                file_list=file_list,
                serve_url=serve_url,
            )
        )
