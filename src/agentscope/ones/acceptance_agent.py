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
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

from .._logging import logger


def _log_progress(
    msg: str,
    *,
    level: str = "info",
    hub: "Any | None" = None,
    event_type: str | None = None,
    metadata: dict | None = None,
    project_id: str | None = None,
) -> None:
    """Log progress with immediate flush for observability.

    Args:
        msg: Message to log.
        level: Log level (info, warning, error).
        hub: Optional ObservabilityHub instance for timeline tracking.
        event_type: Optional timeline event type for ObservabilityHub.
        metadata: Optional metadata for timeline event.
        project_id: Optional project ID for timeline event.
    """
    from datetime import datetime

    timestamp = time.strftime("%H:%M:%S")
    prefix = "[AcceptanceAgent]"
    formatted = f"{timestamp} | {prefix} {msg}"

    # Print with flush for immediate visibility
    print(formatted, flush=True)

    # Also log via logger for file logging
    if level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.info(msg)

    # Record to ObservabilityHub if provided
    if hub is not None and event_type is not None:
        try:
            from ..observability._types import TimelineEvent

            event = TimelineEvent(
                timestamp=datetime.now(),
                event_type=event_type,  # type: ignore[arg-type]
                project_id=project_id,
                agent_id="acceptance_agent",
                metadata={"message": msg, **(metadata or {})},
            )
            hub.record_timeline_event(event)
        except Exception:
            pass  # Don't fail on observability errors

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
    critical: bool = False  # If True, failure stops all subsequent checks
    phase: str = "function"  # dependency/compile/startup/function


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
                    "phase": c.phase,
                    "critical": c.critical,
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
分析产物和交付标准，生成验收策略。

### 【强制】验收必须按顺序覆盖以下阶段：

**阶段 1：依赖验证**（required=true, critical=true）
- 根据项目文件（如 requirements.txt、package.json、go.mod、Cargo.toml 等）验证依赖安装
- 必须执行实际的安装命令并检查输出是否有错误
- 检查安装命令的 exit code 和输出中是否包含 ERROR/error/failed 等关键词
- 此阶段失败意味着依赖不完整，代码无法运行

**阶段 2：编译/导入验证**（required=true, critical=true）
- 验证代码可以成功编译或导入，【禁止】只检查文件是否存在
- 根据项目类型执行相应的验证命令，例如：
  - Python 项目：执行 `python -c "from <main_module> import <entry>"` 验证导入无错误
  - TypeScript/前端项目：执行 `npm run build` 或 `npx tsc --noEmit` 验证编译
  - Go 项目：执行 `go build ./...` 验证编译
  - Rust 项目：执行 `cargo check` 验证编译
  - Java 项目：执行 `mvn compile` 或 `gradle build` 验证编译
- 此阶段失败意味着代码存在语法错误或类型错误，必须标记为 critical

**阶段 3：启动验证**（required=true, critical=true）
- 验证服务可以成功启动并保持运行
- 【禁止】只检查启动命令是否执行成功，必须验证服务确实在运行
- 验证方式：健康检查端点、端口监听检测、进程状态检查、日志无致命错误
- 对于后台服务，启动后等待数秒再验证服务状态

**阶段 4：功能验证**（根据交付标准设计）
- 验证业务功能是否满足用户需求和交付标准
- 使用 API 测试、浏览器测试等方式验证具体功能

### 【重要】验收规则：
- 阶段 1-3 的检查必须设置 "critical": true，任一失败则整体验收失败
- 不能跳过阶段 1-3 直接进行功能验证
- 每个阶段至少包含一个验证检查
- 根据实际文件判断项目类型，不要假设任何特定框架

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
      "phase": "dependency/compile/startup/function",
      "acceptance_criterion": "对应哪条交付标准",
      "environment": "cli/browser/api/gui/mobile/visual",
      "action": {{
        "type": "动作类型",
        ... 动作参数
      }},
      "expected_result": "期望结果描述",
      "required": true,
      "critical": true/false
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

### 【critical 检查规则】
- phase 为 dependency/compile/startup 的检查必须设置 "critical": true
- critical=true 的检查失败会导致整体验收立即失败，不会继续后续检查
- 必须先通过依赖、编译、启动验证，再进行功能验证
- 验收策略必须包含至少：1个依赖检查 + 1个编译/导入检查 + 1个启动检查
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

### 【重要】验收规则
- 验收结果包含 phase 字段（dependency/compile/startup/function）和 critical 字段
- 【强制】如果任何 critical=true 的检查失败，整体验收必须为 "failed"，score=0
- 【强制】dependency/compile/startup 阶段的失败不能被忽略，这些是代码可运行的前提
- 只有当所有 critical 检查都通过后，才根据功能验证结果判断最终状态

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
        project_id: str | None = None,
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
            project_id: Optional project ID for observability tracking.
        """
        self._model = model
        self._orchestrator = sandbox_orchestrator
        self._runtime_workspace = runtime_workspace
        self._playwright_mcp = playwright_mcp
        self._http_port = http_port
        self._default_timeout = default_timeout
        self._project_id = project_id

        # Initialize ObservabilityHub for timeline tracking
        try:
            from ..observability import ObservabilityHub
            self._hub = ObservabilityHub()
        except Exception:
            self._hub = None

    def _emit_event(
        self,
        event_type: str,
        message: str,
        *,
        level: str = "info",
        metadata: dict | None = None,
    ) -> None:
        """Emit a progress event to console and ObservabilityHub.

        Args:
            event_type: Type of event (acceptance_start/end/step/check).
            message: Human-readable message.
            level: Log level (info, warning, error).
            metadata: Additional event metadata.
        """
        _log_progress(
            message,
            level=level,
            hub=self._hub,
            event_type=event_type,
            metadata=metadata,
            project_id=self._project_id,
        )

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
        validation_start = time.time()
        self._emit_event("acceptance_start", "=" * 60)
        self._emit_event(
            "acceptance_start",
            "🔍 开始验收流程",
            metadata={"artifact_type": artifact_type, "workspace": workspace_dir},
        )
        self._emit_event("acceptance_step", f"   产物类型: {artifact_type}")
        self._emit_event("acceptance_step", f"   工作区: {workspace_dir}")
        if acceptance_criteria:
            self._emit_event(
                "acceptance_step",
                f"   验收标准: {len(acceptance_criteria)} 条",
                metadata={"criteria_count": len(acceptance_criteria)},
            )

        # Step 1: Get file list if not provided
        if file_list is None:
            self._emit_event("acceptance_step", "📁 步骤1: 扫描工作区文件...")
            file_list = await self._list_workspace_files(workspace_dir)
            self._emit_event(
                "acceptance_step",
                f"   找到 {len(file_list)} 个文件",
                metadata={"file_count": len(file_list)},
            )

        if not file_list:
            return AcceptanceResult(
                status=AcceptanceStatus.ERROR,
                score=0.0,
                summary="工作区为空，没有找到任何文件",
                recommendations=["请先生成项目文件"],
            )

        # Step 2: Generate validation strategy using LLM
        self._emit_event("acceptance_step", "🧠 步骤2: 生成验收策略（调用LLM）...")
        strategy_start = time.time()

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

        strategy_elapsed = time.time() - strategy_start
        if strategy is None:
            self._emit_event(
                "acceptance_step",
                f"   ❌ 策略生成失败 (耗时: {strategy_elapsed:.1f}s)",
                level="error",
                metadata={"elapsed_s": strategy_elapsed, "success": False},
            )
            return AcceptanceResult(
                status=AcceptanceStatus.ERROR,
                score=0.0,
                summary="无法生成验收策略",
                recommendations=["请检查LLM配置"],
            )

        check_count = len(strategy.get("validation_checks", []))
        self._emit_event(
            "acceptance_step",
            f"   ✓ 策略生成完成 (耗时: {strategy_elapsed:.1f}s)",
            metadata={"elapsed_s": strategy_elapsed, "check_count": check_count},
        )
        self._emit_event("acceptance_step", f"   生成 {check_count} 个验收检查项")

        # Step 2.5: Prepare services (install deps & start services) if needed
        needs_api = any(
            c.get("environment") == "api"
            for c in strategy.get("validation_checks", [])
        )
        service_info = None
        service_prep_failed = False
        service_prep_errors: list[str] = []
        if needs_api:
            self._emit_event("acceptance_step", "🚀 步骤2.5: 准备服务（安装依赖、启动服务）...")
            prep_start = time.time()
            prep_result = await self._prepare_services(
                workspace_dir=workspace_dir,
                file_list=file_list,
                artifact_type=artifact_type,
            )
            prep_elapsed = time.time() - prep_start
            if prep_result.get("services"):
                service_info = prep_result
                self._emit_event(
                    "acceptance_step",
                    f"   ✓ 服务准备完成 (耗时: {prep_elapsed:.1f}s)",
                    metadata={"elapsed_s": prep_elapsed, "success": True},
                )
            if not prep_result.get("success"):
                service_prep_failed = True
                service_prep_errors = prep_result.get("errors", [])
                self._emit_event(
                    "acceptance_step",
                    f"   ⚠ 服务准备失败: {'; '.join(service_prep_errors[:2])}",
                    level="warning",
                    metadata={"errors": service_prep_errors},
                )

        # Step 3: Execute validation checks in appropriate environments
        self._emit_event("acceptance_step", f"✅ 步骤3: 执行 {check_count} 个验收检查...")
        checks_start = time.time()
        checks = await self._execute_validation_checks(
            strategy=strategy,
            workspace_dir=workspace_dir,
            serve_url=serve_url,
            skip_api_if_service_failed=service_prep_failed,
            service_prep_errors=service_prep_errors,
        )
        checks_elapsed = time.time() - checks_start

        # Summary of check results
        passed_checks = sum(1 for c in checks if c.passed)
        failed_checks = len(checks) - passed_checks
        self._emit_event(
            "acceptance_step",
            f"   检查完成 (耗时: {checks_elapsed:.1f}s)",
            metadata={"elapsed_s": checks_elapsed},
        )
        self._emit_event(
            "acceptance_step",
            f"   结果: ✓ {passed_checks} 通过, ✗ {failed_checks} 失败",
            metadata={"passed": passed_checks, "failed": failed_checks},
        )

        # Step 4: Analyze results using LLM
        self._emit_event("acceptance_step", "📊 步骤4: 分析验收结果（调用LLM）...")
        analyze_start = time.time()
        result = await self._analyze_results(
            checks=checks,
            user_requirement=user_requirement,
            acceptance_criteria=criteria_str,
        )
        analyze_elapsed = time.time() - analyze_start
        self._emit_event(
            "acceptance_step",
            f"   分析完成 (耗时: {analyze_elapsed:.1f}s)",
            metadata={"elapsed_s": analyze_elapsed},
        )

        # Final summary
        total_elapsed = time.time() - validation_start
        self._emit_event("acceptance_end", "=" * 60)
        status_emoji = "✅" if result.passed else "❌"
        self._emit_event(
            "acceptance_end",
            f"{status_emoji} 验收结果: {result.status.value.upper()}",
            metadata={
                "status": result.status.value,
                "score": result.score,
                "total_elapsed_s": total_elapsed,
            },
        )
        self._emit_event("acceptance_end", f"   得分: {result.score * 100:.0f}%")
        self._emit_event("acceptance_end", f"   总耗时: {total_elapsed:.1f}s")
        if result.summary:
            self._emit_event("acceptance_end", f"   摘要: {result.summary[:100]}...")
        self._emit_event("acceptance_end", "=" * 60)

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
                # Use relative path from workspace_dir to RuntimeWorkspace base
                # This handles cases where workspace_dir might be delivery_dir
                # or working_dir different from RuntimeWorkspace.workspace_dir
                rt_base = getattr(self._runtime_workspace, "base_workspace_dir", "/workspace")
                if workspace_dir.startswith(rt_base):
                    # Extract relative path from base
                    rel_path = workspace_dir[len(rt_base):].lstrip("/")
                else:
                    rel_path = ""
                files = self._runtime_workspace.list_directory(rel_path)
                if files:
                    # Recursively get all files
                    all_files = []
                    self._collect_files_recursive(all_files, "", files, base_path=rel_path)
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
        self,
        all_files: list[str],
        prefix: str,
        entries: list[str],
        *,
        base_path: str = "",
    ) -> None:
        """Recursively collect files from directory listing.

        Args:
            all_files: List to append file paths to.
            prefix: Current path prefix for file names.
            entries: Directory entries to process.
            base_path: Base path in container (e.g., "delivery" for /workspace/delivery).
        """
        for entry in entries:
            if entry.startswith(".") or entry.startswith("_"):
                continue
            # File path relative to workspace_dir (for returned results)
            file_path = f"{prefix}/{entry}" if prefix else entry
            # Container path for list_directory calls
            container_path = f"{base_path}/{file_path}".lstrip("/") if base_path else file_path
            try:
                # Try to list as directory
                sub_entries = self._runtime_workspace.list_directory(container_path)
                if sub_entries:
                    self._collect_files_recursive(
                        all_files, file_path, sub_entries, base_path=base_path
                    )
                else:
                    all_files.append(file_path)
            except Exception:
                # Probably a file, not a directory
                all_files.append(file_path)

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
        total_cmds = len(commands)
        for cmd_idx, cmd_spec in enumerate(commands, 1):
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

            _log_progress(f"      [{cmd_idx}/{total_cmds}] 执行: {desc}")
            _log_progress(f"               命令: {cmd[:80]}{'...' if len(cmd) > 80 else ''}")

            # For background commands, wrap with nohup
            if background:
                cmd = f"nohup {cmd} > /tmp/service_{len(result['services'])}.log 2>&1 & echo $!"

            cmd_start = time.time()
            exec_result = await self._execute_command_in_workspace(
                cmd,
                working_dir=effective_working_dir,
                timeout=timeout,
            )
            cmd_elapsed = time.time() - cmd_start

            if exec_result["success"]:
                _log_progress(f"               ✓ 成功 ({cmd_elapsed:.1f}s)")
                if background and exec_result["output"].strip():
                    result["services"].append({
                        "description": desc,
                        "pid": exec_result["output"].strip(),
                    })
            else:
                error_msg = f"{desc}: {exec_result['error'][:200]}"
                result["errors"].append(error_msg)
                _log_progress(f"               ✗ 失败 ({cmd_elapsed:.1f}s)", level="warning")
                _log_progress(f"               错误: {exec_result['error'][:100]}", level="warning")

                # Check if this is a critical command
                if cmd_spec.get("critical", False):
                    _log_progress("      ⚠ 关键命令失败，终止服务准备", level="warning")
                    return result

        # Wait for services to initialize if any were started
        if result["services"]:
            wait_time = startup_strategy.get("wait_after_start", 3)
            _log_progress(f"      ⏳ 等待 {wait_time}s 让服务初始化...")
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

        Returns:
            List of ValidationCheck results. If a critical check fails,
            subsequent checks are skipped.
        """
        checks: list[ValidationCheck] = []
        critical_failed = False  # Track if any critical check failed
        total_checks = len(strategy.get("validation_checks", []))

        for idx, check_spec in enumerate(strategy.get("validation_checks", []), 1):
            name = check_spec.get("name", "Unknown")
            description = check_spec.get("description", "")
            env_str = check_spec.get("environment", "cli")
            action = check_spec.get("action", {})
            is_critical = check_spec.get("critical", False)
            phase = check_spec.get("phase", "function")

            # Skip remaining checks if a critical check has already failed
            if critical_failed:
                check = ValidationCheck(
                    name=name,
                    description=description,
                    environment=ValidationEnvironment.CLI,
                    action=action,
                    passed=False,
                    error="跳过：前置关键检查失败",
                    critical=is_critical,
                    phase=phase,
                )
                checks.append(check)
                self._emit_event(
                    "acceptance_check",
                    f"   [{idx}/{total_checks}] ⏭ {name} - 跳过(前置失败)",
                    metadata={"name": name, "skipped": True},
                )
                continue

            try:
                env = ValidationEnvironment(env_str)
            except ValueError:
                env = ValidationEnvironment.CLI

            # Log check start with phase info
            phase_emoji = {"dependency": "📦", "compile": "🔨", "startup": "🚀", "function": "⚙️"}.get(phase, "📋")
            critical_marker = "[关键]" if is_critical else ""
            self._emit_event(
                "acceptance_check",
                f"   [{idx}/{total_checks}] {phase_emoji} {name} {critical_marker}",
                metadata={"name": name, "phase": phase, "critical": is_critical, "index": idx},
            )
            self._emit_event("acceptance_check", f"            环境: {env.value}, 阶段: {phase}")
            check_start = time.time()

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
                            critical=is_critical,
                            phase=phase,
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
                        critical=is_critical,
                        phase=phase,
                    )
            except Exception as exc:
                check = ValidationCheck(
                    name=name,
                    description=description,
                    environment=env,
                    action=action,
                    passed=False,
                    error=str(exc),
                    critical=is_critical,
                    phase=phase,
                )

            # Set critical and phase on check (in case it was created by sub-methods)
            check.critical = is_critical
            check.phase = phase

            checks.append(check)
            check_elapsed = time.time() - check_start

            # Log check result with details
            if check.passed:
                self._emit_event(
                    "acceptance_check",
                    f"            ✓ 通过 ({check_elapsed:.1f}s)",
                    metadata={"name": name, "passed": True, "elapsed_s": check_elapsed},
                )
                if check.output and len(check.output) < 100:
                    self._emit_event("acceptance_check", f"            输出: {check.output}")
            else:
                self._emit_event(
                    "acceptance_check",
                    f"            ✗ 失败 ({check_elapsed:.1f}s)",
                    level="warning",
                    metadata={"name": name, "passed": False, "elapsed_s": check_elapsed, "error": check.error},
                )
                if check.error:
                    self._emit_event(
                        "acceptance_check",
                        f"            错误: {check.error[:150]}",
                        level="warning",
                    )

            # If critical check failed, mark for skipping subsequent checks
            if is_critical and not check.passed:
                critical_failed = True
                self._emit_event(
                    "acceptance_check",
                    f"   ⚠ 关键检查 '{name}' 失败，后续检查将被跳过",
                    level="warning",
                    metadata={"critical_failure": True, "name": name},
                )

        return checks

    async def _execute_command_in_workspace(
        self, command: str, *, working_dir: str | None = None, timeout: int = 300
    ) -> dict[str, Any]:
        """Execute command using RuntimeWorkspace or SandboxOrchestrator.

        Returns dict with keys: success, output, error
        """
        # Prefer RuntimeWorkspace if available (same Docker sandbox)
        if self._runtime_workspace and self._runtime_workspace.is_initialized:
            # execute_command is synchronous, run in executor to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._runtime_workspace.execute_command(
                    command, working_dir=working_dir, timeout=timeout
                )
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
            result = await self._execute_command_in_workspace(
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
                    result = await self._execute_command_in_workspace(
                        f"test -e {full_path} && echo 'EXISTS' || echo 'NOT_FOUND'",
                        timeout=10,
                    )
                    passed = "EXISTS" in result["output"]
                elif check_type == "not_empty":
                    result = await self._execute_command_in_workspace(
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
            result = await self._execute_command_in_workspace(cmd, timeout=30)

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
        """Use LLM to analyze validation results against acceptance criteria.

        IMPORTANT: If any critical check failed, immediately return FAILED
        status without consulting the LLM. This ensures that dependency,
        compile, and startup failures cannot be overridden.
        """
        if not checks:
            return AcceptanceResult(
                status=AcceptanceStatus.ERROR,
                score=0.0,
                summary="没有执行任何验收检查",
            )

        # Check for critical failures first - these cannot be overridden
        critical_failures = [c for c in checks if c.critical and not c.passed]
        if critical_failures:
            failed_phases = set(c.phase for c in critical_failures)
            failed_names = [c.name for c in critical_failures]
            self._emit_event(
                "acceptance_step",
                "⚠️ 发现关键检查失败，跳过LLM分析",
                level="warning",
                metadata={"critical_failures": len(critical_failures), "phases": list(failed_phases)},
            )
            self._emit_event(
                "acceptance_step",
                f"   失败阶段: {', '.join(failed_phases)}",
                level="warning",
            )
            for cf in critical_failures[:3]:
                self._emit_event(
                    "acceptance_step",
                    f"   - {cf.name}: {cf.error or '检查失败'}",
                    level="warning",
                )
            return AcceptanceResult(
                status=AcceptanceStatus.FAILED,
                score=0.0,
                checks=checks,
                summary=f"关键验收检查失败（{', '.join(failed_phases)}阶段）：{'; '.join(failed_names[:3])}",
                recommendations=[
                    f"修复 {c.phase} 阶段的问题：{c.name} - {c.error or '检查失败'}"
                    for c in critical_failures[:5]
                ],
            )

        # Format results for LLM
        results_str = json.dumps(
            [
                {
                    "name": c.name,
                    "description": c.description,
                    "environment": c.environment.value,
                    "phase": c.phase,
                    "critical": c.critical,
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
        # Note: Critical failures are already handled above, so if we reach here,
        # all critical checks have passed.
        passed_count = sum(1 for c in checks if c.passed)
        total_count = len(checks)
        score = passed_count / total_count if total_count > 0 else 0.0

        # Require higher threshold: 90% for PASSED (was 80%)
        if score >= 0.9:
            status = AcceptanceStatus.PASSED
        elif score >= 0.6:
            status = AcceptanceStatus.PARTIAL
        else:
            status = AcceptanceStatus.FAILED

        return AcceptanceResult(
            status=status,
            score=score,
            checks=checks,
            summary=f"通过 {passed_count}/{total_count} 项检查（需要 90% 以上通过）",
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
