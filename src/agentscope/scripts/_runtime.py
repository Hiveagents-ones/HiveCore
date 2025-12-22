# -*- coding: utf-8 -*-
"""Runtime harness building and configuration.

This module provides:
- RuntimeHarness dataclass
- Runtime requirement/acceptance builders
- Project ID derivation
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.ones import AASystemAgent


# ---------------------------------------------------------------------------
# RuntimeHarness
# ---------------------------------------------------------------------------
@dataclass
class RuntimeHarness:
    """Container for runtime components.

    Attributes:
        aa_agent: The AA system agent instance
        mcp_clients: List of regular MCP clients
        aa_mcp_clients: List of AA-side MCP clients
        resource_handles: Resource handle metadata
        mcp_prompt: Combined MCP context prompt
    """

    aa_agent: "AASystemAgent"
    mcp_clients: list[Any] = field(default_factory=list)
    aa_mcp_clients: list[Any] = field(default_factory=list)
    resource_handles: list[dict[str, Any]] = field(default_factory=list)
    mcp_prompt: str = ""


# ---------------------------------------------------------------------------
# Environment Loading
# ---------------------------------------------------------------------------
def _load_env_file(env_path: str | Path = ".env") -> dict[str, str]:
    """Load environment variables from a .env file.

    Args:
        env_path: Path to .env file

    Returns:
        dict: Loaded environment variables
    """
    env_vars: dict[str, str] = {}
    path = Path(env_path)

    if not path.exists():
        return env_vars

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
                    os.environ.setdefault(key, value)
    except Exception:
        pass

    return env_vars


# ---------------------------------------------------------------------------
# Tag Inference
# ---------------------------------------------------------------------------

# Tag inference keyword mappings (extensible, not framework-specific)
# These are common technical terms that help categorize requirements
_TAG_KEYWORDS = {
    "frontend": [
        # Generic terms (bilingual)
        "前端", "frontend", "ui", "页面", "界面", "组件", "客户端", "client",
        "用户界面", "user interface", "交互", "interaction",
        # Web frameworks (extensible list)
        "react", "vue", "angular", "svelte", "nextjs", "nuxt", "gatsby",
        "jquery", "bootstrap", "tailwind", "antd", "element",
        # Mobile
        "react native", "flutter", "ios", "android", "mobile",
        # Web technologies
        "html", "css", "sass", "scss", "less", "javascript", "typescript",
        "dom", "browser", "responsive", "webpack", "vite", "rollup",
    ],
    "backend": [
        # Generic terms (bilingual)
        "后端", "backend", "api", "接口", "服务", "server", "服务端",
        "restful", "graphql", "grpc", "微服务", "microservice",
        # Python frameworks
        "fastapi", "django", "flask", "tornado", "aiohttp", "sanic",
        # JavaScript/Node frameworks
        "express", "nestjs", "koa", "hapi", "fastify",
        # Other languages
        "spring", "springboot", "gin", "echo", "fiber",  # Go
        "rails", "sinatra",  # Ruby
        "laravel", "symfony",  # PHP
        "actix", "axum", "rocket",  # Rust
    ],
    "database": [
        # Generic terms (bilingual)
        "数据库", "database", "db", "存储", "storage", "持久化", "persistence",
        "数据", "data", "缓存", "cache", "索引", "index",
        # Relational databases
        "mysql", "postgres", "postgresql", "sqlite", "mariadb", "oracle", "mssql",
        "sql", "关系型",
        # NoSQL databases
        "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb",
        "nosql", "文档数据库", "键值存储",
        # ORMs
        "sqlalchemy", "prisma", "sequelize", "typeorm", "hibernate", "gorm",
    ],
    "testing": [
        # Generic terms (bilingual)
        "测试", "test", "qa", "验证", "质量", "quality", "检验",
        "单元测试", "unit test", "集成测试", "integration test",
        "端到端", "e2e", "end-to-end",
        # Testing frameworks
        "pytest", "jest", "mocha", "cypress", "playwright", "selenium",
        "vitest", "junit", "testify",
    ],
    "deployment": [
        # Generic terms (bilingual)
        "部署", "deploy", "运维", "devops", "发布", "release",
        "上线", "运行", "runtime", "环境", "environment",
        # Container/orchestration
        "docker", "kubernetes", "k8s", "container", "容器",
        # CI/CD
        "cicd", "ci/cd", "jenkins", "github actions", "gitlab ci",
        # Cloud
        "aws", "azure", "gcp", "云", "cloud", "serverless",
    ],
    "design": [
        # Generic terms (bilingual)
        "设计", "design", "ux", "用户体验", "交互设计",
        "ui设计", "ui design", "原型", "prototype", "wireframe",
        "figma", "sketch", "adobe xd",
    ],
    "security": [
        # Security terms (bilingual)
        "安全", "security", "认证", "authentication", "授权", "authorization",
        "加密", "encryption", "密码", "password", "token", "jwt", "oauth",
        "权限", "permission", "访问控制", "access control",
    ],
}


def _infer_tags(text: str) -> list[str]:
    """Infer capability tags from text using keyword matching.

    This is a heuristic-based approach that uses keyword matching
    to infer tags. The keyword lists are extensible and cover
    common frameworks across multiple languages.

    Args:
        text: Text to analyze (requirement description, etc.)

    Returns:
        list: Inferred tags
    """
    text_lower = text.lower()
    tags: list[str] = []

    for tag, keywords in _TAG_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)

    return list(set(tags))


# ---------------------------------------------------------------------------
# Runtime Builders
# ---------------------------------------------------------------------------
def build_runtime_requirements(
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build runtime requirement objects from specification.

    Args:
        spec: Specification dict

    Returns:
        list: List of runtime requirement dicts
    """
    runtime_reqs: list[dict[str, Any]] = []

    for req in spec.get("requirements", []):
        rid = req.get("id", "")
        title = req.get("title", "")
        summary = req.get("summary", req.get("description", ""))
        category = req.get("category", "general")

        # Infer tags from requirement text
        tags = _infer_tags(f"{title} {summary}")
        tags.append(category.lower())

        runtime_reqs.append({
            "id": rid,
            "title": title,
            "description": summary,
            "category": category,
            "tags": list(set(tags)),
            "priority": req.get("priority", "medium"),
        })

    return runtime_reqs


def build_runtime_acceptance(
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Build runtime acceptance criteria from specification.

    Args:
        spec: Specification dict

    Returns:
        dict: Acceptance configuration
    """
    acceptance = spec.get("acceptance", {})
    acceptance_map = spec.get("acceptance_map", [])

    return {
        "overall_target": acceptance.get("overall_target", 0.85),
        "per_requirement_target": acceptance.get("per_requirement_target", 0.80),
        "criteria_by_requirement": {
            item.get("requirement_id", ""): item.get("criteria", [])
            for item in acceptance_map
        },
    }


def compute_runtime_metrics(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute runtime metrics from execution results.

    Args:
        results: List of execution result dicts

    Returns:
        dict: Computed metrics
    """
    if not results:
        return {"pass_rate": 0.0, "total": 0, "passed": 0}

    passed = sum(1 for r in results if r.get("overall_passed", False))
    total = len(results)

    return {
        "pass_rate": passed / total if total > 0 else 0.0,
        "total": total,
        "passed": passed,
        "failed": total - passed,
    }


# ---------------------------------------------------------------------------
# Project ID
# ---------------------------------------------------------------------------
def derive_project_id(
    initial_requirement: str,
    user_id: str = "",
    hint: str | None = None,
) -> str:
    """Derive a project ID from requirement and user.

    Args:
        initial_requirement: Initial requirement text
        user_id: User identifier
        hint: Optional project ID hint

    Returns:
        str: Derived project ID
    """
    if hint:
        # Sanitize hint
        safe_hint = re.sub(r"[^\w\-_]", "_", hint)[:50]
        return safe_hint

    # Generate from requirement hash
    text = f"{user_id}:{initial_requirement}"
    hash_part = hashlib.md5(text.encode()).hexdigest()[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    return f"project_{timestamp}_{hash_part}"


# ---------------------------------------------------------------------------
# Harness Builder
# ---------------------------------------------------------------------------
def build_runtime_harness(
    spec: dict[str, Any],
    *,
    user_id: str = "cli-user",
    project_hint: str | None = None,
    resource_handles: list[dict[str, Any]] | None = None,
    mcp_clients: list[Any] | None = None,
    aa_mcp_clients: list[Any] | None = None,
    mcp_prompt: str | None = None,
    llm: Any = None,
    agent_market_dir: str | None = None,
    sandbox_manager: Any = None,
) -> RuntimeHarness:
    """Build a RuntimeHarness from specification.

    Args:
        spec: Specification dict
        user_id: User identifier
        project_hint: Optional project ID hint
        resource_handles: MCP resource handles
        mcp_clients: Regular MCP clients
        aa_mcp_clients: AA-side MCP clients
        mcp_prompt: Combined MCP context prompt
        llm: LLM model instance
        agent_market_dir: Path to agent market directory
        sandbox_manager: Sandbox manager instance

    Returns:
        RuntimeHarness: Configured runtime harness
    """
    from agentscope.ones import AASystemAgent
    from agentscope.ones._system import SystemRegistry, UserProfile
    from agentscope.ones.memory import ProjectPool, MemoryPool, ResourceLibrary
    from agentscope.ones.task_graph import TaskGraphBuilder
    from agentscope.ones.kpi import KPITracker
    from agentscope.ones.intent import AssistantOrchestrator, AcceptanceCriteria
    from agentscope.ones.execution import ExecutionLoop
    from agentscope.aa import Requirement, AgentProfile, StaticScore, AgentCapabilities
    from ._agent_market import load_agent_market, default_agent_profiles

    # Helper to convert dict to AgentProfile
    def _dict_to_profile(agent_id: str, info: dict[str, Any]) -> AgentProfile:
        """Convert dict profile to AgentProfile object."""
        base_score = info.get("base_score", 0.75)
        capabilities = info.get("capabilities", [])
        return AgentProfile(
            agent_id=agent_id,
            name=info.get("name", agent_id),
            static_score=StaticScore(
                performance=base_score,
                brand=0.5,
                recognition=0.5,
            ),
            capabilities=AgentCapabilities(
                skills=set(capabilities),
                domains=set([info.get("role", "general")]),
            ),
            metadata={"description": info.get("description", "")},
        )

    # Load agent profiles
    agent_profiles_dict = default_agent_profiles()
    if agent_market_dir:
        market_agents = load_agent_market(agent_market_dir)
        agent_profiles_dict.update(market_agents)

    # Convert to AgentProfile objects
    agent_profiles: list[AgentProfile] = [
        _dict_to_profile(aid, info) for aid, info in agent_profiles_dict.items()
    ]

    # Derive project ID
    initial_req = spec.get("summary", "")
    project_id = derive_project_id(initial_req, user_id, project_hint)

    # Build runtime requirements
    runtime_reqs = build_runtime_requirements(spec)
    runtime_acceptance = build_runtime_acceptance(spec)

    # Create core components
    system_registry = SystemRegistry()
    project_pool = ProjectPool()
    memory_pool = MemoryPool()
    resource_library = ResourceLibrary()
    task_graph_builder = TaskGraphBuilder(fallback_agent_id="default-agent")
    kpi_tracker = KPITracker(target_reduction=0.9)

    # Create orchestrator
    orchestrator = AssistantOrchestrator(
        system_registry=system_registry,
        scoring_config=None,
        spawn_factory=None,
    )

    # Register agent profiles as candidates
    orchestrator.register_candidates(agent_profiles)

    # Create execution loop
    execution_loop = ExecutionLoop(
        project_pool=project_pool,
        memory_pool=memory_pool,
        resource_library=resource_library,
        orchestrator=orchestrator,
        task_graph_builder=task_graph_builder,
        kpi_tracker=kpi_tracker,
        max_rounds=3,
    )

    # Create requirement resolver
    def requirement_resolver(utterance: str) -> dict[str, Requirement]:
        """Resolve requirements from utterance."""
        requirements: dict[str, Requirement] = {}
        for req in runtime_reqs:
            rid = req.get("id", "")
            tags = set(req.get("tags", []))
            # Map tags to skills/domains for agent matching
            skills = set()
            domains = set()
            for tag in tags:
                if tag in ("frontend", "backend", "database", "testing", "design"):
                    domains.add(tag)
                else:
                    skills.add(tag)
            requirements[rid] = Requirement(
                skills=skills,
                domains=domains,
                notes=f"{req.get('title', '')}: {req.get('description', '')}",
            )
        return requirements

    # Create acceptance resolver
    def acceptance_resolver(utterance: str) -> AcceptanceCriteria:
        """Resolve acceptance criteria from utterance."""
        criteria_by_req = runtime_acceptance.get("criteria_by_requirement", {})
        # Build description from all criteria
        descriptions = []
        for rid, criteria_list in criteria_by_req.items():
            for c in criteria_list:
                descriptions.append(f"{rid}: {c.get('name', '')} - {c.get('description', '')}")
        description = "\n".join(descriptions) if descriptions else "Default acceptance criteria"
        # Build metrics
        metrics = {
            "pass_threshold": runtime_acceptance.get("per_requirement_target", 0.8),
            "overall_target": runtime_acceptance.get("overall_target", 0.85),
        }
        return AcceptanceCriteria(
            description=description,
            metrics=metrics,
        )

    # Create user profile
    user_profile = UserProfile(user_id=user_id)

    # Create AA agent
    aa_agent = AASystemAgent(
        name="HiveCore-AA",
        user_id=user_id,
        orchestrator=orchestrator,
        execution_loop=execution_loop,
        requirement_resolver=requirement_resolver,
        acceptance_resolver=acceptance_resolver,
        user_profile=user_profile,
    )

    return RuntimeHarness(
        aa_agent=aa_agent,
        mcp_clients=mcp_clients or [],
        aa_mcp_clients=aa_mcp_clients or [],
        resource_handles=resource_handles or [],
        mcp_prompt=mcp_prompt or "",
    )


__all__ = [
    "RuntimeHarness",
    "_load_env_file",
    "_infer_tags",
    "build_runtime_requirements",
    "build_runtime_acceptance",
    "compute_runtime_metrics",
    "derive_project_id",
    "build_runtime_harness",
]
