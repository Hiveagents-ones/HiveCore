# -*- coding: utf-8 -*-
"""Tests for the specialized ReAct agents."""
import pytest

from agentscope.model import ChatModelBase, ChatResponse
from agentscope.formatter import FormatterBase
from agentscope.ones import (
    StrategyReActAgent,
    BuilderReActAgent,
    ReviewerReActAgent,
    ProductReActAgent,
    UxReActAgent,
    FrontendReActAgent,
    BackendReActAgent,
    QAReActAgent,
)


class DummyModel(ChatModelBase):
    def __init__(self) -> None:
        super().__init__(model_name="dummy", stream=False)

    async def __call__(self, *args, **kwargs):
        return ChatResponse(content=[])


class DummyFormatter(FormatterBase):
    async def format(self, *args, **kwargs):
        return []


@pytest.mark.parametrize(
    "cls, keyword",
    [
        (StrategyReActAgent, "策略官"),
        (BuilderReActAgent, "构建官"),
        (ReviewerReActAgent, "验收官"),
        (ProductReActAgent, "产品官"),
        (UxReActAgent, "体验官"),
        (FrontendReActAgent, "前端工程官"),
        (BackendReActAgent, "后端工程官"),
        (QAReActAgent, "质量官"),
    ],
)
def test_specialist_agents_have_role_prompts(cls, keyword):
    agent = cls(
        name="tester",
        model=DummyModel(),
        formatter=DummyFormatter(),
    )
    assert keyword in agent._sys_prompt
