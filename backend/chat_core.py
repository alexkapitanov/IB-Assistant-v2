import asyncio, uuid
from agents.dialog_manager import handle_message
from backend.memory import get_mem
from backend.log_streamer import SessionLogHandler
from backend.chat_db import save_dialog_full, get_current_thread_messages
import logging
import traceback

async def chat_stream(thread_id: str,
                      incoming: asyncio.Queue,
                      outgoing: asyncio.Queue):
    """
    Универсальный «двигатель»: читает сообщения из incoming,
    вызывает handle_message() и кладёт ответы в outgoing.
    incoming.put_nowait(None) → graceful shutdown.
    """
    import json
    from backend import status_bus

    # слушаем status_bus параллельно
    async def status_forward():
        async for data in status_bus.listen(thread_id):
            await outgoing.put({"type":"status", **data})
    status_task = asyncio.create_task(status_forward())

    # Создаем и настраиваем логгер для этой сессии
    session_logger = logging.getLogger(f"session_{thread_id}")
    session_logger.setLevel(logging.INFO)
    
    # Удаляем существующих обработчиков, чтобы избежать дублирования
    if session_logger.hasHandlers():
        session_logger.handlers.clear()
        
    # Добавляем наш кастомный обработчик
    session_handler = SessionLogHandler(thread_id)
    session_logger.addHandler(session_handler)
    
    session_logger.info("Chat stream started.")

    while True:
        msg = await incoming.get()
        # Считаем входящие запросы
        from backend import metrics
        metrics.STARTED.labels(stage="inbound").inc()
        if msg is None:
            break
        # Обрабатываем входящее сообщение
        try:
            # Парсим JSON и получаем текст сообщения
            data = json.loads(msg)
            user_message = data.get("message")
            if not isinstance(user_message, str):
                session_logger.warning(f"Skipping message without 'message' key or non-string: {msg}")
                continue

            # Логируем получение и считаем запрос
            slots = get_mem(thread_id)
            session_logger.info(f"Received message: '{user_message}'")

            # Обрабатываем сообщение и отправляем ответ
            resp = await handle_message(thread_id, user_message, slots, session_logger)
            if resp:
                await outgoing.put(resp)
            session_logger.info("Response sent to outgoing queue.")

            # Сохраняем полную историю диалога
            messages = get_current_thread_messages(thread_id)
            save_dialog_full(thread_id, messages)
            session_logger.info(f"Dialog history saved for thread {thread_id}.")
        except json.JSONDecodeError as e:
            # Логируем ошибку парсинга и уведомляем клиента
            session_logger.error(f"JSON decode error: {e}. Message: '{msg}'")
            await outgoing.put({
                "type": "error",
                "role": "system",
                "content": f"Ошибка формата запроса: {e}. Ожидается JSON с ключом 'message'."
            })
        except Exception as e:
            # Логируем полное исключение в лог сессии и уведомляем клиента
            session_logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")
            await outgoing.put({
                "type": "error",
                "role": "system",
                "content": f"Произошла внутренняя ошибка сервера. ID: {thread_id}"
            })
    
    session_logger.info("Chat stream finished.")
    # Отменяем задачу status_forward
    if 'status_task' in locals():
        status_task.cancel()
        try:
            await status_task
        except asyncio.CancelledError:
            pass
    # Сигнал завершения для очереди outgoing
    await outgoing.put(None)

from fastapi import WebSocket
import json

async def chat_stream_handler(ws: WebSocket):
    """
    Обёртка для chat_stream, работает с FastAPI WebSocket.
    Принимает одно входящее сообщение через receive_json,
    прогоняет через chat_stream и отправляет результаты обратно.
    """
    # Принять соединение
    await ws.accept()
    # Передать фиктивный thread_id
    thread_id = "test-thread"
    # Отправить session-сообщение клиенту
    await ws.send_json({"type": "session", "sessionId": thread_id})
    # Создать очереди для chat_stream
    in_q: asyncio.Queue = asyncio.Queue()
    out_q: asyncio.Queue = asyncio.Queue()
    # Получить одно входное сообщение и поставить в очередь
    msg = await ws.receive_json()
    # JSON-строка или dict?
    if isinstance(msg, dict):
        raw = json.dumps(msg)
    else:
        raw = msg
    await in_q.put(raw)
    await in_q.put(None)
    # Запустить обработчик
    task = asyncio.create_task(chat_stream(thread_id, in_q, out_q))
    # Отправить все выходные сообщения обратно клиенту
    while True:
        resp = await out_q.get()
        if resp is None:
            break
        await ws.send_json(resp)
    await task
