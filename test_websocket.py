#!/usr/bin/env python3
"""
Простой тест WebSocket подключения к IB-Assistant backend
"""

import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Подключение к WebSocket успешно!")
            
            # Отправляем тестовое сообщение
            test_message = "привет"
            await websocket.send(test_message)
            print(f"📤 Отправлено: {test_message}")
            
            # Ждем ответ
            print("⏳ Ожидаем ответ...")
            
            # Получаем несколько сообщений
            message_count = 0
            timeout_seconds = 30
            
            while message_count < 5:  # Ограничим количество сообщений
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
                    data = json.loads(response)
                    
                    if data.get("type") == "status":
                        status = data.get("status", "unknown")
                        print(f"🔄 Статус: {status}")
                        
                    elif data.get("type") == "message" or "content" in data:
                        content = data.get("content", data.get("answer", response))
                        print(f"📥 Ответ: {content[:100]}...")
                        break
                        
                    message_count += 1
                    
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout после {timeout_seconds} секунд")
                    break
                except json.JSONDecodeError:
                    print(f"📥 Сырой ответ: {response}")
                    break
                    
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 Тестируем WebSocket подключение...")
    asyncio.run(test_websocket())
