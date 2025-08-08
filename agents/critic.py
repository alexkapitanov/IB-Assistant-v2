"""Compatibility layer for tests expecting agents.critic module."""
from __future__ import annotations

import re
from typing import Optional


def _score_to_float(text: str) -> Optional[float]:
    """Parse common score formats like '0.83 / 1', 'score:0.7', or return None."""
    if not isinstance(text, str):
        return None
    s = text.strip().lower()
    # Extract first floating number pattern
    m = re.search(r"([0-9]+[\.,][0-9]+|[01])", s)
    if not m:
        return None
    val = m.group(1).replace(",", ".")
    try:
        f = float(val)
    except ValueError:
        return None
    if 0.0 <= f <= 1.0:
        return f
    return None


async def ask_critic(text: str) -> bool:
    """Compatibility stub used by tests to monkeypatch this function."""
    # Default heuristic: confident if long enough
    return len(text or "") > 20
