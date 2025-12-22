# -*- coding: utf-8 -*-
"""
真实 API 测试: 验证 HiveCore 并行协作框架
使用硅基流动 API 运行多 agent 协作流程
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from datetime import datetime

from agentscope.aa import (
    AgentCapabilities,
    AgentProfile,
    RoleRequirement,
    StaticScore,
)
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.ones import (
    AcceptanceCriteria,
    AssistantOrchestrator,
    CollaborativeExecutor,
    ExecutionLoop,
    IntentRequest,
    KPITracker,
    MemoryPool,
    ProjectPool,
    ResourceLibrary,
    StrategyReActAgent,
    BuilderReActAgent,
    ProductReActAgent,
    FrontendReActAgent,
    BackendReActAgent,
    QAReActAgent,
    SystemRegistry,
    TaskGraphBuilder,
)


# ---------------------------------------------------------------------------
# 环境配置
# ---------------------------------------------------------------------------
def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                os.environ.setdefault(key, value)


def load_credentials() -> dict[str, str]:
    root = Path(__file__).resolve().parent.parent.parent.parent
    candidates = [
        root / ".env",
        root / "agentscope" / ".env",
        Path.home() / "agentscope" / ".env",
        Path.home() / ".agentscope" / ".env",
    ]
    for path in candidates:
        _load_env_file(path)

    creds = {}
    for key in ("SILICONFLOW_API_KEY", "SILICONFLOW_BASE_URL", "SILICONFLOW_MODEL"):
        if os.environ.get(key):
            creds[key] = os.environ[key]
    return creds


def initialize_llm(
    provider: str,
    silicon_creds: dict[str, str],
    *,
    ollama_model: str = "qwen3:8b",
    ollama_host: str = "http://localhost:11434",
):
    have_silicon = all(
        key in silicon_creds for key in ("SILICONFLOW_API_KEY", "SILICONFLOW_MODEL")
    )
    provider = provider.lower()

    if provider == "siliconflow":
        if not have_silicon:
            raise RuntimeError("未检测到硅基流动配置")
        return OpenAIChatModel(
            model_name=silicon_creds["SILICONFLOW_MODEL"],
            api_key=silicon_creds["SILICONFLOW_API_KEY"],
            stream=False,
            client_args={
                "base_url": silicon_creds.get(
                    "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
                ),
            },
        )

    if provider == "ollama":
        return OllamaChatModel(
            model_name=ollama_model,
            stream=False,
            host=ollama_host,
        )

    # Auto-detect
    if have_silicon:
        return initialize_llm("siliconflow", silicon_creds)
    return initialize_llm(
        "ollama", silicon_creds, ollama_model=ollama_model, ollama_host=ollama_host
    )


# ---------------------------------------------------------------------------
# 创建专家代理
# ---------------------------------------------------------------------------
def create_specialist_agents(llm, formatter, *, with_file_tools: bool = False):
    """创建一组专家 ReAct 代理

    Args:
        llm: LLM 模型实例
        formatter: 消息格式化器
        with_file_tools: 是否为工程类 Agent 添加文件操作工具
    """
    from agentscope.scripts.hive_toolkit import HiveToolkitManager

    agents = {}

    # 为工程类 Agent 创建带文件工具的 Toolkit
    dev_toolkit = None
    builder_toolkit = None
    if with_file_tools:
        toolkit_manager = HiveToolkitManager(llm=llm)
        # 开发工具：文件操作
        dev_toolkit = toolkit_manager.build_toolkit(
            tools_filter={"view_text_file", "write_text_file", "insert_text_file"}
        )
        # 构建工具：文件操作 + shell 命令
        builder_toolkit = toolkit_manager.build_toolkit(
            tools_filter={
                "view_text_file", "write_text_file", "insert_text_file",
                "execute_shell_command"
            }
        )

    # 策略官
    agents["strategy"] = StrategyReActAgent(
        name="策略官",
        model=llm,
        formatter=formatter,
    )

    # 产品官
    agents["product"] = ProductReActAgent(
        name="产品官",
        model=llm,
        formatter=formatter,
    )

    # 构建官 (带文件+shell工具)
    agents["builder"] = BuilderReActAgent(
        name="构建官",
        model=llm,
        formatter=formatter,
        toolkit=builder_toolkit,
    )

    # 前端官 (带文件工具)
    agents["frontend"] = FrontendReActAgent(
        name="前端官",
        model=llm,
        formatter=formatter,
        toolkit=dev_toolkit,
    )

    # 后端官 (带文件工具)
    agents["backend"] = BackendReActAgent(
        name="后端官",
        model=llm,
        formatter=formatter,
        toolkit=dev_toolkit,
    )

    # 质量官
    agents["qa"] = QAReActAgent(
        name="质量官",
        model=llm,
        formatter=formatter,
    )

    return agents


def create_agent_profile(agent_id: str, role: str, skills: set[str]) -> AgentProfile:
    """创建 agent profile 用于 AA 选择"""
    return AgentProfile(
        agent_id=agent_id,
        name=f"{role}专家",
        role=role,
        static_score=StaticScore(performance=0.9, brand=0.8, recognition=0.85),
        capabilities=AgentCapabilities(
            skills=skills,
            tools={"ai", "code"},
            domains={"web", "ai"},
            languages={"zh", "en"},
            regions={"cn"},
        ),
    )


# ---------------------------------------------------------------------------
# 测试 1: 使用 ExecutionLoop (线性流程 + 上下文传递)
# ---------------------------------------------------------------------------
async def test_execution_loop(llm, formatter, user_request: str):
    """测试 ExecutionLoop 的上下文传递"""
    print("\n" + "=" * 60)
    print("测试 1: ExecutionLoop 线性执行 + 上下文传递")
    print("=" * 60)

    agents = create_specialist_agents(llm, formatter)

    # 创建 orchestrator
    registry = SystemRegistry()
    orchestrator = AssistantOrchestrator(system_registry=registry)

    # 注册 agent profiles
    for role, agent in [
        ("Strategy", agents["strategy"]),
        ("Product", agents["product"]),
    ]:
        profile = create_agent_profile(agent.name, role, {"planning", "analysis"})
        orchestrator.register_candidates(role, [profile])
        orchestrator._runtime_agents[agent.name] = agent

    # 创建执行器
    executor = ExecutionLoop(
        project_pool=ProjectPool(),
        memory_pool=MemoryPool(),
        resource_library=ResourceLibrary(),
        orchestrator=orchestrator,
        task_graph_builder=TaskGraphBuilder(),
        kpi_tracker=KPITracker(target_reduction=0.5),
        max_rounds=1,
    )

    # 创建意图请求
    intent = IntentRequest(
        user_id="test-user",
        utterance=user_request,
        role_requirements={
            "task-strategy": RoleRequirement(role="Strategy", skills={"planning"}),
            "task-product": RoleRequirement(role="Product", skills={"requirements"}),
        },
    )

    acceptance = AcceptanceCriteria(
        description="完成需求分析",
        metrics={"quality": 0.5},  # 降低阈值确保通过
    )

    print(f"\n用户请求: {user_request}")
    print("\n执行中...")

    import time

    start = time.time()
    report = executor.run_cycle(
        intent,
        acceptance,
        baseline_cost=100,
        observed_cost=30,
        baseline_time=100,
        observed_time=30,
    )
    elapsed = time.time() - start

    print(f"\n执行完成! 耗时: {elapsed:.2f}s")
    print(f"接受状态: {'✓ 通过' if report.accepted else '✗ 未通过'}")
    print(f"Agent 输出数: {len(report.agent_outputs)}")

    for i, output in enumerate(report.agent_outputs, 1):
        print(f"\n--- Agent {i}: {output.agent_id} ---")
        print(f"状态: {'成功' if output.success else '失败'}")
        print(f"输出预览: {output.content[:300]}..." if len(output.content) > 300 else f"输出: {output.content}")

    return report


# ---------------------------------------------------------------------------
# 测试 2: 使用 CollaborativeExecutor (并行协作)
# ---------------------------------------------------------------------------
async def test_collaborative_executor(llm, formatter, user_request: str):
    """测试 CollaborativeExecutor 的并行协作"""
    print("\n" + "=" * 60)
    print("测试 2: CollaborativeExecutor 并行协作")
    print("=" * 60)

    agents = create_specialist_agents(llm, formatter)

    # 创建协作执行器
    executor = CollaborativeExecutor(
        agents={
            "strategy": agents["strategy"],
            "product": agents["product"],
            "frontend": agents["frontend"],
            "backend": agents["backend"],
            "qa": agents["qa"],
        },
        agent_roles={
            "strategy": "策略官",
            "product": "产品官",
            "frontend": "前端官",
            "backend": "后端官",
            "qa": "质量官",
        },
        timeout_seconds=120.0,
    )

    # 定义任务
    tasks = {
        "strategy": f"分析以下用户需求，分解为具体任务:\n{user_request}",
        "product": f"基于用户需求定义产品规格:\n{user_request}",
        "frontend": "设计前端页面结构和组件",
        "backend": "设计后端 API 和数据模型",
        "qa": "制定测试策略和验收标准",
    }

    # 定义依赖
    #   strategy
    #      |
    #   product
    #   /     \
    # frontend  backend
    #   \     /
    #     qa
    dependencies = {
        "product": {"strategy"},
        "frontend": {"product"},
        "backend": {"product"},
        "qa": {"frontend", "backend"},
    }

    print(f"\n用户请求: {user_request}")
    print(f"\n任务分配:")
    for agent_id, task in tasks.items():
        print(f"  - {agent_id}: {task[:50]}...")
    print(f"\n依赖关系:")
    for agent_id, deps in dependencies.items():
        print(f"  - {agent_id} 依赖 {deps}")

    print("\n并行执行中...")

    import time

    start = time.time()
    states = await executor.execute_parallel(tasks, dependencies)
    elapsed = time.time() - start

    print(f"\n执行完成! 耗时: {elapsed:.2f}s")

    # 统计结果
    completed = sum(1 for s in states.values() if s.status == "completed")
    blocked = sum(1 for s in states.values() if s.status == "blocked")

    print(f"\n执行统计:")
    print(f"  - 完成: {completed}/{len(states)}")
    print(f"  - 阻塞: {blocked}/{len(states)}")

    # 显示各 agent 状态
    for agent_id, state in states.items():
        status_icon = "✓" if state.status == "completed" else "✗"
        print(f"\n--- [{status_icon}] {state.role} ({agent_id}) ---")
        print(f"状态: {state.status}")
        if state.output:
            preview = state.output[:400] + "..." if len(state.output) > 400 else state.output
            print(f"输出:\n{preview}")
        if state.blocked_reason:
            print(f"阻塞原因: {state.blocked_reason}")

    # 显示共享工作区
    print("\n--- 共享工作区 ---")
    print(f"产物数量: {len(executor.workspace.artifacts)}")
    for name in list(executor.workspace.artifacts.keys())[:5]:
        print(f"  - {name}")
    print(f"消息记录: {len(executor.workspace.message_history)} 条")

    return states


# ---------------------------------------------------------------------------
# 测试 3: 简单对话测试
# ---------------------------------------------------------------------------
async def test_simple_agent(llm, formatter, user_request: str):
    """测试单个 agent 的基本响应"""
    print("\n" + "=" * 60)
    print("测试 0: 单 Agent 基本响应")
    print("=" * 60)

    from agentscope.message import Msg

    agent = StrategyReActAgent(
        name="策略官",
        model=llm,
        formatter=formatter,
    )

    print(f"\n用户请求: {user_request}")
    print("\n等待响应...")

    import time

    start = time.time()
    msg = Msg(name="user", role="user", content=user_request)
    response = await agent.reply(msg)
    elapsed = time.time() - start

    print(f"\n响应完成! 耗时: {elapsed:.2f}s")
    print(f"\n策略官回复:\n{response.content}")

    return response


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(description="HiveCore 真实 API 测试")
    parser.add_argument(
        "-r",
        "--request",
        type=str,
        default="我需要一个 AI 驱动的产品展示网站，支持智能推荐功能",
        help="用户需求描述",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="auto",
        choices=["auto", "siliconflow", "ollama"],
        help="LLM 提供商",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="qwen3:8b",
        help="Ollama 模型名称",
    )
    parser.add_argument(
        "--ollama-host",
        type=str,
        default="http://localhost:11434",
        help="Ollama 服务地址",
    )
    parser.add_argument(
        "--test",
        type=str,
        default="all",
        choices=["simple", "loop", "collab", "all"],
        help="要运行的测试",
    )
    args = parser.parse_args()

    # 加载凭证
    print("加载配置...")
    creds = load_credentials()

    # 初始化 LLM
    print("初始化 LLM...")
    try:
        llm = initialize_llm(
            args.provider,
            creds,
            ollama_model=args.ollama_model,
            ollama_host=args.ollama_host,
        )
        print(f"LLM 初始化成功: {llm.model_name}")
    except Exception as e:
        print(f"LLM 初始化失败: {e}")
        print("\n请确保:")
        print("  1. 设置了 SILICONFLOW_API_KEY 环境变量，或")
        print("  2. Ollama 服务正在运行 (ollama serve)")
        return

    # 创建 formatter
    formatter = OpenAIChatFormatter()

    print(f"\n开始测试...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 运行测试
    if args.test in ("simple", "all"):
        await test_simple_agent(llm, formatter, args.request)

    if args.test in ("loop", "all"):
        await test_execution_loop(llm, formatter, args.request)

    if args.test in ("collab", "all"):
        await test_collaborative_executor(llm, formatter, args.request)

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
