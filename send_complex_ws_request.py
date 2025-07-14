import websockets
import asyncio
import json

async def send_request():
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Успешное подключение к WebSocket!")

            # Отправляем сообщение
            message = {"message": "сравни DLP-решения от Infowatch и Zecurion по функциональности, стоимости и интеграции"}
            print(f"📤 Отправка: {json.dumps(message)}")
            await websocket.send(json.dumps(message))

            # Ожидаем ответ
            print("⏳ Ожидание ответа...")
            while True:
                response_str = await websocket.recv()
                response = json.loads(response_str)
                print(f"📥 Получено: {response}")
                # Финальный ответ имеет тип 'chat' и роль 'assistant'
                if response.get("type") == "chat" and response.get("role") == "assistant":
                    break
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(send_request())
