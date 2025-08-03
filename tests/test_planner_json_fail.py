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
    from backend.json_utils import BadJSON
    
    async def mock_bad_plan(q, slots, logger):
        raise BadJSON("Mock JSON parsing failure")
    
    monkeypatch.setattr(
        p, "_build_plan",
        mock_bad_plan
    )
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as ws:
            # Отправляем в правильном формате
            await ws.send('{"message": "сложный вопрос"}')
            
            # Ищем сообщение об ошибке среди нескольких сообщений
            error_found = False
            for _ in range(5):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(response)
                    
                    # Пропускаем session сообщения
                    if data.get("type") == "session":
                        continue
                        
                    # Ищем системное сообщение или ошибку
                    if (data.get("role") == "system" or 
                        data.get("type") == "error" or
                        "ошибка" in str(data).lower()):
                        error_found = True
                        break
                        
                except asyncio.TimeoutError:
                    break
                    
            assert error_found, "No error message received after JSON parsing failure"
            assert "затруднился" in data["content"]
    except asyncio.TimeoutError:
        pytest.fail("Test timed out waiting for response.")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")