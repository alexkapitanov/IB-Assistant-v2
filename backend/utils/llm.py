"""Utilities for selecting model names and building LLM configs (AutoGen).
Centralizes model and API-key configuration to avoid hard-coded strings across agents.
"""
from __future__ import annotations

import os
from typing import Dict, Any

from backend import config


def get_api_key() -> str:
    """Returns OpenAI API key or empty string if not set."""
    return os.getenv("OPENAI_API_KEY", getattr(config, "OPENAI_API_KEY", ""))


def model_for(kind: str) -> str:
    """Pick model name based on logical kind.

    kinds:
      - expert: high-quality model (default MODEL_GPT4)
      - mini: cost-effective model (default MODEL_GPT4_MINI)
      - o3mini: reasoning/smaller (default MODEL_O3_MINI)
    """
    kind = kind.lower()
    if kind == "expert":
        return getattr(config, "MODEL_GPT4", "gpt-4.1")
    if kind == "mini":
        return getattr(config, "MODEL_GPT4_MINI", "gpt-4.1-mini")
    if kind == "o3mini":
        return getattr(config, "MODEL_O3_MINI", "o3-mini")
    # Fallback to mini
    return getattr(config, "MODEL_GPT4_MINI", "gpt-4.1-mini")


def autogen_llm_config(model: str | None = None, *, temperature: float = 0.2) -> Dict[str, Any]:
    """Builds LLM config for AutoGen AssistantAgent/GroupChatManager.

    If model is None, uses mini model by default.
    """
    model = model or model_for("mini")
    return {
        "config_list": [{"model": model, "api_key": get_api_key()}],
        "temperature": temperature,
    }
