# -*- coding: utf-8 -*-
"""Local gym system test with Docker-based compile validation."""
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Environment variable to enable/disable runtime (Docker) validation
USE_RUNTIME = os.environ.get("USE_RUNTIME", "0") == "1"


async def main():
    """Run gym system test with optional Docker runtime."""
    from agentscope.scripts._spec import collect_spec, enrich_acceptance_map
    from agentscope.scripts._execution import run_execution
    from agentscope.scripts._observability import init_observability
    from agentscope.scripts._llm_utils import load_siliconflow_env, initialize_llm

    # Configure logging
    init_observability(log_level="DEBUG")

    # Initialize LLM
    print("初始化 LLM...")
    silicon_creds = load_siliconflow_env()
    llm, provider = initialize_llm("siliconflow", silicon_creds)
    print(f"使用 LLM 提供方: {provider}")

    # Requirement
    requirement = "健身房会员管理系统，包含会员注册、登录、会员卡管理、课程预约、健身记录和教练管理功能"

    print(f"需求: {requirement}")
    print("=" * 60)

    # Collect spec
    print("\n[1/3] 收集需求规格...")
    spec = await collect_spec(llm, requirement, auto_confirm=True, verbose=True)

    print(f"\n项目概述: {spec.get('summary', 'N/A')}")
    print(f"需求数量: {len(spec.get('requirements', []))}")
    for req in spec.get('requirements', []):
        print(f"  [{req['id']}] {req.get('title', 'N/A')} ({req.get('category', 'N/A')})")

    # Generate acceptance criteria
    print("\n[2/3] 生成验收标准...")
    await enrich_acceptance_map(llm, spec, verbose=True)

    # Print acceptance criteria summary
    for item in spec.get("acceptance_map", []):
        rid = item.get("requirement_id", "?")
        criteria = item.get("criteria", [])
        print(f"  [{rid}] {len(criteria)} 条验收标准")

    # Create workspace
    workspace_dir = Path("deliverables/workspace_local")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Initialize RuntimeWorkspace if USE_RUNTIME is enabled
    runtime_workspace = None
    if USE_RUNTIME:
        print("\n[Runtime] 初始化 Docker 运行时环境...")
        try:
            from agentscope.scripts._sandbox import RuntimeWorkspace
            runtime_workspace = RuntimeWorkspace(
                workspace_dir="/workspace",
                timeout=600,
                local_mirror_dir=workspace_dir,
            )
            if runtime_workspace.start():
                print("[Runtime] ✓ Docker 运行时环境已启动")
            else:
                print("[Runtime] ✗ Docker 运行时环境启动失败，将跳过编译验证")
                runtime_workspace = None
        except Exception as exc:
            print(f"[Runtime] ✗ 无法初始化 Docker 运行时: {exc}")
            runtime_workspace = None

    # Run execution
    print("\n[3/3] 执行实现 (最大3轮)...")
    print("=" * 60)

    try:
        result = await run_execution(
            llm=llm,
            spec=spec,
            max_rounds=3,
            verbose=True,
            workspace_dir=workspace_dir,
            skip_code_validation=False,
            use_collaborative_agents=False,
            require_runtime=False,  # Don't require runtime, but use it if available
            runtime_workspace=runtime_workspace,  # Pass runtime workspace for compile validation
            use_edit_mode=True,  # Claude Code style edit mode (read before write)
        )
    finally:
        # Cleanup runtime workspace
        if runtime_workspace:
            try:
                runtime_workspace.stop()
                print("[Runtime] Docker 运行时环境已停止")
            except Exception:
                pass

    # Print results
    print("\n" + "=" * 60)
    print("执行结果摘要")
    print("=" * 60)

    summary = result.get("execution_summary", {})
    print(f"总需求数: {summary.get('total_requirements', 'N/A')}")
    print(f"通过数: {summary.get('passed_count', 'N/A')}")
    print(f"失败数: {summary.get('failed_count', 'N/A')}")
    print(f"全部通过: {summary.get('all_passed', 'N/A')}")
    print(f"总轮次: {summary.get('total_rounds', 'N/A')}")

    final_regression = result.get("final_regression", {})
    if final_regression.get("regressed"):
        print(f"最终回归: {final_regression.get('regressed', [])}")
    else:
        print("最终回归: 无")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
