# Agent 可观测性改进方案

## 问题总结

### 问题 1：只有一个 Agent 被选中
- `builder-agent` 的 capabilities 太广，覆盖所有任务类型
- 需要更智能的任务路由

### 问题 2：执行过程不可观测
- `ModularAgent.reply()` 的 ReAct 循环没有任何日志输出
- 无法观察 Agent 的思考、工具调用、任务板状态

---

## 改进方案

### 方案 1：添加 `AgentReActObserver`

在 `_observability.py` 中添加新的 Observer：

```python
class AgentReActObserver:
    """Observer for Agent ReAct loop."""

    def __init__(self, ctx: ObservabilityContext | None = None):
        self._ctx = ctx

    @property
    def ctx(self) -> ObservabilityContext:
        return self._ctx or get_context()

    # ReAct 循环事件
    def on_react_start(self, agent_id: str, task_id: str, query: str) -> None:
        """ReAct 循环开始"""
        self.ctx.logger.info(f"\n[{agent_id}] ▶ 开始处理任务 {task_id}")
        self.ctx.logger.info(f"[{agent_id}]   查询: {query[:100]}...")

    def on_thinking(self, agent_id: str, thought: str) -> None:
        """Agent 思考"""
        self.ctx.logger.info(f"[{agent_id}]   💭 思考: {thought[:80]}...")

    def on_tool_call(self, agent_id: str, tool_name: str, tool_input: dict) -> None:
        """工具调用开始"""
        input_preview = str(tool_input)[:100]
        self.ctx.logger.info(f"[{agent_id}]   🔧 调用工具: {tool_name}")
        self.ctx.logger.debug(f"[{agent_id}]     输入: {input_preview}...")

    def on_tool_result(self, agent_id: str, tool_name: str, result: str, success: bool) -> None:
        """工具调用结果"""
        status = "✓" if success else "✗"
        result_preview = result[:100] if result else "[无输出]"
        self.ctx.logger.info(f"[{agent_id}]   {status} {tool_name}: {result_preview}...")

    def on_iteration(self, agent_id: str, iteration: int, max_iters: int) -> None:
        """ReAct 迭代"""
        self.ctx.logger.debug(f"[{agent_id}]   迭代 {iteration}/{max_iters}")

    def on_react_complete(self, agent_id: str, task_id: str, success: bool, summary: str) -> None:
        """ReAct 循环完成"""
        status = "✓ 完成" if success else "✗ 失败"
        self.ctx.logger.info(f"[{agent_id}] ◀ {status}: {summary[:80]}")

    def on_task_board_update(self, agent_id: str, tasks: list[dict]) -> None:
        """任务板更新"""
        self.ctx.logger.debug(f"[{agent_id}]   📋 任务板: {len(tasks)} 个任务")
        for task in tasks[:3]:
            status_icon = {"pending": "○", "in_progress": "◐", "completed": "●"}.get(task.get("status"), "?")
            self.ctx.logger.debug(f"[{agent_id}]     {status_icon} {task.get('content', '')[:50]}")
```

### 方案 2：在 `ModularAgent.reply()` 中集成 Observer

修改 `_modular_agent.py` 中的 ReAct 循环：

```python
async def reply(self, msg: Msg | Sequence[Msg] | None = None, **kwargs: Any) -> Msg:
    # 获取 observer
    from agentscope.scripts._observability import get_agent_react_observer
    observer = get_agent_react_observer()

    # ReAct 开始
    task_id = kwargs.get("task_id", "unknown")
    observer.on_react_start(self.id, task_id, user_query)

    for iteration in range(max_iters):
        observer.on_iteration(self.id, iteration + 1, max_iters)

        # LLM 调用...
        resp = await self.llm(llm_messages, tools=tool_schemas)

        # 提取思考内容
        if text_content:
            observer.on_thinking(self.id, text_content)

        # 工具调用
        for tool_call in tool_call_blocks:
            observer.on_tool_call(self.id, tool_name, tool_input)
            try:
                result = await self.toolkit.call_tool_function(...)
                observer.on_tool_result(self.id, tool_name, result_text, True)
            except Exception as e:
                observer.on_tool_result(self.id, tool_name, str(e), False)

        # 任务板更新
        if self.task_board:
            observer.on_task_board_update(self.id, self.task_board.get_all_tasks())

    # ReAct 完成
    observer.on_react_complete(self.id, task_id, True, response_text[:100])
```

### 方案 3：改进 Agent 选择策略

修改 `_agent_market.py`：

```python
def default_agent_profiles() -> dict[str, dict[str, Any]]:
    return {
        # builder-agent 只处理 "通用开发" 类型，不再覆盖所有类型
        "builder-agent": _profile(
            name="BuilderAgent",
            role="developer",
            capabilities=["coding", "implementation", "fullstack"],  # 收窄范围
            base_score=0.70,  # 降低优先级
            description="通用开发任务",
        ),
        # 专业 Agent 提高优先级
        "frontend-agent": _profile(
            name="FrontendAgent",
            role="frontend-developer",
            capabilities=["frontend", "react", "vue", "html", "css", "javascript", "ui"],
            base_score=0.90,  # 提高优先级
            description="前端开发专家",
        ),
        "backend-agent": _profile(
            name="BackendAgent",
            role="backend-developer",
            capabilities=["backend", "api", "database", "python", "fastapi", "django"],
            base_score=0.90,  # 提高优先级
            description="后端开发专家",
        ),
        # ...
    }
```

并添加强制路由规则：

```python
def route_requirement_to_agent(requirement: dict) -> str:
    """根据需求类型强制路由到专业 Agent"""
    req_type = requirement.get("type", "").lower()

    ROUTING_TABLE = {
        "database": "backend-agent",
        "backend": "backend-agent",
        "api": "backend-agent",
        "frontend": "frontend-agent",
        "ui": "ux-agent",
        "design": "ux-agent",
        "test": "qa-agent",
    }

    return ROUTING_TABLE.get(req_type, "builder-agent")
```

---

## 实现优先级

1. **P0 - 可观测性**：添加 `AgentReActObserver` 和集成到 `ModularAgent`
2. **P1 - Agent 路由**：改进 Agent 选择策略
3. **P2 - 任务板可视化**：在 CLI 中实时显示 Agent 任务板状态

## 预期效果

```
[CLI] 开始执行: 14 个需求

[REQ-001] 数据库设计 -> backend-agent
  [backend-agent] ▶ 开始处理任务 REQ-001
    💭 思考: 需要设计会员、课程、预约等数据模型...
    🔧 调用工具: claude_code_edit
      输入: 创建 backend/app/models/member.py...
    ✓ claude_code_edit: 创建了 member.py, course.py...
    💭 思考: 模型创建完成，接下来添加关系...
    📋 任务板: 2 个任务
      ● 创建数据模型
      ○ 添加关系约束
  [backend-agent] ◀ ✓ 完成: 数据库模型设计完成

[REQ-002] 会员注册 API -> backend-agent
  ...
```
