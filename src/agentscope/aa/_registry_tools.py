# -*- coding: utf-8 -*-
"""Registry query tools for AA to search domains and agents.

Instead of injecting all domains/agents into the prompt, AA can use these
tools to search on-demand, keeping the prompt size manageable.

Usage:
    from agentscope.aa._registry_tools import create_registry_tools
    tools = create_registry_tools(agents_dir="deliverables/agents")
    # Register tools to AA's toolkit
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .._logging import logger


@dataclass
class AgentIndexEntry:
    """Indexed agent entry for fast search."""

    agent_id: str
    name: str
    skills: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    description: str = ""
    manifest_path: str = ""

    def matches(self, keyword: str) -> float:
        """Calculate match score for a keyword.

        Supports both exact substring match and token-based match.

        Args:
            keyword: Search keyword (case-insensitive).

        Returns:
            Match score (0.0 - 1.0+, higher = better match).
        """
        kw = keyword.lower()
        score = 0.0

        # Build searchable text corpus
        corpus = f"{self.agent_id} {self.name} {self.description}".lower()
        all_tags = " ".join(self.skills | self.domains | self.tags).lower()

        # Direct substring match in corpus (supports Chinese)
        if kw in corpus:
            # Boost based on where it matches
            if kw in self.agent_id.lower():
                score += 2.0
            elif kw in self.name.lower():
                score += 1.5
            elif kw in self.description.lower():
                score += 0.5

        # Token-based match for skills/domains/tags
        for skill in self.skills:
            if kw in skill.lower() or skill.lower() in kw:
                score += 1.0
                break

        for domain in self.domains:
            if kw in domain.lower() or domain.lower() in kw:
                score += 0.8
                break

        for tag in self.tags:
            if kw in tag.lower() or tag.lower() in kw:
                score += 0.6
                break

        return score


class RegistryIndex:
    """In-memory index for fast agent/domain search.

    Built from file system scan of agents directory.
    """

    def __init__(self, agents_dir: str | Path | None = None) -> None:
        """Initialize the index.

        Args:
            agents_dir: Directory containing agent manifests.
        """
        self.agents_dir = Path(agents_dir) if agents_dir else Path("deliverables/agents")
        self.agents: dict[str, AgentIndexEntry] = {}
        self.domains: dict[str, dict[str, Any]] = {}
        self._indexed = False

    def _ensure_indexed(self) -> None:
        """Build index from file system if not already done."""
        if self._indexed:
            return

        self._scan_agents_directory()
        self._indexed = True

    def _scan_agents_directory(self) -> None:
        """Scan agents directory and build index."""
        if not self.agents_dir.exists():
            logger.debug("[RegistryIndex] Agents directory not found: %s", self.agents_dir)
            return

        # Scan for manifest.json files
        for manifest_path in self.agents_dir.rglob("manifest.json"):
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    data = json.load(f)

                agent_id = data.get("id", manifest_path.parent.name)
                metadata = data.get("metadata", {})

                entry = AgentIndexEntry(
                    agent_id=agent_id,
                    name=data.get("name", agent_id),
                    skills=set(data.get("skills", [])),
                    domains=set(data.get("domains", [])),
                    tags=set(metadata.get("tags", [])),
                    description=data.get("description", ""),
                    manifest_path=str(manifest_path),
                )
                self.agents[agent_id] = entry

                # Index domains
                for domain in entry.domains:
                    if domain not in self.domains:
                        self.domains[domain] = {
                            "name": domain,
                            "agents": [],
                            "is_custom": domain not in _CORE_DOMAIN_NAMES,
                        }
                    self.domains[domain]["agents"].append(agent_id)

            except Exception as e:
                logger.warning("[RegistryIndex] Failed to index %s: %s", manifest_path, e)

        # Also load from registry.json if exists
        registry_path = self.agents_dir / "registry.json"
        if registry_path.exists():
            try:
                with open(registry_path, encoding="utf-8") as f:
                    registry_data = json.load(f)

                # Index domains from registry
                for name, domain_data in registry_data.get("domains", {}).items():
                    if name not in self.domains:
                        self.domains[name] = {
                            "name": name,
                            "display_name": domain_data.get("display_name", name),
                            "description": domain_data.get("description", ""),
                            "parent": domain_data.get("parent"),
                            "capabilities": domain_data.get("capabilities", []),
                            "is_core": domain_data.get("is_core", False),
                            "agents": [],
                        }
                    else:
                        # Merge registry info
                        self.domains[name].update({
                            "display_name": domain_data.get("display_name", name),
                            "description": domain_data.get("description", ""),
                            "parent": domain_data.get("parent"),
                            "capabilities": domain_data.get("capabilities", []),
                            "is_core": domain_data.get("is_core", False),
                        })

            except Exception as e:
                logger.warning("[RegistryIndex] Failed to load registry.json: %s", e)

        logger.info(
            "[RegistryIndex] Indexed %d agents, %d domains from %s",
            len(self.agents),
            len(self.domains),
            self.agents_dir,
        )

    def search_agents(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search agents by keyword.

        Args:
            keyword: Search keyword (matches id, name, skills, domains, tags).
            limit: Maximum results to return.

        Returns:
            List of matching agents with scores.
        """
        self._ensure_indexed()

        if not keyword.strip():
            # Return all agents if no keyword
            return [
                {
                    "agent_id": e.agent_id,
                    "name": e.name,
                    "skills": list(e.skills)[:5],
                    "domains": list(e.domains),
                    "tags": list(e.tags)[:5],
                }
                for e in list(self.agents.values())[:limit]
            ]

        # Score and rank agents
        scored: list[tuple[float, AgentIndexEntry]] = []
        for entry in self.agents.values():
            score = entry.matches(keyword)
            if score > 0:
                scored.append((score, entry))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "agent_id": e.agent_id,
                "name": e.name,
                "skills": list(e.skills)[:5],
                "domains": list(e.domains),
                "tags": list(e.tags)[:5],
                "match_score": round(score, 2),
            }
            for score, e in scored[:limit]
        ]

    def search_domains(
        self,
        keyword: str = "",
        parent: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search domains by keyword or filter by parent.

        Args:
            keyword: Search keyword (optional).
            parent: Filter by parent domain (optional).
            limit: Maximum results to return.

        Returns:
            List of matching domains.
        """
        self._ensure_indexed()

        results = []
        kw = keyword.lower() if keyword else ""

        for name, info in self.domains.items():
            # Filter by parent if specified
            if parent and info.get("parent") != parent:
                continue

            # Match keyword
            if kw:
                match = (
                    kw in name.lower()
                    or kw in info.get("display_name", "").lower()
                    or kw in info.get("description", "").lower()
                    or any(kw in cap.lower() for cap in info.get("capabilities", []))
                )
                if not match:
                    continue

            results.append({
                "name": name,
                "display_name": info.get("display_name", name),
                "description": info.get("description", ""),
                "parent": info.get("parent"),
                "is_core": info.get("is_core", False),
                "agent_count": len(info.get("agents", [])),
            })

        # Sort by agent count (more agents = more relevant)
        results.sort(key=lambda x: x["agent_count"], reverse=True)
        return results[:limit]

    def get_domain_tree(self) -> dict[str, Any]:
        """Get hierarchical domain structure.

        Returns:
            Nested dict of domains grouped by parent.
        """
        self._ensure_indexed()

        tree: dict[str, Any] = {"core": {}, "custom": {}}

        for name, info in self.domains.items():
            entry = {
                "display_name": info.get("display_name", name),
                "agent_count": len(info.get("agents", [])),
            }

            if info.get("is_core"):
                tree["core"][name] = entry
            else:
                parent = info.get("parent", "specialist")
                if parent not in tree["custom"]:
                    tree["custom"][parent] = {}
                tree["custom"][parent][name] = entry

        return tree

    def get_agent_detail(self, agent_id: str) -> dict[str, Any] | None:
        """Get detailed info for a specific agent.

        Args:
            agent_id: The agent ID to look up.

        Returns:
            Agent details or None if not found.
        """
        self._ensure_indexed()

        entry = self.agents.get(agent_id)
        if not entry:
            return None

        return {
            "agent_id": entry.agent_id,
            "name": entry.name,
            "skills": list(entry.skills),
            "domains": list(entry.domains),
            "tags": list(entry.tags),
            "description": entry.description,
            "manifest_path": entry.manifest_path,
        }

    def refresh(self) -> None:
        """Force re-scan of agents directory."""
        self.agents.clear()
        self.domains.clear()
        self._indexed = False
        self._ensure_indexed()


# Core domain names for reference
_CORE_DOMAIN_NAMES = {
    "backend", "frontend", "design", "qa",
    "devops", "architecture", "product", "specialist",
}


# Global index instance
_global_index: RegistryIndex | None = None


def get_registry_index(agents_dir: str | Path | None = None) -> RegistryIndex:
    """Get or create the global registry index.

    Args:
        agents_dir: Agents directory (only used on first call).

    Returns:
        Global RegistryIndex instance.
    """
    global _global_index
    if _global_index is None:
        _global_index = RegistryIndex(agents_dir)
    return _global_index


# =============================================================================
# Tool Definitions for AA
# =============================================================================

def create_registry_tools(agents_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Create tool definitions for registry queries.

    These tools can be registered to AA's toolkit for on-demand
    agent/domain discovery.

    Args:
        agents_dir: Directory containing agent manifests.

    Returns:
        List of tool definitions in OpenAI function format.
    """
    index = get_registry_index(agents_dir)

    def search_agents(keyword: str = "", limit: int = 10) -> str:
        """Search for agents by keyword.

        Args:
            keyword: Search keyword matching agent id, name, skills, domains, or tags.
            limit: Maximum number of results (default 10).

        Returns:
            JSON string of matching agents.
        """
        results = index.search_agents(keyword, limit)
        if not results:
            return f"No agents found matching '{keyword}'"
        return json.dumps(results, ensure_ascii=False, indent=2)

    def search_domains(keyword: str = "", parent: str = "") -> str:
        """Search for domains by keyword or parent.

        Args:
            keyword: Search keyword (optional).
            parent: Filter by parent domain like 'backend', 'specialist' (optional).

        Returns:
            JSON string of matching domains.
        """
        results = index.search_domains(keyword, parent if parent else None)
        if not results:
            return f"No domains found matching '{keyword}'"
        return json.dumps(results, ensure_ascii=False, indent=2)

    def get_domain_tree() -> str:
        """Get the hierarchical structure of all domains.

        Returns:
            JSON string of domain tree grouped by core/custom and parent.
        """
        tree = index.get_domain_tree()
        return json.dumps(tree, ensure_ascii=False, indent=2)

    def get_agent_detail(agent_id: str) -> str:
        """Get detailed information about a specific agent.

        Args:
            agent_id: The agent ID to look up.

        Returns:
            JSON string of agent details or error message.
        """
        detail = index.get_agent_detail(agent_id)
        if not detail:
            return f"Agent '{agent_id}' not found"
        return json.dumps(detail, ensure_ascii=False, indent=2)

    # Return tool definitions in OpenAI function format
    return [
        {
            "type": "function",
            "function": {
                "name": "search_agents",
                "description": "搜索已注册的 Agent。支持模糊匹配 agent_id、名称、技能、领域、标签。用于查找可复用的现有 Agent。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词，如 'blockchain'、'后端'、'python'",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果数量上限，默认 10",
                            "default": 10,
                        },
                    },
                },
                "_callable": search_agents,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_domains",
                "description": "搜索已有的领域分类。可按关键词搜索或按父域筛选。用于了解现有分类体系。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词，如 'AI'、'区块链'",
                        },
                        "parent": {
                            "type": "string",
                            "description": "按父域筛选，如 'backend'、'specialist'",
                        },
                    },
                },
                "_callable": search_domains,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_domain_tree",
                "description": "获取完整的领域层级结构。显示核心域和自定义域的父子关系。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
                "_callable": get_domain_tree,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_agent_detail",
                "description": "获取指定 Agent 的详细信息，包括完整技能列表、领域、标签等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Agent ID，如 'smart-contract-auditor'",
                        },
                    },
                    "required": ["agent_id"],
                },
                "_callable": get_agent_detail,
            },
        },
    ]


def execute_registry_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Execute a registry tool by name.

    Args:
        tool_name: Name of the tool to execute.
        arguments: Tool arguments.

    Returns:
        Tool execution result as string.
    """
    index = get_registry_index()

    if tool_name == "search_agents":
        results = index.search_agents(
            arguments.get("keyword", ""),
            arguments.get("limit", 10),
        )
        return json.dumps(results, ensure_ascii=False, indent=2) if results else "No agents found"

    elif tool_name == "search_domains":
        results = index.search_domains(
            arguments.get("keyword", ""),
            arguments.get("parent"),
        )
        return json.dumps(results, ensure_ascii=False, indent=2) if results else "No domains found"

    elif tool_name == "get_domain_tree":
        tree = index.get_domain_tree()
        return json.dumps(tree, ensure_ascii=False, indent=2)

    elif tool_name == "get_agent_detail":
        detail = index.get_agent_detail(arguments.get("agent_id", ""))
        return json.dumps(detail, ensure_ascii=False, indent=2) if detail else "Agent not found"

    else:
        return f"Unknown tool: {tool_name}"
