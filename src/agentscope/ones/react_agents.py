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
            "当你需要更多信息时，要明确写出缺口并提出具体请求。"
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


class BackendReActAgent(SpecialistReActAgent):
    role_description = "后端工程官"
    deliverable_expectation = "搭建AI网站的服务层、缓存与权限方案"
    collaboration_guidelines = (
        "列出接口定义与数据模型",
        "描述模型推理/检索链路",
        "评估可观测性与扩缩策略",
    )


class QAReActAgent(SpecialistReActAgent):
    role_description = "质量官"
    deliverable_expectation = "制定AI建站验收清单、黑白盒测试与监控方案"
    collaboration_guidelines = (
        "覆盖功能、提示词质量、可用性三层指标",
        "记录阻塞级别与复测步骤",
        "输出上线前后的监控触发条件",
    )
