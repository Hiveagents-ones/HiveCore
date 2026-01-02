# -*- coding: utf-8 -*-
"""LLM-driven team selection for collaborative task execution.

This module implements dynamic team selection where the AA (through LLM) analyzes
each requirement and decides:
1. Whether multi-agent collaboration is needed
2. Which roles are required
3. How agents should collaborate

Example workflow:
    LLM analyzes: "会员信息管理 (backend)"
    LLM decides:
      - Complexity: medium
      - Needs: [backend_dev] (simple CRUD, single agent sufficient)
      - Mode: single

    LLM analyzes: "设计并实现完整的支付系统"
    LLM decides:
      - Complexity: high
      - Needs: [architect, backend_dev, qa] (complex system needs collaboration)
      - Mode: sequential
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, Any, TYPE_CHECKING

from ._types import (
    AgentProfile,
    CandidateRanking,
    Requirement,
    AAScoringConfig,
)
from ._selector import RequirementFitScorer
from .._logging import logger

if TYPE_CHECKING:
    from ..model import ModelResponse


class TeamRole(str, Enum):
    """Roles that can participate in a task team.

    Each role represents a specific responsibility in the development process.
    """

    # Core roles
    PRODUCT_MANAGER = "product_manager"
    ARCHITECT = "architect"

    # Development roles
    FRONTEND_DEV = "frontend_dev"
    BACKEND_DEV = "backend_dev"
    FULLSTACK_DEV = "fullstack_dev"
    DATABASE_DEV = "database_dev"

    # Design roles
    UX_DESIGNER = "ux_designer"
    UI_DESIGNER = "ui_designer"

    # Quality roles
    QA = "qa"
    CODE_REVIEWER = "code_reviewer"

    # Support roles
    DEVOPS = "devops"
    TECH_WRITER = "tech_writer"


class CollaborationMode(str, Enum):
    """How team members collaborate on a task."""

    # All agents work in parallel, then merge results
    PARALLEL = "parallel"

    # Agents work in sequence: PM -> Architect -> Dev -> QA
    SEQUENTIAL = "sequential"

    # Iterative collaboration with feedback loops
    ITERATIVE = "iterative"

    # Single agent (no collaboration needed)
    SINGLE = "single"


# Mapping from role to required capabilities/skills
ROLE_CAPABILITIES: dict[TeamRole, set[str]] = {
    TeamRole.PRODUCT_MANAGER: {"product_management", "requirements", "acceptance"},
    TeamRole.ARCHITECT: {"architecture", "system_design", "code_review"},
    TeamRole.FRONTEND_DEV: {"frontend", "react", "vue", "javascript", "typescript", "css"},
    TeamRole.BACKEND_DEV: {"backend", "python", "java", "go", "api", "database"},
    TeamRole.FULLSTACK_DEV: {"fullstack", "frontend", "backend"},
    TeamRole.DATABASE_DEV: {"database", "sql", "postgresql", "mysql", "mongodb"},
    TeamRole.UX_DESIGNER: {"ux", "user_experience", "wireframe", "prototype"},
    TeamRole.UI_DESIGNER: {"ui", "visual_design", "figma", "sketch"},
    TeamRole.QA: {"testing", "qa", "test_automation", "quality"},
    TeamRole.CODE_REVIEWER: {"code_review", "best_practices"},
    TeamRole.DEVOPS: {"devops", "docker", "kubernetes", "ci_cd", "deployment"},
    TeamRole.TECH_WRITER: {"documentation", "technical_writing"},
}

# Keep for backward compatibility but mark as deprecated
TEAM_TEMPLATES: dict[str, Any] = {}


@dataclass
class RoleAssignment:
    """Assignment of an agent to a role.

    Attributes:
        role (`TeamRole`):
            The role being filled.
        agent (`AgentProfile`):
            The agent assigned to this role.
        ranking (`CandidateRanking`):
            The ranking information for this assignment.
        is_required (`bool`):
            Whether this role is required for the task.
    """

    role: TeamRole
    agent: AgentProfile
    ranking: CandidateRanking
    is_required: bool = True


@dataclass
class AgentSpec:
    """Specification for a new agent to be spawned by AA.

    When no existing agent fits a required role, LLM generates this spec
    to define the new agent's identity and capabilities.

    Attributes:
        role (`str`):
            The role this agent will fill (e.g., "backend_dev").
        agent_id (`str`):
            Meaningful identifier (e.g., "payment-backend-expert").
        name (`str`):
            Display name (e.g., "支付后端专家").
        skills (`list[str]`):
            List of skills/capabilities.
        domains (`list[str]`):
            Expertise domains (can include new custom domains).
        tags (`list[str]`):
            Free-form tags for fine-grained matching.
        parent_domain (`str | None`):
            If domains include a new domain, specify its parent category.
        system_prompt (`str`):
            Role-specific system prompt.
    """

    role: str
    agent_id: str
    name: str
    skills: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    parent_domain: str | None = None
    system_prompt: str = ""
    description: str = ""  # Agent 简介，用于需求符合度评分


@dataclass
class LLMTeamAnalysis:
    """Result of LLM analysis for team composition.

    Attributes:
        complexity (`str`):
            Task complexity: "low", "medium", "high".
        needs_collaboration (`bool`):
            Whether multi-agent collaboration is recommended.
        required_roles (`list[str]`):
            List of role names that are required.
        optional_roles (`list[str]`):
            List of role names that are optional.
        collaboration_mode (`str`):
            Recommended collaboration mode.
        reasoning (`str`):
            LLM's reasoning for the decision.
        new_agent_specs (`list[AgentSpec]`):
            Specs for new agents to spawn when no suitable candidate exists.
    """

    complexity: str = "medium"
    needs_collaboration: bool = False
    required_roles: list[str] = field(default_factory=list)
    optional_roles: list[str] = field(default_factory=list)
    collaboration_mode: str = "single"
    reasoning: str = ""
    new_agent_specs: list[AgentSpec] = field(default_factory=list)


@dataclass
class TeamSelection:
    """Result of team selection for a requirement.

    Attributes:
        requirement_id (`str`):
            The requirement ID this team is for.
        assignments (`list[RoleAssignment]`):
            List of role -> agent assignments.
        collaboration_mode (`CollaborationMode`):
            How the team should collaborate.
        llm_analysis (`LLMTeamAnalysis | None`):
            The LLM analysis that led to this selection.
    """

    requirement_id: str
    assignments: list[RoleAssignment] = field(default_factory=list)
    collaboration_mode: CollaborationMode = CollaborationMode.SINGLE
    llm_analysis: LLMTeamAnalysis | None = None

    @property
    def agent_ids(self) -> list[str]:
        """Get all agent IDs in this team."""
        return [a.agent.agent_id for a in self.assignments]

    @property
    def primary_agent_id(self) -> str | None:
        """Get primary agent ID for backward compatibility."""
        if not self.assignments:
            return None
        # Return the first required role's agent, or first agent if none required
        for assignment in self.assignments:
            if assignment.is_required:
                return assignment.agent.agent_id
        return self.assignments[0].agent.agent_id if self.assignments else None

    @property
    def rankings(self) -> list[CandidateRanking]:
        """Get all rankings for this team."""
        return [a.ranking for a in self.assignments]

    def get_agent_for_role(self, role: TeamRole) -> AgentProfile | None:
        """Get the agent assigned to a specific role."""
        for assignment in self.assignments:
            if assignment.role == role:
                return assignment.agent
        return None


# Keep TeamTemplate for backward compatibility
@dataclass
class TeamTemplate:
    """Deprecated: Use LLM-driven selection instead."""

    task_type: str = "default"
    required_roles: list[TeamRole] = field(default_factory=list)
    optional_roles: list[TeamRole] = field(default_factory=list)
    collaboration_mode: CollaborationMode = CollaborationMode.SINGLE
    min_team_size: int = 1
    max_team_size: int = 5


# Prompt template for LLM team analysis (with tool support)
TEAM_ANALYSIS_PROMPT_WITH_TOOLS = """You are an expert software project manager. Analyze the following requirement and decide how to staff it.

## Requirement
ID: {requirement_id}
Description: {description}
Skills needed: {skills}
Type/Category: {task_type}

## Your Task
1. **First**, use the provided tools to search for existing agents and domains that match this requirement
2. **Then**, decide the team composition based on your findings
3. If no suitable agent exists for a required role, specify a new agent to be created

## Available Roles
- product_manager: 需求分析、验收把控
- architect: 系统设计、技术方案
- frontend_dev: 前端开发
- backend_dev: 后端开发
- fullstack_dev: 全栈开发
- database_dev: 数据库设计与开发
- ux_designer: 用户体验设计
- ui_designer: 视觉设计
- qa: 测试质量保证
- code_reviewer: 代码审查
- devops: 部署运维
- tech_writer: 技术文档

## Decision Guidelines
1. Simple tasks (CRUD, simple fixes) → Single agent is enough
2. Medium tasks (feature with multiple components) → Consider 2 agents
3. Complex tasks (system design, cross-cutting) → May need 3+ agents
4. Don't over-staff: only add roles that provide real value

## Core Domains
- backend, frontend, design, qa, devops, architecture, product, specialist

When ready to respond, output JSON in this format:
```json
{{
  "complexity": "low|medium|high",
  "needs_collaboration": true|false,
  "required_roles": ["role1", "role2"],
  "optional_roles": ["role3"],
  "collaboration_mode": "single|sequential|parallel|iterative",
  "reasoning": "Brief explanation",
  "new_agent_specs": [
    {{
      "role": "backend_dev",
      "agent_id": "meaningful-kebab-id",
      "name": "中文名称",
      "skills": ["skill1", "skill2"],
      "domains": ["domain1"],
      "tags": ["tag1", "tag2"],
      "parent_domain": "backend",
      "system_prompt": "角色描述"
    }}
  ]
}}
```"""

# Fallback prompt without tools (for when tool calling is not supported)
TEAM_ANALYSIS_PROMPT = """You are an expert software project manager. Analyze the following requirement and decide how to staff it.

## Requirement
ID: {requirement_id}
Description: {description}
Skills needed: {skills}
Type/Category: {task_type}

## Available Agents
{agent_list}

## Available Roles
- product_manager: 需求分析、验收把控
- architect: 系统设计、技术方案
- frontend_dev: 前端开发
- backend_dev: 后端开发
- fullstack_dev: 全栈开发
- database_dev: 数据库设计与开发
- ux_designer: 用户体验设计
- ui_designer: 视觉设计
- qa: 测试质量保证
- code_reviewer: 代码审查
- devops: 部署运维
- tech_writer: 技术文档

## Decision Guidelines
1. Simple tasks (CRUD, simple fixes, single feature) → Single agent is enough
2. Medium tasks (feature with multiple components) → Consider 2 agents
3. Complex tasks (system design, cross-cutting concerns) → May need 3+ agents
4. Don't over-staff: only add roles that provide real value
5. Product manager is NOT always needed - only for requirements that need clarification or acceptance validation

## New Agent Specs (IMPORTANT)
If a required role has NO suitable agent in the available list, you MUST provide a spec for a new agent to be created.

### Core Domains (use these when applicable)
- backend: 后端开发
- frontend: 前端开发
- design: UI/UX设计
- qa: 质量保证/测试
- devops: 部署运维
- architecture: 系统架构
- product: 产品管理
- specialist: 特定领域专家（当不属于上述任何分类时）

### Agent Spec Fields
- role: The role being filled (from Available Roles list)
- agent_id: A meaningful kebab-case ID based on the task (e.g., "member-crud-backend", "smart-contract-auditor")
- name: A descriptive Chinese name (e.g., "会员管理后端专家", "智能合约审计专家")
- description: A brief description of the agent's capabilities and what it does (1-2 sentences, for matching with task requirements)
- skills: Specific skills needed for THIS task
- domains: List of domains. Use core domains when applicable. For specialized tasks (e.g., blockchain, AI/ML), you MAY create a new domain
- tags: Free-form tags for fine-grained capability matching (e.g., ["python", "solidity", "security", "audit"])
- parent_domain: If creating a new domain, specify which core domain it belongs under (e.g., "blockchain" -> parent_domain: "backend")
- system_prompt: A brief role description for the agent

## Output Format (JSON)
{{
  "complexity": "low|medium|high",
  "needs_collaboration": true|false,
  "required_roles": ["role1", "role2"],
  "optional_roles": ["role3"],
  "collaboration_mode": "single|sequential|parallel|iterative",
  "reasoning": "Brief explanation of your decision",
  "new_agent_specs": [
    {{
      "role": "backend_dev",
      "agent_id": "smart-contract-auditor",
      "name": "智能合约审计专家",
      "description": "专注于智能合约安全审计，能够发现Solidity代码中的重入攻击、整数溢出等安全漏洞",
      "skills": ["solidity", "security", "blockchain"],
      "domains": ["blockchain", "backend"],
      "tags": ["solidity", "ethereum", "security", "audit", "defi"],
      "parent_domain": "backend",
      "system_prompt": "你是一个专注于智能合约安全审计的专家，擅长发现Solidity代码中的安全漏洞。"
    }}
  ]
}}

IMPORTANT: For EACH role in required_roles, check if there's a suitable agent in the Available Agents list:
- If YES: that role is covered, no spec needed
- If NO (or if "No agents available"): you MUST create a new_agent_spec for that role

When "No agents available" is shown, you MUST create new_agent_specs for ALL required_roles.

Analyze and respond with JSON only:"""

# Tool definitions for team analysis
TEAM_ANALYSIS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_agents",
            "description": "搜索已注册的 Agent。支持模糊匹配 agent_id、名称、技能、领域、标签。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，如 'blockchain'、'后端'、'python'",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_domains",
            "description": "搜索已有的领域分类。可按关键词搜索或按父域筛选。",
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_domain_tree",
            "description": "获取完整的领域层级结构，显示核心域和自定义域。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


class TeamSelector:
    """LLM-driven team selector for dynamic agent composition.

    This selector uses LLM to analyze each requirement and decide:
    1. Whether collaboration is needed (or single agent is sufficient)
    2. Which roles are required
    3. How agents should collaborate

    If LLM is not configured, falls back to single-agent selection.

    Attributes:
        config (`AAScoringConfig`):
            Scoring configuration.
        model_config_name (`str | None`):
            Model config name for LLM analysis. If None, uses single-agent.
        enable_multi_agent (`bool`):
            Whether to enable multi-agent teams.
        min_fit_threshold (`float`):
            Minimum fit score for role assignment.
    """

    def __init__(
        self,
        config: AAScoringConfig | None = None,
        model_config_name: str | None = None,
        model: Any | None = None,
        enable_multi_agent: bool = True,
        min_fit_threshold: float = 0.1,
        # Deprecated parameters for backward compatibility
        templates: dict | None = None,
        enable_llm_analysis: bool = True,  # Deprecated, ignored
    ) -> None:
        """Initialize the team selector.

        Args:
            config: Scoring configuration.
            model_config_name: Model config name for LLM analysis.
            model: Pre-initialized model instance to use directly.
            enable_multi_agent: Whether to enable multi-agent teams.
            min_fit_threshold: Minimum fit score for role assignment.
            templates: Deprecated, ignored.
            enable_llm_analysis: Deprecated, ignored.
        """
        self.config = config or AAScoringConfig()
        self.model_config_name = model_config_name
        self.enable_multi_agent = enable_multi_agent
        self.min_fit_threshold = min_fit_threshold
        self._fit_scorer = RequirementFitScorer(self.config)
        self._model = model  # Allow direct model injection

    def _get_model(self):
        """Lazy load the model for LLM analysis."""
        if self._model is None and self.model_config_name:
            from ..model import load_model_by_config_name
            self._model = load_model_by_config_name(self.model_config_name)
        return self._model

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a registry tool and return result.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            Tool execution result as string.
        """
        from ._registry_tools import execute_registry_tool
        return execute_registry_tool(tool_name, arguments)

    def _call_model(self, messages: list, tools: list | None = None):
        """Call the model with proper async handling.

        Args:
            messages: Messages to send.
            tools: Optional tools for function calling.

        Returns:
            Model response.
        """
        import asyncio
        import inspect

        model = self._get_model()

        # Build kwargs for model call
        kwargs: dict = {}
        if tools:
            kwargs["tools"] = tools

        call_result = model(messages, **kwargs) if kwargs else model(messages)

        # Handle async model calls
        if inspect.iscoroutine(call_result):
            try:
                # Check if we're already in an event loop
                loop = asyncio.get_running_loop()
                # If we get here, there's a running loop - use thread
                import concurrent.futures

                def _run_in_thread():
                    return asyncio.run(
                        model(messages, **kwargs) if kwargs else model(messages)
                    )

                call_result.close()  # Close the original coroutine
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    future = executor.submit(_run_in_thread)
                    return future.result(timeout=120)
                finally:
                    executor.shutdown(wait=False)
            except RuntimeError:
                # No running event loop - safe to use asyncio.run
                try:
                    return asyncio.run(call_result)
                except Exception as e:
                    logger.error("[TeamSelector] Async model call failed: %s", e)
                    raise
        return call_result

    def _analyze_with_llm(
        self,
        requirement_id: str,
        requirement: Requirement,
        candidates: Sequence[AgentProfile],
    ) -> LLMTeamAnalysis | None:
        """Use LLM to analyze requirement and decide team composition.

        Supports two modes:
        1. Tool-calling mode: LLM can search agents/domains on-demand (preferred)
        2. Fallback mode: All agents listed in prompt (for models without tool support)

        Args:
            requirement_id: The requirement identifier.
            requirement: The requirement to analyze.
            candidates: Available agent candidates.

        Returns:
            LLMTeamAnalysis with the decision, or None if no model available.
        """
        model = self._get_model()
        if model is None:
            return None

        # Try tool-calling mode first
        try:
            return self._analyze_with_tools(requirement_id, requirement)
        except Exception as e:
            logger.debug(
                "[TeamSelector] Tool-calling failed (%s), falling back to prompt mode",
                e,
            )

        # Fallback to prompt-based mode (all agents in prompt)
        return self._analyze_with_prompt(requirement_id, requirement, candidates)

    def _analyze_with_tools(
        self,
        requirement_id: str,
        requirement: Requirement,
    ) -> LLMTeamAnalysis | None:
        """Analyze using tool-calling mode.

        LLM can search agents and domains on-demand, avoiding prompt bloat.

        Args:
            requirement_id: The requirement identifier.
            requirement: The requirement to analyze.

        Returns:
            LLMTeamAnalysis or None.
        """
        prompt = TEAM_ANALYSIS_PROMPT_WITH_TOOLS.format(
            requirement_id=requirement_id,
            description=requirement.notes or "No description",
            skills=", ".join(requirement.skills) if requirement.skills else "Not specified",
            task_type=getattr(requirement, "type", "") or getattr(requirement, "category", "") or "general",
        )

        messages = [{"role": "user", "content": prompt}]
        max_rounds = 5  # Prevent infinite loops

        for round_num in range(max_rounds):
            logger.debug(
                "[TeamSelector] Tool-calling round %d for %s",
                round_num + 1,
                requirement_id,
            )

            response = self._call_model(messages, tools=TEAM_ANALYSIS_TOOLS)

            # Check for tool calls
            tool_calls = self._extract_tool_calls(response)

            if tool_calls:
                # Execute tools and add results to messages
                messages.append({
                    "role": "assistant",
                    "content": self._extract_text(response),
                    "tool_calls": tool_calls,
                })

                for tool_call in tool_calls:
                    tool_name = tool_call.get("function", {}).get("name", "")
                    tool_args = tool_call.get("function", {}).get("arguments", {})

                    # Parse arguments if string
                    if isinstance(tool_args, str):
                        tool_args = json.loads(tool_args)

                    result = self._execute_tool(tool_name, tool_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", f"call_{round_num}"),
                        "content": result,
                    })

                    logger.debug(
                        "[TeamSelector] Tool %s(%s) -> %d chars",
                        tool_name,
                        tool_args,
                        len(result),
                    )
            else:
                # No tool calls, extract final response
                content = self._extract_text(response)
                return self._parse_analysis_response(content)

        logger.warning("[TeamSelector] Max tool-calling rounds reached")
        return None

    def _analyze_with_prompt(
        self,
        requirement_id: str,
        requirement: Requirement,
        candidates: Sequence[AgentProfile],
    ) -> LLMTeamAnalysis | None:
        """Analyze using prompt mode (fallback).

        All agents are listed in prompt. Used when tool-calling fails.

        Args:
            requirement_id: The requirement identifier.
            requirement: The requirement to analyze.
            candidates: Available agent candidates.

        Returns:
            LLMTeamAnalysis or None.
        """
        # Build agent list description
        agent_descriptions = []
        for agent in list(candidates)[:15]:  # Limit to prevent prompt bloat
            skills = ", ".join(sorted(agent.capabilities.skills)[:5])
            domains = ", ".join(sorted(agent.capabilities.domains)[:3]) if agent.capabilities.domains else "general"
            tags = ", ".join(sorted(agent.capabilities.compliance_tags)[:5]) if agent.capabilities.compliance_tags else ""
            desc = f"- {agent.agent_id}: {agent.name} (skills: {skills}, domains: {domains})"
            if tags:
                desc += f" [tags: {tags}]"
            agent_descriptions.append(desc)

        # Get custom domains (limited)
        custom_domains_desc = ""
        try:
            from ._agent_registry import get_global_registry
            registry = get_global_registry()
            custom_domains = [
                f"- {d.name}: {d.display_name} (parent: {d.parent})"
                for d in list(registry.domains.values())[:10]
                if not d.is_core and d.parent
            ]
            if custom_domains:
                custom_domains_desc = "\n\n### Existing Custom Domains (reuse if applicable)\n" + "\n".join(custom_domains)
        except Exception:
            pass

        prompt = TEAM_ANALYSIS_PROMPT.format(
            requirement_id=requirement_id,
            description=requirement.notes or "No description",
            skills=", ".join(requirement.skills) if requirement.skills else "Not specified",
            task_type=getattr(requirement, "type", "") or getattr(requirement, "category", "") or "general",
            agent_list="\n".join(agent_descriptions) if agent_descriptions else "No agents available",
        )

        if custom_domains_desc:
            prompt = prompt.replace(
                "- specialist: 特定领域专家（当不属于上述任何分类时）",
                f"- specialist: 特定领域专家（当不属于上述任何分类时）{custom_domains_desc}",
            )

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self._call_model(messages)
            content = self._extract_text(response)
            return self._parse_analysis_response(content)
        except Exception as e:
            logger.warning("[TeamSelector] Prompt analysis failed: %s", e)
            return None

    def _extract_tool_calls(self, response) -> list[dict]:
        """Extract tool calls from model response.

        Args:
            response: Model response object.

        Returns:
            List of tool call dicts.
        """
        tool_calls = []

        # Handle different response formats
        if hasattr(response, "tool_calls") and response.tool_calls:
            return response.tool_calls

        # Check content blocks for tool_use
        if hasattr(response, "content"):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": block.get("input", {}),
                        },
                    })

        return tool_calls

    def _extract_text(self, response) -> str:
        """Extract text content from model response.

        Args:
            response: Model response object.

        Returns:
            Extracted text content.
        """
        text_parts = []

        if hasattr(response, "content"):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)

        return "".join(text_parts).strip()

    def _parse_analysis_response(self, content: str) -> LLMTeamAnalysis | None:
        """Parse JSON analysis response from LLM.

        Args:
            content: Response content string.

        Returns:
            LLMTeamAnalysis or None if parsing fails.
        """
        try:
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            # Parse new_agent_specs if present
            new_agent_specs: list[AgentSpec] = []
            for spec_data in data.get("new_agent_specs", []):
                if isinstance(spec_data, dict):
                    new_agent_specs.append(AgentSpec(
                        role=spec_data.get("role", ""),
                        agent_id=spec_data.get("agent_id", ""),
                        name=spec_data.get("name", ""),
                        skills=spec_data.get("skills", []),
                        domains=spec_data.get("domains", []),
                        tags=spec_data.get("tags", []),
                        parent_domain=spec_data.get("parent_domain"),
                        system_prompt=spec_data.get("system_prompt", ""),
                        description=spec_data.get("description", ""),
                    ))

            return LLMTeamAnalysis(
                complexity=data.get("complexity", "medium"),
                needs_collaboration=data.get("needs_collaboration", False),
                required_roles=data.get("required_roles", []),
                optional_roles=data.get("optional_roles", []),
                collaboration_mode=data.get("collaboration_mode", "single"),
                reasoning=data.get("reasoning", ""),
                new_agent_specs=new_agent_specs,
            )

        except Exception as e:
            logger.warning("[TeamSelector] Failed to parse response: %s", e)
            return None

    def _create_role_requirement(
        self,
        role: TeamRole,
        base_requirement: Requirement,
    ) -> Requirement:
        """Create a requirement for a specific role.

        Args:
            role: The role to create requirement for.
            base_requirement: The original task requirement.

        Returns:
            A new Requirement with role-specific skills.
        """
        role_skills = ROLE_CAPABILITIES.get(role, set())
        # Only use role_skills for matching, not combined with base_requirement.skills
        # This prevents score dilution when base_requirement contains skills for
        # multiple roles (e.g., frontend + backend + database)
        # The role-specific skills are sufficient for agent matching
        matching_skills = role_skills if role_skills else base_requirement.skills

        return Requirement(
            skills=matching_skills,
            tools=base_requirement.tools,
            domains=base_requirement.domains,
            languages=base_requirement.languages,
            regions=base_requirement.regions,
            compliance_tags=base_requirement.compliance_tags,
            hard_constraints=base_requirement.hard_constraints,
            weight_overrides=base_requirement.weight_overrides,
            notes=f"[{role.value}] {base_requirement.notes or ''}",
        )

    def _score_agent_for_role(
        self,
        agent: AgentProfile,
        role: TeamRole,
        base_requirement: Requirement,
    ) -> CandidateRanking:
        """Score an agent for a specific role.

        Args:
            agent: The agent to score.
            role: The role to score for.
            base_requirement: The base task requirement.

        Returns:
            CandidateRanking with the agent's fit for this role.
        """
        role_requirement = self._create_role_requirement(role, base_requirement)
        fit = self._fit_scorer.score(role_requirement, agent.capabilities)

        s_base = agent.s_base
        if s_base is None:
            s_base = agent.compute_s_base(self.config.severity_weights)

        combined = s_base + (fit.score * self.config.requirement_weight)

        return CandidateRanking(
            profile=agent,
            s_base=s_base,
            requirement_fit=fit,
            combined_score=combined,
            cold_start_slot_reserved=agent.is_cold_start,
            risk_notes=[f"Role: {role.value}"] + fit.rationales,
        )

    def _select_agent_for_role(
        self,
        role: TeamRole,
        candidates: Sequence[AgentProfile],
        base_requirement: Requirement,
        already_assigned: set[str],
    ) -> tuple[AgentProfile | None, CandidateRanking | None]:
        """Select the best agent for a role.

        Args:
            role: The role to fill.
            candidates: Available agent candidates.
            base_requirement: The base task requirement.
            already_assigned: Agent IDs already assigned to other roles.

        Returns:
            Tuple of (agent, ranking) or (None, None) if no suitable agent.
        """
        best_agent: AgentProfile | None = None
        best_ranking: CandidateRanking | None = None
        best_score = -1.0

        for agent in candidates:
            # Skip already assigned agents
            if agent.agent_id in already_assigned:
                continue

            ranking = self._score_agent_for_role(agent, role, base_requirement)

            if ranking.requirement_fit.score < self.min_fit_threshold:
                continue

            if ranking.combined_score > best_score:
                best_score = ranking.combined_score
                best_agent = agent
                best_ranking = ranking

        return best_agent, best_ranking

    def _role_from_string(self, role_str: str) -> TeamRole | None:
        """Convert role string to TeamRole enum."""
        role_str = role_str.lower().strip()
        for role in TeamRole:
            if role.value == role_str:
                return role
        return None

    def select_team(
        self,
        requirement_id: str,
        requirement: Requirement,
        candidates: Sequence[AgentProfile],
        task_type: str | None = None,  # Deprecated, ignored
    ) -> TeamSelection:
        """Select a team of agents for a requirement using LLM analysis.

        The LLM analyzes the requirement and decides:
        1. Whether multi-agent collaboration is needed
        2. Which roles are required
        3. How agents should collaborate

        If LLM is not available or analysis fails, falls back to single-agent selection.

        Args:
            requirement_id: The requirement identifier.
            requirement: The requirement to fulfill.
            candidates: Available agent candidates.
            task_type: Deprecated, ignored. Task type is inferred by LLM.

        Returns:
            TeamSelection with the assigned team.
        """
        # If multi-agent is disabled, select single agent
        if not self.enable_multi_agent:
            return self._select_single_best_agent(requirement_id, requirement, candidates)

        # Analyze requirement with LLM
        analysis = self._analyze_with_llm(requirement_id, requirement, candidates)

        # If LLM analysis failed or not available, use single agent
        if analysis is None:
            logger.info(
                "[TeamSelector] No LLM analysis for %s, using single-agent selection",
                requirement_id,
            )
            return self._select_single_best_agent(requirement_id, requirement, candidates)

        logger.info(
            "[TeamSelector] LLM analysis for %s: complexity=%s, needs_collaboration=%s, roles=%s",
            requirement_id,
            analysis.complexity,
            analysis.needs_collaboration,
            analysis.required_roles + analysis.optional_roles,
        )

        # If collaboration not needed, select single agent
        if not analysis.needs_collaboration:
            selection = self._select_single_best_agent(requirement_id, requirement, candidates)
            selection.llm_analysis = analysis
            return selection

        # Build team based on LLM analysis
        assignments: list[RoleAssignment] = []
        assigned_agents: set[str] = set()

        # Assign required roles
        for role_str in analysis.required_roles:
            role = self._role_from_string(role_str)
            if role is None:
                logger.warning("Unknown role: %s", role_str)
                continue

            agent, ranking = self._select_agent_for_role(
                role, candidates, requirement, assigned_agents
            )
            if agent and ranking:
                assignments.append(
                    RoleAssignment(
                        role=role,
                        agent=agent,
                        ranking=ranking,
                        is_required=True,
                    )
                )
                assigned_agents.add(agent.agent_id)

        # Assign optional roles
        for role_str in analysis.optional_roles:
            role = self._role_from_string(role_str)
            if role is None:
                continue

            agent, ranking = self._select_agent_for_role(
                role, candidates, requirement, assigned_agents
            )
            if agent and ranking:
                assignments.append(
                    RoleAssignment(
                        role=role,
                        agent=agent,
                        ranking=ranking,
                        is_required=False,
                    )
                )
                assigned_agents.add(agent.agent_id)

        # Determine collaboration mode
        mode_str = analysis.collaboration_mode.lower()
        if mode_str == "parallel":
            collaboration_mode = CollaborationMode.PARALLEL
        elif mode_str == "iterative":
            collaboration_mode = CollaborationMode.ITERATIVE
        elif mode_str == "sequential":
            collaboration_mode = CollaborationMode.SEQUENTIAL
        else:
            collaboration_mode = CollaborationMode.SINGLE

        # If only one agent assigned, use SINGLE mode
        if len(assignments) <= 1:
            collaboration_mode = CollaborationMode.SINGLE

        selection = TeamSelection(
            requirement_id=requirement_id,
            assignments=assignments,
            collaboration_mode=collaboration_mode,
            llm_analysis=analysis,
        )

        logger.info(
            "[TeamSelector] Team for %s: %d agents, mode=%s, agents=%s",
            requirement_id,
            len(assignments),
            collaboration_mode.value,
            [f"{a.role.value}:{a.agent.agent_id}" for a in assignments],
        )

        return selection

    def _select_single_best_agent(
        self,
        requirement_id: str,
        requirement: Requirement,
        candidates: Sequence[AgentProfile],
    ) -> TeamSelection:
        """Select the single best agent for a requirement.

        Args:
            requirement_id: The requirement identifier.
            requirement: The requirement to fulfill.
            candidates: Available agent candidates.

        Returns:
            TeamSelection with a single agent.
        """
        best_agent: AgentProfile | None = None
        best_ranking: CandidateRanking | None = None
        best_score = -1.0

        # Score all candidates against the base requirement
        for agent in candidates:
            fit = self._fit_scorer.score(requirement, agent.capabilities)

            s_base = agent.s_base
            if s_base is None:
                s_base = agent.compute_s_base(self.config.severity_weights)

            combined = s_base + (fit.score * self.config.requirement_weight)

            if combined > best_score:
                best_score = combined
                best_agent = agent
                best_ranking = CandidateRanking(
                    profile=agent,
                    s_base=s_base,
                    requirement_fit=fit,
                    combined_score=combined,
                    cold_start_slot_reserved=agent.is_cold_start,
                    risk_notes=fit.rationales,
                )

        assignments = []
        if best_agent and best_ranking:
            # Determine role based on agent capabilities
            role = self._infer_agent_role(best_agent)
            assignments.append(
                RoleAssignment(
                    role=role,
                    agent=best_agent,
                    ranking=best_ranking,
                    is_required=True,
                )
            )

        return TeamSelection(
            requirement_id=requirement_id,
            assignments=assignments,
            collaboration_mode=CollaborationMode.SINGLE,
        )

    def _infer_agent_role(self, agent: AgentProfile) -> TeamRole:
        """Infer the most appropriate role for an agent based on capabilities.

        Args:
            agent: The agent to analyze.

        Returns:
            The most appropriate TeamRole.
        """
        skills = {s.lower() for s in agent.capabilities.skills}

        # Check each role's capabilities
        best_role = TeamRole.FULLSTACK_DEV
        best_overlap = 0

        for role, role_skills in ROLE_CAPABILITIES.items():
            overlap = len(skills & {s.lower() for s in role_skills})
            if overlap > best_overlap:
                best_overlap = overlap
                best_role = role

        return best_role


def suggest_agents_for_requirements(
    requirements: list[dict[str, str]],
    model_config_name: str | None = None,
    model: Any | None = None,
    existing_agents: Sequence[AgentProfile] | None = None,
) -> list[AgentSpec]:
    """Suggest agent specs for given requirements using LLM analysis.

    This is a standalone function that can be called without full team selection.
    It analyzes requirements and returns suggested agent specs that could be
    created to handle those requirements.

    Args:
        requirements (`list[dict[str, str]]`):
            List of requirement dicts with 'id', 'content', and optional 'skills' keys.
        model_config_name (`str | None`, optional):
            LLM model config name. If None, uses auto-detection.
        model (`Any | None`, optional):
            Pre-initialized model instance to use directly.
        existing_agents (`Sequence[AgentProfile] | None`, optional):
            Optional list of existing agent profiles for reference.

    Returns:
        `list[AgentSpec]`:
            List of AgentSpec suggestions from LLM analysis.

    Raises:
        ValueError: If requirements list is empty.
        RuntimeError: If LLM model initialization fails.
    """
    if not requirements:
        raise ValueError("Requirements list cannot be empty")

    selector = TeamSelector(model_config_name=model_config_name, model=model)

    # Ensure model is available
    model = selector._get_model()
    if model is None:
        raise RuntimeError(
            "LLM model not available. Please configure model_config_name or "
            "set up default model configuration."
        )

    all_specs: list[AgentSpec] = []
    candidates = list(existing_agents) if existing_agents else []

    for req in requirements:
        requirement = Requirement(
            skills=set(req.get("skills", [])),
            notes=req.get("content", ""),
        )

        # Call LLM analysis
        analysis = selector._analyze_with_prompt(
            requirement_id=str(req.get("id", "req-1")),
            requirement=requirement,
            candidates=candidates,
        )

        if analysis and analysis.new_agent_specs:
            all_specs.extend(analysis.new_agent_specs)

    # Deduplicate by role
    seen_roles: set[str] = set()
    unique_specs: list[AgentSpec] = []
    for spec in all_specs:
        if spec.role not in seen_roles:
            seen_roles.add(spec.role)
            unique_specs.append(spec)

    return unique_specs
