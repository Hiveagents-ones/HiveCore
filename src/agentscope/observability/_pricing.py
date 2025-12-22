# -*- coding: utf-8 -*-
"""Model pricing database for cost calculation."""
from __future__ import annotations

from typing import Dict

# Model pricing database (USD per 1K tokens)
# Updated: 2025-01
_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input_per_1k": 0.005, "output_per_1k": 0.015},
    "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    "gpt-4-turbo": {"input_per_1k": 0.01, "output_per_1k": 0.03},
    "gpt-4": {"input_per_1k": 0.03, "output_per_1k": 0.06},
    "gpt-3.5-turbo": {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
    "o1": {"input_per_1k": 0.015, "output_per_1k": 0.06},
    "o1-mini": {"input_per_1k": 0.003, "output_per_1k": 0.012},
    # Anthropic
    "claude-3-5-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-3-5-haiku": {"input_per_1k": 0.001, "output_per_1k": 0.005},
    "claude-3-opus": {"input_per_1k": 0.015, "output_per_1k": 0.075},
    "claude-3-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
    # Google
    "gemini-1.5-pro": {"input_per_1k": 0.00125, "output_per_1k": 0.005},
    "gemini-1.5-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.0003},
    "gemini-2.0-flash": {"input_per_1k": 0.0001, "output_per_1k": 0.0004},
    # DashScope / Qwen (SiliconFlow pricing)
    "qwen-turbo": {"input_per_1k": 0.0001, "output_per_1k": 0.0002},
    "qwen-plus": {"input_per_1k": 0.0004, "output_per_1k": 0.0012},
    "qwen-max": {"input_per_1k": 0.002, "output_per_1k": 0.006},
    "qwen2.5": {"input_per_1k": 0.0001, "output_per_1k": 0.0002},
    "qwen3": {"input_per_1k": 0.0001, "output_per_1k": 0.0002},
    # DeepSeek
    "deepseek-chat": {"input_per_1k": 0.00014, "output_per_1k": 0.00028},
    "deepseek-coder": {"input_per_1k": 0.00014, "output_per_1k": 0.00028},
    # Local models (free)
    "default_local": {"input_per_1k": 0.0, "output_per_1k": 0.0},
}


def get_model_pricing(model_name: str) -> Dict[str, float]:
    """Get pricing for a model.

    Supports exact match, prefix match, and local model detection.

    Args:
        model_name (`str`):
            The model name to look up.

    Returns:
        `Dict[str, float]`:
            Dictionary with 'input_per_1k' and 'output_per_1k' keys.
    """
    # Normalize model name
    model_lower = model_name.lower()

    # Exact match
    if model_name in _MODEL_PRICING:
        return _MODEL_PRICING[model_name]

    # Case-insensitive exact match
    for key, pricing in _MODEL_PRICING.items():
        if key.lower() == model_lower:
            return pricing

    # Prefix match (e.g., "gpt-4o-2024-08-06" matches "gpt-4o")
    for key, pricing in _MODEL_PRICING.items():
        if model_lower.startswith(key.lower()):
            return pricing

    # Contains match for common model families
    model_families = [
        ("gpt-4o-mini", "gpt-4o-mini"),
        ("gpt-4o", "gpt-4o"),
        ("gpt-4-turbo", "gpt-4-turbo"),
        ("gpt-4", "gpt-4"),
        ("gpt-3.5", "gpt-3.5-turbo"),
        ("claude-3-5-sonnet", "claude-3-5-sonnet"),
        ("claude-3-opus", "claude-3-opus"),
        ("claude-3-sonnet", "claude-3-sonnet"),
        ("claude-3-haiku", "claude-3-haiku"),
        ("gemini-1.5-pro", "gemini-1.5-pro"),
        ("gemini-1.5-flash", "gemini-1.5-flash"),
        ("gemini-2.0", "gemini-2.0-flash"),
        ("qwen", "qwen2.5"),
        ("deepseek", "deepseek-chat"),
    ]

    for pattern, pricing_key in model_families:
        if pattern in model_lower:
            return _MODEL_PRICING[pricing_key]

    # Local model detection
    local_indicators = ["ollama", "llama", "local", "localhost"]
    if any(indicator in model_lower for indicator in local_indicators):
        return _MODEL_PRICING["default_local"]

    # Default to gpt-4o-mini pricing (conservative estimate)
    return _MODEL_PRICING["gpt-4o-mini"]


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model_name: str,
) -> float:
    """Calculate the cost of an LLM call.

    Args:
        input_tokens (`int`):
            Number of input tokens.
        output_tokens (`int`):
            Number of output tokens.
        model_name (`str`):
            The model used.

    Returns:
        `float`:
            Estimated cost in USD.
    """
    pricing = get_model_pricing(model_name)
    return (
        input_tokens * pricing["input_per_1k"] / 1000
        + output_tokens * pricing["output_per_1k"] / 1000
    )
