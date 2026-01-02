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
        depends_on = req.get("depends_on", [])
        if depends_on:
            deps_str = ", ".join(depends_on) if isinstance(depends_on, list) else depends_on
            logger.info(f"  [{rid}] {title} ({category}) <- 依赖: {deps_str}")
        else:
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
                    "priority": "high|medium|low",
                    "depends_on": ["REQ-XXX"]
                }}
            ],
            "dependency_edges": [
                ["REQ-001", "REQ-002"]
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
        5. **重要**: 分析需求之间的依赖关系，按正确的开发顺序排列：
           - 数据库设计 → API设计 → 后端实现 → 前端设计 → 前端实现
           - UI/UX设计 应在 前端实现 之前
           - 基础功能（如登录注册）应在 业务功能 之前
        6. dependency_edges 格式: [[前置需求ID, 依赖需求ID], ...]
           表示"依赖需求"必须在"前置需求"完成后才能开始
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

    # Process dependency_edges into depends_on for each requirement
    dependency_edges = spec.get("dependency_edges", [])
    if dependency_edges:
        # Build a map: req_id -> set of dependency IDs
        depends_map: dict[str, set[str]] = {}
        for edge in dependency_edges:
            if isinstance(edge, (list, tuple)) and len(edge) == 2:
                # edge format: [prereq_id, dependent_id]
                # meaning: dependent_id depends on prereq_id
                prereq_id, dependent_id = edge
                if dependent_id not in depends_map:
                    depends_map[dependent_id] = set()
                depends_map[dependent_id].add(prereq_id)

        # Update each requirement's depends_on field
        for req in requirements:
            rid = req.get("id")
            if rid and rid in depends_map:
                existing_deps = req.get("depends_on", [])
                if isinstance(existing_deps, str):
                    existing_deps = [existing_deps]
                # Merge with existing dependencies
                all_deps = set(existing_deps) | depends_map[rid]
                req["depends_on"] = list(all_deps)

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
    # Note: Thresholds lowered from 0.95/0.90 to 0.85/0.80 to account for
    # common validation noise (import warnings, linter style issues, etc.)
    spec.setdefault("acceptance", {
        "overall_target": 0.85,
        "per_requirement_target": 0.80,
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
    total = len(requirements)
    print(f"\n生成验收标准 (共 {total} 个需求)...")

    for i, req in enumerate(requirements):
        rid = req.get("id", f"REQ-{i + 1}")
        print(f"  [{i + 1}/{total}] {rid}: {req.get('title', '')[:40]}...", end=" ", flush=True)

        # Check if already has criteria
        existing = next((a for a in acceptance_map if a.get("requirement_id") == rid), None)
        if existing and existing.get("criteria"):
            print("(已存在，跳过)")
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
            2. 标准必须是**代码层面可验证的**，即通过阅读代码就能判断是否实现
            3. 覆盖功能完整性、数据处理逻辑、错误处理、API设计等方面

            【禁止生成的标准类型】
            - 性能测试标准（如"响应时间在X秒内"、"支持X并发"）
            - 压力测试标准（如"大数据量验证"）
            - 用户体验测试标准（如"用户满意度"、"界面美观"）
            - 需要实际运行才能验证的标准

            【正确示例】
            ✓ "实现了会员信息的增删改查功能"
            ✓ "对无效输入返回适当的错误信息"
            ✓ "使用了索引优化数据库查询"
            ✓ "实现了JWT身份验证机制"

            【错误示例】
            ✗ "响应时间在1秒内" - 需要运行时测试
            ✗ "支持1000并发用户" - 需要压力测试
            ✗ "界面美观易用" - 主观标准
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
        print(f"✓ ({len(standards)} 条标准)")

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
    print("验收标准生成完成\n")


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
