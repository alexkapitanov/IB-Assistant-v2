from unittest.mock import Mock
import pytest, asyncio
from backend.agents import expert_gc
from backend import config

@pytest.mark.asyncio
async def test_gc_timeout(monkeypatch):
    # подменяем GC-реализацию, чтобы спала дольше таймаута
    async def _slow_gc(*a, **k): await asyncio.sleep(0.1)
    monkeypatch.setattr(expert_gc, "auto_run_groupchat", _slow_gc, raising=False)

    monkeypatch.setenv("GC_TIMEOUT_SEC", "0")   # таймаут 0 с
    from importlib import reload; reload(config)  # перечитать env
    
    mock_logger = Mock()
    out = await expert_gc.run_expert_gc("tid","Q",{}, {}, mock_logger)
    assert out["role"] == "system" and "Время вышло" in out["content"]
