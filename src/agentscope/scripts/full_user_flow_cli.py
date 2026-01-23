# -*- coding: utf-8 -*-
"""HiveCore Full User Flow CLI - Main Entry Point.

This is the main CLI entry point for the HiveCore multi-agent orchestration system.
It provides a complete flow for requirement collection, implementation, and validation.

Usage:
    python -m agentscope.scripts.full_user_flow_cli \\
        -r "我要一个展示新品发布的单页网站" \\
        --auto-confirm

The implementation has been modularized into the following submodules:
- _llm_utils: LLM initialization and calling utilities
- _mcp: MCP client management
- _agent_market: Agent market loading
- _sandbox: Sandbox and workspace management
- _validation: Code validation utilities
- _spec: Specification collection and processing
- _architecture: Architecture contract generation
- _runtime: Runtime harness building
- _agent_roles: Agent role implementations
- _qa: QA validation utilities
- _execution: Main execution flow
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

# Load .env file for environment variables (ZHIPU_API_KEY, etc.)
try:
    from dotenv import load_dotenv
    # Try to load from current directory, then from agentscope directory
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent.parent / ".env",  # agentscope/.env
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # dotenv not installed, rely on system environment variables

# Re-export key symbols from submodules for backward compatibility
from ._llm_utils import (
    load_zhipu_env,
    load_siliconflow_env,
    get_llm_provider,
    initialize_llm,
    call_llm_raw,
    call_llm_json,
)
from ._mcp import (
    MCPServerConfig,
    parse_mcp_server,
    initialize_mcp_clients,
    summarize_mcp_clients,
    advisor_hints,
    shutdown_mcp_clients,
)
from ._agent_market import (
    load_agent_market,
    default_agent_profiles,
)
from ._sandbox import (
    SimpleHTTPServer,
    BrowserSandboxManager,
    RuntimeWorkspace,
    run_playwright_test,
    run_browser_sandbox_test,
)
from ._runtime_workspace import RuntimeWorkspaceWithPR


def _is_ecs_environment() -> bool:
    """Check if running in AWS ECS environment.

    Returns:
        `bool`: True if should use ECS runtime.
    """
    use_aws = os.environ.get("USE_AWS", "").lower() == "true"
    environment = os.environ.get("ENVIRONMENT", "")
    return use_aws and environment == "aws_ecs"


def _get_ecs_runtime_workspace(
    use_pr_mode: bool,
    workspace_dir: Path,
    obs_ctx: Any,
) -> Any:
    """Create ECS-based RuntimeWorkspace.

    Args:
        use_pr_mode (`bool`): Whether to use PR mode.
        workspace_dir (`Path`): Local workspace directory.
        obs_ctx: Observation context for logging.

    Returns:
        ECSRuntimeWorkspace instance.
    """
    from ..ones.runtime.ecs_runtime import ECSRuntimeWorkspace

    # Load ECS configuration from environment
    cluster = os.environ.get("ECS_CLUSTER", "hivecore-cluster")
    task_definition = os.environ.get(
        "ECS_TASK_DEFINITION", "hivecore-runtime:latest"
    )
    region = os.environ.get("AWS_REGION", "ap-northeast-1")

    # Parse subnet and security group IDs
    subnet_ids_str = os.environ.get("ECS_SUBNET_IDS", "")
    subnet_ids = [s.strip() for s in subnet_ids_str.split(",") if s.strip()]

    sg_ids_str = os.environ.get("ECS_SECURITY_GROUP_IDS", "")
    security_group_ids = [s.strip() for s in sg_ids_str.split(",") if s.strip()]

    obs_ctx.logger.info(
        f"[CLI] 使用 ECS Runtime: cluster={cluster}, "
        f"task={task_definition}, region={region}"
    )

    return ECSRuntimeWorkspace(
        cluster=cluster,
        task_definition=task_definition,
        region=region,
        subnet_ids=subnet_ids if subnet_ids else None,
        security_group_ids=security_group_ids if security_group_ids else None,
        base_workspace_dir="/workspace",
        timeout=600,
        enable_pr_mode=use_pr_mode,
    )
from ._validation import (
    CodeValidationResult,
    layered_code_validation,
)
from ._spec import (
    sanitize_filename,
    collect_spec,
    enrich_acceptance_map,
    criteria_for_requirement,
)
from ._architecture import (
    generate_architecture_contract,
    format_architecture_contract,
)
from ._runtime import (
    RuntimeHarness,
    build_runtime_harness,
)
from ._agent_roles import (
    design_requirement,
    implement_requirement,
    stepwise_generate_files,
)
from ._qa import (
    qa_requirement,
    _normalize_qa_report,
)
from ._execution import (
    DELIVERABLE_DIR,
    run_execution,
)
from ._agent_execution import (
    create_developer_agent,
    execute_with_agent,
    edit_file_with_agent,
)


# ---------------------------------------------------------------------------
# CLI Main Flow
# ---------------------------------------------------------------------------
async def run_cli(
    initial_requirement: str,
    scripted_inputs: list[str] | None = None,
    auto_confirm: bool = False,
    provider: str = "auto",
    verbose: bool = False,
    user_id: str = "cli-user",
    project_id: str | None = None,
    mcp_configs: list[MCPServerConfig] | None = None,
    playwright_mcp: bool = False,
    agent_market_dir: str | None = None,
    mcp_advisor: bool = False,
    max_rounds: int = 3,
    skip_code_validation: bool = False,
    use_collaborative_agents: bool = False,
    use_parallel_execution: bool = False,
    parallel_timeout: float = 300.0,
    use_edit_mode: bool = False,
    use_git_isolation: bool = True,
    keep_containers: bool = False,
    use_pr_mode: bool = True,
    log_level: str = "INFO",
    log_format: str = "text",
    log_file: str | None = None,
    track_tokens: bool = True,
    show_summary: bool = True,
) -> None:
    """Run the full HiveCore CLI flow.

    Args:
        initial_requirement: Initial user requirement text
        scripted_inputs: Pre-defined inputs for testing
        auto_confirm: Whether to auto-confirm without user input
        provider: LLM provider ('auto', 'siliconflow')
        verbose: Whether to print debug info
        user_id: User identifier
        project_id: Optional project ID
        mcp_configs: MCP server configurations
        playwright_mcp: Whether to enable Playwright testing
        agent_market_dir: Path to agent market directory
        mcp_advisor: Whether to enable MCP Advisor
        max_rounds: Maximum execution rounds
        skip_code_validation: Whether to skip code validation
        use_collaborative_agents: Whether to use collaborative agent mode
        use_git_isolation: Whether to use Git branch isolation
        keep_containers: Whether to keep containers running for delivery
        log_level: Log level (DEBUG, INFO, WARN, ERROR)
        log_format: Log format (text, json, rich)
        log_file: Optional log file path
        track_tokens: Whether to track token consumption
        show_summary: Whether to show execution summary
    """
    from agentscope.mcp import StdIOStatefulClient
    from agentscope.ones import SandboxManager
    from ._observability import init_observability, get_context, get_cli_observer

    # Initialize observability
    obs_ctx = init_observability(
        log_level=log_level,
        log_format=log_format,
        log_destination=log_file or "stdout",
        track_tokens=track_tokens,
        track_timing=True,
    )
    obs_ctx.timing_tracker.start_total()
    cli_obs = get_cli_observer()

    # Initialize LLM (auto-detects provider based on LLM_PROVIDER env or --provider arg)
    llm, provider_used = initialize_llm(provider)
    cli_obs.on_llm_provider(provider_used)

    # Collect specification
    spec = await collect_spec(
        llm,
        initial_requirement,
        scripted_inputs,
        auto_confirm,
        verbose=verbose,
    )

    if spec.get("cancelled"):
        return

    # Enrich acceptance criteria
    await enrich_acceptance_map(llm, spec, verbose=verbose)

    # Initialize MCP clients
    mcp_clients, aa_mcp_clients = await initialize_mcp_clients(
        mcp_configs,
        enable_playwright=playwright_mcp,
        enable_advisor=mcp_advisor,
    )
    mcp_context, resource_handles = await summarize_mcp_clients(mcp_clients)
    advisor_context = await advisor_hints(aa_mcp_clients)
    combined_mcp_prompt = "\n\n".join(
        part for part in (mcp_context, advisor_context) if part
    ) or None

    # Create sandbox manager if agent market is provided
    sandbox_manager: SandboxManager | None = None
    if agent_market_dir:
        try:
            sandbox_manager = SandboxManager()
            cli_obs.on_component_created("SandboxManager")
        except Exception as exc:
            cli_obs.on_component_error("SandboxManager", exc)

    # Create workspace directory
    workspace_dir = DELIVERABLE_DIR / "workspace"
    if workspace_dir.exists():
        import shutil
        old_files = list(workspace_dir.iterdir())
        if old_files:
            cli_obs.on_cleanup_old_files(len(old_files))
            for item in old_files:
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception:
                    pass
    workspace_dir.mkdir(parents=True, exist_ok=True)
    cli_obs.on_workspace_dir(str(workspace_dir))

    # Create filesystem MCP client
    filesystem_mcp: StdIOStatefulClient | None = None
    try:
        filesystem_mcp = StdIOStatefulClient(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", str(workspace_dir)],
        )
        await filesystem_mcp.connect()
        cli_obs.on_component_connect("Filesystem MCP")
    except Exception as exc:
        cli_obs.on_component_error("Filesystem MCP", exc)
        filesystem_mcp = None

    # Create Playwright client
    playwright_client: BrowserSandboxManager | StdIOStatefulClient | None = None
    browser_sandbox: BrowserSandboxManager | None = None
    try:
        browser_sandbox = BrowserSandboxManager(timeout=300)
        if browser_sandbox.start():
            playwright_client = browser_sandbox
            cli_obs.on_component_start("BrowserSandbox")
        else:
            browser_sandbox = None
            playwright_client = StdIOStatefulClient(
                name="playwright",
                command="npx",
                args=["-y", "@playwright/mcp@latest", "--headless"],
            )
            await playwright_client.connect()
            cli_obs.on_component_connect("Playwright MCP")
    except Exception as exc:
        cli_obs.on_component_error("Playwright 测试环境", exc)
        if browser_sandbox:
            browser_sandbox.stop()
            browser_sandbox = None
        playwright_client = None

    # Initialize RuntimeWorkspace (required for multi-tenant mode)
    # Use RuntimeWorkspaceWithPR for PR mode (delivery/ + working/ isolation)
    runtime_workspace: RuntimeWorkspace | RuntimeWorkspaceWithPR | None = None
    try:
        if use_pr_mode:
            # PR模式：使用双目录隔离
            runtime_workspace = RuntimeWorkspaceWithPR(
                base_workspace_dir="/workspace",
                timeout=600,
                image="agentscope/runtime-sandbox-claudecode:latest",
                enable_pr_mode=True,
            )
            # 设置 local_mirror_dir 用于文件同步
            runtime_workspace.local_mirror_dir = workspace_dir
            obs_ctx.logger.info("[CLI] PR模式已启用 (delivery/ + working/ 双目录隔离)")
        else:
            runtime_workspace = RuntimeWorkspace(
                workspace_dir="/workspace",
                timeout=600,
                local_mirror_dir=workspace_dir,
                # Use image with Claude Code CLI pre-installed
                image="agentscope/runtime-sandbox-claudecode:latest",
            )
        if runtime_workspace.start():
            cli_obs.on_component_start("RuntimeWorkspace")
            # Set container context for Claude Code execution
            # This enables Claude Code CLI to run inside the container
            from ._claude_code import set_container_context
            # In PR mode, use /workspace/working as the working directory
            # Otherwise, use /workspace directly
            claude_workspace = "/workspace/working" if use_pr_mode else "/workspace"
            set_container_context(
                container_id=runtime_workspace.container_id,
                container_workspace=claude_workspace,
            )
            obs_ctx.logger.info(f"[CLI] Claude Code 容器模式已启用 (container: {runtime_workspace.sandbox_id}, workspace: {claude_workspace})")
        else:
            cli_obs.on_runtime_workspace_error()
            raise RuntimeError("RuntimeWorkspace is required but failed to start")
    except RuntimeError:
        raise
    except Exception as exc:
        cli_obs.on_component_error("RuntimeWorkspace", exc)
        cli_obs.on_runtime_workspace_error()
        raise RuntimeError(f"RuntimeWorkspace is required but failed: {exc}")

    # Build runtime harness
    obs_ctx.logger.debug("[CLI] 开始构建 RuntimeHarness...")
    runtime: RuntimeHarness | None = None
    try:
        # workspace_dir for ExecutionLoop should be the HOST path
        # (used for ProjectMemory file saving)
        # AcceptanceAgent will get container path from runtime_workspace
        runtime = build_runtime_harness(
            spec,
            user_id=user_id,
            project_hint=project_id,
            resource_handles=resource_handles,
            mcp_clients=mcp_clients,
            aa_mcp_clients=aa_mcp_clients,
            mcp_prompt=combined_mcp_prompt,
            llm=llm,
            agent_market_dir=agent_market_dir,
            sandbox_manager=sandbox_manager,
            playwright_mcp=playwright_client,
            runtime_workspace=runtime_workspace,
            workspace_dir=str(workspace_dir),  # Host path for ProjectMemory
        )

        obs_ctx.logger.debug("[CLI] RuntimeHarness 构建完成")

        # Execute AA agent
        obs_ctx.logger.debug("[CLI] 开始执行 AA Agent...")
        from agentscope.message import Msg
        import json

        runtime_payload = json.dumps(
            {
                "initial_requirement": initial_requirement,
                "summary": spec.get("summary"),
                "requirements": spec.get("requirements", []),
            },
            ensure_ascii=False,
            indent=2,
        )
        runtime_msg = await runtime.aa_agent.reply(
            Msg(name=user_id, role="user", content=runtime_payload),
        )
        runtime_text = runtime_msg.get_text_content() or ""
        cli_obs.on_runtime_output("Hive Runtime (AA)", runtime_text)
        obs_ctx.logger.debug("[CLI] AA Agent 执行完成")

        # Run execution
        obs_ctx.logger.debug(f"[CLI] 开始执行 run_execution (parallel={use_parallel_execution})...")
        result = await run_execution(
            llm,
            spec,
            max_rounds=max_rounds,
            verbose=verbose,
            runtime_summary=runtime_text,
            mcp_context=mcp_context or None,
            filesystem_mcp=filesystem_mcp,
            workspace_dir=workspace_dir,
            playwright_mcp=playwright_client,
            runtime_workspace=runtime_workspace,
            skip_code_validation=skip_code_validation,
            use_collaborative_agents=use_collaborative_agents,
            use_parallel_execution=use_parallel_execution,  # Parallel multi-agent execution
            parallel_timeout=parallel_timeout,  # Parallel execution timeout
            require_runtime=True,  # Multi-tenant mode: require container isolation
            use_edit_mode=use_edit_mode,  # Claude Code style editing with CodeGuard
            use_git_isolation=use_git_isolation,  # Git branch isolation per requirement
            use_pr_mode=use_pr_mode,  # PR mode: delivery/ + working/ isolation
        )

        # Print results
        cli_obs.on_deliverables_header()
        for rid, path in result["deliverables"].items():
            cli_obs.on_deliverable(rid, str(path.resolve()) if path else None)

        last_round = result["rounds"][-1]
        cli_obs.on_acceptance_header()
        for item in last_round["results"]:
            rid = item["requirement_id"]
            qa = item["qa"]
            cli_obs.on_requirement_result(rid)
            for criterion in qa.get("criteria", []):
                cli_obs.on_criterion_result(
                    criterion.get("pass", False),
                    criterion.get("name", ""),
                    criterion.get("reason", ""),
                )
            cli_obs.on_pass_ratio(item["pass_ratio"])

        # Print execution summary
        obs_ctx.timing_tracker.stop_total()
        if show_summary:
            obs_ctx.print_summary()

    finally:
        # Cleanup
        targets = []
        if runtime:
            targets.extend(runtime.mcp_clients)
            targets.extend(runtime.aa_mcp_clients)
        else:
            targets.extend(mcp_clients)
            targets.extend(aa_mcp_clients)

        if filesystem_mcp:
            try:
                await filesystem_mcp.close()
                cli_obs.on_component_disconnect("Filesystem MCP")
            except Exception:
                pass

        if keep_containers:
            # Keep containers running for delivery verification
            cli_obs.ctx.logger.info("[CLI] 保留容器用于交付验收")
            if runtime_workspace:
                container_id = getattr(runtime_workspace, "container_id", None)
                if container_id:
                    cli_obs.ctx.logger.info(f"[CLI] RuntimeWorkspace 容器: {container_id[:12]}")
                    cli_obs.ctx.logger.info(f"[CLI] 进入容器: docker exec -it {container_id[:12]} bash")
            if browser_sandbox:
                sandbox_id = getattr(browser_sandbox, "_sandbox", None)
                if sandbox_id:
                    container = getattr(sandbox_id, "container_id", None)
                    if container:
                        cli_obs.ctx.logger.info(f"[CLI] BrowserSandbox 容器: {container[:12]}")
        else:
            if browser_sandbox:
                try:
                    browser_sandbox.stop()
                    cli_obs.on_component_stop("BrowserSandbox")
                except Exception:
                    pass
            elif playwright_client and hasattr(playwright_client, "close"):
                try:
                    await playwright_client.close()
                    cli_obs.on_component_disconnect("Playwright MCP")
                except Exception:
                    pass

            if runtime_workspace:
                try:
                    runtime_workspace.stop()
                    cli_obs.on_component_stop("RuntimeWorkspace")
                except Exception:
                    pass

            if sandbox_manager:
                try:
                    sandbox_manager.cleanup()
                    cli_obs.on_component_cleanup("SandboxManager")
                except Exception:
                    pass

        await shutdown_mcp_clients(targets)


def parse_auto_inputs(value: str | None) -> list[str] | None:
    """Parse auto-input string into list.

    Args:
        value: Input string with '||' separators

    Returns:
        list or None: Parsed inputs
    """
    if not value:
        return None
    return [token.strip() for token in value.split("||") if token.strip()]


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="HiveCore 全流程 CLI")
    parser.add_argument("-r", "--requirement", dest="requirement", help="初始需求描述")
    parser.add_argument("--auto-answers", dest="auto_answers", help="使用 '||' 分隔的自动输入")
    parser.add_argument("--auto-confirm", dest="auto_confirm", action="store_true", help="自动确认需求")
    parser.add_argument(
        "--provider",
        choices=["auto", "zhipu-anthropic", "zhipu", "siliconflow"],
        default="auto",
        help="选择 LLM 提供方 (zhipu-anthropic=智谱Anthropic兼容API[推荐], zhipu=智谱OpenAI兼容API, siliconflow=硅基流动)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="打印详细输出")
    parser.add_argument("-q", "--quiet", action="store_true", help="静默模式，只显示错误和最终结果")
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARN", "ERROR"],
        default="INFO",
        help="日志级别",
    )
    parser.add_argument(
        "--log-format",
        dest="log_format",
        choices=["text", "json", "rich"],
        default="text",
        help="日志格式 (text=纯文本, json=结构化, rich=带颜色)",
    )
    parser.add_argument(
        "--log-file",
        dest="log_file",
        type=str,
        default=None,
        help="日志输出文件路径",
    )
    parser.add_argument(
        "--track-tokens",
        dest="track_tokens",
        action="store_true",
        default=True,
        help="追踪 Token 消耗 (默认开启)",
    )
    parser.add_argument(
        "--no-track-tokens",
        dest="track_tokens",
        action="store_false",
        help="禁用 Token 消耗追踪",
    )
    parser.add_argument(
        "--show-summary",
        dest="show_summary",
        action="store_true",
        default=True,
        help="显示执行摘要 (默认开启)",
    )
    parser.add_argument("--user-id", dest="user_id", default="cli-user", help="用户 ID")
    parser.add_argument("--project-id", dest="project_id", help="项目 ID")
    parser.add_argument("--playwright-mcp", action="store_true", help="启用 Playwright MCP")
    parser.add_argument(
        "--mcp-server",
        dest="mcp_servers",
        action="append",
        help="MCP 服务配置 (name,url 或 name,transport,url)",
    )
    parser.add_argument("--agent-market", dest="agent_market", help="Agent 市场目录")
    parser.add_argument(
        "--no-mcp-advisor",
        action="store_false",
        dest="mcp_advisor",
        default=True,
        help="禁用 MCP Advisor (用于访问 MCP 规范文档)",
    )
    parser.add_argument("--max-rounds", dest="max_rounds", type=int, default=3, help="最大轮次")
    parser.add_argument(
        "--skip-code-validation",
        action="store_true",
        dest="skip_code_validation",
        help="跳过代码验证",
    )
    parser.add_argument(
        "--collaborative",
        action="store_true",
        dest="use_collaborative_agents",
        help="启用协作 Agent 模式",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        dest="use_parallel_execution",
        default=True,
        help="启用智能并行执行模式（默认启用，Agent 自动判断是否需要并行）",
    )
    parser.add_argument(
        "--no-parallel",
        action="store_false",
        dest="use_parallel_execution",
        help="禁用并行执行，强制串行处理",
    )
    parser.add_argument(
        "--parallel-timeout",
        dest="parallel_timeout",
        type=float,
        default=300.0,
        help="并行执行超时时间（秒，默认 300）",
    )
    parser.add_argument(
        "--edit-mode",
        action="store_true",
        dest="use_edit_mode",
        help="启用编辑模式 (Claude Code 风格: 读取后编辑, 增量修改, 包含 CodeGuard 防幻觉)",
    )
    parser.add_argument(
        "--git-isolation",
        action="store_true",
        dest="use_git_isolation",
        default=True,
        help="启用 Git 分支隔离 (每个需求独立分支，防止文件冲突，支持回滚，默认开启)",
    )
    parser.add_argument(
        "--no-git-isolation",
        action="store_false",
        dest="use_git_isolation",
        help="禁用 Git 分支隔离",
    )
    parser.add_argument(
        "--keep-containers",
        action="store_true",
        dest="keep_containers",
        help="保留容器用于交付验收（不清理 RuntimeWorkspace 和 BrowserSandbox）",
    )
    parser.add_argument(
        "--pr-mode",
        action="store_true",
        dest="use_pr_mode",
        default=True,
        help="启用 PR 模式（双目录隔离：delivery/ + working/，QA只审阅diff，消除需求间覆盖问题，默认开启）",
    )
    parser.add_argument(
        "--no-pr-mode",
        action="store_false",
        dest="use_pr_mode",
        help="禁用 PR 模式",
    )

    args = parser.parse_args()

    requirement = args.requirement or input("请输入你的项目需求：").strip()
    scripted = parse_auto_inputs(args.auto_answers)

    mcp_configs = None
    if args.mcp_servers:
        from ._observability import get_cli_observer
        cli_obs = get_cli_observer()
        parsed: list[MCPServerConfig] = []
        for raw in args.mcp_servers:
            try:
                parsed.append(parse_mcp_server(raw))
            except ValueError as exc:
                cli_obs.on_invalid_mcp_param(raw, exc)
        mcp_configs = parsed or None

    # Determine effective log level
    effective_log_level = args.log_level
    if args.verbose:
        effective_log_level = "DEBUG"
    elif args.quiet:
        effective_log_level = "ERROR"

    try:
        asyncio.run(
            run_cli(
                requirement,
                scripted,
                args.auto_confirm,
                provider=args.provider,
                verbose=args.verbose,
                user_id=args.user_id,
                project_id=args.project_id,
                mcp_configs=mcp_configs,
                playwright_mcp=args.playwright_mcp,
                agent_market_dir=args.agent_market,
                mcp_advisor=args.mcp_advisor,
                max_rounds=args.max_rounds,
                skip_code_validation=args.skip_code_validation,
                use_collaborative_agents=args.use_collaborative_agents,
                use_parallel_execution=args.use_parallel_execution,
                parallel_timeout=args.parallel_timeout,
                use_edit_mode=args.use_edit_mode,
                use_git_isolation=args.use_git_isolation,
                keep_containers=args.keep_containers,
                use_pr_mode=args.use_pr_mode,
                log_level=effective_log_level,
                log_format=args.log_format,
                log_file=args.log_file,
                track_tokens=args.track_tokens,
                show_summary=args.show_summary,
            ),
        )
    except RuntimeError as e:
        if "RuntimeWorkspace" in str(e):
            from ._observability import get_cli_observer
            cli_obs = get_cli_observer()
            cli_obs.on_docker_error()
            raise SystemExit(1)
        raise


if __name__ == "__main__":
    main()
