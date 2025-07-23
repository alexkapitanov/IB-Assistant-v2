from backend.embedding_pool import get_embedding_async as get_async_vec
from backend.qdrant_client import qdr
import numpy as np
import logging
import asyncio
import time

SIM_HARD = 0.95    # reuse без изменений
SIM_SOFT = 0.60    # ниже → прямая эскалация

async def kb_search(query:str, expected_tokens:int=1500):
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
    try:
        hits = qdr.search(collection_name="dialogs", query_vector=vec, limit=k)
        logging.info(f"Found {len(hits)} similar dialogs.")
        if hits and hits[0].score >= SIM_HARD:
            logging.info(f"Found a very similar dialog with score {hits[0].score:.4f}. Reusing answer.")
            return "reuse", hits[0].payload["answer"]
    except Exception as e:
        logging.warning(f"Could not search in 'dialogs' collection: {e}")
        hits = []

    # 2. Сбор контекста для эскалации
    context = {
        "similar_dialogs": [h.payload for h in hits if h.score >= SIM_SOFT]
    }
    logging.info(f"Found {len(context['similar_dialogs'])} dialogs with score >= {SIM_SOFT}.")

    # 3. Поиск по документам (RAG)
    try:
        # В README указана коллекция 'docs', используем ее.
        rag_hits = qdr.search(collection_name="docs", query_vector=vec, limit=k)
        context["rag"] = [h.payload for h in rag_hits] # Сохраняем payload, а не весь объект
        logging.info(f"Found {len(rag_hits)} relevant document chunks.")
    except Exception as e:
        logging.error(f"Failed to search in 'docs' collection: {e}")
        context["rag"] = []

    logging.info("Escalating with the collected context.")
    return "escalate", context

