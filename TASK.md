# HiveCore 骨架测试任务

以下步骤帮助你验证当前已实现的 AgentScope + HiveCore 骨架功能。请按照顺序执行，并在执行过程中记录观察结果。

---

## 1. 环境准备
1.1 在仓库根目录创建并激活虚拟环境：
```bash
python3 -m venv .venv
source .venv/bin/activate
```
1.2 安装依赖（以可编辑模式安装当前项目）：
```bash
pip install -e .
```
1.3 （可选）配置本地 `.env` 或环境变量，以便后续连接模型/工具。如果仅运行单元测试，可跳过模型配置。

---

## 2. 单元测试验证
2.1 运行 AA 选型相关单测，确认 `AssistantAgentSelector` 工作正常：
```bash
pytest tests/aa_selection_test.py
```
2.2 （若存在）运行 One·s 子模块单测：
```bash
pytest tests/ones
```
观察点：
- 所有用例通过，无失败或错误。
- 关注日志中对 Requirement/Ranking 的输出，确认评分机制符合预期。

---

## 3. 手工流程演练
通过最小脚本串起 orchestrator、执行循环与 AA agent，验证核心骨架能运行一轮。

3.1 在 `examples/`（或任意目录）创建 `manual_loop.py`，示例：
```python
from agentscope.message import Msg, TextBlock
from agentscope.ones import (
    AASystemAgent, AssistantOrchestrator, ExecutionLoop,
    KPITracker, TaskGraphBuilder, ProjectPool, MemoryPool,
    ResourceLibrary, SystemRegistry, UserProfile
)
from agentscope.aa import AgentCapabilities, AgentProfile, RoleRequirement, StaticScore

registry = SystemRegistry()
orchestrator = AssistantOrchestrator(system_registry=registry)
project_pool = ProjectPool()
memory_pool = MemoryPool()
resource_lib = ResourceLibrary()
execution = ExecutionLoop(
    project_pool=project_pool,
    memory_pool=memory_pool,
    resource_library=resource_lib,
    orchestrator=orchestrator,
    task_graph_builder=TaskGraphBuilder(),
    kpi_tracker=KPITracker(),
)

candidate = AgentProfile(
    agent_id="agent-coder",
    name="Coder",
    role="coder",
    static_score=StaticScore(performance=0.9, brand=0.8, recognition=0.7, fault_impact=0.0),
    capabilities=AgentCapabilities(skills={"python"}),
)
orchestrator.register_candidates("coder", [candidate])

requirement = RoleRequirement(role="coder", skills={"python"})

aa = AASystemAgent(
    name="aa",
    user_id="user-1",
    orchestrator=orchestrator,
    execution_loop=execution,
    requirement_resolver=lambda text: {"task-1": requirement},
    acceptance_resolver=lambda text: (
        # 简化：始终要求质量>=0.9
        type("Acceptance", (), {"metrics": {"quality": 0.9}, "description": "demo"})()
    ),
    user_profile=UserProfile(user_id="user-1"),
)

msg = Msg(name="user", role="user", content=[TextBlock(type="text", text="请帮我写一个脚本")])
response = asyncio.run(aa.reply(msg))
print(response.content[0].text)
print(response.metadata)
```
3.2 运行脚本：
```bash
python examples/manual_loop.py
```
观察点：
- 控制台输出中包含任务状态列表、KPI 信息。
- `response.metadata` 应包含 `accepted`, `project_id`, `task_status` 等键。

---

## 4. 内存与注册表检查
4.1 脚本运行后，检查内存池是否记录了最新意图：
```python
from agentscope.ones.memory import MemoryPool
# 假设使用同一个 memory_pool 实例
print(memory_pool.load("intent:user-1:None"))
```
期望：能读到 `content` 为用户输入的 `MemoryEntry`。

4.2 检查 `SystemRegistry` 是否绑定了用户与 AA：
```python
print(registry.aa_binding("user-1"))  # 预期输出 aa id
```

---

## 5. 下一步（可选）
- 将 `project_pool.register(...)`、`memory_pool.save(...)` 扩展为持久化实现，以便后续验证“项目上下文共享”场景。
- 为 KPI Tracker 添加断言：若小于 90% 则触发返工逻辑。

完成以上步骤后，可在 README 中更新“进行中/已完成”的状态，或撰写测试报告总结观察结果。

---

## 6. 实战增强：MsgHub 实时广播
目标：把 `ExecutionLoop` 产出的轮次摘要通过 AgentScope 的 `MsgHub` 推送给真实参与者（例如仪表盘 Agent / 在线订阅者）。

6.1 **实现广播桥**
- 在 `agentscope/ones/msghub.py` 中新增一个实现 `MsgHubBroadcaster` 的类，内部可复用 `agentscope.pipeline.MsgHub`。
- 将 `RoundUpdate` 格式化为文本或结构化数据，并写入 `Msg.metadata`，以便订阅方二次处理。

6.2 **注册项目级 Hub**
- 提供工厂/注册机制，可按 `project_id` 绑定特定的 MsgHub 或订阅者列表。
- `ExecutionLoop` 调用 `msg_hub_factory(project_id)` 时，应返回绑定后的广播器，若无绑定则回退到内存实现。

6.3 **验证**
- 编写一个最小订阅 Agent（覆写 `observe` 方法记录消息），注册到 Hub。
- 运行 `tests/ones/` 或手工脚本，确认订阅 Agent 收到 `RoundUpdate`，并输出项目/轮次信息。

6.4 **CLI 集成（可选）**
- 为 `scripts/full_user_flow_cli.py` 增加参数，让用户能指定监听者或打开实时广播调试输出。
- 在 README 中更新“MsgHub 广播”状态，说明现已支持实时推送。
