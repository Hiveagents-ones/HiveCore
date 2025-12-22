# -*- coding: utf-8 -*-
"""Metaso-backed search agent and factory."""
from __future__ import annotations

import asyncio
import json
import os
import math
from typing import Iterable, Sequence, Any, Coroutine

import shortuuid
import requests
from qdrant_client import QdrantClient, models

from ..model import OpenAIChatModel
from ..message import Msg, TextBlock
from ..aa import AgentCapabilities, AgentProfile, StaticScore, RoleRequirement
from ..tool import metaso_search, metaso_read, metaso_chat, ToolResponse, Toolkit
from ._agent_base import AgentBase
from ..mcp import MCPClientBase
from .._logging import logger


def _latest_message(msg: Msg | Sequence[Msg] | None) -> Msg | None:
    if msg is None:
        return None
    if isinstance(msg, Iterable) and not isinstance(msg, Msg):
        seq = list(msg)
        return seq[-1] if seq else None
    return msg  # type: ignore[return-value]


class MetasoSearchAgent(AgentBase):
    """Simple agent that answers by searching Metaso and returning the hits."""

    def __init__(
        self,
        *,
        name: str = "MetasoAgent",
        memory_pool: object | None = None,
        scope: str = "webpage",
        size: int = 5,
        include_summary: bool = False,
        include_raw_content: bool = False,
        concise_snippet: bool = True,
    ) -> None:
        super().__init__()
        self.name = name
        self.memory_pool = memory_pool
        self.scope = scope
        self.size = size
        self.include_summary = include_summary
        self.include_raw_content = include_raw_content
        self.concise_snippet = concise_snippet
        self._history: list[Msg] = []

    async def observe(self, msg: Msg | Sequence[Msg] | None) -> None:
        if msg is None:
            return
        if isinstance(msg, Sequence) and not isinstance(msg, Msg):
            self._history.extend(list(msg))
        else:
            self._history.append(msg)  # type: ignore[arg-type]

    async def reply(self, msg: Msg | Sequence[Msg] | None = None, **kwargs) -> Msg:
        if msg is not None:
            await self.observe(msg)
        message = _latest_message(msg)
        if message is None:
            raise ValueError("MetasoSearchAgent requires at least one message.")
        query = message.get_text_content()
        if not query:
            raise ValueError("MetasoSearchAgent requires textual content.")

        resp = metaso_search(
            query,
            scope=self.scope,
            size=self.size,
            include_summary=self.include_summary,
            include_raw_content=self.include_raw_content,
            concise_snippet=self.concise_snippet,
            store_in_memory=self.memory_pool is not None,
            memory_pool=self.memory_pool,
        )

        first_block = resp.content[0]
        text = first_block.text if hasattr(first_block, "text") else str(first_block)
        content = [TextBlock(type="text", text=text)]

        reply_msg = Msg(
            name=self.name,
            role="assistant",
            content=content,
            metadata=resp.metadata,
        )
        await self.observe(reply_msg)
        return reply_msg


def create_metaso_agent(
    *,
    name: str = "MetasoAgent",
    memory_pool: object | None = None,
    scope: str = "webpage",
    size: int = 5,
    include_summary: bool = False,
    include_raw_content: bool = False,
    concise_snippet: bool = True,
) -> MetasoSearchAgent:
    """Factory method to build a MetasoSearchAgent with sensible defaults."""
    return MetasoSearchAgent(
        name=name,
        memory_pool=memory_pool,
        scope=scope,
        size=size,
        include_summary=include_summary,
        include_raw_content=include_raw_content,
        concise_snippet=concise_snippet,
    )


def spawn_metaso_agent(
    requirement: RoleRequirement | None = None,
    utterance: str = "",
    *,
    memory_pool: object | None = None,
    scope: str = "webpage",
    size: int = 5,
    include_summary: bool = False,
    include_raw_content: bool = False,
    concise_snippet: bool = True,
) -> tuple[AgentProfile, MetasoSearchAgent]:
    """Spawn a Metaso agent instance plus its AgentProfile (for AA selection).

    Args:
        requirement: Capability requirements (used to enhance agent capabilities).
        utterance: User utterance (not used in basic agent, kept for API consistency).
        memory_pool: Optional memory pool.
        scope: Search scope.
        size: Number of results.
        include_summary: Include summary in results.
        include_raw_content: Include raw content.
        concise_snippet: Use concise snippets.

    Returns:
        Tuple of (AgentProfile, MetasoSearchAgent).
    """
    agent_id = f"metaso-{shortuuid.uuid()[:8]}"
    agent = create_metaso_agent(
        name="Metaso Search",
        memory_pool=memory_pool,
        scope=scope,
        size=size,
        include_summary=include_summary,
        include_raw_content=include_raw_content,
        concise_snippet=concise_snippet,
    )
    agent.id = agent_id  # align runtime id with profile id

    # Build capabilities from requirement if provided
    skills = {"search"}
    tools = {"metaso"}
    domains = {"general"}
    languages = {"zh", "en"}
    if requirement:
        skills = skills | set(requirement.skills)
        tools = tools | set(requirement.tools)
        if requirement.domains:
            domains = set(requirement.domains)
        if requirement.languages:
            languages = set(requirement.languages)

    profile = AgentProfile(
        agent_id=agent_id,
        name="Metaso Search",
        static_score=StaticScore(performance=0.55, brand=0.5, recognition=0.5),
        capabilities=AgentCapabilities(
            skills=skills,
            tools=tools,
            domains=domains,
            languages=languages,
        ),
        metadata={"source": "metaso_factory"},
    )
    return profile, agent


class MetasoKnowledgeAgent(AgentBase):
    """Agent that replies using pre-fetched Metaso knowledge."""

    def __init__(
        self,
        *,
        name: str,
        knowledge: str,
        memory_key: str | None = None,
        memory_pool: object | None = None,
        llm: object | None = None,
        knowledge_docs: list[dict[str, str]] | None = None,
        knowledge_store: dict[str, str] | None = None,
        toolkit: Toolkit | None = None,
        system_prompt: str | None = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.knowledge = knowledge
        self.memory_key = memory_key
        self.memory_pool = memory_pool
        self.llm = llm
        self._knowledge_docs = knowledge_docs or []
        self._knowledge_store = knowledge_store
        self.toolkit = toolkit
        self.system_prompt = system_prompt
        self._history: list[Msg] = []

    async def observe(self, msg: Msg | Sequence[Msg] | None) -> None:
        if msg is None:
            return
        if isinstance(msg, Sequence) and not isinstance(msg, Msg):
            self._history.extend(list(msg))
        else:
            self._history.append(msg)  # type: ignore[arg-type]

    async def reply(self, msg: Msg | Sequence[Msg] | None = None, **kwargs) -> Msg:
        if msg is not None:
            await self.observe(msg)
        text = self.knowledge
        if self.memory_key and self.memory_pool is not None:
            try:
                stored = self.memory_pool.load(self.memory_key)  # type: ignore[attr-defined]
                if stored and stored.content:
                    text = stored.content
            except Exception:
                # best-effort; keep pre-fetched knowledge
                pass
        # RAG: retrieve top-K and build context
        retrieved_context = self._retrieve_context(msg)
        context_with_tools = self._augment_context_with_tools(retrieved_context or text)

        # If LLM is available, ask it to reason over RAG context / knowledge.
        if self.llm is not None:
            last = _latest_message(msg)
            user_query = last.get_text_content() if last else ""
            context = context_with_tools

            # Use custom system prompt if provided, otherwise default
            if self.system_prompt:
                prompt = (
                    f"{self.system_prompt}\n\n"
                    f"【检索片段】\n{context}\n\n【用户问题】{user_query}"
                )
            else:
                prompt = (
                    "你是根据以下搜索结果和片段检索回答问题的助手。"
                    "请结合上下文给出简洁、准确的中文回答，必要时列出参考片段。"
                    "\n\n【检索片段】\n"
                    f"{context}\n\n【用户问题】{user_query}"
                )
            try:
                resp = await self.llm([{"role": "user", "content": prompt}], stream=False)  # type: ignore[arg-type]
                combined = ""
                for block in resp.content:
                    if isinstance(block, dict):
                        combined += block.get("text", "")
                if combined.strip():
                    text = combined.strip()
            except Exception:
                pass
        else:
            last = _latest_message(msg)
            user_query = last.get_text_content() if last else ""
            context = context_with_tools
            prompt = (
                "请结合以下资料回答用户问题，必要时列出参考来源。\n"
                f"【资料】\n{context}\n\n【问题】{user_query}"
            )
            try:
                chat_response = metaso_chat([{"role": "user", "content": prompt}])
                if chat_response:
                    text = chat_response
            except Exception:
                pass
        metadata: dict[str, Any] | None = None
        tool_names = self._tool_names()
        if self.memory_key or tool_names:
            metadata = {}
            if self.memory_key:
                metadata["memory_key"] = self.memory_key
            if tool_names:
                metadata["tools"] = tool_names

        response = Msg(
            name=self.name,
            role="assistant",
            content=[TextBlock(type="text", text=text)],
            metadata=metadata,
        )
        await self.observe(response)
        return response

    def _tool_names(self) -> list[str]:
        if not self.toolkit or not getattr(self.toolkit, "tools", None):
            return []
        return list(self.toolkit.tools.keys())

    def _tool_overview(self) -> str:
        if not self.toolkit or not getattr(self.toolkit, "tools", None):
            return ""
        lines: list[str] = []
        for registered in self.toolkit.tools.values():
            schema = registered.json_schema.get("function", {})
            name = schema.get("name") or registered.name
            desc = schema.get("description") or ""
            snippet = f"{name}: {desc}".strip()
            lines.append(snippet)
        return "\n".join(line for line in lines if line).strip()

    def _augment_context_with_tools(self, context: str) -> str:
        overview = self._tool_overview()
        if not overview:
            return context
        if not context:
            return f"【MCP 工具】\n{overview}"
        return f"{context}\n\n【MCP 工具】\n{overview}"

    def _retrieve_context(self, msg: Msg | Sequence[Msg] | None, limit: int = 5) -> str:
        if not self._knowledge_docs:
            return ""
        last = _latest_message(msg)
        query = (last.get_text_content() if last else "") or ""
        scored: list[tuple[float, dict[str, str]]] = []

        if self._knowledge_store and query:
            query_vecs = _embed_texts([query])
            if query_vecs:
                client = QdrantClient(path=self._knowledge_store["path"])
                hits = client.search(
                    collection_name=self._knowledge_store["collection"],
                    query_vector=query_vecs[0],
                    limit=limit,
                    with_payload=True,
                )
                for hit in hits:
                    payload = hit.payload or {}
                    scored.append((hit.score or 0.0, {"text": payload.get("text", ""), "url": payload.get("url", "")}))

        if not scored:
            query_vecs = _embed_texts([query]) if query else []
            if query_vecs:
                query_vec = query_vecs[0]

                def cosine(a: list[float], b: list[float]) -> float:
                    dot = sum(x * y for x, y in zip(a, b))
                    na = math.sqrt(sum(x * x for x in a)) or 1e-6
                    nb = math.sqrt(sum(y * y for y in b)) or 1e-6
                    return dot / (na * nb)

                for doc in self._knowledge_docs:
                    vec = doc.get("embedding")
                    if isinstance(vec, list):
                        scored.append((cosine(query_vec, vec), doc))

        if not scored:
            query_tokens = set(query.split())
            for doc in self._knowledge_docs:
                text = doc.get("text", "")
                tokens = set(text.split())
                overlap = len(tokens & query_tokens)
                score = overlap / (len(query_tokens) + 1e-6)
                if score > 0 or not query_tokens:
                    scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        snippets = []
        for score, doc in scored[:limit]:
            snippet = doc.get("text", "")
            url = doc.get("url")
            snippets.append(f"[score={score:.2f}] {snippet}\n{url or ''}")
        if not snippets:
            snippets = [doc.get("text", "") for doc in self._knowledge_docs[:limit]]
        return "\n\n".join(snippets)


def spawn_metaso_kb_agent(
    requirement: RoleRequirement,
    utterance: str,
    *,
    memory_pool: object | None = None,
    scope: str = "webpage",
    size: int = 5,
    include_summary: bool = False,
    include_raw_content: bool = False,
    concise_snippet: bool = True,
    toolkit: Toolkit | None = None,
    mcp_clients: Sequence[MCPClientBase] | None = None,
    system_prompt: str | None = None,
    agent_name: str | None = None,
    with_file_tools: bool = False,
    llm: object | None = None,
) -> tuple[AgentProfile, MetasoKnowledgeAgent]:
    """Spawn an agent whose knowledge base is filled by Metaso search.

    Args:
        requirement: Capability requirements for the agent.
        utterance: User utterance used to search and build knowledge base.
        memory_pool: Optional memory pool.
        scope: Search scope.
        size: Number of results.
        include_summary: Include summary in results.
        include_raw_content: Include raw content.
        concise_snippet: Use concise snippets.
        toolkit: Optional toolkit.
        mcp_clients: Optional MCP clients.
        system_prompt: Optional custom system prompt for the agent.
        agent_name: Optional custom name for the agent.
        with_file_tools: Whether to add file operation tools (view/write/insert).
        llm: Optional LLM instance (used for HiveToolkitManager if with_file_tools).

    Returns:
        Tuple of (AgentProfile, MetasoKnowledgeAgent).
    """
    resp = metaso_search(
        utterance,
        scope=scope,
        size=size,
        include_summary=include_summary,
        include_raw_content=include_raw_content,
        concise_snippet=concise_snippet,
        store_in_memory=memory_pool is not None,
        memory_pool=memory_pool,
    )
    first_block = resp.content[0]
    knowledge_text = first_block.text if hasattr(first_block, "text") else str(first_block)
    memory_key = resp.metadata.get("memory_key") if resp.metadata else None

    agent_id = f"metaso-kb-{shortuuid.uuid()[:8]}"
    agent_llm = llm or _build_silicon_llm()
    knowledge_docs, knowledge_store = _build_knowledge_store(resp, agent_id)

    # Build toolkit: priority order is explicit toolkit > file tools > MCP clients
    if toolkit is None:
        if with_file_tools:
            try:
                from agentscope.scripts.hive_toolkit import HiveToolkitManager
                toolkit_manager = HiveToolkitManager(llm=agent_llm)
                toolkit = toolkit_manager.build_toolkit(
                    tools_filter={"view_text_file", "write_text_file", "insert_text_file"}
                )
            except ImportError:
                toolkit = _build_toolkit_from_mcp(mcp_clients)
        else:
            toolkit = _build_toolkit_from_mcp(mcp_clients)

    # Use provided agent name or default
    final_name = agent_name or "Metaso Knowledge"

    agent = MetasoKnowledgeAgent(
        name=final_name,
        knowledge=knowledge_text,
        memory_key=memory_key,
        memory_pool=memory_pool,
        llm=llm,
        knowledge_docs=knowledge_docs,
        knowledge_store=knowledge_store,
        toolkit=toolkit,
        system_prompt=system_prompt,
    )
    agent.id = agent_id

    skills = set(requirement.skills) | {"search"}
    tools = set(requirement.tools) | {"metaso"}
    domains = set(requirement.domains) or {"general"}
    languages = set(requirement.languages) or {"zh", "en"}

    # Cold start defaults: moderate scores that will be updated based on task performance
    profile = AgentProfile(
        agent_id=agent_id,
        name=final_name,
        static_score=StaticScore(
            performance=0.7,   # Cold start default, will improve with successful tasks
            brand=0.5,         # New agent, no reputation yet
            recognition=0.5,   # New agent, no track record yet
        ),
        capabilities=AgentCapabilities(
            skills=skills,
            tools=tools,
            domains=domains,
            languages=languages,
        ),
        is_cold_start=True,  # Mark as cold start for special handling
        metadata={
            "source": "metaso_kb_factory",
            "memory_key": memory_key,
            "utterance": utterance,
        },
    )
    return profile, agent


def _build_silicon_llm() -> OpenAIChatModel | None:
    """Try to build a SiliconFlow-backed OpenAIChatModel; return None on failure."""

    api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("API_KEY")
    model_name = os.getenv("SILICONFLOW_MODEL") or "deepseek-chat"
    base_url = os.getenv("SILICONFLOW_BASE_URL") or "https://api.siliconflow.cn/v1"
    if not api_key:
        return None
    try:
        return OpenAIChatModel(
            model_name=model_name,
            api_key=api_key,
            stream=False,
            client_args={"base_url": base_url},
        )
    except Exception:
        return None


def _build_knowledge_store(resp: ToolResponse | None, agent_id: str):
    """Fetch full articles, embed them, and persist in Qdrant."""

    hits = []
    if resp and resp.metadata:
        hits = resp.metadata.get("hits") or []

    docs: list[dict[str, str]] = []
    if hits:
        for hit in hits:
            url = hit.get("url") or ""
            article = ""
            if url:
                try:
                    article = metaso_read(url)
                except Exception:
                    article = ""
            text = article or hit.get("snippet") or hit.get("title") or ""
            docs.append(
                {
                    "title": hit.get("title", ""),
                    "url": url,
                    "text": text.strip(),
                },
            )
    elif resp:
        docs.append(
            {
                "title": "metaso_fallback",
                "url": "",
                "text": str(resp.content[0]),
            },
        )

    vectors = _embed_texts([doc.get("text", "") for doc in docs]) if docs else []
    for doc, vec in zip(docs, vectors):
        doc["embedding"] = vec

    store_dir = os.getenv("METASO_VECTOR_DIR") or "./knowledge/vector"
    os.makedirs(store_dir, exist_ok=True)
    safe_agent = agent_id.replace("-", "_")
    client = QdrantClient(path=os.path.join(store_dir, safe_agent))
    collection = safe_agent
    dim = len(vectors[0]) if vectors else 0
    if dim and not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
    if vectors:
        points = []
        for idx, (doc, vec) in enumerate(zip(docs, vectors)):
            points.append(
                models.PointStruct(
                    id=idx,
                    vector=vec,
                    payload={"title": doc.get("title", ""), "url": doc.get("url", ""), "text": doc.get("text", "")},
                ),
            )
        client.upsert(collection_name=collection, points=points)

    store_config = {"path": os.path.join(store_dir, safe_agent), "collection": collection} if vectors else None
    return [], store_config


def _embed_texts(texts: list[str]) -> list[list[float]]:
    api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("API_KEY")
    base_url = os.getenv("SILICONFLOW_BASE_URL") or "https://api.siliconflow.cn/v1"
    model_name = os.getenv("SILICONFLOW_EMBED_MODEL") or "Qwen/Qwen3-Embedding-4B"
    if not api_key or not texts:
        return []
    url = base_url.rstrip("/") + "/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "input": texts,
        "encoding_format": "float",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    embeddings = []
    for item in data.get("data", []):
        embeddings.append(item.get("embedding", []))
    return embeddings


def _run_coro_safely(coro: Coroutine[Any, Any, Any]):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    return asyncio.run(coro)


def _build_toolkit_from_mcp(mcp_clients: Sequence[MCPClientBase] | None) -> Toolkit | None:
    if not mcp_clients:
        return None
    toolkit = Toolkit()

    async def _register_all() -> None:
        for client in mcp_clients:
            try:
                await toolkit.register_mcp_client(client)
            except Exception as exc:  # pragma: no cover - best effort registration
                client_name = getattr(client, "name", "unknown")
                logger.warning("Failed to register MCP client %s: %s", client_name, exc)

    _run_coro_safely(_register_all())
    return toolkit if toolkit.tools else None

def _build_embedding_model() -> EmbeddingModelBase | None:
    api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("API_KEY")
    base_url = os.getenv("SILICONFLOW_BASE_URL") or "https://api.siliconflow.cn/v1"
    embed_model_name = os.getenv("SILICONFLOW_EMBED_MODEL") or "Qwen/Qwen3-Embedding-4B"
    if not api_key:
        return None
    return _OpenAICompatibleEmbedding(
        api_key=api_key,
        model_name=embed_model_name,
        base_url=base_url,
        dimensions=1024,
    )
