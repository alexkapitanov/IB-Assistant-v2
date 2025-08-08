import logging

from backend import status_bus


async def _classify_intent(user_q: str, slots: dict):
    """Классифицирует намерение пользователя"""
    user_q_lower = user_q.lower()

    # Простая эвристика классификации
    if any(
        greeting in user_q_lower for greeting in ["привет", "здравств", "добр", "спасибо", "пока"]
    ):
        return "small_talk", 0.9
    elif "файл" in user_q_lower or "скачать" in user_q_lower:
        return "file", 0.8
    else:
        return "request", 0.7




async def handle_message(thread_id: str, user_q: str, slots: dict, session_logger: logging.Logger):
    # Отправляем статус "thinking"
    await status_bus.publish(thread_id, "thinking", "Обработка запроса")

    intent, conf = await _classify_intent(user_q, slots)
    session_logger.info("Intent: %s, conf: %.2f", intent, conf)

    # Существующий критик и проверки остаются в Planner/ExpertGC; на этапе интента без доп. критика

    # small_talk значит пользователь сказал «Привет» или «Спасибо»:
    if intent == "small_talk":
        return {"type": "chat", "role": "assistant", "content": "Здравствуйте! Чем могу помочь?"}

    if intent == "file":
        if key := slots.get("file_key"):
            from backend.agents.file_retrieval import get_file_link

            return await get_file_link(key)
        # если файла нет – продолжаем как request

    # intent == "request" | "kb_search"
    # 1) Сначала пробуем KB-Search (reuse → сразу ответ, escalate → обогащённый контекст для Planner)
    try:
        await status_bus.publish(thread_id, "searching", "Поиск в базе знаний")
        from backend.agents.kb_search import kb_search
        action, data = await kb_search(user_q, expected_tokens=1500, thread_id=thread_id)
        if action == "reuse":
            # финальный ответ из памяти
            await status_bus.publish(thread_id, "generating", "Финализация ответа")
            # Опционально пропустить через Refine
            try:
                from backend.agents.refine import refine_answer
                refined = await refine_answer(data)
                return {"type": "chat", "role": "assistant", "content": refined or data}
            except Exception:
                return {"type": "chat", "role": "assistant", "content": data}
        # иначе data — контекст для Planner
        kb_context = data
    except Exception:
        kb_context = None

    await status_bus.publish(thread_id, "searching", "Построение плана")

    from backend.agents.planner import ask_planner
    # Пытаемся построить план; если JSON парсинг упал — отдаем дружелюбную системную ошибку
    try:
        plan = await ask_planner(thread_id, user_q, slots | ({"kb": kb_context} if kb_context else {}), session_logger)
    except Exception as e:
        # Узнаем BadJSON по имени класса, чтобы не тащить импорт в горячий путь
        if e.__class__.__name__ == "BadJSON":
            return {
                "type": "error",
                "role": "system",
                "content": "Я затруднился разобрать ответ планировщика. Попробуйте уточнить запрос.",
            }
        raise

    if plan["need_clarify"]:
        return {"type": "chat", "role": "assistant", "content": plan["clarify"]}

    if plan["need_escalate"]:
        from backend.agents.expert_gc import run_expert_gc

        resp = await run_expert_gc(thread_id, plan["plan"], {"slots": slots})
        # Refine stage
        try:
            from backend.agents.refine import refine_answer
            refined = await refine_answer(resp.get("content") if isinstance(resp, dict) else resp)
            return {"type": "chat", "role": "assistant", "content": refined or (resp.get("content") if isinstance(resp, dict) else resp)}
        except Exception:
            return {"type": "chat", "role": "assistant", "content": (resp.get("content") if isinstance(resp, dict) else resp)}

    # Если есть готовый draft - отправляем статус generating + refine
    await status_bus.publish(thread_id, "generating", "Финализация ответа")
    draft = plan["draft"]
    try:
        from backend.agents.refine import refine_answer
        refined = await refine_answer(draft)
        return {"type": "chat", "role": "assistant", "content": refined or draft}
    except Exception:
        return {"type": "chat", "role": "assistant", "content": draft}
