# -*- coding: utf-8 -*-
"""Modular Agent - A self-contained agent unit with memory, knowledge, tasks, prompts, and tools."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

import shortuuid

from ..agent import AgentBase
from ..message import Msg, TextBlock
from ..model import ChatModelBase
from ..tool import Toolkit, ToolResponse
from ..mcp import MCPClientBase


# =============================================================================
# AgentMemory: Context + Short-term + Long-term Memory
# =============================================================================

@dataclass
class MemoryItem:
    """A single memory item."""
    content: str
    role: str = "user"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0-1, for long-term memory filtering


class AgentMemory:
    """Agent's memory system with context, short-term, and long-term storage.

    - context: Current conversation messages (cleared each session)
    - short_term: Recent important items within session (limited size)
    - long_term: Persistent memories across sessions (optional)
    """

    def __init__(
        self,
        *,
        context_limit: int = 20,
        short_term_limit: int = 50,
        long_term_store: Any | None = None,
    ) -> None:
        self.context_limit = context_limit
        self.short_term_limit = short_term_limit
        self.long_term_store = long_term_store

        # Context: current conversation
        self._context: list[MemoryItem] = []
        # Short-term: important items from current session
        self._short_term: list[MemoryItem] = []
        # Long-term: persistent (delegated to store)
        self._long_term_cache: list[MemoryItem] = []

    def add_to_context(self, content: str, role: str = "user", **metadata: Any) -> None:
        """Add message to current conversation context."""
        item = MemoryItem(content=content, role=role, metadata=metadata)
        self._context.append(item)
        # Trim if exceeds limit
        if len(self._context) > self.context_limit:
            self._context = self._context[-self.context_limit:]

    def add_to_short_term(
        self, content: str, importance: float = 0.5, **metadata: Any
    ) -> None:
        """Add important item to short-term memory."""
        item = MemoryItem(
            content=content, role="memory", importance=importance, metadata=metadata
        )
        self._short_term.append(item)
        # Trim by importance if exceeds limit
        if len(self._short_term) > self.short_term_limit:
            self._short_term.sort(key=lambda x: x.importance, reverse=True)
            self._short_term = self._short_term[: self.short_term_limit]

    async def add_to_long_term(self, content: str, **metadata: Any) -> None:
        """Add to persistent long-term memory."""
        item = MemoryItem(content=content, role="long_term", metadata=metadata)
        self._long_term_cache.append(item)
        if self.long_term_store:
            # TODO: Integrate with vector store for persistence
            pass

    def get_context_messages(self) -> list[dict[str, str]]:
        """Get context as LLM-compatible messages."""
        return [{"role": item.role, "content": item.content} for item in self._context]

    def get_short_term_summary(self, limit: int = 5) -> str:
        """Get summary of recent short-term memories."""
        recent = sorted(self._short_term, key=lambda x: x.timestamp, reverse=True)[
            :limit
        ]
        if not recent:
            return ""
        lines = [f"- {item.content}" for item in recent]
        return "【会话记忆】\n" + "\n".join(lines)

    async def retrieve_long_term(self, query: str, limit: int = 3) -> str:
        """Retrieve relevant long-term memories."""
        # TODO: Vector similarity search
        if not self._long_term_cache:
            return ""
        # Simple keyword match for now
        matches = [
            item for item in self._long_term_cache if query.lower() in item.content.lower()
        ][:limit]
        if not matches:
            return ""
        lines = [f"- {item.content}" for item in matches]
        return "【长期记忆】\n" + "\n".join(lines)

    def clear_context(self) -> None:
        """Clear current conversation context."""
        self._context.clear()

    def clear_session(self) -> None:
        """Clear context and short-term memory (new session)."""
        self._context.clear()
        self._short_term.clear()


# =============================================================================
# AgentKnowledge: RAG Document Retrieval
# =============================================================================

@dataclass
class KnowledgeDocument:
    """A document in the knowledge base."""
    content: str
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


class AgentKnowledge:
    """Agent's knowledge base for RAG retrieval."""

    def __init__(
        self,
        *,
        documents: list[KnowledgeDocument] | None = None,
        vector_store: Any | None = None,
        embedding_model: Any | None = None,
    ) -> None:
        self._documents = documents or []
        self._vector_store = vector_store
        self._embedding_model = embedding_model

    def add_document(self, content: str, source: str = "", **metadata: Any) -> None:
        """Add a document to the knowledge base."""
        doc = KnowledgeDocument(content=content, source=source, metadata=metadata)
        self._documents.append(doc)

    async def retrieve(self, query: str, limit: int = 5) -> list[KnowledgeDocument]:
        """Retrieve relevant documents for the query."""
        if self._vector_store and self._embedding_model:
            # TODO: Vector similarity search
            pass

        # Simple keyword match fallback
        query_tokens = set(query.lower().split())
        scored: list[tuple[float, KnowledgeDocument]] = []
        for doc in self._documents:
            doc_tokens = set(doc.content.lower().split())
            overlap = len(query_tokens & doc_tokens)
            score = overlap / (len(query_tokens) + 1e-6)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:limit]]

    def get_context(self, docs: list[KnowledgeDocument]) -> str:
        """Format retrieved documents as context."""
        if not docs:
            return ""
        lines = []
        for i, doc in enumerate(docs, 1):
            source_info = f" ({doc.source})" if doc.source else ""
            lines.append(f"[{i}]{source_info} {doc.content}")
        return "【知识库】\n" + "\n".join(lines)

    @property
    def document_count(self) -> int:
        """Number of documents in knowledge base."""
        return len(self._documents)


# =============================================================================
# AgentTaskBoard: Task Tracking
# =============================================================================

@dataclass
class TaskItem:
    """A task item on the task board."""
    task_id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    result: str = ""
    subtasks: list["TaskItem"] = field(default_factory=list)


class AgentTaskBoard:
    """Agent's task board for tracking work."""

    def __init__(self, *, max_history: int = 100) -> None:
        self.max_history = max_history
        self._current_task: TaskItem | None = None
        self._task_history: list[TaskItem] = []

    def create_task(self, description: str) -> TaskItem:
        """Create a new task."""
        task = TaskItem(
            task_id=f"task-{shortuuid.uuid()[:8]}",
            description=description,
        )
        self._current_task = task
        return task

    def add_subtask(self, description: str) -> TaskItem | None:
        """Add a subtask to the current task."""
        if not self._current_task:
            return None
        subtask = TaskItem(
            task_id=f"subtask-{shortuuid.uuid()[:8]}",
            description=description,
        )
        self._current_task.subtasks.append(subtask)
        return subtask

    def update_status(
        self, status: str, result: str = "", task_id: str | None = None
    ) -> None:
        """Update task status."""
        task = self._find_task(task_id) if task_id else self._current_task
        if task:
            task.status = status
            if result:
                task.result = result
            if status in ("completed", "failed"):
                task.completed_at = datetime.now(timezone.utc)

    def complete_current(self, result: str = "") -> None:
        """Complete current task and archive it."""
        if self._current_task:
            self._current_task.status = "completed"
            self._current_task.result = result
            self._current_task.completed_at = datetime.now(timezone.utc)
            self._task_history.append(self._current_task)
            if len(self._task_history) > self.max_history:
                self._task_history = self._task_history[-self.max_history:]
            self._current_task = None

    def get_status_summary(self) -> str:
        """Get current task status summary."""
        if not self._current_task:
            return "【任务状态】无进行中的任务"

        task = self._current_task
        lines = [f"【当前任务】{task.description} ({task.status})"]
        if task.subtasks:
            for st in task.subtasks:
                status_icon = {"completed": "✓", "in_progress": "→", "failed": "✗"}.get(
                    st.status, "○"
                )
                lines.append(f"  {status_icon} {st.description}")
        return "\n".join(lines)

    def _find_task(self, task_id: str) -> TaskItem | None:
        """Find task by ID."""
        if self._current_task and self._current_task.task_id == task_id:
            return self._current_task
        for subtask in (self._current_task.subtasks if self._current_task else []):
            if subtask.task_id == task_id:
                return subtask
        return None

    @property
    def current_task(self) -> TaskItem | None:
        """Get current task."""
        return self._current_task


# =============================================================================
# AgentPrompt: Prompt Management
# =============================================================================

class AgentPrompt:
    """Agent's prompt configuration and builder."""

    def __init__(
        self,
        *,
        system_prompt: str = "",
        role_description: str = "",
        deliverable_expectation: str = "",
        collaboration_guidelines: list[str] | None = None,
        variables: dict[str, str] | None = None,
    ) -> None:
        self.system_prompt = system_prompt
        self.role_description = role_description
        self.deliverable_expectation = deliverable_expectation
        self.collaboration_guidelines = collaboration_guidelines or []
        self.variables = variables or {}

    def build_system_prompt(self) -> str:
        """Build complete system prompt."""
        if self.system_prompt:
            return self._apply_variables(self.system_prompt)

        if not self.role_description:
            return ""

        guidelines = "\n".join(f"- {g}" for g in self.collaboration_guidelines)
        prompt = f"角色: {self.role_description}\n"
        if self.deliverable_expectation:
            prompt += f"使命: {self.deliverable_expectation}\n"
        if guidelines:
            prompt += f"协作守则:\n{guidelines}\n"
        prompt += "当你需要更多信息时，要明确写出缺口并提出具体请求。"
        return self._apply_variables(prompt)

    def build_context_prompt(
        self,
        *,
        memory_context: str = "",
        knowledge_context: str = "",
        task_context: str = "",
        tool_context: str = "",
    ) -> str:
        """Build context section of prompt."""
        sections = []
        if memory_context:
            sections.append(memory_context)
        if knowledge_context:
            sections.append(knowledge_context)
        if task_context:
            sections.append(task_context)
        if tool_context:
            sections.append(f"【可用工具】\n{tool_context}")
        return "\n\n".join(sections)

    def _apply_variables(self, text: str) -> str:
        """Apply variable substitutions."""
        result = text
        for key, value in self.variables.items():
            result = result.replace(f"{{{key}}}", value)
        return result


# =============================================================================
# ModularAgent: The Complete Self-Contained Agent
# =============================================================================

class ModularAgent(AgentBase):
    """A modular, self-contained agent with memory, knowledge, tasks, prompts, and tools.

    This is the "拎包入住" (move-in ready) agent that encapsulates all components
    needed for autonomous operation.
    """

    def __init__(
        self,
        *,
        agent_id: str | None = None,
        name: str,
        # Core components
        memory: AgentMemory | None = None,
        knowledge: AgentKnowledge | None = None,
        task_board: AgentTaskBoard | None = None,
        prompt: AgentPrompt | None = None,
        toolkit: Toolkit | None = None,
        # Runtime
        llm: ChatModelBase | None = None,
        mcp_clients: Sequence[MCPClientBase] | None = None,
    ) -> None:
        super().__init__()
        self.id = agent_id or f"modular-{shortuuid.uuid()[:8]}"
        self.name = name

        # Initialize components with defaults
        self.memory = memory or AgentMemory()
        self.knowledge = knowledge or AgentKnowledge()
        self.task_board = task_board or AgentTaskBoard()
        self.prompt = prompt or AgentPrompt()
        self.toolkit = toolkit or Toolkit()
        self.llm = llm
        self._mcp_clients = list(mcp_clients or [])

        # Register MCP clients to toolkit
        self._mcp_registered = False

    async def _ensure_mcp_registered(self) -> None:
        """Ensure MCP clients are registered to toolkit."""
        if self._mcp_registered or not self._mcp_clients:
            return
        for client in self._mcp_clients:
            try:
                await self.toolkit.register_mcp_client(client)
            except Exception:
                pass
        self._mcp_registered = True

    async def observe(self, msg: Msg | Sequence[Msg] | None) -> None:
        """Observe and store messages in memory."""
        if msg is None:
            return
        messages = [msg] if isinstance(msg, Msg) else list(msg)
        for m in messages:
            content = m.get_text_content()
            self.memory.add_to_context(content, role=m.role)

    async def reply(self, msg: Msg | Sequence[Msg] | None = None, **kwargs: Any) -> Msg:
        """Generate a reply using all agent components."""
        if msg is not None:
            await self.observe(msg)

        await self._ensure_mcp_registered()

        # Get user query
        user_query = ""
        if msg:
            last_msg = msg[-1] if isinstance(msg, Sequence) else msg
            user_query = last_msg.get_text_content()

        # Build context from all components
        memory_ctx = self.memory.get_short_term_summary()
        long_term_ctx = await self.memory.retrieve_long_term(user_query)

        knowledge_docs = await self.knowledge.retrieve(user_query)
        knowledge_ctx = self.knowledge.get_context(knowledge_docs)

        task_ctx = self.task_board.get_status_summary()
        tool_ctx = self._get_tool_overview()

        # Build complete prompt
        system_prompt = self.prompt.build_system_prompt()
        context_prompt = self.prompt.build_context_prompt(
            memory_context="\n".join(filter(None, [memory_ctx, long_term_ctx])),
            knowledge_context=knowledge_ctx,
            task_context=task_ctx,
            tool_context=tool_ctx,
        )

        # Build messages for LLM
        messages = self.memory.get_context_messages()

        # Construct the final prompt
        final_prompt = f"{system_prompt}\n\n{context_prompt}" if context_prompt else system_prompt

        # Call LLM
        response_text = ""
        if self.llm:
            try:
                # Add system message at the beginning
                llm_messages = [{"role": "system", "content": final_prompt}] if final_prompt else []
                llm_messages.extend(messages)

                resp = await self.llm(llm_messages, stream=False)
                for block in resp.content:
                    if isinstance(block, dict):
                        response_text += block.get("text", "")
                    elif hasattr(block, "text"):
                        response_text += block.text
            except Exception as e:
                response_text = f"[Error] {e}"
        else:
            response_text = "[No LLM configured]"

        # Store response in memory
        self.memory.add_to_context(response_text, role="assistant")

        # Build response message
        response = Msg(
            name=self.name,
            role="assistant",
            content=[TextBlock(type="text", text=response_text)],
            metadata={"agent_id": self.id},
        )
        return response

    def _get_tool_overview(self) -> str:
        """Get overview of available tools."""
        if not self.toolkit or not getattr(self.toolkit, "tools", None):
            return ""
        lines = []
        for registered in self.toolkit.tools.values():
            schema = registered.json_schema.get("function", {})
            name = schema.get("name") or registered.name
            desc = schema.get("description") or ""
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    # Task management shortcuts
    def start_task(self, description: str) -> TaskItem:
        """Start a new task."""
        task = self.task_board.create_task(description)
        task.status = "in_progress"
        return task

    def complete_task(self, result: str = "") -> None:
        """Complete current task."""
        self.task_board.complete_current(result)

    # Memory shortcuts
    def remember(self, content: str, importance: float = 0.5) -> None:
        """Add to short-term memory."""
        self.memory.add_to_short_term(content, importance)

    async def remember_long_term(self, content: str) -> None:
        """Add to long-term memory."""
        await self.memory.add_to_long_term(content)

    def new_session(self) -> None:
        """Start a new session (clear context and short-term memory)."""
        self.memory.clear_session()

    # Knowledge shortcuts
    def add_knowledge(self, content: str, source: str = "") -> None:
        """Add document to knowledge base."""
        self.knowledge.add_document(content, source)


# =============================================================================
# Factory Functions
# =============================================================================

def create_modular_agent_from_manifest(
    manifest: "AgentManifest",
    *,
    llm: ChatModelBase | None = None,
    mcp_clients: Sequence[MCPClientBase] | None = None,
    toolkit: Toolkit | None = None,
) -> ModularAgent:
    """Create a ModularAgent from an AgentManifest.

    Args:
        manifest: The agent manifest configuration.
        llm: Optional LLM model for agent reasoning.
        mcp_clients: Optional MCP clients for tool access.
        toolkit: Optional pre-built toolkit.

    Returns:
        A fully configured ModularAgent instance.
    """
    from .manifest import AgentManifest  # Avoid circular import

    # Build memory from config
    memory_config = manifest.memory_config
    memory = AgentMemory(
        context_limit=memory_config.context_limit if memory_config else 20,
        short_term_limit=memory_config.short_term_limit if memory_config else 50,
        long_term_store=None,  # TODO: Initialize vector store if enabled
    )

    # Build knowledge base from config
    knowledge = AgentKnowledge()
    if manifest.knowledge_configs:
        base_dir = manifest.manifest_path.parent if manifest.manifest_path else None
        for kb_config in manifest.knowledge_configs:
            # Load documents from directory
            if kb_config.documents_dir and base_dir:
                doc_dir = base_dir / kb_config.documents_dir
                if doc_dir.exists():
                    for doc_path in doc_dir.rglob("*"):
                        if doc_path.is_file() and doc_path.suffix in (".md", ".txt", ".json"):
                            try:
                                content = doc_path.read_text(encoding="utf-8")
                                knowledge.add_document(content, source=str(doc_path.name))
                            except Exception:
                                pass

            # Load individual document files
            for doc_file in kb_config.document_files:
                if base_dir:
                    doc_path = base_dir / doc_file
                    if doc_path.exists():
                        try:
                            content = doc_path.read_text(encoding="utf-8")
                            knowledge.add_document(content, source=doc_file)
                        except Exception:
                            pass

    # Build task board from config
    tb_config = manifest.task_board_config
    task_board = AgentTaskBoard(
        max_history=tb_config.max_history if tb_config else 100,
    )

    # Build prompt from config
    prompt_config = manifest.prompt_config
    prompt = AgentPrompt(
        system_prompt=prompt_config.system_prompt if prompt_config else "",
        role_description=prompt_config.role_description if prompt_config else "",
        deliverable_expectation=prompt_config.deliverable_expectation if prompt_config else "",
        collaboration_guidelines=prompt_config.collaboration_guidelines if prompt_config else [],
        variables=prompt_config.variables if prompt_config else {},
    ) if prompt_config else AgentPrompt()

    # Build or use provided toolkit
    final_toolkit = toolkit or Toolkit()

    return ModularAgent(
        agent_id=manifest.id,
        name=manifest.name,
        memory=memory,
        knowledge=knowledge,
        task_board=task_board,
        prompt=prompt,
        toolkit=final_toolkit,
        llm=llm,
        mcp_clients=mcp_clients,
    )


def _build_knowledge_from_metaso(
    utterance: str,
    *,
    scope: str = "webpage",
    size: int = 5,
) -> AgentKnowledge:
    """Build AgentKnowledge from Metaso search results.

    Args:
        utterance: Search query (user utterance).
        scope: Search scope for metaso_search.
        size: Number of results to fetch.

    Returns:
        AgentKnowledge populated with search results.
    """
    from ..tool import metaso_search

    knowledge = AgentKnowledge()

    try:
        resp = metaso_search(
            utterance,
            scope=scope,
            size=size,
            include_summary=False,
            include_raw_content=False,
            concise_snippet=True,
        )
        # Extract documents from response
        hits = resp.metadata.get("hits", []) if resp.metadata else []
        for hit in hits:
            title = hit.get("title", "")
            snippet = hit.get("snippet", "") or hit.get("summary", "")
            url = hit.get("url", "")
            if snippet:
                content = f"{title}\n{snippet}" if title else snippet
                knowledge.add_document(content, source=url)

        # Also add main response content
        if resp.content:
            first_block = resp.content[0]
            main_text = first_block.text if hasattr(first_block, "text") else str(first_block)
            if main_text:
                knowledge.add_document(main_text, source="metaso_summary")

    except Exception as exc:
        # Log but don't fail - knowledge is optional
        from ..scripts._observability import get_logger
        get_logger().warn(f"[WARN] Metaso search failed: {exc}")

    return knowledge


def spawn_modular_agent(
    requirement: Any,
    utterance: str,
    *,
    llm: ChatModelBase | None = None,
    mcp_clients: Sequence[MCPClientBase] | None = None,
    toolkit: Toolkit | None = None,
    system_prompt: str | None = None,
    agent_name: str | None = None,
    use_metaso: bool = True,
    metaso_scope: str = "webpage",
    metaso_size: int = 5,
    with_file_tools: bool = False,
) -> tuple[Any, ModularAgent]:
    """Spawn a new ModularAgent based on requirements.

    This is the dynamic agent creation function that creates a fully
    self-contained agent with memory, knowledge, tasks, prompts, and tools.

    Args:
        requirement: Role requirement from AA selection.
        utterance: User utterance for context.
        llm: Optional LLM model.
        mcp_clients: Optional MCP clients.
        toolkit: Optional toolkit.
        system_prompt: Optional custom system prompt.
        agent_name: Optional agent name.
        use_metaso: Whether to use Metaso search to populate knowledge base.
        metaso_scope: Scope for Metaso search (webpage, academic, etc.).
        metaso_size: Number of Metaso search results.
        with_file_tools: Whether to add file operation tools (view/write/insert).

    Returns:
        Tuple of (AgentProfile, ModularAgent).
    """
    from ..aa import AgentProfile, AgentCapabilities, StaticScore

    # Generate agent ID and name
    agent_id = f"modular-{shortuuid.uuid()[:8]}"
    name = agent_name or "Modular Agent"

    # Extract capabilities from requirement
    skills = set(getattr(requirement, "skills", []))
    tools = set(getattr(requirement, "tools", []))
    domains = set(getattr(requirement, "domains", [])) or {"general"}
    languages = set(getattr(requirement, "languages", [])) or {"zh", "en"}

    # Build prompt
    if system_prompt:
        prompt = AgentPrompt(system_prompt=system_prompt)
    else:
        skills_str = ", ".join(skills) if skills else "通用技能"
        tools_str = ", ".join(tools) if tools else "基础工具"
        domains_str = ", ".join(domains) if domains else "通用领域"
        prompt = AgentPrompt(
            role_description=name,
            deliverable_expectation=f"专注于 {domains_str} 领域，运用 {skills_str} 技能",
            collaboration_guidelines=[
                "准确理解用户需求，提供专业解答",
                "合理使用可用工具完成任务",
                "遇到不确定时明确指出并提供建议",
            ],
        )

    # Build knowledge base from Metaso search
    if use_metaso and utterance:
        knowledge = _build_knowledge_from_metaso(
            utterance, scope=metaso_scope, size=metaso_size
        )
        from ..scripts._observability import get_logger
        get_logger().info(f"[INFO] Agent {name} 知识库已填充 {knowledge.document_count} 篇文档")
    else:
        knowledge = AgentKnowledge()

    # Build toolkit with file tools if requested
    final_toolkit = toolkit
    if final_toolkit is None and with_file_tools:
        try:
            from agentscope.scripts.hive_toolkit import HiveToolkitManager
            toolkit_manager = HiveToolkitManager(llm=llm)
            final_toolkit = toolkit_manager.build_toolkit(
                tools_filter={"view_text_file", "write_text_file", "insert_text_file"}
            )
            from ..scripts._observability import get_logger
            get_logger().info(f"[INFO] Agent {name} 已添加文件操作工具")
        except ImportError:
            final_toolkit = Toolkit()
    elif final_toolkit is None:
        final_toolkit = Toolkit()

    # Create agent
    agent = ModularAgent(
        agent_id=agent_id,
        name=name,
        memory=AgentMemory(),
        knowledge=knowledge,
        task_board=AgentTaskBoard(),
        prompt=prompt,
        toolkit=final_toolkit,
        llm=llm,
        mcp_clients=mcp_clients,
    )

    # Create profile
    profile = AgentProfile(
        agent_id=agent_id,
        name=name,
        static_score=StaticScore(
            performance=0.7,
            brand=0.5,
            recognition=0.5,
        ),
        capabilities=AgentCapabilities(
            skills=skills,
            tools=tools,
            domains=domains,
            languages=languages,
        ),
        is_cold_start=True,
        metadata={
            "source": "modular_agent_factory",
            "utterance": utterance,
            "knowledge_docs": knowledge.document_count,
        },
    )

    return profile, agent
