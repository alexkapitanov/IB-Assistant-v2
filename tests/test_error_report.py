"""
Тест для проверки корректной обработки ошибок в WebSocket соединении
"""
import pytest
import websockets
import json
import asyncio
import socket
from contextlib import closing


def _check_server_available(host="localhost", port=8000):
    """Check if server is available"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_message_shown():
    """Проверяем, что ошибки сервера корректно передаются клиенту"""
    if not _check_server_available():
        pytest.skip("WebSocket server not available")
        
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as ws:
            # Отправляем некорректное сообщение (не JSON), которое должно вызвать ошибку
            await ws.send("this is not json")
    
            # Ожидаем получить сообщение об ошибке
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(response)
    
            # Проверяем, что получили системное сообщение об ошибке
            assert data.get("role") == "system"
            assert "ошибка" in data.get("content", "").lower()
    except asyncio.TimeoutError:
        pytest.fail("Test timed out waiting for error message.")
    except websockets.exceptions.ConnectionClosedOK:
        pytest.fail("Connection closed unexpectedly")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_connection():
    """Базовый тест подключения к WebSocket"""
    if not _check_server_available():
        pytest.skip("WebSocket server not available")
    
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as ws:
            # Проверим, что соединение открыто, но по-другому
            # У ClientConnection нет атрибута open/is_open, так что просто попробуем отправить ping
            await ws.ping()
    except Exception as e:
        pytest.fail(f"WebSocket connection failed: {e}")
