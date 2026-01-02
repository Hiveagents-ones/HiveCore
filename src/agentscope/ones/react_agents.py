# -*- coding: utf-8 -*-
"""Specialized ReAct agents for the One·s delivery stack.

Architecture Model:
- Agent = Brain (大脑): High-level decision making, task analysis, planning
- Claude Code = Limbs (四肢): Code execution, file operations
- MCP/Toolkit = Tools (工具): Resources used by Claude Code

Each Agent uses claude_code_edit as its "limbs" to execute code-related tasks.
"""
from __future__ import annotations

from ..agent import ReActAgent
from ..formatter import FormatterBase
from ..memory import MemoryBase, LongTermMemoryBase
from ..model import ChatModelBase
from ..plan import PlanNotebook
from ..rag import KnowledgeBase
from ..tool import Toolkit


# ---------------------------------------------------------------------------
# Claude Code Integration Prompt (Shared by all code-capable agents)
# ---------------------------------------------------------------------------
CLAUDE_CODE_LIMBS_PROMPT = """
## 🦾 你的"四肢" - Claude Code

你拥有一个强大的执行工具 `claude_code_edit`，它是你的"四肢"，负责所有代码编写和文件操作。

### 工作模式：大脑-四肢分工

**你（大脑）负责：**
1. 分析需求，理解任务目标
2. 制定实现计划，列出任务清单
3. 决定技术方案和架构
4. 评估执行结果，提供反馈

**Claude Code（四肢）负责：**
1. 探索代码库，了解现有结构
2. 创建和修改文件
3. 编写具体代码实现
4. 执行命令和测试

### 如何使用四肢

当需要编写代码或修改文件时，调用 `claude_code_edit` 工具：

```
claude_code_edit(
    prompt="你的指令，描述要做什么",
    workspace="/path/to/project"  # 可选，指定工作目录
)
```

### 指令编写技巧

给四肢的指令应该：
- **清晰具体**：明确说明要创建/修改哪些文件
- **包含上下文**：提供必要的技术背景和约束
- **指定验收标准**：说明完成后应该达到什么效果

示例：
```
claude_code_edit(prompt=\"\"\"
请在 backend/app/routers/ 目录下创建 users.py 文件，实现用户管理 API：

1. GET /users - 获取用户列表，支持分页
2. POST /users - 创建新用户
3. GET /users/{id} - 获取用户详情
4. PUT /users/{id} - 更新用户信息
5. DELETE /users/{id} - 删除用户

技术要求：
- 使用 FastAPI 和 Pydantic v2
- 数据库操作使用 SQLAlchemy
- 包含适当的错误处理

请确保代码完整可运行。
\"\"\")
```

### 任务拆分原则（重要！）

**每次调用四肢时，任务应该足够小：**
- 每次只处理 **1-2 个文件**
- **避免同时处理前端和后端** - 先完成一端，再处理另一端
- 如果任务涉及多个模块，**分多次调用**

**正确做法示例：**
```
# 第一次调用：只创建模型
claude_code_edit(prompt="创建 backend/app/models/user.py，定义 User 模型")

# 第二次调用：只创建路由
claude_code_edit(prompt="创建 backend/app/routers/users.py，实现用户 API")

# 第三次调用：只创建前端组件
claude_code_edit(prompt="创建 frontend/src/views/UserList.vue")
```

**错误做法（会导致超时）：**
```
# 不要这样！任务太大
claude_code_edit(prompt="创建完整的用户管理系统，包括前端和后端所有文件")
```

### 重要原则

1. **不要自己写代码** - 让四肢（Claude Code）来写
2. **专注于决策** - 你负责"想"，四肢负责"做"
3. **验证结果** - 四肢执行后，评估是否满足要求
4. **小步快跑** - 每次调用四肢只做一件小事，多次调用完成大任务
"""


class SpecialistReActAgent(ReActAgent):
    """Base class that injects opinionated prompts for specialist roles.

    Each specialist agent acts as a "brain" with its own expertise,
    using Claude Code as its "limbs" to execute code-related tasks.
    """

    role_description: str = "Specialist"
    deliverable_expectation: str = "Produce structured responses"
    collaboration_guidelines: tuple[str, ...] = (
        "同步上下游任务依赖",
        "遇到阻塞时给出下一步建议",
        "所有产出需可追溯",
    )
    # Whether this agent can use Claude Code as limbs
    has_code_limbs: bool = False

    def __init__(
        self,
        *,
        name: str,
        model: ChatModelBase,
        formatter: FormatterBase,
        sys_prompt: str | None = None,
        toolkit: Toolkit | None = None,
        memory: MemoryBase | None = None,
        long_term_memory: LongTermMemoryBase | None = None,
        knowledge: KnowledgeBase | list[KnowledgeBase] | None = None,
        plan_notebook: PlanNotebook | None = None,
        **kwargs,
    ) -> None:
        prompt = sys_prompt or self.build_prompt()
        super().__init__(
            name=name,
            sys_prompt=prompt,
            model=model,
            formatter=formatter,
            toolkit=toolkit,
            memory=memory,
            long_term_memory=long_term_memory,
            knowledge=knowledge,
            plan_notebook=plan_notebook,
            **kwargs,
        )

    @classmethod
    def build_prompt(cls) -> str:
        guidelines = "\n".join(f"- {item}" for item in cls.collaboration_guidelines)
        base_prompt = (
            f"角色: {cls.role_description}\n"
            f"使命: {cls.deliverable_expectation}\n"
            "协作守则:\n"
            f"{guidelines}\n"
            "当你需要更多信息时，要明确写出缺口并提出具体请求。\n"
        )

        # Add Claude Code limbs prompt for code-capable agents
        if cls.has_code_limbs:
            base_prompt += CLAUDE_CODE_LIMBS_PROMPT

        base_prompt += """
## 重要：记录技术决策
当你做出重要的技术决策时（如选择框架、库、架构模式、API设计等），
必须在输出中使用以下格式记录，以便后续Agent遵循：

```
[决策记录]
- 类型: tech_stack / architecture / api_design / component / constraint / dependency
- 键: 决策名称（如 frontend_framework, database, api_pattern）
- 值: 决策内容（如 Vue 3, PostgreSQL, RESTful）
- 说明: 选择原因或约束说明
```

例如：
```
[决策记录]
- 类型: tech_stack
- 键: frontend_framework
- 值: Vue 3
- 说明: 使用 Vue 3 Composition API，配合 Pinia 状态管理
```

这些决策会被记录到项目记忆中，后续Agent会自动遵循。

## 重要：记录依赖包
**当你在代码中使用任何第三方库时，必须记录依赖**：

```
[决策记录]
- 类型: dependency
- 键: 包名（如 pydantic, sqlalchemy, fastapi）
- 值: 版本要求（如 >=2.0.0, ~=1.4.0，或 latest）
- 说明: 用途说明
```

## 重要：Pydantic v2 兼容性
使用 Pydantic 时必须遵循 v2 语法：
- 使用 `model_config = ConfigDict(from_attributes=True)` 而非 `class Config: orm_mode = True`
- 使用 `field_validator` 而非 `validator`
- 使用 `model_validator` 而非 `root_validator`
- 从 `pydantic` 导入 `ConfigDict`
"""
        return base_prompt


class StrategyReActAgent(SpecialistReActAgent):
    """Strategy agent - focuses on high-level planning, no code limbs needed."""

    role_description = "策略官"
    deliverable_expectation = "分解需求、标注依赖、输出任务图摘要"
    has_code_limbs = False  # Strategy is pure brain work
    collaboration_guidelines = (
        "优先澄清SLA与验收标准",
        "输出包含优先级、假设、风险",
        "对AA提出的上下文进行一致性校验",
    )


class BuilderReActAgent(SpecialistReActAgent):
    """Builder agent - uses Claude Code as limbs to implement solutions."""

    role_description = "构建官"
    deliverable_expectation = "根据任务图实施方案、使用四肢（Claude Code）执行构建"
    has_code_limbs = True  # Builder needs limbs to write code
    collaboration_guidelines = (
        "每次执行前确认输入与资源是否齐备",
        "分析任务后，调用 claude_code_edit 让四肢执行",
        "以表格形式列出产出与验证结果",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for builder agent."""
        base = super().build_prompt()
        return base + """

## 构建最佳实践
1. 先分析任务，理解要实现什么
2. 列出任务清单和实现计划
3. 调用 claude_code_edit 让四肢执行具体编码
4. 验证四肢的执行结果
5. 遇到阻塞时及时反馈并提供替代方案
"""


class ReviewerReActAgent(SpecialistReActAgent):
    """Reviewer agent - focuses on evaluation, no code limbs needed."""

    role_description = "验收官"
    deliverable_expectation = "对照SLA审核产出并给出放行/返工意见"
    has_code_limbs = False  # Reviewer is pure brain work
    collaboration_guidelines = (
        "明确引用SLA条款",
        "列出关键风险和回归测试建议",
        "返工时必须指定责任Agent",
    )


class ProductReActAgent(SpecialistReActAgent):
    """Product agent - focuses on requirements, no code limbs needed."""

    role_description = "产品官"
    deliverable_expectation = "梳理AI建站需求、定义SLA与MVP范围"
    has_code_limbs = False  # Product is pure brain work
    collaboration_guidelines = (
        "将用户意图映射为页面/模块清单",
        "标注数据/接口依赖，确认AI能力形态",
        "提供可立即执行的优先级排序",
    )


class UxReActAgent(SpecialistReActAgent):
    """UX agent - focuses on design, no code limbs needed."""

    role_description = "体验官"
    deliverable_expectation = "输出信息架构、线框稿与提示词策略"
    has_code_limbs = False  # UX is pure brain work
    collaboration_guidelines = (
        "以用户任务流为线索标注交互节点",
        "说明需要AI生成的素材及质量要求",
        "针对可视化需求提供示例或配色建议",
    )


class FrontendReActAgent(SpecialistReActAgent):
    """Frontend agent - uses Claude Code as limbs to write frontend code."""

    role_description = "前端工程官"
    deliverable_expectation = "分析前端需求，指挥四肢（Claude Code）实现响应式页面"
    has_code_limbs = True  # Frontend needs limbs to write code
    collaboration_guidelines = (
        "明确每个组件的输入输出",
        "说明与后端/推理服务的契约",
        "调用 claude_code_edit 让四肢实现组件",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for frontend agent."""
        base = super().build_prompt()
        return base + """

## 前端开发最佳实践
1. 分析需求，设计组件结构
2. 调用 claude_code_edit 让四肢实现具体组件
3. 验证四肢的执行结果
4. Vue/React 组件应该模块化、可复用
5. 确保响应式设计和可访问性
"""


class BackendReActAgent(SpecialistReActAgent):
    """Backend agent - uses Claude Code as limbs to write backend code."""

    role_description = "后端工程官"
    deliverable_expectation = "设计后端架构，指挥四肢（Claude Code）实现服务层"
    has_code_limbs = True  # Backend needs limbs to write code
    collaboration_guidelines = (
        "列出接口定义与数据模型",
        "描述模型推理/检索链路",
        "调用 claude_code_edit 让四肢实现 API",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for backend agent."""
        base = super().build_prompt()
        return base + """

## 后端开发最佳实践
1. 分析需求，设计 API 和数据模型
2. 调用 claude_code_edit 让四肢实现具体代码
3. 验证四肢的执行结果
4. API 设计遵循 RESTful 规范
5. 确保数据模型和接口定义清晰

## 重要：Pydantic v2 与 pydantic-settings
在 Pydantic v2 中，`BaseSettings` 已移至独立的 `pydantic-settings` 包：

```python
# ✅ 正确 - 从 pydantic-settings 导入
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```
"""


class QAReActAgent(SpecialistReActAgent):
    """QA agent - uses Claude Code as limbs to write tests and validate."""

    role_description = "质量官"
    deliverable_expectation = "制定验收标准，指挥四肢（Claude Code）编写测试"
    has_code_limbs = True  # QA can write test code
    collaboration_guidelines = (
        "覆盖功能、提示词质量、可用性三层指标",
        "调用 claude_code_edit 让四肢编写测试代码",
        "输出上线前后的监控触发条件",
    )


class DeveloperReActAgent(SpecialistReActAgent):
    """Developer agent - the most general code-capable agent.

    Uses Claude Code as limbs for all code operations.
    """

    role_description = "开发工程师"
    deliverable_expectation = "分析开发任务，指挥四肢（Claude Code）实现功能"
    has_code_limbs = True  # Developer definitely needs limbs
    collaboration_guidelines = (
        "分析任务需求，制定实现计划",
        "调用 claude_code_edit 让四肢执行具体编码",
        "验证四肢的执行结果，必要时迭代修正",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for the developer agent."""
        base = super().build_prompt()
        return base + """

## 开发工作流程
1. **理解需求**：分析任务目标和验收标准
2. **制定计划**：列出需要创建/修改的文件和功能
3. **调用四肢**：使用 claude_code_edit 让四肢执行具体编码
4. **验证结果**：检查四肢的输出是否满足要求
5. **迭代修正**：如有问题，提供反馈让四肢修正

记住：你是"大脑"，负责思考和决策；Claude Code 是你的"四肢"，负责执行。
"""
