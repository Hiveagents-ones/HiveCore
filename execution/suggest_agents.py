# -*- coding: utf-8 -*-
"""Agent suggestion service - bridges Django with AgentScope TeamSelector.

This module provides the interface between Django API and AgentScope's
LLM-based agent suggestion functionality. Enhanced to support library agent
ranking and comparison with Metaso-generated agents.
"""

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _compute_metaso_estimated_score(spec: dict[str, Any]) -> float:
    """Compute estimated score for a Metaso-generated agent spec.

    Metaso agents get:
    - metaso_generated: 1.0 (5% weight)
    - cold_start_bonus: 0.15
    - Default performance/recognition: 0.5
    - brand_certified: 0.0 (user-generated)

    S_base ≈ 0.25*0.5 + 0.15*0.5 + 0.10*0 + 0.05*1.0 + 0.10*1.0 = 0.35
    With cold start bonus: 0.35 + 0.15 = 0.50
    """
    return 0.50  # Base score for Metaso agent with cold start bonus


def _find_best_library_agent_for_role(
    role: str,
    skills: list[str],
    domains: list[str],
) -> dict[str, Any] | None:
    """Find the best matching agent from the library for a given role.

    Args:
        role: The role/duty to match.
        skills: Required skills.
        domains: Required domains.

    Returns:
        Dict with agent info and score, or None if no match found.
    """
    from api.models import Agent

    # Query agents that might match this role
    # Use duty field for role matching
    agents = Agent.objects.all()

    best_agent = None
    best_score = 0.0

    for agent in agents:
        # Compute a simple requirement fit score
        score = _compute_library_agent_score(agent, role, skills, domains)
        if score > best_score:
            best_score = score
            best_agent = agent

    if best_agent and best_score >= 0.10:  # min_fit_threshold
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
    """Compute score for a library agent based on role/skills/domains match.

    Uses simplified scoring similar to HiveCore's requirement fit:
    - Role/duty match: 0.3
    - Skills overlap: 0.4
    - Domains overlap: 0.3
    """
    score = 0.0

    # Role/duty match (case-insensitive partial match)
    agent_duty = (agent.duty or "").lower()
    role_lower = role.lower()
    if role_lower in agent_duty or agent_duty in role_lower:
        score += 0.3
    elif any(word in agent_duty for word in role_lower.split()):
        score += 0.15

    # Skills match (from agent.detail field - simplified)
    agent_detail = (agent.detail or "").lower()
    if skills:
        matched_skills = sum(1 for s in skills if s.lower() in agent_detail)
        score += 0.4 * (matched_skills / len(skills))

    # Domains match
    if domains:
        matched_domains = sum(1 for d in domains if d.lower() in agent_detail)
        score += 0.3 * (matched_domains / len(domains))

    return min(1.0, score)


def suggest_agents_for_requirements(
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Suggest agents for given requirements using LLM.

    Returns enhanced format with both Metaso agent specs and library agents.

    Args:
        requirements (`list[dict[str, Any]]`):
            List of requirement dicts with 'id' and 'content' keys.

    Returns:
        `dict[str, Any]`:
            Dict with 'suggestions' (enhanced format), 'reasoning', 'complexity'.

    Raises:
        RuntimeError: If LLM initialization or analysis fails.
        ValueError: If requirements list is empty.
    """
    from agentscope.aa import suggest_agents_for_requirements as as_suggest
    from agentscope.scripts._llm_utils import initialize_llm

    # Initialize LLM
    llm, provider = initialize_llm("auto")
    logger.info("LLM initialized for suggest-agents: %s", provider)

    # Convert requirements format
    req_list = []
    for req in requirements:
        req_list.append({
            "id": str(req.get("id", "")),
            "content": req.get("content", ""),
            "skills": req.get("skills", []),
        })

    # Get suggestions from agentscope, passing the initialized model
    specs = as_suggest(req_list, model=llm)

    # Convert AgentSpec to enhanced format
    suggestions = []
    for spec in specs:
        # Generate temporary ID for Metaso agent
        metaso_agent_id = f"metaso_{spec.role.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"

        # Compute estimated score for Metaso agent
        metaso_score = _compute_metaso_estimated_score({
            "skills": list(spec.skills) if spec.skills else [],
            "domains": list(spec.domains) if spec.domains else [],
        })

        # Find best library agent for this role
        library_agent = _find_best_library_agent_for_role(
            role=spec.role,
            skills=list(spec.skills) if spec.skills else [],
            domains=list(spec.domains) if spec.domains else [],
        )

        # Determine default selection
        library_score = library_agent["score"] if library_agent else 0.0
        default_is_metaso = metaso_score >= library_score

        suggestion = {
            "role": spec.role,
            "metaso_agent": {
                "agent_id": metaso_agent_id,
                "name": spec.name,
                "description": spec.description,
                "skills": list(spec.skills) if spec.skills else [],
                "domains": list(spec.domains) if spec.domains else [],
                "tags": list(spec.tags) if spec.tags else [],
                "parent_domain": spec.parent_domain,
                "system_prompt": spec.system_prompt,
                "estimated_score": metaso_score,
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
        "reasoning": "",
        "complexity": "medium",
    }
