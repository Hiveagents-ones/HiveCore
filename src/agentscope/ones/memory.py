# -*- coding: utf-8 -*-
"""Memory, project, and resource pools (Section II.1)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class DecisionCategory(str, Enum):
    """Categories of project-level decisions."""

    TECH_STACK = "tech_stack"  # Technology choices (Vue, React, FastAPI, etc.)
    ARCHITECTURE = "architecture"  # Architecture patterns and decisions
    FILE_STRUCTURE = "file_structure"  # Directory and file organization
    API_DESIGN = "api_design"  # API endpoints and data models
    COMPONENT = "component"  # UI components and their responsibilities
    CONSTRAINT = "constraint"  # Important constraints or requirements
    DEPENDENCY = "dependency"  # Package dependencies
    TOOLING = "tooling"  # Development tools (linters, formatters, build tools)


@dataclass
class ProjectDecision:
    """Represents a project-level decision made by an agent."""

    category: DecisionCategory
    key: str  # e.g., "frontend_framework", "state_management"
    value: str  # e.g., "Vue 3", "Pinia"
    description: str  # Human-readable explanation
    made_by: str  # Agent ID that made this decision
    round_index: int  # Round when decision was made
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "made_by": self.made_by,
            "round_index": self.round_index,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectDecision":
        """Create from dictionary."""
        return cls(
            category=DecisionCategory(data["category"]),
            key=data["key"],
            value=data["value"],
            description=data["description"],
            made_by=data["made_by"],
            round_index=data["round_index"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class ProjectMemory:
    """Persistent project memory for cross-agent context sharing.

    This class maintains a record of important project-level decisions
    that all agents should be aware of. It ensures consistency across
    multiple rounds of code generation by:

    1. Recording technology choices (e.g., Vue 3 + Pinia + Element Plus)
    2. Tracking architecture decisions (e.g., API patterns, file structure)
    3. Persisting to disk for durability across sessions
    4. Providing formatted context for agent prompts

    Usage:
        # Initialize with project workspace
        memory = ProjectMemory(project_id="proj-123", workspace_dir="/workspace")

        # Record a decision
        memory.record_decision(
            category=DecisionCategory.TECH_STACK,
            key="frontend_framework",
            value="Vue 3",
            description="Using Vue 3 with Composition API",
            made_by="scaffold-agent",
            round_index=0,
        )

        # Get formatted context for agent prompt
        context = memory.get_context_for_prompt()
    """

    MEMORY_FILE_NAME = ".project_memory.json"

    def __init__(
        self,
        project_id: str,
        workspace_dir: str | Path | None = None,
    ) -> None:
        """Initialize project memory.

        Args:
            project_id: Unique project identifier.
            workspace_dir: Optional workspace directory for persistence.
        """
        self.project_id = project_id
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None
        self._decisions: dict[str, ProjectDecision] = {}
        self._file_registry: dict[str, str] = {}  # path -> description
        self._load()

    def _get_memory_path(self) -> Path | None:
        """Get path to memory file."""
        if self.workspace_dir:
            return self.workspace_dir / self.MEMORY_FILE_NAME
        return None

    def _load(self) -> None:
        """Load memory from disk if available."""
        path = self._get_memory_path()
        if path and path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                for key, dec_data in data.get("decisions", {}).items():
                    self._decisions[key] = ProjectDecision.from_dict(dec_data)
                self._file_registry = data.get("file_registry", {})
            except (json.JSONDecodeError, KeyError, ValueError):
                pass  # Start fresh if corrupted

    def _save(self) -> None:
        """Persist memory to disk."""
        path = self._get_memory_path()
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "project_id": self.project_id,
                "decisions": {k: v.to_dict() for k, v in self._decisions.items()},
                "file_registry": self._file_registry,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def record_decision(
        self,
        category: DecisionCategory,
        key: str,
        value: str,
        description: str,
        made_by: str,
        round_index: int,
    ) -> None:
        """Record a project-level decision.

        Args:
            category: Decision category (tech_stack, architecture, etc.).
            key: Decision key (e.g., "frontend_framework").
            value: Decision value (e.g., "Vue 3").
            description: Human-readable explanation.
            made_by: Agent ID that made this decision.
            round_index: Round when decision was made.
        """
        decision = ProjectDecision(
            category=category,
            key=key,
            value=value,
            description=description,
            made_by=made_by,
            round_index=round_index,
        )
        full_key = f"{category.value}:{key}"
        self._decisions[full_key] = decision
        self._save()

    def get_decision(
        self, category: DecisionCategory, key: str
    ) -> ProjectDecision | None:
        """Get a specific decision."""
        full_key = f"{category.value}:{key}"
        return self._decisions.get(full_key)

    def get_decisions_by_category(
        self, category: DecisionCategory
    ) -> list[ProjectDecision]:
        """Get all decisions in a category."""
        prefix = f"{category.value}:"
        return [d for k, d in self._decisions.items() if k.startswith(prefix)]

    def record_api_endpoint(
        self,
        path: str,
        methods: list[str],
        description: str,
        request_schema: str | None = None,
        response_schema: str | None = None,
    ) -> None:
        """Record an API endpoint definition.

        Args:
            path: API path (e.g., "/api/v1/members").
            methods: HTTP methods (e.g., ["GET", "POST"]).
            description: Endpoint description.
            request_schema: Request schema name.
            response_schema: Response schema name.
        """
        key = f"api:{path}"
        endpoint_data = {
            "path": path,
            "methods": methods,
            "description": description,
            "request_schema": request_schema,
            "response_schema": response_schema,
        }
        self.record_decision(
            category=DecisionCategory.API_DESIGN,
            key=key,
            value=", ".join(methods) + " " + path,
            description=description,
            made_by="architect",
            round_index=0,
        )
        # Also store full endpoint data
        if not hasattr(self, "_api_endpoints"):
            self._api_endpoints: dict[str, dict] = {}
        self._api_endpoints[path] = endpoint_data
        self._save()

    def record_data_model(
        self,
        name: str,
        fields: list[dict[str, str]],
        description: str = "",
    ) -> None:
        """Record a data model definition.

        Args:
            name: Model name (e.g., "Member").
            fields: List of field definitions.
            description: Model description.
        """
        field_names = [f.get("name", "") for f in fields]
        self.record_decision(
            category=DecisionCategory.API_DESIGN,
            key=f"model:{name}",
            value=name,
            description=f"Fields: {', '.join(field_names)}",
            made_by="architect",
            round_index=0,
        )

    def import_from_contract(self, contract: dict) -> None:
        """Import decisions from an architecture contract.

        This method extracts key information from an ArchitectAgent's
        contract and records it in project memory.

        Args:
            contract: Architecture contract dictionary.
        """
        # Record API endpoints
        for endpoint in contract.get("api_endpoints", []):
            self.record_api_endpoint(
                path=endpoint.get("path", ""),
                methods=endpoint.get("methods", ["GET"]),
                description=endpoint.get("description", ""),
                request_schema=endpoint.get("request_schema"),
                response_schema=endpoint.get("response_schema"),
            )

        # Record data models
        for model in contract.get("data_models", []):
            self.record_data_model(
                name=model.get("name", ""),
                fields=model.get("fields", []),
            )

        # Record file structure decisions
        file_struct = contract.get("file_structure", {})
        if file_struct.get("backend"):
            be = file_struct["backend"]
            self.record_decision(
                category=DecisionCategory.FILE_STRUCTURE,
                key="backend_app_entry",
                value=be.get("app_entry", "backend/app/main.py"),
                description="后端应用入口文件",
                made_by="architect",
                round_index=0,
            )
            self.record_decision(
                category=DecisionCategory.FILE_STRUCTURE,
                key="backend_routers_dir",
                value=be.get("routers_dir", "backend/app/routers"),
                description="后端路由目录",
                made_by="architect",
                round_index=0,
            )
        if file_struct.get("frontend"):
            fe = file_struct["frontend"]
            self.record_decision(
                category=DecisionCategory.FILE_STRUCTURE,
                key="frontend_views_dir",
                value=fe.get("views_dir", "frontend/src/views"),
                description="前端视图目录",
                made_by="architect",
                round_index=0,
            )
            self.record_decision(
                category=DecisionCategory.FILE_STRUCTURE,
                key="frontend_api_dir",
                value=fe.get("api_dir", "frontend/src/api"),
                description="前端API封装目录",
                made_by="architect",
                round_index=0,
            )

    def register_file(self, path: str, description: str) -> None:
        """Register a file in the project.

        Args:
            path: Relative file path from workspace root.
            description: Brief description of the file's purpose.
        """
        self._file_registry[path] = description
        self._save()

    def get_file_registry(self) -> dict[str, str]:
        """Get all registered files."""
        return dict(self._file_registry)

    def get_tech_stack_info(self) -> str:
        """Get formatted tech stack information for linter selection.

        Returns a string summarizing the project's technology choices,
        including frameworks, languages, and tooling decisions.

        Returns:
            Formatted string with tech stack info, or empty string if none.
        """
        lines: list[str] = []

        # Get tech stack decisions
        tech_stack = self.get_decisions_by_category(DecisionCategory.TECH_STACK)
        if tech_stack:
            lines.append("技术栈:")
            for d in tech_stack:
                lines.append(f"  - {d.key}: {d.value}")

        # Get tooling decisions
        tooling = self.get_decisions_by_category(DecisionCategory.TOOLING)
        if tooling:
            lines.append("开发工具:")
            for d in tooling:
                lines.append(f"  - {d.key}: {d.value}")

        # Get dependencies
        deps = self.get_decisions_by_category(DecisionCategory.DEPENDENCY)
        if deps:
            lines.append("依赖包:")
            for d in deps:
                lines.append(f"  - {d.key}: {d.value}")

        return "\n".join(lines)

    def get_all_dependencies(self) -> list[tuple[str, str]]:
        """Get all recorded dependencies as (package_name, version_spec) tuples.

        Returns:
            List of (package_name, version_spec) tuples.
            If no version is specified, returns 'latest'.

        Example:
            >>> memory.get_all_dependencies()
            [('pydantic', '>=2.0.0'), ('sqlalchemy', '>=2.0.0'), ('fastapi', 'latest')]
        """
        deps = self.get_decisions_by_category(DecisionCategory.DEPENDENCY)
        result: list[tuple[str, str]] = []
        for d in deps:
            package_name = d.key
            version_spec = d.value if d.value else "latest"
            result.append((package_name, version_spec))
        return result

    def get_pip_install_command(self) -> str | None:
        """Generate pip install command for all recorded dependencies.

        Returns:
            pip install command string, or None if no dependencies.

        Example:
            >>> memory.get_pip_install_command()
            'pip install pydantic>=2.0.0 sqlalchemy>=2.0.0 fastapi'
        """
        deps = self.get_all_dependencies()
        if not deps:
            return None

        packages: list[str] = []
        for name, version in deps:
            if version and version != "latest":
                # Handle version specifiers
                if version.startswith((">=", "<=", "==", "~=", "!=", "<", ">")):
                    packages.append(f"{name}{version}")
                else:
                    packages.append(f"{name}=={version}")
            else:
                packages.append(name)

        return f"pip install {' '.join(packages)}"

    def get_context_for_prompt(self, include_instructions: bool = True) -> str:
        """Generate formatted context for agent prompts.

        Args:
            include_instructions: Whether to include decision recording instructions.

        Returns:
            Markdown-formatted string with all project decisions and context.
        """
        lines = ["## 项目记忆 (Project Memory)", ""]

        # Check if there are existing decisions
        has_decisions = bool(self._decisions)

        if has_decisions:
            lines.append(
                "以下是本项目已确定的技术决策和约束，**请务必遵循这些决策**，"
                "不要引入冲突的技术栈或库。"
            )
            lines.append("")

            # Group by category
            categories = {
                DecisionCategory.TECH_STACK: "### 技术栈",
                DecisionCategory.ARCHITECTURE: "### 架构决策",
                DecisionCategory.API_DESIGN: "### API 设计",
                DecisionCategory.COMPONENT: "### 组件设计",
                DecisionCategory.DEPENDENCY: "### 依赖包",
                DecisionCategory.CONSTRAINT: "### 约束条件",
                DecisionCategory.FILE_STRUCTURE: "### 文件结构",
                DecisionCategory.TOOLING: "### 开发工具",
            }

            for cat, header in categories.items():
                decisions = self.get_decisions_by_category(cat)
                if decisions:
                    lines.append(header)
                    for d in decisions:
                        lines.append(f"- **{d.key}**: {d.value}")
                        if d.description:
                            lines.append(f"  - {d.description}")
                    lines.append("")

            # Add file registry summary if not too large
            if self._file_registry and len(self._file_registry) <= 30:
                lines.append("### 已创建的文件")
                for path, desc in sorted(self._file_registry.items()):
                    lines.append(f"- `{path}`: {desc}")
                lines.append("")
        else:
            lines.append(
                "这是一个新项目，尚未做出任何技术决策。"
            )
            lines.append("")

        # Add instructions for recording decisions
        if include_instructions:
            lines.append("### 重要提示：记录你的决策")
            lines.append("")
            lines.append(
                "当你做出重要的技术决策时（如选择框架、库、架构模式等），"
                "请在输出中明确标注，格式如下："
            )
            lines.append("")
            lines.append("```")
            lines.append("[决策记录]")
            lines.append("- 类型: tech_stack / architecture / api_design / tooling / constraint")
            lines.append("- 键: 决策名称（如 frontend_framework, linter）")
            lines.append("- 值: 决策内容（如 Vue 3, ESLint）")
            lines.append("- 说明: 选择原因")
            lines.append("```")
            lines.append("")
            lines.append(
                "这些决策会被记录到项目记忆中，供后续 Agent 参考。"
            )
            lines.append("")

        return "\n".join(lines)

    def parse_decisions_from_output(
        self,
        output: str,
        agent_id: str,
        round_index: int,
    ) -> list[ProjectDecision]:
        """Parse decision records from agent output and save them.

        Agents can include decision records in their output using a specific
        format. This method parses those records and saves them to memory.

        Args:
            output: Agent output text to parse.
            agent_id: ID of the agent that produced the output.
            round_index: Current round index.

        Returns:
            List of parsed decisions.
        """
        import re

        decisions: list[ProjectDecision] = []

        # Pattern to match decision records
        # Matches blocks like:
        # [决策记录]
        # - 类型: tech_stack
        # - 键: frontend_framework
        # - 值: Vue 3
        # - 说明: 使用 Vue 3 Composition API
        pattern = r"\[决策记录\]\s*\n((?:[-•]\s*(?:类型|键|值|说明)\s*[:：]\s*.+\n?)+)"
        matches = re.finditer(pattern, output, re.MULTILINE)

        for match in matches:
            block = match.group(1)

            # Extract fields
            category_match = re.search(r"类型\s*[:：]\s*(.+)", block)
            key_match = re.search(r"键\s*[:：]\s*(.+)", block)
            value_match = re.search(r"值\s*[:：]\s*(.+)", block)
            desc_match = re.search(r"说明\s*[:：]\s*(.+)", block)

            if category_match and key_match and value_match:
                category_str = category_match.group(1).strip().lower()
                key = key_match.group(1).strip()
                value = value_match.group(1).strip()
                description = desc_match.group(1).strip() if desc_match else ""

                # Map category string to enum
                category_map = {
                    "tech_stack": DecisionCategory.TECH_STACK,
                    "architecture": DecisionCategory.ARCHITECTURE,
                    "api_design": DecisionCategory.API_DESIGN,
                    "component": DecisionCategory.COMPONENT,
                    "dependency": DecisionCategory.DEPENDENCY,
                    "constraint": DecisionCategory.CONSTRAINT,
                    "file_structure": DecisionCategory.FILE_STRUCTURE,
                }

                category = category_map.get(category_str, DecisionCategory.ARCHITECTURE)

                self.record_decision(
                    category=category,
                    key=key,
                    value=value,
                    description=description,
                    made_by=agent_id,
                    round_index=round_index,
                )

                decisions.append(
                    ProjectDecision(
                        category=category,
                        key=key,
                        value=value,
                        description=description,
                        made_by=agent_id,
                        round_index=round_index,
                    )
                )

        return decisions

    def clear(self) -> None:
        """Clear all memory (for testing)."""
        self._decisions.clear()
        self._file_registry.clear()
        path = self._get_memory_path()
        if path and path.exists():
            path.unlink()


@dataclass
class ProjectDescriptor:
    project_id: str
    name: str
    status: str = "draft"
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectPool:
    """Registry that groups all project contexts."""

    def __init__(self) -> None:
        self._projects: dict[str, ProjectDescriptor] = {}

    def register(self, descriptor: ProjectDescriptor) -> None:
        self._projects[descriptor.project_id] = descriptor

    def get(self, project_id: str) -> ProjectDescriptor | None:
        return self._projects.get(project_id)

    def update_status(self, project_id: str, status: str) -> None:
        if project_id in self._projects:
            self._projects[project_id].status = status

    def list_projects(self) -> list[ProjectDescriptor]:
        return list(self._projects.values())


@dataclass
class MemoryEntry:
    """Captures prompts, tasks, agent descriptors, etc."""

    key: str
    content: str
    tags: set[str] = field(default_factory=set)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryPool:
    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}

    def save(self, entry: MemoryEntry) -> None:
        entry.updated_at = datetime.now(timezone.utc)
        self._store[entry.key] = entry

    def load(self, key: str) -> MemoryEntry | None:
        return self._store.get(key)

    def query_by_tag(self, tag: str) -> list[MemoryEntry]:
        return [entry for entry in self._store.values() if tag in entry.tags]


@dataclass
class ResourceHandle:
    identifier: str
    type: str
    uri: str
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)


class ResourceLibrary:
    """Tracks available MCP endpoints, tools, docs, etc."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceHandle] = {}

    def register(self, resource: ResourceHandle) -> None:
        self._resources[resource.identifier] = resource

    def remove(self, resource_id: str) -> None:
        self._resources.pop(resource_id, None)

    def get(self, resource_id: str) -> ResourceHandle | None:
        return self._resources.get(resource_id)

    def search(self, *, tags: Iterable[str] | None = None, type_: str | None = None) -> list[ResourceHandle]:
        tags = set(tags or [])
        results: list[ResourceHandle] = []
        for handle in self._resources.values():
            if type_ and handle.type != type_:
                continue
            if tags and not tags.issubset(handle.tags):
                continue
            results.append(handle)
        return results
