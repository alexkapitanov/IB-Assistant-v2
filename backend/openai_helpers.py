import os, time
from openai import OpenAI
from backend.utils import is_test_mode

# Проверяем наличие валидного OpenAI API ключа
if not (k := os.getenv("OPENAI_API_KEY")) or k.startswith("test_"):
    raise RuntimeError("OPENAI_API_KEY отсутствует или тестовый")

# Stub-LLM для офлайн-режима и CI
if k == "stub":
    def call_llm(model: str, prompt: str, *args, **kwargs):
        """Stub-реализация для тестирования без реального API ключа"""
        return "[stub] Тестовый ответ", 0
    
    # Экспортируем stub-функцию
    export_call_llm = call_llm
else:
    # Реальная реализация с OpenAI API
    
    # Глобальная переменная для клиента
    _client = None

    def _get_client():
        """Ленивая инициализация OpenAI клиента"""
        global _client
        if _client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            _client = OpenAI(api_key=api_key)
        return _client

    def call_llm(model: str, prompt: str, tools: list | None = None, temperature: float = 0):
        """
        Вызов модели OpenAI ChatCompletion.
        Возвращает ответ и время задержки в миллисекундах.
        """
        t0 = time.time()
        
        # Заглушка для тестирования
        if is_test_mode():
            # Имитируем ответ на основе промпта
            if "классификатор" in prompt.lower():
                content = "simple_faq"
            else:
                content = "Это тестовый ответ от ассистента. API ключ не настроен для реальных запросов к OpenAI."
            latency_ms = 100  # Имитируем небольшую задержку
            return content, latency_ms
        
        client = _get_client()
        rsp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            tools=tools or [],
            temperature=temperature,
        )
        content = rsp.choices[0].message.content.strip()
        latency_ms = int((time.time() - t0) * 1000)
        return content, latency_ms
