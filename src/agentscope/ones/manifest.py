# -*- coding: utf-8 -*-
"""Agent manifest data structures for modular agent deployment."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..aa._types import AgentCapabilities, AgentProfile, StaticScore


@dataclass
class MemoryConfig:
    """Configuration for agent memory system.

    Manages context (current conversation), short-term (session), and long-term (persistent) memory.
    """

    context_limit: int = 20  # Max messages in current conversation
    short_term_limit: int = 50  # Max items in short-term memory
    long_term_enabled: bool = False  # Enable persistent long-term memory
    long_term_store_type: str = "milvus_lite"  # Vector store type
    long_term_collection: str = ""  # Collection name for long-term storage

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "context_limit": self.context_limit,
            "short_term_limit": self.short_term_limit,
            "long_term_enabled": self.long_term_enabled,
            "long_term_store_type": self.long_term_store_type,
            "long_term_collection": self.long_term_collection,
        }


@dataclass
class TaskBoardConfig:
    """Configuration for agent task board.

    Tracks current task, subtasks, and task history.
    """

    max_history: int = 100  # Max completed tasks to keep
    track_subtasks: bool = True  # Enable subtask tracking
    auto_archive: bool = True  # Auto archive completed tasks

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_history": self.max_history,
            "track_subtasks": self.track_subtasks,
            "auto_archive": self.auto_archive,
        }


@dataclass
class KnowledgeBaseConfig:
    """Configuration for agent knowledge base (RAG).

    Supports file-based document loading with vector store backends.
    """

    name: str
    documents_dir: str = ""
    document_files: list[str] = field(default_factory=list)
    store_type: str = "milvus_lite"  # milvus_lite, qdrant
    collection_name: str = ""
    embedding_model: str = ""
    chunk_size: int = 512
    chunk_overlap: int = 50
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "documents_dir": self.documents_dir,
            "document_files": self.document_files,
            "store_type": self.store_type,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "metadata": self.metadata,
        }


@dataclass
class PromptConfig:
    """Configuration for agent prompts.

    Supports system prompt, role description, and prompt templates.
    """

    system_prompt: str = ""
    role_description: str = ""
    deliverable_expectation: str = ""
    collaboration_guidelines: list[str] = field(default_factory=list)
    prompt_template: str = ""
    variables: dict[str, str] = field(default_factory=dict)

    def build_system_prompt(self) -> str:
        """Build complete system prompt from components."""
        if self.system_prompt:
            return self.system_prompt

        if not self.role_description:
            return ""

        guidelines = "\n".join(f"- {item}" for item in self.collaboration_guidelines)
        prompt = f"角色: {self.role_description}\n"
        if self.deliverable_expectation:
            prompt += f"使命: {self.deliverable_expectation}\n"
        if guidelines:
            prompt += f"协作守则:\n{guidelines}\n"
        prompt += "当你需要更多信息时，要明确写出缺口并提出具体请求。"
        return prompt

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "system_prompt": self.system_prompt,
            "role_description": self.role_description,
            "deliverable_expectation": self.deliverable_expectation,
            "collaboration_guidelines": self.collaboration_guidelines,
            "prompt_template": self.prompt_template,
            "variables": self.variables,
        }


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server in the sandbox."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    optional: bool = False

    def to_runtime_config(self) -> dict[str, Any]:
        """Convert to agentscope-runtime format."""
        config: dict[str, Any] = {
            "command": self.command,
            "args": self.args,
        }
        if self.env:
            config["env"] = self.env
        return config


@dataclass
class AgentManifest:
    """Complete manifest describing an agent's capabilities and dependencies.

    This is the "move-in ready" package for an agent, containing:
    - Profile information for AA selection
    - MCP server dependencies to be initialized in sandbox
    - Built-in tool requirements
    - Factory path for instantiation
    - Prompt configuration (system prompt, role description)
    - Knowledge base configuration (RAG documents)
    """

    id: str
    name: str
    version: str = "1.0.0"

    # Profile for AA selection
    skills: set[str] = field(default_factory=set)
    tools: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=lambda: {"zh", "en"})

    # MCP dependencies (to be initialized in sandbox)
    mcp_servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    # Built-in tools from HiveToolkitManager
    builtin_tools: set[str] = field(default_factory=set)

    # Factory path for instantiation
    factory: str | None = None

    # Prompt configuration
    prompt_config: PromptConfig | None = None

    # Knowledge base configurations
    knowledge_configs: list[KnowledgeBaseConfig] = field(default_factory=list)

    # Memory configuration
    memory_config: MemoryConfig | None = None

    # Task board configuration
    task_board_config: TaskBoardConfig | None = None

    # Additional metadata
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # Source path (set when loaded from file)
    manifest_path: Path | None = None

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.

        Returns prompt from prompt_config if available, otherwise empty string.
        """
        if self.prompt_config:
            return self.prompt_config.build_system_prompt()
        return ""

    def get_knowledge_base_paths(self) -> list[Path]:
        """Get all document paths from knowledge configs.

        Returns list of resolved paths relative to manifest location.
        """
        paths: list[Path] = []
        base_dir = self.manifest_path.parent if self.manifest_path else Path.cwd()

        for kb_config in self.knowledge_configs:
            if kb_config.documents_dir:
                doc_dir = base_dir / kb_config.documents_dir
                if doc_dir.exists():
                    paths.append(doc_dir)

            for doc_file in kb_config.document_files:
                doc_path = base_dir / doc_file
                if doc_path.exists():
                    paths.append(doc_path)

        return paths

    def to_agent_profile(
        self,
        static_score: StaticScore | None = None,
    ) -> AgentProfile:
        """Convert manifest to AgentProfile for AA selection."""
        if static_score is None:
            static_score = StaticScore(
                performance=0.75,
                brand=0.70,
                recognition=0.70,
            )
        return AgentProfile(
            agent_id=self.id,
            name=self.name,
            static_score=static_score,
            capabilities=AgentCapabilities(
                skills=self.skills,
                tools=self.tools,
                domains=self.domains,
                languages=self.languages,
            ),
            metadata={
                "source": "manifest",
                "version": self.version,
                "manifest_path": str(self.manifest_path) if self.manifest_path else "",
                "has_prompt": bool(self.prompt_config),
                "knowledge_count": len(self.knowledge_configs),
            },
            is_cold_start=True,  # New agents start in cold start mode
        )

    def get_mcp_runtime_configs(self) -> dict[str, dict[str, Any]]:
        """Get MCP configs in agentscope-runtime format.

        Returns config wrapped in 'mcpServers' key as expected by runtime API.
        """
        servers = {
            name: config.to_runtime_config()
            for name, config in self.mcp_servers.items()
        }
        return {"mcpServers": servers} if servers else {}

    @classmethod
    def from_dict(cls, data: dict[str, Any], manifest_path: Path | None = None) -> "AgentManifest":
        """Create manifest from dictionary."""
        # Parse MCP servers
        mcp_servers: dict[str, MCPServerConfig] = {}
        for name, config in data.get("mcp_servers", {}).items():
            if isinstance(config, dict):
                mcp_servers[name] = MCPServerConfig(
                    name=name,
                    command=config.get("command", ""),
                    args=config.get("args", []),
                    env=config.get("env", {}),
                    optional=config.get("optional", False),
                )

        # Parse prompt config
        prompt_config: PromptConfig | None = None
        prompt_data = data.get("prompt_config") or data.get("prompt")
        if prompt_data and isinstance(prompt_data, dict):
            prompt_config = PromptConfig(
                system_prompt=prompt_data.get("system_prompt", ""),
                role_description=prompt_data.get("role_description", ""),
                deliverable_expectation=prompt_data.get("deliverable_expectation", ""),
                collaboration_guidelines=prompt_data.get("collaboration_guidelines", []),
                prompt_template=prompt_data.get("prompt_template", ""),
                variables=prompt_data.get("variables", {}),
            )

        # Parse knowledge configs
        knowledge_configs: list[KnowledgeBaseConfig] = []
        kb_data = data.get("knowledge_configs") or data.get("knowledge")
        if kb_data and isinstance(kb_data, list):
            for kb in kb_data:
                if isinstance(kb, dict):
                    knowledge_configs.append(
                        KnowledgeBaseConfig(
                            name=kb.get("name", "default"),
                            documents_dir=kb.get("documents_dir", ""),
                            document_files=kb.get("document_files", []),
                            store_type=kb.get("store_type", "milvus_lite"),
                            collection_name=kb.get("collection_name", ""),
                            embedding_model=kb.get("embedding_model", ""),
                            chunk_size=kb.get("chunk_size", 512),
                            chunk_overlap=kb.get("chunk_overlap", 50),
                            metadata=kb.get("metadata", {}),
                        )
                    )

        # Parse memory config
        memory_config: MemoryConfig | None = None
        mem_data = data.get("memory_config") or data.get("memory")
        if mem_data and isinstance(mem_data, dict):
            memory_config = MemoryConfig(
                context_limit=mem_data.get("context_limit", 20),
                short_term_limit=mem_data.get("short_term_limit", 50),
                long_term_enabled=mem_data.get("long_term_enabled", False),
                long_term_store_type=mem_data.get("long_term_store_type", "milvus_lite"),
                long_term_collection=mem_data.get("long_term_collection", ""),
            )

        # Parse task board config
        task_board_config: TaskBoardConfig | None = None
        tb_data = data.get("task_board_config") or data.get("task_board")
        if tb_data and isinstance(tb_data, dict):
            task_board_config = TaskBoardConfig(
                max_history=tb_data.get("max_history", 100),
                track_subtasks=tb_data.get("track_subtasks", True),
                auto_archive=tb_data.get("auto_archive", True),
            )

        # Parse profile section
        profile = data.get("profile", {})

        return cls(
            id=data.get("id", ""),
            name=data.get("name", data.get("id", "")),
            version=data.get("version", "1.0.0"),
            skills=set(profile.get("skills", data.get("skills", []))),
            tools=set(profile.get("tools", data.get("tools", []))),
            domains=set(profile.get("domains", data.get("domains", []))),
            languages=set(profile.get("languages", ["zh", "en"])),
            mcp_servers=mcp_servers,
            builtin_tools=set(data.get("builtin_tools", [])),
            factory=data.get("factory"),
            prompt_config=prompt_config,
            knowledge_configs=knowledge_configs,
            memory_config=memory_config,
            task_board_config=task_board_config,
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            manifest_path=manifest_path,
        )

    @classmethod
    def from_file(cls, path: Path | str) -> "AgentManifest":
        """Load manifest from JSON file."""
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, manifest_path=path)

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "profile": {
                "skills": list(self.skills),
                "tools": list(self.tools),
                "domains": list(self.domains),
                "languages": list(self.languages),
            },
            "mcp_servers": {
                name: {
                    "command": config.command,
                    "args": config.args,
                    "env": config.env,
                    "optional": config.optional,
                }
                for name, config in self.mcp_servers.items()
            },
            "builtin_tools": list(self.builtin_tools),
            "factory": self.factory,
            "description": self.description,
            "metadata": self.metadata,
        }

        # Add prompt config if present
        if self.prompt_config:
            result["prompt_config"] = self.prompt_config.to_dict()

        # Add knowledge configs if present
        if self.knowledge_configs:
            result["knowledge_configs"] = [kb.to_dict() for kb in self.knowledge_configs]

        # Add memory config if present
        if self.memory_config:
            result["memory_config"] = self.memory_config.to_dict()

        # Add task board config if present
        if self.task_board_config:
            result["task_board_config"] = self.task_board_config.to_dict()

        return result

    def save(self, path: Path | str) -> None:
        """Save manifest to JSON file."""
        path = Path(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


def load_manifests_from_directory(directory: Path | str) -> list[AgentManifest]:
    """Load all agent manifests from a directory.

    Searches for manifest.json files in subdirectories.

    Args:
        directory: Root directory to search.

    Returns:
        List of loaded AgentManifest objects.
    """
    directory = Path(directory)
    manifests: list[AgentManifest] = []

    if not directory.exists():
        return manifests

    for manifest_path in directory.rglob("manifest.json"):
        try:
            manifest = AgentManifest.from_file(manifest_path)
            manifests.append(manifest)
        except Exception as exc:
            from .._logging import logger
            logger.warning("Failed to load manifest %s: %s", manifest_path, exc)

    return manifests
