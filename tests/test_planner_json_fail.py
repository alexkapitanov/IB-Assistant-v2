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
    async def mock_bad_json(tid, q, s, history):
        raise p.BadJSON("fail")
    monkeypatch.setattr(
        p, "_call_planner_llm",
        mock_bad_json
    )
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send('{"text": "сложный вопрос"}')
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(response)
            assert data["role"] == "system"
            assert "затруднился" in data["content"]
    except asyncio.TimeoutError:
        pytest.fail("Test timed out waiting for response.")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")