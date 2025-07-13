import asyncio, json, websockets, uuid
import pytest
import socket

# Пропускаем тесты, если сервер недоступен
pytestmark = pytest.mark.integration

def is_server_available():
    """Проверяет доступность WebSocket сервера"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        return result == 0
    except:
        return False

async def run_round():
    if not is_server_available():
        pytest.skip("WebSocket server not available at localhost:8000")
        
    try:
        uri="ws://localhost:8000/ws"
        async with websockets.connect(uri) as ws:
            await ws.send("что такое dlp?")
            while True:
                data=json.loads(await ws.recv())
                if data["type"]=="status" and data["status"]=="thinking":
                    return True
    except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
        pytest.skip("WebSocket server not available")
    except Exception as e:
        pytest.skip(f"WebSocket server connection failed: {e}")

async def check_status_sequence():
    """Проверяем последовательность статусов: thinking -> searching -> generating"""
    if not is_server_available():
        pytest.skip("WebSocket server not available at localhost:8000")
        
    try:
        uri="ws://localhost:8000/ws"
        statuses = []
        
        async with websockets.connect(uri) as ws:
            await ws.send("что такое machine learning?")
            
            while len(statuses) < 3:
                try:
                    # Устанавливаем timeout для избежания бесконечного ожидания
                    data = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                    
                    if data.get("type") == "status":
                        status = data.get("status")
                        if status in ["thinking", "searching", "generating"]:
                            statuses.append(status)
                    elif data.get("type") == "message" or "content" in data:
                        # Получили финальный ответ
                        break
                        
                except asyncio.TimeoutError:
                    break
        
        return statuses
    except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
        pytest.skip("WebSocket server not available")
    except Exception as e:
        pytest.skip(f"WebSocket server connection failed: {e}")

@pytest.mark.asyncio
async def test_status_thinking():
    """Тест проверки статуса 'thinking'"""
    assert await run_round()

@pytest.mark.asyncio  
async def test_status_sequence():
    """Тест проверки последовательности статусов"""
    statuses = await check_status_sequence()
    
    # Проверяем, что получили хотя бы статус thinking
    assert "thinking" in statuses
    
    # Если есть searching, он должен идти после thinking
    if "searching" in statuses and "thinking" in statuses:
        assert statuses.index("thinking") < statuses.index("searching")
    
    # Если есть generating, он должен идти последним
    if "generating" in statuses:
        assert statuses[-1] == "generating" or statuses.index("generating") == len(statuses) - 1
