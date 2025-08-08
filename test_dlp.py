
import asyncio
import json
import websockets

async def send_query(uri, query):
    async with websockets.connect(uri) as websocket:
        # Получаем session_id
        session_info = await websocket.recv()
        print(f"<- {session_info}")
        session_id = json.loads(session_info)["sessionId"]

        # Отправляем запрос
        print(f"> {query}")
        await websocket.send(json.dumps({"message": query, "session_id": session_id}))

        # Получаем и выводим ответы
        while True:
            try:
                message = await websocket.recv()
                print(f"<- {message}")
                # Простое условие для завершения теста: если в ответе есть осмысленная часть.
                # В реальном тесте здесь может быть более сложная логика.
                if "DLP" in message or "система" in message:
                    break
            except websockets.ConnectionClosed:
                print("Соединение закрыто.")
                break

if __name__ == "__main__":
    asyncio.run(send_query("ws://localhost:8000/ws", "Что такое DLP?"))
