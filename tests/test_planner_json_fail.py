import asyncio, websockets, json, os, pytest
import socket
from contextlib import closing

def _check_server_available(host="localhost", port=8000):
    """Check if WebSocket server is available"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0

@pytest.mark.asyncio
@pytest.mark.integration
async def test_planner_json_fail(monkeypatch):
    if not _check_server_available():
        pytest.skip("WebSocket server not available")
        
    # подкладываем broken ответ от LLM
    import backend.agents.planner as p
    monkeypatch.setattr(
        p, "_call_planner_llm",
        lambda tid, q, s: (_ for _ in ()).throw(p.BadJSON("fail"))
    )
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri, timeout=5) as ws:
            await ws.send("test")
            msg = json.loads(await ws.recv())
            assert msg["role"] == "system" and "Не смог" in msg["content"]
    except (websockets.exceptions.ConnectionClosed, OSError) as e:
        pytest.skip(f"WebSocket server unavailable: {e}")