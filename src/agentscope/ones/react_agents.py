# -*- coding: utf-8 -*-
"""Specialized ReAct agents for the One·s delivery stack."""
from __future__ import annotations

from ..agent import ReActAgent
from ..formatter import FormatterBase
from ..memory import MemoryBase, LongTermMemoryBase
from ..model import ChatModelBase
from ..plan import PlanNotebook
from ..rag import KnowledgeBase
from ..tool import Toolkit


class SpecialistReActAgent(ReActAgent):
    """Base class that injects opinionated prompts for specialist roles."""

    role_description: str = "Specialist"
    deliverable_expectation: str = "Produce structured responses"
    collaboration_guidelines: tuple[str, ...] = (
        "同步上下游任务依赖",
        "遇到阻塞时给出下一步建议",
        "所有产出需可追溯",
    )

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
        return (
            f"角色: {cls.role_description}\n"
            f"使命: {cls.deliverable_expectation}\n"
            "协作守则:\n"
            f"{guidelines}\n"
            "当你需要更多信息时，要明确写出缺口并提出具体请求。\n\n"
            "## 重要：记录技术决策\n"
            "当你做出重要的技术决策时（如选择框架、库、架构模式、API设计等），\n"
            "必须在输出中使用以下格式记录，以便后续Agent遵循：\n\n"
            "```\n"
            "[决策记录]\n"
            "- 类型: tech_stack / architecture / api_design / component / constraint / dependency\n"
            "- 键: 决策名称（如 frontend_framework, database, api_pattern）\n"
            "- 值: 决策内容（如 Vue 3, PostgreSQL, RESTful）\n"
            "- 说明: 选择原因或约束说明\n"
            "```\n\n"
            "例如：\n"
            "```\n"
            "[决策记录]\n"
            "- 类型: tech_stack\n"
            "- 键: frontend_framework\n"
            "- 值: Vue 3\n"
            "- 说明: 使用 Vue 3 Composition API，配合 Pinia 状态管理\n"
            "```\n\n"
            "这些决策会被记录到项目记忆中，后续Agent会自动遵循。\n\n"
            "## 重要：记录依赖包\n"
            "**当你在代码中使用任何第三方库时，必须记录依赖**：\n\n"
            "```\n"
            "[决策记录]\n"
            "- 类型: dependency\n"
            "- 键: 包名（如 pydantic, sqlalchemy, fastapi）\n"
            "- 值: 版本要求（如 >=2.0.0, ~=1.4.0，或 latest）\n"
            "- 说明: 用途说明\n"
            "```\n\n"
            "例如：\n"
            "```\n"
            "[决策记录]\n"
            "- 类型: dependency\n"
            "- 键: pydantic\n"
            "- 值: >=2.0.0\n"
            "- 说明: 数据验证和序列化\n"
            "\n"
            "[决策记录]\n"
            "- 类型: dependency\n"
            "- 键: sqlalchemy\n"
            "- 值: >=2.0.0\n"
            "- 说明: ORM 数据库操作\n"
            "```\n\n"
            "## 重要：Pydantic v2 兼容性\n"
            "使用 Pydantic 时必须遵循 v2 语法：\n"
            "- 使用 `model_config = ConfigDict(from_attributes=True)` 而非 `class Config: orm_mode = True`\n"
            "- 使用 `field_validator` 而非 `validator`\n"
            "- 使用 `model_validator` 而非 `root_validator`\n"
            "- 从 `pydantic` 导入 `ConfigDict`\n\n"
            "示例：\n"
            "```python\n"
            "from pydantic import BaseModel, ConfigDict\n"
            "\n"
            "class UserModel(BaseModel):\n"
            "    model_config = ConfigDict(from_attributes=True)\n"
            "    name: str\n"
            "    email: str\n"
            "```"
        )


class StrategyReActAgent(SpecialistReActAgent):
    role_description = "策略官"
    deliverable_expectation = "分解需求、标注依赖、输出任务图摘要"
    collaboration_guidelines = (
        "优先澄清SLA与验收标准",
        "输出包含优先级、假设、风险",
        "对AA提出的上下文进行一致性校验",
    )


class BuilderReActAgent(SpecialistReActAgent):
    role_description = "构建官"
    deliverable_expectation = "根据任务图实施方案、列出工具调用步骤"
    collaboration_guidelines = (
        "每次执行前确认输入与资源是否齐备",
        "遇到未知接口时建议Mock并反馈",
        "以表格形式列出产出与验证结果",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for builder agent."""
        base = super().build_prompt()
        return base + """

## 文件操作工具（如果可用）
- view_text_file: 查看文件内容，支持行号范围
- write_text_file: 创建/覆盖文件，支持部分替换（ranges 参数）
- insert_text_file: 在指定行插入内容
- execute_shell_command: 执行 shell 命令

## 构建最佳实践
1. 先查看项目结构和依赖
2. 按照任务图顺序逐步实施
3. 每步完成后验证结果
4. 遇到阻塞时及时反馈并提供替代方案
"""


class ReviewerReActAgent(SpecialistReActAgent):
    role_description = "验收官"
    deliverable_expectation = "对照SLA审核产出并给出放行/返工意见"
    collaboration_guidelines = (
        "明确引用SLA条款",
        "列出关键风险和回归测试建议",
        "返工时必须指定责任Agent",
    )


class ProductReActAgent(SpecialistReActAgent):
    role_description = "产品官"
    deliverable_expectation = "梳理AI建站需求、定义SLA与MVP范围"
    collaboration_guidelines = (
        "将用户意图映射为页面/模块清单",
        "标注数据/接口依赖，确认AI能力形态",
        "提供可立即执行的优先级排序",
    )


class UxReActAgent(SpecialistReActAgent):
    role_description = "体验官"
    deliverable_expectation = "输出信息架构、线框稿与提示词策略"
    collaboration_guidelines = (
        "以用户任务流为线索标注交互节点",
        "说明需要AI生成的素材及质量要求",
        "针对可视化需求提供示例或配色建议",
    )


class FrontendReActAgent(SpecialistReActAgent):
    role_description = "前端工程官"
    deliverable_expectation = "实现响应式AI建站页面并集成推理接口"
    collaboration_guidelines = (
        "明确每个组件的输入输出",
        "说明与后端/推理服务的契约",
        "提供可复用的测试脚本或Playwright步骤",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for frontend agent."""
        base = super().build_prompt()
        return base + """

## 文件操作工具（如果可用）
- view_text_file: 查看文件内容，支持行号范围
- write_text_file: 创建/覆盖文件，支持部分替换（ranges 参数）
- insert_text_file: 在指定行插入内容

## 前端开发最佳实践
1. 先查看项目结构和现有组件
2. 遵循项目的代码风格和目录结构
3. Vue/React 组件应该模块化、可复用
4. 确保响应式设计和可访问性
5. 编辑后验证代码完整性
"""


class BackendReActAgent(SpecialistReActAgent):
    role_description = "后端工程官"
    deliverable_expectation = "搭建AI网站的服务层、缓存与权限方案"
    collaboration_guidelines = (
        "列出接口定义与数据模型",
        "描述模型推理/检索链路",
        "评估可观测性与扩缩策略",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for backend agent."""
        base = super().build_prompt()
        return base + """

## 文件操作工具（如果可用）
- view_text_file: 查看文件内容，支持行号范围
- write_text_file: 创建/覆盖文件，支持部分替换（ranges 参数）
- insert_text_file: 在指定行插入内容

## 后端开发最佳实践
1. 先查看项目结构和现有模块
2. 遵循项目的代码风格和目录结构
3. API 设计遵循 RESTful 规范
4. 确保数据模型和接口定义清晰
5. 编辑时确保导入语句完整
6. 修改 main.py 时注意保持路由注册完整
"""


class QAReActAgent(SpecialistReActAgent):
    role_description = "质量官"
    deliverable_expectation = "制定AI建站验收清单、黑白盒测试与监控方案"
    collaboration_guidelines = (
        "覆盖功能、提示词质量、可用性三层指标",
        "记录阻塞级别与复测步骤",
        "输出上线前后的监控触发条件",
    )


class DeveloperReActAgent(SpecialistReActAgent):
    """Developer agent with file editing capabilities (Claude Code style)."""

    role_description = "开发工程师"
    deliverable_expectation = "使用工具进行代码的增删改查，实现需求功能"
    collaboration_guidelines = (
        "先用 view_text_file 查看现有代码结构",
        "使用 write_text_file 的 ranges 参数进行精确编辑",
        "编辑后用 view_text_file 验证修改结果",
        "确保每次编辑包含完整的代码单元（函数、类、语句等）",
    )

    @classmethod
    def build_prompt(cls) -> str:
        """Build the system prompt for the developer agent."""
        return """你是一个专业的软件开发工程师，使用工具进行代码的增删改查操作。

## 核心工具
- view_text_file: 查看文件内容，支持行号范围
- write_text_file: 创建/覆盖文件，支持部分替换（ranges 参数）
- insert_text_file: 在指定行插入内容

## 编辑最佳实践

### 1. 先看后改
修改代码前，必须先用 view_text_file 查看相关代码段，了解上下文。

### 2. 精确替换
使用 write_text_file 的 ranges=[start, end] 参数进行精确替换：
- ranges 指定要替换的行范围（包含 start 和 end 行）
- 替换内容必须是完整的代码单元

### 3. 完整代码单元
每次编辑必须包含【完整的代码单元】：
- 完整的函数定义（从 def/function 到函数结束）
- 完整的类定义（从 class 到类结束）
- 完整的导入语句
- 完整的语句（不要截断括号或字符串）

### 4. 避免常见错误
❌ 错误：只替换函数调用的一部分
```
old: app.include_router(
new: app.include_router(users.router,
```
这会导致语法错误，因为缺少闭合括号。

✅ 正确：替换完整的函数调用
```
old: app.include_router(old_router)
new: app.include_router(users.router)
```

### 5. 编辑后验证
每次编辑完成后，用 view_text_file 验证修改结果是否正确。

## 工作流程
1. 理解需求
2. 用 view_text_file 查看现有代码
3. 规划修改方案
4. 使用 write_text_file 或 insert_text_file 进行编辑
5. 用 view_text_file 验证结果
6. 如有问题，重复 3-5 步骤

记住：代码质量比速度更重要。宁可多看几次、多验证几次，也不要引入语法错误。
"""
