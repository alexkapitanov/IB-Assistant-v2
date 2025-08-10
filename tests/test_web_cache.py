import asyncio
import json
import time

import pytest

from backend.agents import web_search as ws


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, val, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = val
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_cache_hit_and_store(monkeypatch):
    calls = {"n": 0}

    async def fake_browser_search(q, k=5):
        calls["n"] += 1
        return "- **Doc** — https://ex.com\n  excerpt"

    monkeypatch.setattr(ws, "browser_search", fake_browser_search)
    fake_r = _FakeRedis()
    monkeypatch.setattr(ws, "_get_redis", lambda: fake_r)
    monkeypatch.setenv("WEB_CACHE_TTL_SEC", "5")
    monkeypatch.setenv("WEB_CACHE_NEG_TTL_SEC", "5")

    from backend import config
    config.config.reload()

    # First call → MISS + STORE
    out1 = await ws.web_search("что такое dlp", slots={"topic": "DLP"})
    assert isinstance(out1, dict)
    assert out1.get("summary")
    assert calls["n"] == 1

    # Second call same query/slots → HIT (no extra calls)
    out2 = await ws.web_search("что   такое   dlp", slots={"topic": "dlp"})
    assert out2.get("summary") == out1.get("summary")
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_negative_cache(monkeypatch):
    async def slow_timeout(q, k=5):
        return ""  # simulate TIMEOUT/empty

    monkeypatch.setattr(ws, "browser_search", slow_timeout)
    fake_r = _FakeRedis()
    monkeypatch.setattr(ws, "_get_redis", lambda: fake_r)
    monkeypatch.setenv("WEB_CACHE_TTL_SEC", "5")
    monkeypatch.setenv("WEB_CACHE_NEG_TTL_SEC", "2")

    from backend import config
    config.config.reload()

    # First call → negative store
    out1 = await ws.web_search("что такое dlp", slots={"product": "InfoWatch"})
    assert out1 == "TIMEOUT"

    # Second call within NEG_TTL → should not call search again and still return TIMEOUT
    out2 = await ws.web_search("что такое dlp", slots={"product": "infowatch"})
    assert out2 == "TIMEOUT"


@pytest.mark.asyncio
async def test_canonicalization_changes_key(monkeypatch):
    async def fake_browser_search(q, k=5):
        return "md"

    monkeypatch.setattr(ws, "browser_search", fake_browser_search)
    fake_r = _FakeRedis()
    monkeypatch.setattr(ws, "_get_redis", lambda: fake_r)
    monkeypatch.setenv("WEB_CACHE_TTL_SEC", "5")

    from backend import config
    config.config.reload()

    out1 = await ws.web_search("что такое dlp", slots={"topic": "dlp"})
    out2 = await ws.web_search("что такое dlp", slots={"topic": "antivirus"})
    # Разные ключи → два отдельных вызова поиска
    assert out1.get("summary")
    assert out2.get("summary")
