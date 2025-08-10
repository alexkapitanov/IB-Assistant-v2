
import asyncio
import json

import websockets


async def send_test_message():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # 1. Отправляем приветственное сообщение для установки соединения
        await websocket.send(json.dumps({"message": "hello"}))
        response = await websocket.recv()
        print(f"<- {response}")

        # 2. Отправляем тестовый запрос
        test_query = "Что такое SIEM и как он помогает в обеспечении безопасности?"
        print(f"> {test_query}")
        await websocket.send(json.dumps({"message": test_query}))

        # 3. Получаем и выводим все ответы от сервера
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                print(f"<- {response}")
                # Простое условие для завершения клиента после получения ответа, 
                # содержащего ключевые слова из предметной области.
                # В реальном сценарии здесь может быть более сложная логика.
                if "SIEM" in response and "безопасности" in response:
                    break
            except asyncio.TimeoutError:
                print("Timeout: не получен ответ от сервера.")
                break
            except websockets.exceptions.ConnectionClosed:
                print("Соединение закрыто.")
                break

if __name__ == "__main__":
    asyncio.run(send_test_message())
