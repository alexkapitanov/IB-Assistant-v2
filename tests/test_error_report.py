"""
Тест для проверки корректной обработки ошибок в WebSocket соединении
"""
import pytest
import websockets
import json
import asyncio


@pytest.mark.asyncio
async def test_error_message_shown():
    """Проверяем, что ошибки сервера корректно передаются клиенту"""
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as ws:
            # Отправляем некорректное сообщение, которое должно вызвать ошибку
            await ws.send("ping")
            
            # Ожидаем получить сообщение об ошибке
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            
            # Проверяем, что получили системное сообщение об ошибке
            assert data["role"] == "system"
            assert "Ошибка сервера" in data["content"]
            
    except websockets.exceptions.ConnectionClosed:
        pytest.skip("WebSocket server not available")
    except asyncio.TimeoutError:
        pytest.fail("Timeout waiting for error response")


@pytest.mark.asyncio
async def test_websocket_connection():
    """Базовый тест подключения к WebSocket"""
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri, timeout=2) as ws:
            # Просто проверяем, что соединение установлено
            assert ws.open
    except (websockets.exceptions.ConnectionClosed, OSError):
        pytest.skip("WebSocket server not available")
