import pytest
import asyncio
from backend.agents import expert_gc

@pytest.mark.asyncio
async def test_gc_timeout(monkeypatch):
    """
    Тест: Проверяет, что `run_chat_with_autogen` прерывается по таймауту.
    """
    # Подменяем GC-реализацию, чтобы она "зависла"
    async def _slow_gc(*a, **k):
        await asyncio.sleep(0.2)

    monkeypatch.setattr(expert_gc, "auto_run_groupchat", _slow_gc)
    
    # Устанавливаем очень маленький таймаут
    monkeypatch.setenv("GC_TIMEOUT_SEC", "0.01")
    from backend import config
    config.config.reload()

    # Ожидаем, что функция вернет сообщение о таймауте
    res = await expert_gc.run_chat_with_autogen([], [])
    assert "Timeout" in res["content"]
