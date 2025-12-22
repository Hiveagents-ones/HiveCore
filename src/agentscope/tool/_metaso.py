# -*- coding: utf-8 -*-
"""Metaso search helper for enriching agent knowledge base."""
from __future__ import annotations

import os
from typing import Any, Iterable

import requests

from ..message import TextBlock
from ._response import ToolResponse


def _default_key(query: str) -> str:
    return f"metaso:{query}"


def _normalize_hits(raw_hits: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shape Metaso responses into a stable list for metadata/output."""
    hits: list[dict[str, Any]] = []
    for hit in raw_hits:
        hits.append(
            {
                "title": hit.get("title", ""),
                "url": hit.get("link") or hit.get("url") or "",
                "score": hit.get("score"),
                "snippet": hit.get("snippet") or hit.get("summary") or "",
                "source": "metaso",
            },
        )
    return hits


def _render_hits(hits: list[dict[str, Any]]) -> str:
    """Human-readable text for agent consumption."""
    lines: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        lines.append(
            "\n".join(
                [
                    f"[{idx}] {hit.get('title', '').strip()}",
                    hit.get("snippet", "").strip(),
                    hit.get("url", "").strip(),
                ],
            ).strip(),
        )
    return "\n\n".join(lines)


def _resolve_api_key() -> str:
    api_key = (
        os.getenv("METASO_API_KEY")
        or os.getenv("METASO_TOKEN")
        or os.getenv("API_KEY")
    )
    if not api_key:
        raise ValueError("Metaso API requires METASO_API_KEY (or API_KEY) in environment")
    return api_key


def metaso_search(
    query: str,
    *,
    scope: str = "webpage",
    size: int = 5,
    include_summary: bool = False,
    include_raw_content: bool = False,
    concise_snippet: bool = True,
    store_in_memory: bool = False,
    memory_pool: Any | None = None,
    memory_key: str | None = None,
) -> ToolResponse:
    """Search Metaso and optionally persist results to a MemoryPool."""

    api_key = _resolve_api_key()
    payload = {
        "q": query,
        "scope": scope,
        "includeSummary": include_summary,
        "size": size,
        "includeRawContent": include_raw_content,
        "conciseSnippet": concise_snippet,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        "https://metaso.cn/api/v1/search",
        headers=headers,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    raw_hits = data.get("webpages") or data.get("results") or []
    hits = _normalize_hits(raw_hits)
    text = _render_hits(hits) or "No results returned from Metaso."

    metadata = {
        "source": "metaso",
        "query": query,
        "total": data.get("total"),
        "credits": data.get("credits"),
        "searchParameters": data.get("searchParameters"),
        "hits": hits,
    }

    if store_in_memory and memory_pool is not None:
        try:
            from agentscope.ones.memory import MemoryEntry  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            MemoryEntry = None
        if MemoryEntry is not None:
            key = memory_key or _default_key(query)
            entry = MemoryEntry(
                key=key,
                content=text,
                tags={"metaso", "search", scope},
            )
            memory_pool.save(entry)  # type: ignore[attr-defined]
            metadata["memory_key"] = key

    return ToolResponse(
        content=[TextBlock(type="text", text=text)],
        metadata=metadata,
    )


def metaso_read(url: str) -> str:
    """Fetch full webpage content via Metaso reader API."""

    if not url:
        return ""
    api_key = _resolve_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/plain",
        "Content-Type": "application/json",
    }
    payload = {"url": url}
    resp = requests.post(
        "https://metaso.cn/api/v1/reader",
        headers=headers,
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.text.strip()


def metaso_chat(
    messages: list[dict[str, str]],
    *,
    model: str = "fast",
    stream: bool = False,
) -> str:
    """Call Metaso chat completions (OpenAI compatible)."""

    api_key = _resolve_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "stream": stream,
        "messages": messages,
    }
    resp = requests.post(
        "https://metaso.cn/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    content = choices[0].get("message", {}).get("content")
    if isinstance(content, list):
        text = "".join(block.get("text", "") for block in content if isinstance(block, dict))
    else:
        text = content or ""
    return text.strip()
