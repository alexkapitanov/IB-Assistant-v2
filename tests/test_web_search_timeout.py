import pytest, asyncio, importlib, types, os

@pytest.mark.asyncio
async def test_web_search_timeout(monkeypatch):
    # Заглушаем browser_search, чтобы «висел»
    from backend.agents import web_search as ws
    async def _slow(*a, **k): await asyncio.sleep(999)
    monkeypatch.setattr(ws, "browser_search", _slow)

    monkeypatch.setenv("WEB_SEARCH_TIMEOUT_SEC", "0")
    # we need to reload config, not the agent module itself
    from backend import config
    importlib.reload(config)

    out = await ws.web_search("test")
    assert out == "TIMEOUT"
