# -*- coding: utf-8 -*-
"""Agent suggestion service - Holistic team planning based on all requirements.

This module analyzes ALL requirements together and suggests a unified team structure,
rather than suggesting agents per-requirement. The AA (Assistant Agent) reviews
the complete requirement list and delivery standards to determine optimal team composition.
"""

import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Team planning prompt - analyzes all requirements holistically
TEAM_PLANNING_PROMPT = """你是一个专业的项目团队规划专家。请分析以下项目需求列表，规划一个最优的团队结构。

## 项目需求列表
{requirements_text}

## 你的任务
1. 纵览所有需求，理解项目的整体范围和复杂度
2. 确定完成这些需求需要哪些专业角色（不是每个需求一个角色，而是整个项目需要的角色）
3. 为每个角色定义职责、技能要求和工作范围

## 输出格式
请以 JSON 格式输出团队规划，格式如下：
```json
{{
  "project_analysis": "项目整体分析（1-2句话）",
  "complexity": "low/medium/high",
  "team_size_recommendation": "建议团队规模（数字）",
  "roles": [
    {{
      "role": "角色名称（如：前端开发、后端开发、UI设计师等）",
      "name": "角色的中文名称",
      "description": "该角色在本项目中的具体职责",
      "skills": ["技能1", "技能2"],
      "domains": ["领域1", "领域2"],
      "assigned_requirements": ["需求ID1", "需求ID2"],
      "priority": "high/medium/low"
    }}
  ],
  "reasoning": "团队结构设计的理由"
}}
```

## 注意事项
- 角色数量应该合理（通常3-8个），不要为每个需求创建一个角色
- 相关的需求应该分配给同一个角色
- 考虑角色之间的协作关系
- 只输出 JSON，不要有其他内容
"""


def _compute_metaso_estimated_score(spec: dict[str, Any]) -> float:
    """Compute estimated score for a Metaso-generated agent spec."""
    return 0.50  # Base score for Metaso agent with cold start bonus


def _find_best_library_agent_for_role(
    role: str,
    skills: list[str],
    domains: list[str],
) -> dict[str, Any] | None:
    """Find the best matching agent from the library for a given role."""
    from api.models import Agent

    agents = Agent.objects.all()
    best_agent = None
    best_score = 0.0

    for agent in agents:
        score = _compute_library_agent_score(agent, role, skills, domains)
        if score > best_score:
            best_score = score
            best_agent = agent

    if best_agent and best_score >= 0.10:
        return {
            "agent_id": best_agent.id,
            "name": best_agent.name,
            "avatar": best_agent.avatar or "",
            "duty": best_agent.duty,
            "detail": best_agent.detail,
            "cost_per_min": float(best_agent.cost_per_min),
            "score": best_score,
        }
    return None


def _compute_library_agent_score(
    agent,
    role: str,
    skills: list[str],
    domains: list[str],
) -> float:
    """Compute score for a library agent based on role/skills/domains match."""
    score = 0.0
    agent_duty = (agent.duty or "").lower()
    role_lower = role.lower()

    if role_lower in agent_duty or agent_duty in role_lower:
        score += 0.3
    elif any(word in agent_duty for word in role_lower.split()):
        score += 0.15

    agent_detail = (agent.detail or "").lower()
    if skills:
        matched_skills = sum(1 for s in skills if s.lower() in agent_detail)
        score += 0.4 * (matched_skills / len(skills))

    if domains:
        matched_domains = sum(1 for d in domains if d.lower() in agent_detail)
        score += 0.3 * (matched_domains / len(domains))

    return min(1.0, score)


def _format_requirements_for_prompt(requirements: list[dict[str, Any]]) -> str:
    """Format requirements list into readable text for LLM prompt."""
    lines = []
    for i, req in enumerate(requirements, 1):
        req_id = req.get("id", f"req-{i}")
        content = req.get("content", "")
        skills = req.get("skills", [])

        line = f"{i}. [{req_id}] {content}"
        if skills:
            line += f" (技能要求: {', '.join(skills)})"
        lines.append(line)

    return "\n".join(lines)


def _parse_llm_response(response_text: str) -> dict[str, Any] | None:
    """Parse LLM response to extract JSON."""
    # Try to extract JSON from response
    text = response_text.strip()

    # Remove markdown code blocks if present
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON: %s", text[:200])
        return None


def suggest_agents_for_requirements(
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Suggest agents by analyzing ALL requirements holistically.

    Instead of suggesting one agent per requirement, this function:
    1. Combines all requirements into a comprehensive overview
    2. Asks LLM to analyze the entire project scope
    3. Returns a unified team structure with roles that cover multiple requirements

    Args:
        requirements: List of requirement dicts with 'id', 'content', and optional 'skills'.

    Returns:
        Dict with 'suggestions' (team roles), 'reasoning', 'complexity'.
    """
    import asyncio
    from agentscope.scripts._llm_utils import initialize_llm

    if not requirements:
        raise ValueError("Requirements list cannot be empty")

    # Initialize LLM
    llm, provider = initialize_llm("auto")
    logger.info("LLM initialized for holistic team planning: %s", provider)

    # Format all requirements into a single prompt
    requirements_text = _format_requirements_for_prompt(requirements)
    prompt = TEAM_PLANNING_PROMPT.format(requirements_text=requirements_text)

    # Single LLM call for holistic analysis (handle async if needed)
    logger.info("Calling LLM for holistic team planning with %d requirements", len(requirements))

    # Format as messages for LLM
    messages = [{"role": "user", "content": prompt}]

    # Call LLM - handle both sync and async cases
    result = llm(messages)
    if asyncio.iscoroutine(result):
        # LLM is async, need to run it
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context, create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    response = pool.submit(asyncio.run, result).result()
            else:
                response = loop.run_until_complete(result)
        except RuntimeError:
            # No event loop, create one
            response = asyncio.run(result)
    else:
        response = result

    # Extract response text - use try/except to handle various response types
    response_text = None
    if isinstance(response, str):
        response_text = response
    elif isinstance(response, list):
        # List of content blocks (e.g., from Anthropic API)
        text_parts = []
        for item in response:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                text_parts.append(item.get('text', ''))
            elif hasattr(item, 'text'):
                text_parts.append(item.text)
        response_text = ''.join(text_parts)
    elif isinstance(response, dict):
        # Dict-like response (e.g., from some LLM APIs)
        content = response.get('text') or response.get('content')
        if isinstance(content, list):
            # content is a list of blocks
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text_parts.append(item.get('text', ''))
            response_text = ''.join(text_parts)
        else:
            response_text = content or str(response)
    else:
        # Object with attributes
        try:
            response_text = getattr(response, 'text', None)
        except (KeyError, TypeError):
            pass
        if response_text is None:
            try:
                content = getattr(response, 'content', None)
                if isinstance(content, list):
                    # content is a list of blocks
                    text_parts = []
                    for item in content:
                        if isinstance(item, str):
                            text_parts.append(item)
                        elif isinstance(item, dict):
                            text_parts.append(item.get('text', ''))
                        elif hasattr(item, 'text'):
                            text_parts.append(item.text)
                    response_text = ''.join(text_parts)
                else:
                    response_text = content
            except (KeyError, TypeError):
                pass
        if response_text is None:
            response_text = str(response)

    # Parse LLM response
    parsed = _parse_llm_response(response_text)
    if not parsed:
        logger.error("Failed to parse LLM response, returning empty suggestions")
        return {
            "suggestions": [],
            "reasoning": "LLM response parsing failed",
            "complexity": "unknown",
        }

    # Convert parsed response to suggestion format
    suggestions = []
    roles = parsed.get("roles", [])

    for role_spec in roles:
        role_name = role_spec.get("role", "未知角色")
        name = role_spec.get("name", role_name)
        description = role_spec.get("description", "")
        skills = role_spec.get("skills", [])
        domains = role_spec.get("domains", [])

        # Generate temporary ID for Metaso agent
        metaso_agent_id = f"metaso_{role_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"

        # Compute estimated score
        metaso_score = _compute_metaso_estimated_score({
            "skills": skills,
            "domains": domains,
        })

        # Find best library agent for this role
        library_agent = _find_best_library_agent_for_role(
            role=role_name,
            skills=skills,
            domains=domains,
        )

        # Determine default selection
        library_score = library_agent["score"] if library_agent else 0.0
        default_is_metaso = metaso_score >= library_score

        suggestion = {
            "role": role_name,
            "metaso_agent": {
                "agent_id": metaso_agent_id,
                "name": name,
                "description": description,
                "skills": skills,
                "domains": domains,
                "tags": [],
                "parent_domain": None,
                "system_prompt": f"你是{name}，负责{description}",
                "estimated_score": metaso_score,
                "assigned_requirements": role_spec.get("assigned_requirements", []),
                "priority": role_spec.get("priority", "medium"),
            },
            "library_agent": library_agent,
            "default_is_metaso": default_is_metaso,
            "default_agent_id": (
                metaso_agent_id if default_is_metaso
                else (library_agent["agent_id"] if library_agent else metaso_agent_id)
            ),
        }
        suggestions.append(suggestion)

    return {
        "suggestions": suggestions,
        "reasoning": parsed.get("reasoning", ""),
        "complexity": parsed.get("complexity", "medium"),
        "project_analysis": parsed.get("project_analysis", ""),
        "team_size_recommendation": parsed.get("team_size_recommendation", len(suggestions)),
    }
