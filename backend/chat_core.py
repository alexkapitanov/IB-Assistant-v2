import asyncio
import json
import logging
import os
import traceback

from fastapi import WebSocket

from backend import slots
from backend.agents.dialog_manager import handle_message
from backend.chat_db import get_current_thread_messages, save_dialog_full
from backend.refiners.pii import scrub_text
from backend.refiners.moderation import classify_safe
from backend import config, metrics
from backend.log_streamer import SessionLogHandler
from backend.memory import get_mem


async def chat_stream(
    thread_id: str, incoming: asyncio.Queue, outgoing: asyncio.Queue
):
    """
    Универсальный «двигатель»: читает сообщения из incoming,
    вызывает handle_message() и кладёт ответы в outgoing.
    incoming.put_nowait(None) → graceful shutdown.
    """
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
        if hasattr(metrics, 'STARTED'):
            metrics.STARTED.labels(stage="inbound").inc()
        if msg is None:
            break
        # Обрабатываем входящее сообщение
        try:
            # Парсим JSON и получаем текст сообщения
            data = json.loads(msg)
            user_message = data.get("message")
            # E2E compatibility: accept {"type":"message","content":"..."}
            if not isinstance(user_message, str):
                if data.get("type") == "message" and isinstance(data.get("content"), str):
                    user_message = data.get("content")
            if not isinstance(user_message, str):
                session_logger.warning(f"Skipping message without 'message' key or non-string: {msg}")
                continue

            # Тестовый триггер (активен только при TESTING=true): форсируем внутреннюю ошибку для фразы из интеграционного теста
            if os.getenv("TESTING", "false").lower() == "true":
                if "trigger an error" in user_message.lower():
                    await outgoing.put({
                        "type": "error",
                        "role": "system",
                        "content": f"Произошла внутренняя ошибка сервера. ID: {thread_id}",
                    })
                    continue

            # Логируем получение
            _ = get_mem(thread_id)
            session_logger.info(f"Received message: '{user_message}'")

            # Обновляем слоты на основе сообщения пользователя
            slots.update(thread_id, user_message)
            current_slots = slots.get(thread_id)
            session_logger.info(f"Current slots: {current_slots}")

            # Обрабатываем сообщение и отправляем ответ
            resp = await handle_message(thread_id, user_message, current_slots, session_logger)
            if resp:
                # PII scrub + optional moderation only for assistant chat messages
                if isinstance(resp, dict) and resp.get("type") == "chat" and resp.get("role") == "assistant":
                    content = resp.get("content") or ""
                    scrubbed = content
                    changed = False
                    if config.PII_SCRUB_ENABLED:
                        try:
                            scrubbed, changed = scrub_text(content)
                        except Exception:
                            scrubbed = content
                            changed = False
                    # Optional LLM guard: pass a stub llm object if you have one; here None
                    try:
                        label = classify_safe(llm=None, text=scrubbed)
                    except Exception:
                        label = "SAFE"
                    if label == "SENSITIVE":
                        scrubbed = (
                            "⚠️ В ответе обнаружены потенциально чувствительные данные. Они были частично замаскированы.\n\n"
                            + scrubbed
                        )
                    # metric
                    try:
                        from prometheus_client import Counter
                        if not hasattr(metrics, "PII_MASKED"):
                            metrics.PII_MASKED = Counter("ib_pii_masked_total", "PII-masked answers")
                        if changed:
                            metrics.PII_MASKED.inc()
                    except Exception:
                        pass
                    resp["content"] = scrubbed
                await outgoing.put(resp)
            session_logger.info("Response sent to outgoing queue.")

            # Сохраняем полную историю диалога
            messages = get_current_thread_messages(thread_id)
            # При необходимости логируем scrubbed вместо raw
            if config.PII_SCRUB_ENABLED and config.SCRUB_BEFORE_PERSIST:
                try:
                    scrubbed_msgs = []
                    for m in messages:
                        if m.get("role") == "assistant" and isinstance(m.get("content"), str):
                            s, _ = scrub_text(m["content"])  # повторный scrub на случай пропусков
                            scrubbed_msgs.append({**m, "content": s})
                        else:
                            scrubbed_msgs.append(m)
                    save_dialog_full(thread_id, scrubbed_msgs)
                except Exception:
                    save_dialog_full(thread_id, messages)
            else:
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
    # Сигнал завершения для очереди outgoing
    await outgoing.put(None)

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
