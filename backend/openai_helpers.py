import os, time
from openai import OpenAI
from backend.utils import is_test_mode

# Глобальная переменная для клиента
_client = None

def _get_client(api_key: str):
    """Ленивая инициализация OpenAI клиента"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client

def call_llm(model: str, prompt: str, tools: list | None = None, temperature: float = 0):
    """
    Вызов LLM с проверкой API ключа и поддержкой stub-режима
    Возвращает ответ и время задержки в миллисекундах.
    """
    
    # Получаем API ключ
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Stub-LLM для офлайн-режима и CI
    if api_key == "stub":
        return "[stub] Тестовый ответ", 0
    
    # Заглушка для тестирования (режим test)
    if is_test_mode():
        # Имитируем ответ на основе промпта
        if "классификатор" in prompt.lower():
            content = "simple_faq"
        else:
            content = "Это тестовый ответ от ассистента. API ключ не настроен для реальных запросов к OpenAI."
        latency_ms = 100  # Имитируем небольшую задержку
        return content, latency_ms
    
    # Проверяем наличие валидного OpenAI API ключа
    if not api_key or api_key.startswith("test_"):
        raise RuntimeError("OPENAI_API_KEY отсутствует или тестовый")
    
    # Реальный вызов OpenAI API
    t0 = time.time()
    client = _get_client(api_key)
    rsp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        tools=tools or [],
        temperature=temperature,
    )
    content = rsp.choices[0].message.content.strip()
    latency_ms = int((time.time() - t0) * 1000)
    return content, latency_ms
