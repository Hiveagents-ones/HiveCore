# -*- coding: utf-8 -*-
"""Modular Agent - A self-contained agent unit with memory, knowledge, tasks, prompts, and tools."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

import shortuuid

logger = logging.getLogger(__name__)

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "importance": self.importance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryItem":
        """Deserialize from dictionary."""
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.now(timezone.utc)
        return cls(
            content=data.get("content", ""),
            role=data.get("role", "user"),
            timestamp=ts,
            metadata=data.get("metadata", {}),
            importance=data.get("importance", 0.5),
        )


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

    @property
    def context(self) -> list[MemoryItem]:
        """Get current conversation context (read-only)."""
        return list(self._context)

    @property
    def short_term(self) -> list[MemoryItem]:
        """Get short-term memories (read-only)."""
        return list(self._short_term)

    @property
    def long_term(self) -> list[MemoryItem]:
        """Get long-term memory cache (read-only)."""
        return list(self._long_term_cache)

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize memory to dictionary.

        Only persists long_term memories (cross-session value).
        context and short_term are session-level and not saved.
        """
        return {
            "context_limit": self.context_limit,
            "short_term_limit": self.short_term_limit,
            # Only persist long_term - context/short_term are session-level
            "long_term": [item.to_dict() for item in self._long_term_cache],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMemory":
        """Deserialize memory from dictionary.

        Only loads long_term memories. context/short_term start fresh.
        """
        memory = cls(
            context_limit=data.get("context_limit", 20),
            short_term_limit=data.get("short_term_limit", 50),
        )
        # Only load long_term - context/short_term start fresh each session
        memory._long_term_cache = [
            MemoryItem.from_dict(item) for item in data.get("long_term", [])
        ]
        return memory


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "source": self.source,
            "metadata": self.metadata,
            # Skip embedding for now (too large)
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeDocument":
        """Deserialize from dictionary."""
        return cls(
            content=data.get("content", ""),
            source=data.get("source", ""),
            metadata=data.get("metadata", {}),
        )


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

    @property
    def documents(self) -> list[KnowledgeDocument]:
        """Get all documents (read-only)."""
        return list(self._documents)

    def to_dict(self) -> dict[str, Any]:
        """Serialize knowledge base to dictionary."""
        return {
            "documents": [doc.to_dict() for doc in self._documents],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentKnowledge":
        """Deserialize knowledge base from dictionary."""
        docs = [
            KnowledgeDocument.from_dict(doc)
            for doc in data.get("documents", [])
        ]
        return cls(documents=docs)


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "subtasks": [st.to_dict() for st in self.subtasks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskItem":
        """Deserialize from dictionary."""
        created = data.get("created_at")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)

        completed = data.get("completed_at")
        if isinstance(completed, str):
            completed = datetime.fromisoformat(completed)

        return cls(
            task_id=data.get("task_id", ""),
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            created_at=created,
            completed_at=completed,
            result=data.get("result", ""),
            subtasks=[cls.from_dict(st) for st in data.get("subtasks", [])],
        )


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize task board to dictionary.

        Only persists current_task (unfinished work).
        task_history is just logs and not saved.
        """
        return {
            "max_history": self.max_history,
            # Only persist current task - history is just logs
            "current_task": self._current_task.to_dict() if self._current_task else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTaskBoard":
        """Deserialize task board from dictionary.

        Only loads current_task. task_history starts fresh.
        """
        board = cls(max_history=data.get("max_history", 100))
        current = data.get("current_task")
        if current:
            board._current_task = TaskItem.from_dict(current)
        # task_history starts fresh each session
        return board


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

    def build_system_prompt(self, *, tool_context: str = "") -> str:
        """Build complete system prompt with tool usage instructions.

        Args:
            tool_context: Overview of available tools (from _get_tool_overview).

        Returns:
            Complete system prompt with role, mission, and tool instructions.
        """
        if self.system_prompt:
            base_prompt = self._apply_variables(self.system_prompt)
        elif self.role_description:
            guidelines = "\n".join(f"- {g}" for g in self.collaboration_guidelines)
            base_prompt = f"角色: {self.role_description}\n"
            if self.deliverable_expectation:
                base_prompt += f"使命: {self.deliverable_expectation}\n"
            if guidelines:
                base_prompt += f"协作守则:\n{guidelines}\n"
            base_prompt += "当你需要更多信息时，要明确写出缺口并提出具体请求。"
            base_prompt = self._apply_variables(base_prompt)
        else:
            base_prompt = ""

        # Add tool usage instructions if tools are available
        if tool_context:
            tool_instructions = f"""

## 工具使用指南

你有以下工具可用，**必须通过 tool_use 调用工具**来完成任务：

{tool_context}

### 重要规则
1. **禁止直接输出代码块**：不要在回复中写 ```code``` 代码块，而是调用相应工具执行
2. **优先使用工具**：当需要编辑文件、执行命令、搜索内容时，必须调用工具
3. **工具调用格式**：使用 tool_use 块调用工具，不要用 markdown 代码块描述操作
4. **一次一个工具**：每次回复只调用一个工具，等待结果后再决定下一步

### 正确示例
- 需要创建文件时 → 调用 claude_code_edit 工具
- 需要查看文件时 → 调用 claude_code_edit 工具（使用 Read 操作）
- 需要执行命令时 → 调用 claude_code_edit 工具（使用 Bash 操作）

### 错误示例（禁止）
- ❌ 直接输出 ```python ... ``` 代码块让用户复制
- ❌ 说"请运行以下命令"然后输出命令文本
- ❌ 描述应该做什么但不实际调用工具"""
            return base_prompt + tool_instructions

        return base_prompt

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize prompt configuration to dictionary."""
        return {
            "system_prompt": self.system_prompt,
            "role_description": self.role_description,
            "deliverable_expectation": self.deliverable_expectation,
            "collaboration_guidelines": self.collaboration_guidelines,
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentPrompt":
        """Deserialize prompt configuration from dictionary."""
        return cls(
            system_prompt=data.get("system_prompt", ""),
            role_description=data.get("role_description", ""),
            deliverable_expectation=data.get("deliverable_expectation", ""),
            collaboration_guidelines=data.get("collaboration_guidelines", []),
            variables=data.get("variables", {}),
        )


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
        """Generate a reply using all agent components with tool calling support.

        This method implements a ReAct-style loop:
        1. Call LLM with available tools
        2. If LLM returns tool calls, execute them
        3. Feed results back to LLM
        4. Repeat until LLM returns a final text response
        """
        import time as _time

        # Get observer for ReAct loop visibility
        try:
            from agentscope.scripts._observability import get_agent_react_observer
            observer = get_agent_react_observer()
        except ImportError:
            observer = None

        if msg is not None:
            await self.observe(msg)

        await self._ensure_mcp_registered()

        # Get user query and task_id
        user_query = ""
        if msg:
            last_msg = msg[-1] if isinstance(msg, Sequence) else msg
            user_query = last_msg.get_text_content()

        task_id = kwargs.get("task_id", "unknown")

        # Notify observer: ReAct loop starting
        if observer:
            observer.on_react_start(self.id, task_id, user_query)

        # Build context from all components
        memory_ctx = self.memory.get_short_term_summary()
        long_term_ctx = await self.memory.retrieve_long_term(user_query)

        knowledge_docs = await self.knowledge.retrieve(user_query)
        knowledge_ctx = self.knowledge.get_context(knowledge_docs)

        task_ctx = self.task_board.get_status_summary()
        tool_ctx = self._get_tool_overview()

        # Build complete prompt with tool instructions in system prompt
        system_prompt = self.prompt.build_system_prompt(tool_context=tool_ctx)
        context_prompt = self.prompt.build_context_prompt(
            memory_context="\n".join(filter(None, [memory_ctx, long_term_ctx])),
            knowledge_context=knowledge_ctx,
            task_context=task_ctx,
            # tool_context is now in system_prompt, no need to duplicate here
        )

        # Build messages for LLM
        messages = self.memory.get_context_messages()

        # Construct the final prompt
        final_prompt = f"{system_prompt}\n\n{context_prompt}" if context_prompt else system_prompt

        # Get tool schemas if toolkit is available
        tool_schemas = None
        if self.toolkit and hasattr(self.toolkit, "get_json_schemas"):
            tool_schemas = self.toolkit.get_json_schemas()

        # ReAct loop with tool calling
        max_iters = kwargs.get("max_iters", 10)
        response_text = ""
        iterations_used = 0
        success = True

        # Set current task board for TaskBoard tools
        from ..tool import set_current_task_board
        set_current_task_board(self.task_board)

        # Set current agent ID for Claude Code observability
        try:
            from ..scripts._claude_code import set_current_agent_id
            set_current_agent_id(self.id)
        except ImportError:
            pass

        if self.llm:
            try:
                # Add system message at the beginning
                # For Anthropic-compatible APIs (like Zhipu), convert system to user
                from ..model import AnthropicChatModel
                is_anthropic = isinstance(self.llm, AnthropicChatModel)

                if is_anthropic:
                    # Zhipu Anthropic API doesn't accept role='system' in messages
                    # Convert to user message with system instruction prefix
                    llm_messages = [{"role": "user", "content": f"[System Instruction]\n{final_prompt}"}] if final_prompt else []
                    # Also convert any system messages in the context to user
                    for m in messages:
                        if m.get("role") == "system":
                            llm_messages.append({"role": "user", "content": f"[System]\n{m.get('content', '')}"})
                        else:
                            llm_messages.append(m)
                else:
                    llm_messages = [{"role": "system", "content": final_prompt}] if final_prompt else []
                    llm_messages.extend(messages)

                for iteration in range(max_iters):
                    iterations_used = iteration + 1

                    # Notify observer: iteration starting
                    if observer:
                        observer.on_iteration(self.id, iterations_used, max_iters)

                    # Call LLM with tools
                    # Use tool_choice="auto" to encourage tool usage
                    # Some models (like Qwen) may still not generate tool_calls
                    resp = await self.llm(
                        llm_messages,
                        stream=False,
                        tools=tool_schemas,
                        tool_choice="auto" if tool_schemas else None,
                    )

                    # Check if response contains tool calls
                    has_tool_calls = False
                    tool_call_blocks = []
                    text_content = ""

                    for block in resp.content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_use":
                                has_tool_calls = True
                                tool_call_blocks.append(block)
                            elif block.get("type") == "text":
                                text_content += block.get("text", "")
                        elif hasattr(block, "type"):
                            if block.type == "tool_use":
                                has_tool_calls = True
                                tool_call_blocks.append(block)
                            elif block.type == "text":
                                text_content += getattr(block, "text", "")

                    # Notify observer: agent thinking (if text content)
                    if observer and text_content:
                        observer.on_thinking(self.id, text_content)

                    if not has_tool_calls:
                        # No tool calls - check if LLM output code blocks without using tools
                        if self._should_fallback_to_claude_code(text_content):
                            # [CHANGED] 不再自动回退，而是打回让 LLM 重新生成
                            if observer:
                                observer.on_fallback(
                                    self.id,
                                    "LLM 未使用工具",
                                    "打回重新生成"
                                )
                            logger.warning(
                                "[ModularAgent] LLM 输出了代码块但未调用工具，打回重新生成"
                            )

                            # 将当前响应加入历史
                            llm_messages.append({
                                "role": "assistant",
                                "content": text_content,
                            })

                            # 添加提醒消息，要求 LLM 使用工具
                            reminder = """【系统提醒】你刚才直接输出了代码块，但没有调用工具。

**重要规则：**
1. 禁止直接输出 ```code``` 代码块
2. 必须通过 tool_use 调用 claude_code_edit 工具来创建/修改文件
3. 工具调用格式示例：调用 claude_code_edit 工具，传入 prompt 参数描述要执行的操作

请重新生成你的回复，这次必须使用 claude_code_edit 工具来执行代码操作。"""

                            llm_messages.append({
                                "role": "user",
                                "content": reminder,
                            })

                            # 继续循环，让 LLM 重新生成
                            continue

                        # No code blocks, this is a normal text response - done
                        response_text = text_content
                        break

                    # Execute tool calls and collect results
                    # Check if LLM supports native tool_use format in assistant messages
                    _supports_tool_use = True
                    if self.llm:
                        _model_name = getattr(self.llm, "model", "") or ""
                        _config_name = getattr(self.llm, "config_name", "") or ""
                        if "siliconflow" in _config_name.lower() or "silicon" in _model_name.lower():
                            _supports_tool_use = False
                        elif hasattr(self.llm, "_base_url"):
                            _base_url = str(getattr(self.llm, "_base_url", ""))
                            if "siliconflow" in _base_url.lower():
                                _supports_tool_use = False

                    if _supports_tool_use:
                        llm_messages.append({
                            "role": "assistant",
                            "content": list(resp.content),
                        })
                    else:
                        # Convert assistant message to text format for compatibility
                        # Include both text content and tool call descriptions
                        assistant_parts = []
                        if text_content:
                            assistant_parts.append(text_content)
                        for tc in tool_call_blocks:
                            tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                            tc_input = tc.get("input") if isinstance(tc, dict) else getattr(tc, "input", {})
                            assistant_parts.append(f"[调用工具: {tc_name}]\n参数: {tc_input}")
                        llm_messages.append({
                            "role": "assistant",
                            "content": "\n\n".join(assistant_parts) if assistant_parts else "[Calling tools...]",
                        })

                    tool_results = []
                    for tool_call in tool_call_blocks:
                        tool_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
                        tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                        tool_input = tool_call.get("input") if isinstance(tool_call, dict) else getattr(tool_call, "input", {})

                        # Notify observer: tool call starting
                        if observer:
                            observer.on_tool_call_start(self.id, tool_name, tool_input)

                        tool_start = _time.perf_counter()
                        try:
                            # Execute the tool
                            result = await self.toolkit.call_tool_function({
                                "id": tool_id,
                                "name": tool_name,
                                "input": tool_input,
                            })
                            # Collect result content
                            result_text = ""
                            async for chunk in result:
                                if hasattr(chunk, "content"):
                                    for content_block in chunk.content:
                                        if isinstance(content_block, dict):
                                            result_text += content_block.get("text", "")
                                        elif hasattr(content_block, "text"):
                                            result_text += content_block.text

                            tool_duration = _time.perf_counter() - tool_start

                            # Notify observer: tool call succeeded
                            if observer:
                                observer.on_tool_call_end(
                                    self.id, tool_name,
                                    result_text or "[成功]",
                                    success=True,
                                    duration=tool_duration
                                )

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result_text or "[Tool executed successfully]",
                            })
                        except Exception as e:
                            tool_duration = _time.perf_counter() - tool_start

                            # Notify observer: tool call failed
                            if observer:
                                observer.on_tool_call_end(
                                    self.id, tool_name,
                                    str(e),
                                    success=False,
                                    duration=tool_duration
                                )

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"[Tool error: {e}]",
                                "is_error": True,
                            })

                    # Add tool results to messages
                    # Check if LLM supports native tool_result format
                    # SiliconFlow and some other providers only support text/image_url
                    supports_tool_result = True
                    if self.llm:
                        model_name = getattr(self.llm, "model", "") or ""
                        config_name = getattr(self.llm, "config_name", "") or ""
                        # SiliconFlow models don't support tool_result format
                        if "siliconflow" in config_name.lower() or "silicon" in model_name.lower():
                            supports_tool_result = False
                        # Check for other incompatible providers
                        elif hasattr(self.llm, "_base_url"):
                            base_url = str(getattr(self.llm, "_base_url", ""))
                            if "siliconflow" in base_url.lower():
                                supports_tool_result = False

                    if supports_tool_result:
                        llm_messages.append({
                            "role": "user",
                            "content": tool_results,
                        })
                    else:
                        # Convert tool_results to plain text format for compatibility
                        results_text = []
                        for tr in tool_results:
                            tool_id = tr.get("tool_use_id", "unknown")
                            content = tr.get("content", "")
                            is_error = tr.get("is_error", False)
                            prefix = "❌ 工具错误" if is_error else "✅ 工具结果"
                            results_text.append(f"{prefix} [{tool_id}]:\n{content}")
                        llm_messages.append({
                            "role": "user",
                            "content": "\n\n".join(results_text),
                        })

                    # Notify observer: task board update (if applicable)
                    if observer and hasattr(self.task_board, "get_all_tasks"):
                        tasks = self.task_board.get_all_tasks()
                        if tasks:
                            observer.on_task_board_update(self.id, tasks)

                else:
                    # Loop completed without break (max iterations reached)
                    if not response_text:
                        response_text = "[Max iterations reached without final response]"
                        success = False

            except Exception as e:
                response_text = f"[Error] {e}"
                success = False
                if observer:
                    observer.on_error(self.id, e, "ReAct loop")
        else:
            response_text = "[No LLM configured]"
            success = False

        # Store response in memory
        self.memory.add_to_context(response_text, role="assistant")

        # Clear current task board after reply complete
        set_current_task_board(None)

        # Clear current agent ID after reply complete
        try:
            from ..scripts._claude_code import set_current_agent_id
            set_current_agent_id(None)
        except ImportError:
            pass

        # Notify observer: ReAct loop complete
        if observer:
            observer.on_react_complete(
                self.id, task_id, success, response_text, iterations_used
            )

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

    def _should_fallback_to_claude_code(self, text_content: str) -> bool:
        """Check if we should fallback to claude_code_edit for code execution.

        This is triggered when the LLM returns text with code blocks but no tool_use.
        Some models (like SiliconFlow/Qwen) don't support tool calling.

        Args:
            text_content: The text response from LLM.

        Returns:
            True if fallback should be triggered.
        """
        # Check if text contains code blocks
        has_code_blocks = bool(re.search(r"```\w*\n", text_content))
        if not has_code_blocks:
            return False

        # Check if toolkit has claude_code_edit tool
        if not self.toolkit or not getattr(self.toolkit, "tools", None):
            return False

        has_claude_code = any(
            "claude_code" in name.lower()
            for name in self.toolkit.tools.keys()
        )
        return has_claude_code

    async def _fallback_claude_code_edit(
        self, user_query: str, llm_response: str
    ) -> str | None:
        """Execute fallback to claude_code_edit when LLM doesn't generate tool calls.

        This method extracts the LLM's response and forwards it to claude_code_edit
        for actual code execution.

        Args:
            user_query: The original user query.
            llm_response: The LLM's text response containing code blocks.

        Returns:
            The result from claude_code_edit, or None if fallback failed.
        """
        try:
            # Import claude_code_edit
            from agentscope.scripts._claude_code import claude_code_edit

            # Build a comprehensive prompt that includes both the original task
            # and the LLM's suggested implementation
            fallback_prompt = f"""请根据以下内容创建代码文件：

## 原始任务
{user_query}

## LLM 建议的实现方案
{llm_response}

请根据上述建议，创建所需的代码文件。确保：
1. 文件路径正确
2. 代码完整可运行
3. 按照建议的目录结构创建文件

## 验证要求（重要）
完成代码编写后，你**必须**主动验证代码的正确性：
1. 运行适当的命令验证代码可以被正确加载/编译（如导入测试、构建命令等）
2. 如果项目有测试框架，运行相关测试
3. 如果验证失败，立即修复问题后再次验证
4. 只有验证通过后才算任务完成

验证方式由你根据项目类型自行决定，确保代码可以正常运行。"""

            logger.info("[ModularAgent] 🖥️ Fallback: 调用 claude_code_edit 执行代码生成")
            logger.info("[ModularAgent]   任务摘要: %s...", user_query[:100] if len(user_query) > 100 else user_query)

            # Call claude_code_edit
            result = await claude_code_edit(prompt=fallback_prompt)

            # Extract result text
            result_text = ""
            if result and result.content:
                for block in result.content:
                    if hasattr(block, "text"):
                        result_text += block.text
                    elif isinstance(block, dict) and "text" in block:
                        result_text += block["text"]

            if result_text:
                # Log FULL result for transparency
                logger.info("[ModularAgent] ✓ Fallback 成功完成")
                # Show result preview (first 500 chars)
                result_preview = result_text[:500] if len(result_text) > 500 else result_text
                logger.info("[ModularAgent]   结果预览: %s%s",
                    result_preview,
                    "..." if len(result_text) > 500 else ""
                )
                return f"[通过 Claude Code 执行] {result_text}"
            else:
                logger.warning("[ModularAgent] ⚠ Fallback 返回空结果")
                return None

        except ImportError:
            logger.warning("[ModularAgent] claude_code_edit 不可用，跳过 fallback")
            return None
        except Exception as e:
            logger.error("[ModularAgent] Fallback 执行失败: %s", e)
            return None

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

    # =========================================================================
    # Persistence: Save and Load
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent state to dictionary.

        Persistence strategy (only cross-session valuable data):
        - memory: Only long_term (context/short_term are session-level)
        - knowledge: All documents (RAG corpus is core asset)
        - task_board: Only current_task (history is just logs)
        - prompt: Full config (Agent's identity and behavior)
        - toolkit/llm: Runtime configs, not persisted
        """
        return {
            "agent_id": self.id,
            "name": self.name,
            "memory": self.memory.to_dict(),
            "knowledge": self.knowledge.to_dict(),
            "task_board": self.task_board.to_dict(),
            "prompt": self.prompt.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        llm: ChatModelBase | None = None,
        mcp_clients: Sequence[MCPClientBase] | None = None,
        toolkit: Toolkit | None = None,
    ) -> "ModularAgent":
        """Deserialize agent state from dictionary.

        Args:
            data: Serialized agent state.
            llm: Optional LLM model (runtime config).
            mcp_clients: Optional MCP clients (runtime config).
            toolkit: Optional toolkit (runtime config).

        Returns:
            Restored ModularAgent instance.
        """
        return cls(
            agent_id=data.get("agent_id"),
            name=data.get("name", "Agent"),
            memory=AgentMemory.from_dict(data.get("memory", {})),
            knowledge=AgentKnowledge.from_dict(data.get("knowledge", {})),
            task_board=AgentTaskBoard.from_dict(data.get("task_board", {})),
            prompt=AgentPrompt.from_dict(data.get("prompt", {})),
            toolkit=toolkit,
            llm=llm,
            mcp_clients=mcp_clients,
        )

    def save(self, path: str | "Path") -> None:
        """Save agent state to a JSON file.

        Args:
            path: Path to save the agent state file.
        """
        import json
        from pathlib import Path as PathLib

        path = PathLib(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"Agent {self.name} saved to {path}")

    @classmethod
    def load(
        cls,
        path: str | "Path",
        *,
        llm: ChatModelBase | None = None,
        mcp_clients: Sequence[MCPClientBase] | None = None,
        toolkit: Toolkit | None = None,
    ) -> "ModularAgent":
        """Load agent state from a JSON file.

        Args:
            path: Path to the agent state file.
            llm: Optional LLM model (runtime config).
            mcp_clients: Optional MCP clients (runtime config).
            toolkit: Optional toolkit (runtime config).

        Returns:
            Restored ModularAgent instance.
        """
        import json
        from pathlib import Path as PathLib

        path = PathLib(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        agent = cls.from_dict(data, llm=llm, mcp_clients=mcp_clients, toolkit=toolkit)
        logger.info(f"Agent {agent.name} loaded from {path}")
        return agent


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
            include_summary=True,  # Include summary for richer content
            include_raw_content=False,
            concise_snippet=False,  # Get full snippet, not concise
        )
        # Extract documents from response
        hits = resp.metadata.get("hits", []) if resp.metadata else []
        for hit in hits:
            title = hit.get("title", "")
            snippet = hit.get("snippet", "") or hit.get("summary", "")
            url = hit.get("url", "")
            # Add document even if only title is available
            if snippet or title:
                content = f"{title}\n{snippet}" if title and snippet else (title or snippet)
                knowledge.add_document(content, source=url)

        # Also add main response content as summary
        if resp.content:
            first_block = resp.content[0]
            main_text = first_block.text if hasattr(first_block, "text") else str(first_block)
            if main_text and main_text != "No results returned from Metaso.":
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
    persist_to: str | None = None,
    agent_spec: Any | None = None,
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
        persist_to: Directory to persist agent manifest (e.g., "deliverables/agents").
        agent_spec: AgentSpec from LLM analysis with agent identity and capabilities.

    Returns:
        Tuple of (AgentProfile, ModularAgent).
    """
    from pathlib import Path
    from ..aa import AgentProfile, AgentCapabilities, StaticScore

    # Use agent_spec from LLM if provided, otherwise generate basic identity
    if agent_spec is not None:
        # Use LLM-generated spec
        agent_id = agent_spec.agent_id or f"agent-{shortuuid.uuid()[:6]}"
        name = agent_spec.name or agent_name or "Specialist Agent"
        spec_skills = set(agent_spec.skills) if agent_spec.skills else set()
        spec_domains = set(agent_spec.domains) if agent_spec.domains else set()
        spec_system_prompt = agent_spec.system_prompt or ""
        spec_description = getattr(agent_spec, "description", "") or ""
    else:
        # Fallback: generate basic identity
        agent_id = f"agent-{shortuuid.uuid()[:6]}"
        name = agent_name or "Specialist Agent"
        spec_skills = set()
        spec_domains = set()
        spec_system_prompt = ""
        spec_description = ""

    # Extract capabilities from requirement and merge with spec
    # Normalize skills and domains for consistent matching
    from ..aa._vocabulary import normalize_skills, normalize_domains

    raw_skills = set(getattr(requirement, "skills", [])) | spec_skills
    raw_domains = set(getattr(requirement, "domains", [])) | spec_domains or {"general"}

    skills = normalize_skills(raw_skills)
    domains = normalize_domains(raw_domains)
    tools = set(getattr(requirement, "tools", []))
    languages = set(getattr(requirement, "languages", [])) or {"zh", "en"}

    # Build prompt - prioritize: system_prompt arg > agent_spec.system_prompt > generated
    if system_prompt:
        prompt = AgentPrompt(system_prompt=system_prompt)
    elif spec_system_prompt:
        prompt = AgentPrompt(system_prompt=spec_system_prompt)
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
            toolkit_manager = HiveToolkitManager(llm=llm, mcp_clients=mcp_clients)
            # Use Claude Code tools instead of deprecated file tools
            final_toolkit = toolkit_manager.build_toolkit(
                tools_filter={"claude_code_edit", "claude_code_chat"}
            )
            from ..scripts._observability import get_logger
            get_logger().info(f"[INFO] Agent {name} 已添加 Claude Code 工具")
        except ImportError:
            final_toolkit = Toolkit()
    elif final_toolkit is None:
        final_toolkit = Toolkit()

    # Register TaskBoard tools for agent task management
    from ..tool import (
        task_board_write,
        task_board_read,
        TASK_BOARD_WRITE_SCHEMA,
        TASK_BOARD_READ_SCHEMA,
    )
    final_toolkit.register_tool_function(
        task_board_write,
        json_schema=TASK_BOARD_WRITE_SCHEMA,
    )
    final_toolkit.register_tool_function(
        task_board_read,
        json_schema=TASK_BOARD_READ_SCHEMA,
    )

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
    # 秘塔生成的 Agent 设置：
    # - metaso_generated=1.0（秘塔生成）
    # - brand_certified=0.0（用户上传，非官方）
    # - is_cold_start=True（需要冷启动积累数据）
    profile = AgentProfile(
        agent_id=agent_id,
        name=name,
        static_score=StaticScore(
            performance=0.5,       # 默认中等，需要数据积累
            recognition=0.5,       # 默认中等，需要用户评分
            brand_certified=0.0,   # 非官方 Agent
            metaso_generated=1.0,  # 秘塔生成
        ),
        capabilities=AgentCapabilities(
            skills=skills,
            tools=tools,
            domains=domains,
            languages=languages,
            description=spec_description or f"{name}: {', '.join(skills) if skills else '通用技能'}",
        ),
        is_cold_start=True,  # 新 Agent 需要冷启动
        metadata={
            "source": "modular_agent_factory",
            "utterance": utterance,
            "knowledge_docs": knowledge.document_count,
        },
    )

    # Persist agent manifest and full state if directory specified
    agent_description = spec_description or f"{name}: {', '.join(skills) if skills else '通用技能'}"
    if persist_to:
        _persist_agent_manifest(
            agent_id=agent_id,
            name=name,
            persist_dir=persist_to,
            skills=skills,
            tools=tools,
            domains=domains,
            languages=languages,
            prompt=prompt,
            utterance=utterance,
            knowledge_count=knowledge.document_count,
            tags=list(agent_spec.tags) if agent_spec and agent_spec.tags else None,
            parent_domain=agent_spec.parent_domain if agent_spec else None,
            description=agent_description,
        )

        # Save complete agent state (memory, knowledge, task_board, prompt)
        # This enables full agent restoration for immediate use and distribution
        agent_state_path = Path(persist_to) / agent_id / "state.json"
        try:
            agent.save(agent_state_path)
            from ..scripts._observability import get_logger
            get_logger().info(f"[INFO] Agent {name} 完整状态已保存到 {agent_state_path}")
        except Exception as exc:
            from ..scripts._observability import get_logger
            get_logger().warn(f"[WARN] 保存 Agent 完整状态失败: {exc}")

    return profile, agent


def _persist_agent_manifest(
    *,
    agent_id: str,
    name: str,
    persist_dir: str,
    skills: set[str],
    tools: set[str],
    domains: set[str],
    languages: set[str],
    prompt: "AgentPrompt",
    utterance: str,
    knowledge_count: int,
    tags: list[str] | None = None,
    parent_domain: str | None = None,
    description: str | None = None,
) -> None:
    """Persist agent manifest to local storage and register in registry.

    Args:
        agent_id: Agent ID.
        name: Agent display name.
        persist_dir: Base directory for agent storage.
        skills: Agent skills.
        tools: Agent tools.
        domains: Agent domains.
        languages: Agent languages.
        prompt: Agent prompt configuration.
        utterance: Original user utterance.
        knowledge_count: Number of knowledge documents.
        tags: Optional tags for fine-grained matching.
        parent_domain: Parent domain for new custom domains.
        description: Agent description for requirement matching.
    """
    from pathlib import Path
    from .manifest import AgentManifest, PromptConfig

    try:
        # Create agent directory
        agent_dir = Path(persist_dir) / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Build prompt config
        prompt_config = PromptConfig(
            system_prompt=prompt.system_prompt,
            role_description=prompt.role_description,
            deliverable_expectation=prompt.deliverable_expectation,
            collaboration_guidelines=prompt.collaboration_guidelines,
            variables=prompt.variables,
        )

        # Create manifest
        # 使用传入的 description，如果没有则生成默认描述
        final_description = description or f"{name}: {', '.join(skills) if skills else '通用技能'}"
        manifest = AgentManifest(
            id=agent_id,
            name=name,
            version="1.0.0",
            skills=skills,
            tools=tools,
            domains=domains,
            languages=languages,
            prompt_config=prompt_config,
            description=final_description,
            metadata={
                "source": "modular_agent_factory",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "utterance": utterance,
                "knowledge_count": knowledge_count,
                "tags": tags or [],
                "parent_domain": parent_domain,
            },
            manifest_path=agent_dir / "manifest.json",
        )

        # Save manifest
        manifest.save(agent_dir / "manifest.json")

        # Register in global registry
        try:
            from ..aa._agent_registry import (
                get_global_registry,
                AgentRegistryEntry,
            )

            registry_path = Path(persist_dir) / "registry.json"
            registry = get_global_registry(registry_path)

            # Register custom domains if needed
            for domain in domains:
                if domain not in registry.domains:
                    registry.register_domain(
                        domain,
                        parent=parent_domain or "specialist",
                        created_by="llm",
                    )

            # Register agent
            entry = AgentRegistryEntry(
                agent_id=agent_id,
                name=name,
                domains=list(domains),
                skills=list(skills),
                tags=tags or [],
                manifest_path=str(agent_dir / "manifest.json"),
                created_by="llm",
            )
            registry.register_agent(entry)

        except Exception as reg_exc:
            logger.warning("Failed to register agent in registry: %s", reg_exc)

        from ..scripts._observability import get_logger
        get_logger().info(f"[INFO] Agent {name} ({agent_id}) 已保存到 {agent_dir}")

    except Exception as exc:
        from ..scripts._observability import get_logger
        get_logger().warn(f"[WARN] 保存 Agent manifest 失败: {exc}")


def load_modular_agent(
    agent_dir: str,
    *,
    llm: "ChatModelBase | None" = None,
    mcp_clients: "Sequence[MCPClientBase] | None" = None,
    toolkit: "Toolkit | None" = None,
) -> "ModularAgent":
    """Load a ModularAgent from a saved directory.

    This function loads a complete agent from a directory created by
    spawn_modular_agent with persist_to. It restores the full agent state
    including memory, knowledge, task_board, and prompt.

    Args:
        agent_dir: Path to the agent directory (contains state.json).
        llm: Optional LLM model to use (not serialized).
        mcp_clients: Optional MCP clients to use (not serialized).
        toolkit: Optional toolkit to use (not serialized).

    Returns:
        Restored ModularAgent instance.

    Raises:
        FileNotFoundError: If state.json doesn't exist in the directory.
        ValueError: If the state file is invalid.
    """
    from pathlib import Path

    agent_path = Path(agent_dir)
    state_file = agent_path / "state.json"

    if not state_file.exists():
        raise FileNotFoundError(
            f"Agent state file not found: {state_file}. "
            f"Ensure the agent was saved with spawn_modular_agent(persist_to=...)"
        )

    agent = ModularAgent.load(
        state_file,
        llm=llm,
        mcp_clients=mcp_clients,
        toolkit=toolkit,
    )

    from ..scripts._observability import get_logger
    get_logger().info(
        f"[INFO] Agent {agent.name} ({agent.id}) 已从 {agent_dir} 加载，"
        f"知识库: {agent.knowledge.document_count} 篇文档"
    )

    return agent
