import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch

from backend.chat_core import chat_stream

# Dummy metrics with no-op labels and inc
class DummyMetric:
    def labels(self, **kwargs):
        return self
    def inc(self):
        pass

class DummyMetricsModule:
    STARTED = DummyMetric()

# async generator that yields nothing
async def empty_listen(thread_id):
    if False:
        yield

@pytest.mark.asyncio
@patch('backend.chat_core.handle_message', new_callable=AsyncMock)
@patch('backend.chat_core.get_mem', lambda tid: {})
@patch('backend.chat_core.get_current_thread_messages', lambda tid: [])
@patch('backend.chat_core.save_dialog_full', lambda tid, msgs: None)
@patch('backend.status_bus.listen', lambda tid: empty_listen(tid))
async def test_chat_stream_simple(mock_handle):
    """Unit-тест chat_stream: одно сообщение обрабатывается и отдаётся в выход"""
    # Подготовка
    mock_handle.return_value = {"type": "chat", "role": "assistant", "content": "Echo: hello"}
    in_q = asyncio.Queue()
    out_q = asyncio.Queue()
    await in_q.put(json.dumps({"message": "hello"}))
    await in_q.put(None)

    # Запуск
    await chat_stream("test-thread", in_q, out_q)

    # Проверка результатов
    msg = await out_q.get()
    assert isinstance(msg, dict)
    assert msg.get("type") == "chat"
    assert msg.get("content") == "Echo: hello"
    # Сигнал завершения
    end = await out_q.get()
    assert end is None
