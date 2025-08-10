import logging

from backend import status_bus
from backend.agents.web_search import web_search as web_search_tool
from backend.embedding_pool import get_embedding_async as get_async_vec
from backend.qdrant_connection import qdr
from typing import Any, Dict, List

SIM_HARD = 0.95  # reuse без изменений
SIM_SOFT = 0.60  # ниже → прямая эскалация


async def kb_search(query: str, expected_tokens: int = 1500, *, thread_id: str | None = None, slots: dict | None = None):
    """
    Выполняет поиск по базе знаний (диалоги и документы).
    Возвращает кортеж (action, data), где action - "reuse" или "escalate".
    """
    logging.info(f"kb_search started for query: '{query}'")
    vec = await get_async_vec(query)
    # Динамический подбор k в зависимости от ожидаемой длины ответа
    k = max(3, min(10, expected_tokens // 400))
    logging.info(f"Dynamic k={k} for search.")

    # 1. Поиск по существующим диалогам
    hits = []
    try:
        if qdr is None:
            raise RuntimeError("Qdrant client is not initialized")
        hits = qdr.search(collection_name="dialogs", query_vector=vec, limit=k)
        logging.info(f"Found {len(hits)} similar dialogs.")
        if hits and hits[0].score >= SIM_HARD:
            logging.info(
                f"Found a very similar dialog with score {hits[0].score:.4f}. Reusing answer."
            )
            payload0 = getattr(hits[0], "payload", None)
            if isinstance(payload0, dict) and "answer" in payload0:
                return "reuse", payload0["answer"]
    except Exception as e:
        logging.warning(f"Could not search in 'dialogs' collection: {e}")
        hits = []

    # 2. Сбор контекста для эскалации
    context: Dict[str, Any] = {"similar_dialogs": [h.payload for h in hits if getattr(h, "score", 0) >= SIM_SOFT], "rag": []}
    try:
        sim_list = context.get("similar_dialogs") or []
        logging.info(f"Found {len(sim_list)} dialogs with score >= {SIM_SOFT}.")
    except Exception:
        logging.info("Found 0 dialogs with score >= threshold (logging-safe)")

    # 3. Поиск по документам (RAG)
    try:
        # В README указана коллекция 'docs', используем ее.
        if qdr is None:
            raise RuntimeError("Qdrant client is not initialized")
        rag_hits = qdr.search(collection_name="docs", query_vector=vec, limit=k)
        context["rag"] = [h.payload for h in rag_hits]  # Сохраняем payload, а не весь объект
        logging.info(f"Found {len(rag_hits)} relevant document chunks.")
    except Exception as e:
        logging.error(f"Failed to search in 'docs' collection: {e}")
        context["rag"] = []

    # 4. При отсутствии достаточного контекста попробуем web_search (с публикацией статуса)
    try:
        if thread_id:
            await status_bus.publish(thread_id, "web-search", "Поиск в интернете")
        # Вызов web_search может вернуть "TIMEOUT" по декоратору; добавим как источник, если не пусто
        # Передаем известные слоты, если они есть в контексте вызова
        web_md = await web_search_tool(query, slots=slots)
        if web_md:
            context["web"] = web_md
    except Exception as e:
        logging.warning(f"web_search failed: {e}")

    logging.info("Escalating with the collected context.")
    return "escalate", context
