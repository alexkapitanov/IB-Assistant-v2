import asyncio, uuid
from backend.router import handle_message

async def chat_stream(thread_id: str,
                      incoming: asyncio.Queue,
                      outgoing: asyncio.Queue):
    """
    Универсальный «двигатель»: читает сообщения из incoming,
    вызывает handle_message() и кладёт ответы в outgoing.
    incoming.put_nowait(None) → graceful shutdown.
    """
    import json
    while True:
        msg = await incoming.get()
        if msg is None:
            break
        try:
            # Пытаемся парсить JSON из входящего сообщения
            try:
                data = json.loads(msg)
                # Извлекаем текст сообщения из JSON
                user_message = data.get("message", msg)
            except (json.JSONDecodeError, TypeError):
                # Если не удалось парсить JSON, возвращаем ошибку
                await outgoing.put({
                    "type": "chat",
                    "role": "system",
                    "content": "⚠️ JSON parsing error: ожидается корректный JSON"
                })
                continue
                
            resp = await handle_message(thread_id, user_message)
            if resp:
                await outgoing.put(resp)
        except Exception as e:
            await outgoing.put({
                "type": "chat",
                "role": "system",
                "content": f"⚠️ Ошибка сервера: {e}"
            })
