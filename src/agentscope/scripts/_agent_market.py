# -*- coding: utf-8 -*-
"""Agent market loading and profile management.

This module provides:
- Dynamic agent loading from marketplace directories
- Default agent profile definitions
- Capability scoring utilities
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_SCORE: float = 0.75


# ---------------------------------------------------------------------------
# Dynamic Import
# ---------------------------------------------------------------------------
def _import_callable(module_path: str, callable_name: str) -> Callable[..., Any] | None:
    """Dynamically import a callable from a module path.

    Args:
        module_path: Dotted module path (e.g., 'agentscope.agents.my_agent')
        callable_name: Name of the callable to import (e.g., 'MyAgent')

    Returns:
        The imported callable or None if import fails
    """
    try:
        module = importlib.import_module(module_path)
        return getattr(module, callable_name, None)
    except (ImportError, AttributeError) as exc:
        from ._observability import get_logger
        get_logger().warn(f"[AgentMarket] 导入失败 {module_path}.{callable_name}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Agent Market Loading
# ---------------------------------------------------------------------------
def load_agent_market(market_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Load agents from a marketplace directory.

    Expected directory structure:
    ```
    market_dir/
    ├── manifest.json  # Optional: registry of all agents
    ├── agent1/
    │   ├── manifest.json
    │   └── agent.py
    └── agent2/
        ├── manifest.json
        └── agent.py
    ```

    Args:
        market_dir: Path to the agent marketplace directory

    Returns:
        dict: Mapping of agent_id -> agent_info dict
    """
    market_path = Path(market_dir)
    if not market_path.exists():
        from ._observability import get_logger
        get_logger().warn(f"[AgentMarket] 目录不存在: {market_path}")
        return {}

    agents: dict[str, dict[str, Any]] = {}

    # Check for top-level manifest
    top_manifest = market_path / "manifest.json"
    if top_manifest.exists():
        try:
            with open(top_manifest, encoding="utf-8") as f:
                registry = json.load(f)
            for agent_id, agent_info in registry.get("agents", {}).items():
                agents[agent_id] = agent_info
            from ._observability import get_logger
            get_logger().info(f"[AgentMarket] 从顶层 manifest 加载了 {len(agents)} 个 Agent")
        except Exception as exc:
            from ._observability import get_logger
            get_logger().warn(f"[AgentMarket] 读取顶层 manifest 失败: {exc}")

    # Scan subdirectories for individual agent manifests
    for subdir in market_path.iterdir():
        if not subdir.is_dir():
            continue
        manifest_file = subdir / "manifest.json"
        if not manifest_file.exists():
            continue

        try:
            with open(manifest_file, encoding="utf-8") as f:
                agent_info = json.load(f)
            agent_id = agent_info.get("id") or subdir.name
            if agent_id not in agents:
                agents[agent_id] = agent_info
                from ._observability import get_logger
                get_logger().debug(f"[AgentMarket] 发现 Agent: {agent_id}")
        except Exception as exc:
            from ._observability import get_logger
            get_logger().warn(f"[AgentMarket] 读取 {manifest_file} 失败: {exc}")

    return agents


# ---------------------------------------------------------------------------
# Profile Utilities
# ---------------------------------------------------------------------------
def _profile(
    name: str,
    role: str,
    capabilities: list[str],
    *,
    base_score: float = DEFAULT_SCORE,
    description: str = "",
) -> dict[str, Any]:
    """Create an agent profile dictionary.

    Args:
        name: Agent name
        role: Agent role (e.g., 'developer', 'qa', 'designer')
        capabilities: List of capability tags
        base_score: Base capability score
        description: Agent description

    Returns:
        dict: Agent profile dictionary
    """
    return {
        "name": name,
        "role": role,
        "capabilities": capabilities,
        "base_score": base_score,
        "description": description,
    }


def default_agent_profiles() -> dict[str, dict[str, Any]]:
    """Get default agent profiles for the HiveCore system.

    Returns:
        dict: Mapping of agent_id -> profile dict
    """
    return {
        "strategy-agent": _profile(
            name="StrategyAgent",
            role="strategist",
            capabilities=["planning", "decomposition", "prioritization"],
            base_score=0.80,
            description="负责项目规划和任务分解",
        ),
        "builder-agent": _profile(
            name="BuilderAgent",
            role="developer",
            capabilities=["coding", "implementation", "fullstack", "api", "frontend", "backend"],
            base_score=0.85,
            description="负责代码实现和功能开发",
        ),
        "reviewer-agent": _profile(
            name="ReviewerAgent",
            role="reviewer",
            capabilities=["code-review", "quality", "security"],
            base_score=0.75,
            description="负责代码审查和质量把控",
        ),
        "qa-agent": _profile(
            name="QAAgent",
            role="qa",
            capabilities=["testing", "validation", "acceptance"],
            base_score=0.80,
            description="负责测试和验收",
        ),
        "product-agent": _profile(
            name="ProductAgent",
            role="product",
            capabilities=["requirements", "user-story", "specification"],
            base_score=0.75,
            description="负责需求分析和产品规格",
        ),
        "ux-agent": _profile(
            name="UXAgent",
            role="designer",
            capabilities=["ui", "ux", "design", "prototyping"],
            base_score=0.75,
            description="负责用户体验和界面设计",
        ),
        "frontend-agent": _profile(
            name="FrontendAgent",
            role="developer",
            capabilities=["frontend", "react", "vue", "html", "css", "javascript"],
            base_score=0.85,
            description="负责前端开发",
        ),
        "backend-agent": _profile(
            name="BackendAgent",
            role="developer",
            capabilities=["backend", "api", "database", "python", "fastapi", "django"],
            base_score=0.85,
            description="负责后端开发",
        ),
        "devops-agent": _profile(
            name="DevOpsAgent",
            role="devops",
            capabilities=["deployment", "ci-cd", "docker", "kubernetes"],
            base_score=0.75,
            description="负责部署和运维",
        ),
    }


def score_agent_for_requirement(
    agent_profile: dict[str, Any],
    requirement_tags: list[str],
) -> float:
    """Score an agent's fit for a requirement based on capabilities.

    Args:
        agent_profile: Agent profile dictionary
        requirement_tags: Tags describing the requirement

    Returns:
        float: Score between 0 and 1
    """
    if not requirement_tags:
        return agent_profile.get("base_score", DEFAULT_SCORE)

    capabilities = set(agent_profile.get("capabilities", []))
    tags = set(requirement_tags)

    if not capabilities:
        return agent_profile.get("base_score", DEFAULT_SCORE)

    # Calculate overlap score
    overlap = len(capabilities & tags)
    total = len(tags)

    if total == 0:
        return agent_profile.get("base_score", DEFAULT_SCORE)

    # Weighted combination of base score and overlap
    base = agent_profile.get("base_score", DEFAULT_SCORE)
    overlap_score = overlap / total

    return 0.6 * base + 0.4 * overlap_score


__all__ = [
    "DEFAULT_SCORE",
    "_import_callable",
    "load_agent_market",
    "_profile",
    "default_agent_profiles",
    "score_agent_for_requirement",
]
