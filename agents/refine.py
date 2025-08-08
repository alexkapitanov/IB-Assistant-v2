"""Compatibility shim for tests importing agents.refine.refine.
Implements refine() that calls backend.openai_helpers.call_llm.
"""
from __future__ import annotations

from typing import Optional, Tuple

from backend.openai_helpers import call_llm


async def refine(draft: str) -> str:
    prompt = (
        "Улучшить текст: исправить стиль, фактические несостыковки и сделать более структурированным.\n"
        "Верни только улучшенный текст.\n---\n" + draft
    )
    text, _ = await call_llm("gpt-4.1-mini", prompt)
    return text
