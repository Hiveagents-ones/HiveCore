# -*- coding: utf-8 -*-
"""LLM utility functions for initialization, calling, and JSON parsing.

This module provides:
- LLM provider initialization (SiliconFlow, Ollama)
- Raw and JSON-structured LLM calls with retry logic
- JSON extraction and repair utilities
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_text_from_response(resp: Any) -> str:
    """Extract text content from ChatResponse or similar objects.

    Args:
        resp: Response object (ChatResponse, dict, or string)

    Returns:
        str: Extracted text content
    """
    # If it's already a string, return it
    if isinstance(resp, str):
        return resp

    # Try get_text_content method first (Msg objects)
    # Note: ChatResponse inherits from DictMixin which makes hasattr raise KeyError
    # So we check the method exists in the class itself
    if callable(getattr(type(resp), "get_text_content", None)):
        try:
            return resp.get_text_content() or ""
        except (KeyError, AttributeError):
            pass

    # Handle ChatResponse with content attribute (check via type to avoid KeyError)
    content = None
    try:
        content = resp.content
    except (KeyError, AttributeError):
        pass

    if content is not None:
        if isinstance(content, str):
            return content
        if isinstance(content, (list, tuple)):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text" and "text" in block:
                        text_parts.append(block["text"])
                    elif "content" in block:
                        text_parts.append(str(block["content"]))
                elif isinstance(block, str):
                    text_parts.append(block)
            return "\n".join(text_parts)

    # Handle dict response
    if isinstance(resp, dict):
        if "text" in resp:
            return resp["text"]
        if "content" in resp:
            return str(resp["content"])
        if "message" in resp and isinstance(resp["message"], dict):
            return resp["message"].get("content", "")

    return str(resp)


def _load_env_file() -> None:
    """Load .env file if present.

    Searches common locations and loads environment variables.
    """
    from pathlib import Path
    env_candidates = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path(__file__).parent.parent.parent.parent / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and value and key not in os.environ:
                                os.environ[key] = value
                break
            except Exception:
                pass


def load_zhipu_env() -> dict[str, str | None]:
    """Load Zhipu AI credentials from environment variables.

    Returns:
        dict: Dictionary with api_key, base_url, and model.
    """
    _load_env_file()
    return {
        "api_key": os.getenv("ZHIPU_API_KEY"),
        "base_url": os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        "model": os.getenv("ZHIPU_MODEL", "glm-4-plus"),
    }


def load_zhipu_anthropic_env() -> dict[str, str | None]:
    """Load Zhipu AI Anthropic-compatible credentials from environment variables.

    Returns:
        dict: Dictionary with api_key, base_url, and model.
    """
    _load_env_file()
    return {
        "api_key": os.getenv("ZHIPU_API_KEY"),
        "base_url": os.getenv("ZHIPU_ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/anthropic"),
        "model": os.getenv("ZHIPU_ANTHROPIC_MODEL", "GLM-4.7"),
    }


def load_siliconflow_env() -> dict[str, str | None]:
    """Load SiliconFlow credentials from environment variables.

    Automatically loads .env file if present.

    Returns:
        dict: Dictionary with api_key, base_url, and model.
    """
    _load_env_file()
    return {
        "api_key": os.getenv("SILICONFLOW_API_KEY"),
        "base_url": os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        "model": os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
        # API format: "openai" (default) or "anthropic" (for GLM-4.7 tool_use support)
        "api_format": os.getenv("SILICONFLOW_API_FORMAT", "auto"),
    }


def get_llm_provider() -> str:
    """Get the configured LLM provider.

    Returns:
        str: Provider name ('zhipu-anthropic', 'zhipu', 'siliconflow', or 'auto')
    """
    _load_env_file()
    return os.getenv("LLM_PROVIDER", "auto")


def _should_use_anthropic_format(model_name: str, api_format: str) -> bool:
    """Determine if Anthropic API format should be used.

    Args:
        model_name: The model name
        api_format: User-specified format ("auto", "anthropic", or "openai")

    Returns:
        bool: True if Anthropic format should be used
    """
    if api_format == "anthropic":
        return True
    if api_format == "openai":
        return False
    # Auto-detect based on model name
    # GLM-4.x models support Anthropic format with native tool_use
    anthropic_models = ["GLM-4.7", "GLM-4.6", "GLM-4.5"]
    return any(m in model_name for m in anthropic_models)


def initialize_llm(
    provider: str | None = None,
    silicon_creds: dict[str, str | None] | None = None,
    zhipu_creds: dict[str, str | None] | None = None,
) -> tuple[Any, str]:
    """Initialize LLM model based on provider configuration.

    Args:
        provider: Provider name ('auto', 'zhipu-anthropic', 'zhipu', 'siliconflow').
            If None or 'auto', uses LLM_PROVIDER env var.
        silicon_creds: SiliconFlow credentials dict (optional)
        zhipu_creds: Zhipu AI credentials dict (optional)

    Returns:
        tuple: (llm_instance, provider_name_used)
    """
    # Determine provider
    if provider is None or provider == "auto":
        provider = get_llm_provider()
        if provider == "auto":
            # Auto-detect: prefer zhipu-anthropic if configured
            zhipu_creds = load_zhipu_anthropic_env()
            if zhipu_creds.get("api_key"):
                provider = "zhipu-anthropic"
            else:
                provider = "siliconflow"

    from ._observability import get_logger
    logger = get_logger()

    if provider == "zhipu-anthropic":
        # Use Zhipu AI Anthropic-compatible API (native tool_use support)
        zhipu_creds = load_zhipu_anthropic_env()

        if not zhipu_creds.get("api_key"):
            raise ValueError(
                "Zhipu API key not found. Please set ZHIPU_API_KEY environment variable."
            )

        model_name = zhipu_creds.get("model") or "GLM-4.7"
        api_key = zhipu_creds.get("api_key") or ""
        base_url = zhipu_creds.get("base_url") or "https://open.bigmodel.cn/api/anthropic"

        logger.info(f"[LLM] Using Zhipu AI Anthropic-compatible API: {model_name}")

        from agentscope.model import AnthropicChatModel
        # Zhipu uses Bearer token auth instead of x-api-key
        # Pass api_key as None and use default_headers for Bearer auth
        return (
            AnthropicChatModel(
                model_name=model_name,
                api_key=api_key,  # Anthropic SDK will use this as x-api-key
                max_tokens=8192,
                stream=False,
                client_args={
                    "base_url": base_url,
                    # Override auth header with Bearer token format
                    "default_headers": {
                        "Authorization": f"Bearer {api_key}",
                    },
                },
            ),
            "zhipu-anthropic",
        )

    elif provider == "zhipu":
        # Use Zhipu AI OpenAI-compatible API (has issues with tool_result)
        zhipu_creds = zhipu_creds or load_zhipu_env()

        if not zhipu_creds.get("api_key"):
            raise ValueError(
                "Zhipu API key not found. Please set ZHIPU_API_KEY environment variable."
            )

        model_name = zhipu_creds.get("model") or "glm-4-plus"
        api_key = zhipu_creds.get("api_key") or ""
        base_url = zhipu_creds.get("base_url") or "https://open.bigmodel.cn/api/paas/v4"

        logger.info(f"[LLM] Using Zhipu AI OpenAI-compatible API: {model_name}")

        from agentscope.model import OpenAIChatModel
        return (
            OpenAIChatModel(
                model_name=model_name,
                api_key=api_key,
                stream=False,
                client_args={
                    "base_url": base_url,
                },
            ),
            "zhipu",
        )

    else:
        # SiliconFlow provider
        silicon_creds = silicon_creds or load_siliconflow_env()

        if not silicon_creds.get("api_key"):
            raise ValueError(
                "SiliconFlow API key not found. Please set SILICONFLOW_API_KEY environment variable."
            )

        model_name = silicon_creds.get("model") or "Qwen/Qwen2.5-72B-Instruct"
        api_key = silicon_creds.get("api_key") or ""
        base_url = silicon_creds.get("base_url") or "https://api.siliconflow.cn/v1"
        api_format = silicon_creds.get("api_format") or "auto"

        use_anthropic = _should_use_anthropic_format(model_name, api_format)

        if use_anthropic:
            # Use Anthropic format for GLM-4.x models (supports native tool_use)
            from agentscope.model import AnthropicChatModel

            logger.info(
                f"[LLM] Using SiliconFlow Anthropic format: {model_name}"
            )

            # Anthropic SDK automatically appends /v1/messages to base_url
            anthropic_base_url = base_url.rstrip("/")
            if anthropic_base_url.endswith("/v1"):
                anthropic_base_url = anthropic_base_url[:-3]

            return (
                AnthropicChatModel(
                    model_name=model_name,
                    api_key=api_key,
                    max_tokens=8192,
                    stream=False,
                    client_args={
                        "base_url": anthropic_base_url,
                    },
                ),
                "siliconflow-anthropic",
            )
        else:
            # Use OpenAI format (default)
            from agentscope.model import OpenAIChatModel

            logger.info(f"[LLM] Using SiliconFlow OpenAI format: {model_name}")

            return (
                OpenAIChatModel(
                    model_name=model_name,
                    api_key=api_key,
                    stream=False,
                    client_args={
                        "base_url": base_url,
                    },
                ),
                "siliconflow",
            )


async def call_llm_raw(
    llm: Any,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    retries: int = 3,
    label: str = "",
    verbose: bool = False,
) -> str:
    """Call LLM and return raw text response.

    Args:
        llm: LLM model instance
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature
        retries: Number of retry attempts
        label: Label for logging
        verbose: Whether to print debug info

    Returns:
        str: Raw LLM response text
    """
    import asyncio
    from ._observability import get_llm_observer

    observer = get_llm_observer()
    last_err: Exception | None = None

    # Log call start if verbose
    start_time = observer.on_call_start(label, len(messages)) if verbose else 0

    for attempt in range(retries):
        if attempt > 0 and verbose:
            # Re-start timing for retry
            start_time = observer.on_call_start(label, len(messages))

        try:
            # Rate limit API calls to prevent 429 errors
            from ._api_scheduler import zhipu_rate_limit

            async with zhipu_rate_limit(label or "agent_llm"):
                # OpenAIChatModel.__call__ is async, so await it directly
                resp = await llm(messages, temperature=temperature)
            text = extract_text_from_response(resp)

            # Track token usage if available
            usage = getattr(resp, "usage", None)
            # ChatUsage uses input_tokens/output_tokens, not prompt_tokens/completion_tokens
            # Also, DictMixin raises KeyError instead of returning default, so use .get()
            if usage:
                prompt_tokens = usage.get("input_tokens", 0) or 0
                completion_tokens = usage.get("output_tokens", 0) or 0
            else:
                prompt_tokens = 0
                completion_tokens = 0

            if verbose:
                observer.on_call_success(
                    label, start_time, prompt_tokens, completion_tokens, len(text)
                )
            elif prompt_tokens > 0 or completion_tokens > 0:
                # Still track tokens even if not verbose
                observer.ctx.track_llm_call(label, prompt_tokens, completion_tokens)

            return text
        except Exception as exc:
            last_err = exc
            if verbose:
                observer.on_call_error(label, exc, attempt + 1, retries)
            if attempt < retries - 1:
                # Longer backoff for 429 rate limit errors
                is_rate_limit = "429" in str(exc) or "rate" in str(exc).lower()
                if is_rate_limit:
                    wait_time = 10.0 * (attempt + 1)  # 10s, 20s, 30s...
                    logger.warning(
                        "[call_llm_raw] Rate limit hit, waiting %.1fs (attempt=%d)",
                        wait_time,
                        attempt + 1,
                    )
                else:
                    wait_time = 1.5 * (attempt + 1)
                await asyncio.sleep(wait_time)

    raise RuntimeError(f"LLM 调用失败 ({label}): {last_err}")


def extract_json_block(text: str) -> str | None:
    """Extract JSON block from markdown code fence.

    Args:
        text: Text potentially containing ```json ... ``` block

    Returns:
        str or None: Extracted JSON string or None if not found
    """
    # Try to find ```json ... ``` block
    pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()

    # Try to find raw JSON object/array
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        return text

    return None


def repair_truncated_json(text: str) -> str:
    """Attempt to repair truncated JSON by balancing brackets.

    Args:
        text: Potentially truncated JSON string

    Returns:
        str: Repaired JSON string
    """
    text = text.strip()
    if not text:
        return text

    # Count brackets
    open_braces = text.count("{")
    close_braces = text.count("}")
    open_brackets = text.count("[")
    close_brackets = text.count("]")

    # Add missing closing brackets
    result = text
    result += "]" * (open_brackets - close_brackets)
    result += "}" * (open_braces - close_braces)

    return result


def parse_json_from_text(text: str) -> dict[str, Any] | list[Any] | None:
    """Parse JSON from text with multiple fallback strategies.

    Args:
        text: Text containing JSON data

    Returns:
        Parsed JSON object or None if parsing fails
    """
    if not text:
        return None

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from code block
    extracted = extract_json_block(text)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            # Strategy 3: Repair truncated JSON
            repaired = repair_truncated_json(extracted)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    # Strategy 4: Find first { or [ and parse from there
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        if start_idx >= 0:
            # Find matching end
            depth = 0
            in_string = False
            escape = False
            for i, c in enumerate(text[start_idx:], start_idx):
                if escape:
                    escape = False
                    continue
                if c == "\\":
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == start_char:
                    depth += 1
                elif c == end_char:
                    depth -= 1
                    if depth == 0:
                        candidate = text[start_idx : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break

    return None


async def call_llm_json(
    llm: Any,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    retries: int = 3,
    label: str = "",
    verbose: bool = False,
) -> tuple[dict[str, Any], str]:
    """Call LLM and parse response as JSON.

    Args:
        llm: LLM model instance
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature
        retries: Number of retry attempts
        label: Label for logging
        verbose: Whether to print debug info

    Returns:
        tuple: (parsed_json_dict, raw_response_text)

    Raises:
        RuntimeError: If JSON parsing fails after all retries
    """
    raw = await call_llm_raw(
        llm,
        messages,
        temperature=temperature,
        retries=retries,
        label=label,
        verbose=verbose,
    )

    parsed = parse_json_from_text(raw)
    if parsed is not None:
        if isinstance(parsed, dict):
            return parsed, raw
        elif isinstance(parsed, list):
            return {"items": parsed}, raw

    # If parsing failed, return empty dict with warning
    if verbose:
        from ._observability import get_llm_observer
        get_llm_observer().on_json_parse_error(label, len(raw))
    return {}, raw


__all__ = [
    "load_zhipu_env",
    "load_zhipu_anthropic_env",
    "load_siliconflow_env",
    "get_llm_provider",
    "initialize_llm",
    "call_llm_raw",
    "call_llm_json",
    "extract_json_block",
    "repair_truncated_json",
    "parse_json_from_text",
    "extract_text_from_response",
    "_should_use_anthropic_format",
]
