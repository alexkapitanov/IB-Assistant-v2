import asyncio
import pytest
from backend.agents import web_search as ws

@pytest.mark.asyncio
async def test_web_search_timeout(monkeypatch):
    """
    Тест: Проверяет, что `web_search` прерывается по таймауту.
    """
    # Заглушаем browser_search, чтобы он "завис"
    async def _slow(*a, **k):
        await asyncio.sleep(0.2)

    monkeypatch.setattr(ws, "browser_search", _slow)
    
    # Устанавливаем очень маленький таймаут
    monkeypatch.setenv("WEB_SEARCH_TIMEOUT_SEC", "0.01")
    from backend import config
    config.config.reload()

    out = await ws.web_search("test")
    assert "TIMEOUT" in out
