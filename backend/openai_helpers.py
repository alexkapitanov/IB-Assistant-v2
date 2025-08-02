# backend/openai_helpers.py
import os
import openai
import time
import json
import logging
from openai import OpenAI, AsyncClient
from backend.utils import is_test_mode
from backend.token_counter import count_tokens
from qdrant_client import QdrantClient, models
from backend import config

logger = logging.getLogger(__name__)

# Глобальные переменные для клиентов, чтобы переиспользовать соединения
_client: OpenAI | None = None
_async_client: AsyncClient | None = None

def _get_client() -> OpenAI:
    """Ленивая инициализация синхронного OpenAI клиента."""
    global _client
    api_key = config.config.OPENAI_API_KEY
    if not api_key or (api_key.startswith("test_") or api_key == ""):
        if api_key != "stub":
            raise RuntimeError("OPENAI_API_KEY env var missing or dummy")
    
    if _client is None or _client.api_key != api_key:
        _client = OpenAI(api_key=api_key)
    return _client

def _get_async_client() -> AsyncClient:
    """Ленивая инициализация асинхронного OpenAI клиента."""
    global _async_client
    api_key = config.config.OPENAI_API_KEY
    if not api_key or (api_key.startswith("test_") or api_key == ""):
        if api_key != "stub":
            raise RuntimeError("OPENAI_API_KEY env var missing or dummy")

    if _async_client is None or _async_client.api_key != api_key:
        _async_client = AsyncClient(api_key=api_key)
    return _async_client

async def browser_search(query: str, k: int = 5) -> str:
    """
    Выполняет web-поиск через OpenAI Browser-tool.
    Возвращает markdown-список заголовок+URL+excerpt (k результатов).
    """
    client = _get_async_client()
    resp = await client.chat.completions.create(
        model="o3-mini",
        tools=[{"type": "browser", "calls": [{"name": "search"}]}],
        tool_choice={"type": "browser", "function_name": "search"},
        messages=[{"role": "user", "content": query}],
        extra_headers={"browser-search-k": str(k)},
    )
    snippets = []
    # Убедимся, что tools_output не пустой и содержит результаты
    if resp.tools_output and resp.tools_output[0].get("results"):
        for item in resp.tools_output[0]["results"][:k]:
            snippets.append(f"- **{item['title']}** — {item['url']}\n  {item['excerpt']}")
    return "\n".join(snippets)

async def call_llm(model: str, prompt: str, tools: list | None = None, temperature: float = 0, thread_id: str = None, turn_index: int = None):
    """
    Вызов LLM с проверкой API ключа, поддержкой stub-режима и учетом токенов
    Возвращает ответ и время задержки в миллисекундах.
    """
    api_key = config.config.OPENAI_API_KEY
    prompt_tokens = count_tokens(prompt, model)

    if api_key == "stub":
        completion_tokens = 10
        if "Planner-агент" in prompt:
            response = '{"need_clarify": false, "clarify": "", "need_escalate": false, "draft": "Тестовый ответ планировщика"}'
        else:
            response = f"[stub] Тестовый ответ для промпта: {prompt[:20]}..."
        _log_token_usage(thread_id, turn_index, model, prompt_tokens, completion_tokens)
        return response, 0

    if is_test_mode():
        if "классификатор" in prompt.lower():
            content = "simple_faq"
        else:
            content = "Это тестовый ответ от ассистента. API ключ не настроен для реальных запросов к OpenAI."
        completion_tokens = count_tokens(content, model)
        _log_token_usage(thread_id, turn_index, model, prompt_tokens, completion_tokens)
        return content, 100

    client = _get_client()
    t0 = time.time()

    params = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if tools:
        params["tools"] = tools
    if model != "o3-mini":
        params["temperature"] = temperature

    rsp = client.chat.completions.create(**params)
    content = rsp.choices[0].message.content.strip()
    latency_ms = int((time.time() - t0) * 1000)
    
    completion_tokens = count_tokens(content, model)
    _log_token_usage(thread_id, turn_index, model, prompt_tokens, completion_tokens)
    
    return content, latency_ms

def _log_token_usage(thread_id: str, turn_index: int, model: str, prompt_tokens: int, completion_tokens: int):
    """Логирует использование токенов"""
    if thread_id and turn_index is not None:
        try:
            from backend.chat_db import log_message
            meta_data = {
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
            log_message(thread_id, turn_index, "meta", json.dumps(meta_data))
        except ImportError:
            pass

def get_qdrant_client():
    return QdrantClient(host=config.config.QDRANT_HOST, port=6333)

async def setup_qdrant(recreate_collection: bool = False):
    """
    Инициализирует Qdrant, создает коллекцию, если она не существует.
    """
    qdrant_client = get_qdrant_client()
    collection_name = config.config.QDRANT_COLLECTION_NAME
    
    if recreate_collection:
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        logger.info(f"Collection '{collection_name}' recreated.")
        return

    try:
        qdrant_client.get_collection(collection_name=collection_name)
        logger.info(f"Collection '{collection_name}' already exists.")
    except Exception:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        logger.info(f"Collection '{collection_name}' created.")
