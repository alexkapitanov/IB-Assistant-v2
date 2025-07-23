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
        if msg is None:
            break
        try:
            # Теперь мы ожидаем только JSON. Если приходит не JSON, это ошибка.
            try:
                data = json.loads(msg)
                user_message = data.get("message")
                if user_message is None:
                    # Если в JSON нет ключа 'message', это тоже ошибка.
                    raise ValueError("Ключ 'message' отсутствует в JSON-объекте")
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                # Логируем ошибку парсинга и отправляем системное сообщение
                session_logger.error(f"Ошибка парсинга входящего сообщения: {e}. Сообщение: '{msg}'")
                await outgoing.put({
                    "type": "error",
                    "role": "system",
                    "content": f"Ошибка формата запроса: {e}. Ожидается JSON с ключом 'message'."
                })
                continue # Пропускаем остальную часть цикла и ждем следующее сообщение

            slots = get_mem(thread_id)
            
            session_logger.info(f"Received message: '{user_message}'")
            
            resp = await handle_message(thread_id, user_message, slots, session_logger)
            if resp:
                await outgoing.put(resp)
            
            session_logger.info("Response sent to outgoing queue.")

            # Сохраняем полную историю диалога
            messages = get_current_thread_messages(thread_id)
            save_dialog_full(thread_id, messages)
            session_logger.info(f"Dialog history saved for thread {thread_id}.")
            
        except Exception as e:
            # Логируем полное исключение в лог сессии
            session_logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")
            
            # Отправляем пользователю общее сообщение об ошибке
            await outgoing.put({
                "type": "error",
                "role": "system",
                "content": f"Произошла внутренняя ошибка сервера. Мы уже работаем над ее устранением. Пожалуйста, попробуйте позже. ID ошибки: {thread_id}"
            })
    
    session_logger.info("Chat stream finished.")
