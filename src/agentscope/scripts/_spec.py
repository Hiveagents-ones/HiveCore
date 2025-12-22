# -*- coding: utf-8 -*-
"""Requirement specification collection and processing.

This module provides:
- Requirement ID generation
- Specification collection via LLM
- Acceptance criteria enrichment
"""
from __future__ import annotations

import json
import re
import textwrap
from typing import Any


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename.

    Args:
        name: Original name

    Returns:
        str: Sanitized filename
    """
    # Replace unsafe characters
    safe = re.sub(r"[^\w\-_.]", "_", name)
    # Remove consecutive underscores
    safe = re.sub(r"_+", "_", safe)
    # Trim to reasonable length
    return safe[:100].strip("_")


def ensure_requirement_ids(requirements: list[dict[str, Any]]) -> None:
    """Ensure all requirements have unique IDs.

    Modifies requirements in-place to add missing IDs.

    Args:
        requirements: List of requirement dicts
    """
    for i, req in enumerate(requirements):
        if not req.get("id"):
            req["id"] = f"REQ-{i + 1:03d}"


def print_requirements(requirements: list[dict[str, Any]]) -> None:
    """Print requirements in a formatted way.

    Args:
        requirements: List of requirement dicts
    """
    from ._observability import get_logger
    logger = get_logger()

    logger.info("\n=== 需求列表 ===")
    for i, req in enumerate(requirements, 1):
        rid = req.get("id", f"REQ-{i}")
        title = req.get("title", req.get("summary", "未命名"))
        category = req.get("category", "通用")
        logger.info(f"  [{rid}] {title} ({category})")
    logger.info("")


# ---------------------------------------------------------------------------
# Specification Collection
# ---------------------------------------------------------------------------
async def collect_spec(
    llm: Any,
    initial_requirement: str,
    scripted_inputs: list[str] | None = None,
    auto_confirm: bool = False,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Collect and refine project specification via LLM.

    Args:
        llm: LLM model instance
        initial_requirement: Initial user requirement text
        scripted_inputs: Pre-defined inputs for testing
        auto_confirm: Whether to auto-confirm without user input
        verbose: Whether to print debug info

    Returns:
        dict: Specification dict with requirements, summary, etc.
    """
    from ._llm_utils import call_llm_json

    # Build prompt for requirement analysis
    prompt = textwrap.dedent(f"""
        请分析以下用户需求，并将其拆分为具体的可执行需求项。

        【用户需求】
        {initial_requirement}

        【输出格式】
        请输出 JSON:
        {{
            "summary": "项目整体描述（1-2句话）",
            "project_type": "web|api|cli|library|other",
            "requirements": [
                {{
                    "id": "REQ-001",
                    "title": "需求标题",
                    "summary": "详细描述",
                    "category": "frontend|backend|database|ui|api|other",
                    "priority": "high|medium|low"
                }}
            ],
            "tech_stack": {{
                "frontend": "推荐的前端技术",
                "backend": "推荐的后端技术",
                "database": "推荐的数据库"
            }},
            "clarification_questions": ["需要澄清的问题1", "问题2"]
        }}

        【要求】
        1. 每个需求应该是独立可验收的
        2. 需求粒度适中，不要过于宏观或过于细节
        3. 如果需求不清晰，列出需要澄清的问题
        4. 根据需求类型推荐合适的技术栈
    """)

    if verbose:
        from ._observability import get_logger
        get_logger().debug("[Spec] 分析用户需求...")

    spec, _ = await call_llm_json(
        llm,
        [
            {"role": "system", "content": "你是项目需求分析师，善于将模糊需求转化为具体的可执行需求列表。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        label="collect_spec",
        verbose=verbose,
    )

    # Ensure requirements have IDs
    requirements = spec.get("requirements", [])
    ensure_requirement_ids(requirements)

    # Handle clarification questions
    questions = spec.get("clarification_questions", [])
    if questions and not auto_confirm:
        from ._observability import get_logger
        logger = get_logger()
        logger.info("\n需要澄清以下问题：")
        for i, q in enumerate(questions, 1):
            logger.info(f"  {i}. {q}")

        if scripted_inputs:
            answers = scripted_inputs[:len(questions)]
            scripted_inputs = scripted_inputs[len(questions):]
        else:
            from ._observability import get_logger
            get_logger().info("\n请输入答案（每行一个，输入空行结束）：")
            answers = []
            for _ in questions:
                ans = input().strip()
                if not ans:
                    break
                answers.append(ans)

        # Refine spec with answers
        if answers:
            refine_prompt = textwrap.dedent(f"""
                根据用户的回答，更新需求规格。

                【原始规格】
                {json.dumps(spec, ensure_ascii=False, indent=2)}

                【用户回答】
                {json.dumps(dict(zip(questions, answers)), ensure_ascii=False, indent=2)}

                请输出更新后的完整 JSON 规格（格式同上）。
            """)

            spec, _ = await call_llm_json(
                llm,
                [
                    {"role": "system", "content": "你是项目需求分析师。"},
                    {"role": "user", "content": refine_prompt},
                ],
                temperature=0.3,
                label="refine_spec",
                verbose=verbose,
            )

            requirements = spec.get("requirements", [])
            ensure_requirement_ids(requirements)

    # Print summary
    from ._observability import get_logger
    get_logger().info(f"\n项目概述: {spec.get('summary', '未知')}")
    print_requirements(requirements)

    # Confirm
    if not auto_confirm:
        if scripted_inputs:
            confirm = scripted_inputs.pop(0).lower() in ("y", "yes", "确认", "是")
        else:
            confirm = input("确认以上需求？(y/n): ").strip().lower() in ("y", "yes", "确认", "是")

        if not confirm:
            from ._observability import get_logger
            get_logger().info("已取消")
            return {"requirements": [], "summary": "", "cancelled": True}

    # Initialize acceptance structure
    spec.setdefault("acceptance", {
        "overall_target": 0.95,
        "per_requirement_target": 0.90,
    })
    spec.setdefault("acceptance_map", [])

    return spec


# ---------------------------------------------------------------------------
# Acceptance Criteria
# ---------------------------------------------------------------------------
async def enrich_acceptance_map(
    llm: Any,
    spec: dict[str, Any],
    *,
    verbose: bool = False,
) -> None:
    """Enrich specification with acceptance criteria for each requirement.

    Modifies spec in-place to add acceptance_map.

    Args:
        llm: LLM model instance
        spec: Specification dict
        verbose: Whether to print debug info
    """
    from ._llm_utils import call_llm_json

    requirements = spec.get("requirements", [])
    if not requirements:
        return

    acceptance_map = spec.get("acceptance_map", [])

    for i, req in enumerate(requirements):
        rid = req.get("id", f"REQ-{i + 1}")

        # Check if already has criteria
        existing = next((a for a in acceptance_map if a.get("requirement_id") == rid), None)
        if existing and existing.get("criteria"):
            continue

        prompt = textwrap.dedent(f"""
            为以下需求生成验收标准。

            【需求】
            ID: {rid}
            标题: {req.get('title', '')}
            描述: {req.get('summary', req.get('description', ''))}
            类别: {req.get('category', '')}

            【输出格式】
            ```json
            {{
                "standards": [
                    {{
                        "id": "{rid}.1",
                        "title": "验收标准标题",
                        "description": "详细描述",
                        "test_method": "如何验证此标准"
                    }}
                ]
            }}
            ```

            【要求】
            1. 每个需求生成 3-5 个具体的验收标准
            2. 标准应该是可量化、可验证的
            3. 覆盖功能、性能、用户体验等方面
        """)

        data, _ = await call_llm_json(
            llm,
            [
                {"role": "system", "content": "你是 QA 专家，善于制定验收标准。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
            label=f"acceptance_map:{rid}",
            verbose=verbose,
        )

        standards = data.get("standards") or data.get("criteria") or []

        if existing:
            existing["criteria"] = standards
        else:
            acceptance_map.append({
                "requirement_id": rid,
                "criteria": standards,
            })

        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Spec] ({i + 1}/{len(requirements)}) {rid} 生成 {len(standards)} 条验收标准")

    spec["acceptance_map"] = acceptance_map


def criteria_for_requirement(
    spec: dict[str, Any],
    requirement_id: str,
) -> list[dict[str, Any]]:
    """Get acceptance criteria for a specific requirement.

    Args:
        spec: Specification dict
        requirement_id: Requirement ID

    Returns:
        list: List of criteria dicts
    """
    for item in spec.get("acceptance_map", []):
        if item.get("requirement_id") == requirement_id:
            return item.get("criteria", [])
    return []


__all__ = [
    "sanitize_filename",
    "ensure_requirement_ids",
    "print_requirements",
    "collect_spec",
    "enrich_acceptance_map",
    "criteria_for_requirement",
]
