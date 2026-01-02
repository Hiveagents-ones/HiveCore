# -*- coding: utf-8 -*-
"""Agent Registry for dynamic domain and agent management.

This module provides a flexible registry system that:
1. Maintains core domains (stable, predefined)
2. Supports dynamic custom domains (LLM-generated)
3. Uses tags for fine-grained capability matching
4. Prepares data structure for Django migration

The registry persists to JSON and can be migrated to Django models later.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .._logging import logger


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class DomainInfo:
    """Information about a domain (category) of agents.

    Attributes:
        name (`str`):
            Unique domain identifier (e.g., "blockchain", "ai_ml").
        display_name (`str`):
            Human-readable name (e.g., "区块链开发", "AI/ML").
        description (`str`):
            Description of this domain.
        parent (`str | None`):
            Parent domain name for hierarchical organization.
        is_core (`bool`):
            Whether this is a core domain (cannot be deleted).
        created_by (`str`):
            Who created this domain: "system", "llm", or user ID.
        created_at (`str`):
            ISO timestamp of creation.
        capabilities (`list[str]`):
            Typical capabilities/skills for this domain.
    """

    name: str
    display_name: str = ""
    description: str = ""
    parent: str | None = None
    is_core: bool = False
    created_by: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    capabilities: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = self.name


@dataclass
class TagInfo:
    """Information about a tag.

    Attributes:
        name (`str`):
            Tag name (e.g., "python", "security").
        category (`str`):
            Tag category: "skill", "tool", "framework", "domain", "other".
        usage_count (`int`):
            How many agents use this tag.
    """

    name: str
    category: str = "skill"
    usage_count: int = 0


@dataclass
class AgentRegistryEntry:
    """Registry entry for an agent.

    This is a lightweight reference to an agent, not the full manifest.
    Full details are stored in the agent's manifest.json file.

    Attributes:
        agent_id (`str`):
            Unique agent identifier.
        name (`str`):
            Display name.
        domains (`list[str]`):
            Domain names this agent belongs to.
        tags (`list[str]`):
            Tags describing capabilities.
        manifest_path (`str`):
            Path to the agent's manifest.json.
        created_by (`str`):
            Creator: "system", "llm", or user ID.
        created_at (`str`):
            ISO timestamp of creation.
        usage_count (`int`):
            Number of times this agent was used.
        success_rate (`float`):
            Success rate (0.0 - 1.0).
        is_active (`bool`):
            Whether this agent is active.
    """

    agent_id: str
    name: str
    domains: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    manifest_path: str = ""
    created_by: str = "llm"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    usage_count: int = 0
    success_rate: float = 0.0
    is_active: bool = True


# =============================================================================
# Core Domains (Predefined)
# =============================================================================

CORE_DOMAINS: dict[str, DomainInfo] = {
    "backend": DomainInfo(
        name="backend",
        display_name="后端开发",
        description="后端服务、API、数据库开发",
        is_core=True,
        capabilities=["python", "java", "go", "api", "database", "sql"],
    ),
    "frontend": DomainInfo(
        name="frontend",
        display_name="前端开发",
        description="Web/移动端前端开发",
        is_core=True,
        capabilities=["javascript", "typescript", "react", "vue", "css", "html"],
    ),
    "design": DomainInfo(
        name="design",
        display_name="设计",
        description="UI/UX设计、视觉设计",
        is_core=True,
        capabilities=["ui", "ux", "figma", "sketch", "wireframe", "prototype"],
    ),
    "qa": DomainInfo(
        name="qa",
        display_name="质量保证",
        description="测试、代码审查、质量保证",
        is_core=True,
        capabilities=["testing", "code_review", "automation", "security"],
    ),
    "devops": DomainInfo(
        name="devops",
        display_name="DevOps",
        description="部署、运维、CI/CD",
        is_core=True,
        capabilities=["docker", "kubernetes", "ci_cd", "aws", "azure", "gcp"],
    ),
    "architecture": DomainInfo(
        name="architecture",
        display_name="系统架构",
        description="系统设计、技术架构",
        is_core=True,
        capabilities=["system_design", "microservices", "distributed_systems"],
    ),
    "product": DomainInfo(
        name="product",
        display_name="产品",
        description="产品管理、需求分析",
        is_core=True,
        capabilities=["requirements", "user_story", "product_management"],
    ),
    "specialist": DomainInfo(
        name="specialist",
        display_name="专家",
        description="特定领域专家（无法归入其他分类）",
        is_core=True,
        capabilities=[],
    ),
}


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """Registry for managing agents and domains.

    This registry:
    1. Maintains core and custom domains
    2. Tracks all registered agents
    3. Supports tag-based capability matching
    4. Persists to JSON for Django migration

    Usage:
        registry = AgentRegistry.load("path/to/registry.json")
        registry.register_agent(agent_entry)
        registry.register_domain(domain_info)
        registry.save()
    """

    def __init__(self, registry_path: str | Path | None = None) -> None:
        """Initialize the registry.

        Args:
            registry_path: Path to persist registry data.
        """
        self.registry_path = Path(registry_path) if registry_path else None
        self.domains: dict[str, DomainInfo] = dict(CORE_DOMAINS)
        self.agents: dict[str, AgentRegistryEntry] = {}
        self.tags: dict[str, TagInfo] = {}

    def register_domain(
        self,
        name: str,
        *,
        display_name: str = "",
        description: str = "",
        parent: str | None = None,
        created_by: str = "llm",
        capabilities: list[str] | None = None,
    ) -> DomainInfo:
        """Register a new domain.

        If domain already exists, returns existing domain.
        If parent is specified and doesn't exist, creates parent as "specialist" child.

        Args:
            name: Unique domain name.
            display_name: Human-readable name.
            description: Domain description.
            parent: Parent domain name.
            created_by: Creator identifier.
            capabilities: Typical capabilities for this domain.

        Returns:
            The registered DomainInfo.
        """
        # Normalize name
        name = name.lower().replace(" ", "_").replace("-", "_")

        # Return existing if already registered
        if name in self.domains:
            return self.domains[name]

        # Validate parent exists (or create under specialist)
        if parent and parent not in self.domains:
            logger.warning(
                "Parent domain '%s' not found, using 'specialist' as parent",
                parent,
            )
            parent = "specialist"

        domain = DomainInfo(
            name=name,
            display_name=display_name or name,
            description=description,
            parent=parent,
            is_core=False,
            created_by=created_by,
            capabilities=capabilities or [],
        )
        self.domains[name] = domain

        logger.info(
            "[Registry] Registered new domain: %s (parent=%s, by=%s)",
            name,
            parent or "none",
            created_by,
        )

        # Auto-save if path configured
        if self.registry_path:
            self.save()

        return domain

    def register_agent(self, entry: AgentRegistryEntry) -> None:
        """Register an agent in the registry.

        Args:
            entry: Agent registry entry.
        """
        self.agents[entry.agent_id] = entry

        # Update tag usage counts
        for tag_name in entry.tags:
            if tag_name not in self.tags:
                self.tags[tag_name] = TagInfo(name=tag_name)
            self.tags[tag_name].usage_count += 1

        # Ensure domains exist
        for domain_name in entry.domains:
            if domain_name not in self.domains:
                self.register_domain(
                    domain_name,
                    parent="specialist",
                    created_by=entry.created_by,
                )

        logger.info(
            "[Registry] Registered agent: %s (%s) domains=%s tags=%s",
            entry.agent_id,
            entry.name,
            entry.domains,
            entry.tags[:5],  # First 5 tags
        )

        # Auto-save
        if self.registry_path:
            self.save()

    def find_agents_by_domain(
        self,
        domain: str,
        include_children: bool = True,
    ) -> list[AgentRegistryEntry]:
        """Find agents in a domain.

        Args:
            domain: Domain name to search.
            include_children: Whether to include agents in child domains.

        Returns:
            List of matching agents.
        """
        target_domains = {domain}

        if include_children:
            # Find all child domains
            for d in self.domains.values():
                if d.parent == domain:
                    target_domains.add(d.name)

        return [
            agent
            for agent in self.agents.values()
            if agent.is_active and any(d in target_domains for d in agent.domains)
        ]

    def find_agents_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
    ) -> list[AgentRegistryEntry]:
        """Find agents by tags.

        Args:
            tags: Tags to search for.
            match_all: If True, agent must have all tags. If False, any tag matches.

        Returns:
            List of matching agents sorted by match count.
        """
        results: list[tuple[int, AgentRegistryEntry]] = []
        tag_set = set(t.lower() for t in tags)

        for agent in self.agents.values():
            if not agent.is_active:
                continue

            agent_tags = set(t.lower() for t in agent.tags)
            matches = len(tag_set & agent_tags)

            if match_all and matches < len(tag_set):
                continue
            if matches > 0:
                results.append((matches, agent))

        # Sort by match count (descending)
        results.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in results]

    def suggest_domain(self, capabilities: list[str]) -> str:
        """Suggest the best domain for given capabilities.

        Args:
            capabilities: List of capabilities/skills.

        Returns:
            Suggested domain name.
        """
        cap_set = set(c.lower() for c in capabilities)
        best_domain = "specialist"
        best_score = 0

        for domain in self.domains.values():
            if not domain.capabilities:
                continue
            domain_caps = set(c.lower() for c in domain.capabilities)
            score = len(cap_set & domain_caps)
            if score > best_score:
                best_score = score
                best_domain = domain.name

        return best_domain

    def get_domain_tree(self) -> dict[str, Any]:
        """Get hierarchical domain structure.

        Returns:
            Nested dict of domains.
        """
        tree: dict[str, Any] = {}

        # First pass: create root domains
        for domain in self.domains.values():
            if domain.parent is None:
                tree[domain.name] = {
                    "info": domain,
                    "children": {},
                }

        # Second pass: attach children
        for domain in self.domains.values():
            if domain.parent and domain.parent in tree:
                tree[domain.parent]["children"][domain.name] = {
                    "info": domain,
                    "children": {},
                }

        return tree

    def to_dict(self) -> dict[str, Any]:
        """Convert registry to dictionary for serialization."""
        return {
            "version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "domains": {
                name: asdict(domain)
                for name, domain in self.domains.items()
            },
            "agents": {
                agent_id: asdict(entry)
                for agent_id, entry in self.agents.items()
            },
            "tags": {
                name: asdict(tag)
                for name, tag in self.tags.items()
            },
        }

    def save(self, path: str | Path | None = None) -> None:
        """Save registry to JSON file.

        Args:
            path: Override path (uses registry_path if not provided).
        """
        save_path = Path(path) if path else self.registry_path
        if not save_path:
            logger.warning("[Registry] No path configured, cannot save")
            return

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info("[Registry] Saved to %s", save_path)

    @classmethod
    def load(cls, path: str | Path) -> "AgentRegistry":
        """Load registry from JSON file.

        Args:
            path: Path to registry JSON.

        Returns:
            Loaded AgentRegistry.
        """
        path = Path(path)
        registry = cls(registry_path=path)

        if not path.exists():
            logger.info("[Registry] No existing registry at %s, starting fresh", path)
            return registry

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Load domains (keeping core domains)
            for name, domain_data in data.get("domains", {}).items():
                if name not in CORE_DOMAINS:
                    registry.domains[name] = DomainInfo(**domain_data)

            # Load agents
            for agent_id, agent_data in data.get("agents", {}).items():
                registry.agents[agent_id] = AgentRegistryEntry(**agent_data)

            # Load tags
            for tag_name, tag_data in data.get("tags", {}).items():
                registry.tags[tag_name] = TagInfo(**tag_data)

            logger.info(
                "[Registry] Loaded from %s: %d domains, %d agents, %d tags",
                path,
                len(registry.domains),
                len(registry.agents),
                len(registry.tags),
            )

        except Exception as e:
            logger.warning("[Registry] Failed to load from %s: %s", path, e)

        return registry


# =============================================================================
# Utility Functions
# =============================================================================

def create_agent_registry_entry(
    agent_id: str,
    name: str,
    *,
    domains: list[str] | None = None,
    skills: list[str] | None = None,
    tags: list[str] | None = None,
    manifest_path: str = "",
    created_by: str = "llm",
) -> AgentRegistryEntry:
    """Create an agent registry entry.

    Args:
        agent_id: Unique agent ID.
        name: Display name.
        domains: Domain names (will auto-suggest if empty).
        skills: Agent skills/capabilities.
        tags: Capability tags.
        manifest_path: Path to manifest.json.
        created_by: Creator identifier.

    Returns:
        AgentRegistryEntry ready for registration.
    """
    return AgentRegistryEntry(
        agent_id=agent_id,
        name=name,
        domains=domains or ["specialist"],
        skills=skills or [],
        tags=tags or [],
        manifest_path=manifest_path,
        created_by=created_by,
    )


def load_agent_profile_from_manifest(manifest_path: str | Path) -> "AgentProfile | None":
    """Load AgentProfile from a manifest.json file.

    Args:
        manifest_path: Path to the manifest.json file.

    Returns:
        AgentProfile if loaded successfully, None otherwise.
    """
    from pathlib import Path as PathLib
    from ._types import AgentProfile, AgentCapabilities, StaticScore

    path = PathLib(manifest_path)
    if not path.exists():
        logger.warning("[Registry] Manifest not found: %s", path)
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Extract fields from manifest
        # Note: manifest stores skills/tools/domains in "profile" nested object
        from ._vocabulary import normalize_skills, normalize_domains

        agent_id = data.get("id", "")
        name = data.get("name", "Unknown")
        description = data.get("description", "")
        profile_data = data.get("profile", {})
        raw_skills = set(profile_data.get("skills", data.get("skills", [])))
        tools = set(profile_data.get("tools", data.get("tools", [])))
        raw_domains = set(profile_data.get("domains", data.get("domains", [])))
        languages = set(profile_data.get("languages", data.get("languages", ["zh", "en"])))

        # Get tags from metadata
        metadata = data.get("metadata", {})
        tags = set(metadata.get("tags", []))

        # If skills is empty, populate from domains and tags for better matching
        # This ensures agents can match requirements that use domain tags as skills
        if not raw_skills:
            raw_skills = raw_domains | tags

        # Normalize skills and domains for consistent matching
        skills = normalize_skills(raw_skills)
        domains = normalize_domains(raw_domains)

        # Generate default description if not provided
        if not description:
            description = f"{name}: {', '.join(skills) if skills else '通用技能'}"

        # Build AgentProfile
        capabilities = AgentCapabilities(
            skills=skills,
            tools=tools,
            domains=domains,
            languages=languages,
            compliance_tags=tags,  # Use compliance_tags for tags
            description=description,
        )

        # Extract scoring info from metadata
        source = metadata.get("source", "registry")
        is_metaso = source in ("modular_agent_factory", "metaso")

        # Static score for registry-loaded agents
        # 从 manifest 读取或使用默认值
        static_score = StaticScore(
            performance=0.5,       # 默认中等，需要数据积累
            recognition=0.5,       # 默认中等，需要用户评分
            brand_certified=0.0,   # 非官方 Agent
            metaso_generated=1.0 if is_metaso else 0.0,  # 根据来源判断
        )

        profile = AgentProfile(
            agent_id=agent_id,
            name=name,
            static_score=static_score,
            capabilities=capabilities,
            is_cold_start=True,  # LLM-generated agents start cold
            metadata={
                "source": source,
                "manifest_path": str(path),
            },
        )

        logger.debug("[Registry] Loaded profile from manifest: %s", agent_id)
        return profile

    except Exception as e:
        logger.warning("[Registry] Failed to load manifest %s: %s", path, e)
        return None


def load_all_agent_profiles(
    registry: "AgentRegistry | None" = None,
) -> list["AgentProfile"]:
    """Load AgentProfiles for all active agents in registry.

    Args:
        registry: AgentRegistry instance. If None, uses global registry.

    Returns:
        List of AgentProfiles loaded from manifests.
    """
    if registry is None:
        registry = get_global_registry()

    profiles = []
    for entry in registry.agents.values():
        if not entry.is_active:
            continue
        if not entry.manifest_path:
            continue

        profile = load_agent_profile_from_manifest(entry.manifest_path)
        if profile:
            # Update profile with registry stats
            profile.metadata["usage_count"] = str(entry.usage_count)
            profile.metadata["success_rate"] = str(entry.success_rate)
            profiles.append(profile)

    logger.info(
        "[Registry] Loaded %d agent profiles from registry",
        len(profiles),
    )
    return profiles


# Global registry instance (lazy loaded)
_global_registry: AgentRegistry | None = None


def get_global_registry(registry_path: str | Path | None = None) -> AgentRegistry:
    """Get or create the global agent registry.

    Args:
        registry_path: Path to registry file (only used on first call).

    Returns:
        Global AgentRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        default_path = Path("deliverables/agents/registry.json")
        _global_registry = AgentRegistry.load(registry_path or default_path)
    return _global_registry
