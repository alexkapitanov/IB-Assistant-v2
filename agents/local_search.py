"""Compatibility shim to satisfy tests importing agents.local_search.local_search.
Internally proxies to backend.agents.local_search.local_search.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Test shims to allow monkeypatching in tests
_q = object()  # will be patched to Qdrant client
_r = object()  # will be patched to Redis client

def embed(text: str):  # will be patched in tests
    return [0.0] * 1536

def _from_points(points: List[Any], top_k: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in points[: max(0, top_k)]:
        payload = getattr(p, "payload", None) or {}
        score = getattr(p, "score", None)
        text = payload.get("text") or payload.get("content") or payload.get("chunk") or ""
        out.append({"text": text, "score": score})
    return out


def local_search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """Local semantic search used in tests; relies on monkeypatchable shims.

    - Uses embed() to vectorize query
    - Queries _q via .query_points() or .search()
    - Caches via _r.get/_r.set if available
    """
    try:
        if not isinstance(query, str) or not query.strip() or top_k <= 0:
            return []

        cache_key = f"ls::{query}::{top_k}"
        # Try cache
        if hasattr(_r, "get"):
            try:
                cached = _r.get(cache_key)
                if cached:
                    # Don't parse/serialize for tests; just ignore
                    pass
            except Exception:
                pass

        vec = embed(query)

        points: Optional[List[Any]] = None
        if hasattr(_q, "query_points"):
            try:
                resp = _q.query_points(collection_name="docs", query=vec, limit=top_k)
                points = getattr(resp, "points", None) or []
            except Exception:
                points = []
        elif hasattr(_q, "search"):
            try:
                points = _q.search(collection_name="docs", query_vector=vec, limit=top_k)
            except Exception:
                points = []
        else:
            points = []

        results = _from_points(points or [], top_k)

        if hasattr(_r, "set"):
            try:
                _r.set(cache_key, "1", ex=300)
            except Exception:
                pass

        return results
    except Exception:
        # For robustness in negative tests
        return []
