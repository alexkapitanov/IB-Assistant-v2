
import asyncio
import json
import sys

import websockets


async def send_query(uri, query):
    print("--- Начинаю тест ---")
    print(f"Запрос: {query}")
    async with websockets.connect(uri) as websocket:
        # Получаем session_id
        session_info = await websocket.recv()
        print(f"<- {session_info}")
        session_id = json.loads(session_info)["sessionId"]

        # Отправляем запрос
        await websocket.send(json.dumps({"message": query, "session_id": session_id}))

        # Получаем и выводим ответы
        final_answer_received = False
        while not final_answer_received:
            try:
                message_str = await websocket.recv()
                print(f"<- {message_str}")
                message = json.loads(message_str)
                
                # Проверяем, является ли это финальным ответом
                if message.get("type") == "chat" and message.get("role") == "assistant":
                    print("\n--- Финальный ответ ---")
                    print(message.get("content"))
                    print("--- Тест завершен ---\n")
                    final_answer_received = True

            except websockets.ConnectionClosed as e:
                print(f"Соединение закрыто сервером: {e.code} {e.reason}")
                break
            except Exception as e:
                print(f"Произошла ошибка: {e}")
                break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = sys.argv[1]
        asyncio.run(send_query("ws://localhost:8000/ws", query_text))
    else:
        print("Ошибка: не передан текст запроса.")
        print("Пример использования: python test_runner.py 'Что такое DLP?'")

