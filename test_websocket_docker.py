#!/usr/bin/env python3
"""
Тест WebSocket соединения с backend через Docker сеть
"""

import asyncio
import websockets
import json
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket():
    # Тестируем WebSocket соединение
    uri = "ws://localhost:8000/ws"
    print(f"Подключаемся к {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket соединение установлено!")
            
            # Отправляем тестовое сообщение
            test_message = {
                "content": "Привет! Это тест.",
                "chat_id": "test-chat-123"
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"📤 Отправлено: {test_message}")
            
            # Ждем ответ
            print("⏳ Ждем ответ...")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Получен ответ: {response}")
            except asyncio.TimeoutError:
                print("⏰ Timeout - ответ не получен за 5 сек")
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
