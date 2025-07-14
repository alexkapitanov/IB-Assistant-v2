import os, openai, time, json
from openai import OpenAI
from backend.utils import is_test_mode
from backend.token_counter import count_tokens

# Разрешённые модели: o3-mini, gpt-4.1-mini, gpt-4.1
# Проверяем API ключ при загрузке модуля
key = os.getenv("OPENAI_API_KEY")
# Разрешаем stub-режим для разработки и CI, но блокируем test_ и пустые ключи
if not key or (key.startswith("test_") or key == ""):
    # Исключение для stub-режима
    if key != "stub":
        raise RuntimeError("OPENAI_API_KEY env var missing or dummy")

# Устанавливаем ключ для совместимости (если не stub)
if key and key != "stub":
    openai.api_key = key

# Глобальная переменная для клиента
_client = None

def _get_client(api_key: str):
    """Ленивая инициализация OpenAI клиента"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client

async def call_llm(model: str, prompt: str, tools: list | None = None, temperature: float = 0, thread_id: str = None, turn_index: int = None):
    """
    Вызов LLM с проверкой API ключа, поддержкой stub-режима и учетом токенов
    Возвращает ответ и время задержки в миллисекундах.
    """
    
    # Получаем API ключ
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Подсчитываем токены промпта
    prompt_tokens = count_tokens(prompt, model)
    
    # Stub-LLM для офлайн-режима и CI
    if api_key == "stub":
        completion_tokens = 10
        # Генерируем разный ответ для разных промптов, чтобы тесты проходили
        response = f"[stub] Тестовый ответ для промпта: {prompt[:20]}..."
        _log_token_usage(thread_id, turn_index, model, prompt_tokens, completion_tokens)
        return response, 0
    
    # Заглушка для тестирования (режим test)
    if is_test_mode():
        # Имитируем ответ на основе промпта
        if "классификатор" in prompt.lower():
            content = "simple_faq"
        else:
            content = "Это тестовый ответ от ассистента. API ключ не настроен для реальных запросов к OpenAI."
        completion_tokens = count_tokens(content, model)
        _log_token_usage(thread_id, turn_index, model, prompt_tokens, completion_tokens)
        latency_ms = 100  # Имитируем небольшую задержку
        return content, latency_ms
    
    # Проверяем наличие валидного OpenAI API ключа
    if not api_key or api_key.startswith("test_"):
        raise RuntimeError("OPENAI_API_KEY отсутствует или тестовый")
    
    # Реальный вызов OpenAI API
    t0 = time.time()
    client = _get_client(api_key)

    params = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": tools or [],
    }
    # o3-mini не поддерживает temperature
    if model != "o3-mini":
        params["temperature"] = temperature

    rsp = client.chat.completions.create(**params)
    content = rsp.choices[0].message.content.strip()
    latency_ms = int((time.time() - t0) * 1000)
    
    # Подсчитываем токены ответа
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
            pass  # chat_db может быть недоступна в некоторых контекстах
