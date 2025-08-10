import asyncio
import json

import pytest
import websockets

BASE_WS = "ws://localhost:8000/ws"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ws_smalltalk(monkeypatch):
    # Redirect OpenAI to fake service via env
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:8081/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_e2e")
    monkeypatch.setenv("DISABLE_WEB_SEARCH", "1")
    uri = BASE_WS
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "message", "content": "привет"}))
        # ожидание нескольких кадров, берём первый chat
        for _ in range(10):
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)
            if msg.get("type") == "chat" and msg.get("content"):
                assert "ошибка" not in msg.get("content", "").lower()
                return
    assert False, "Не получили chat-сообщение"
