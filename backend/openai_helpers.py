import os, time
from openai import OpenAI

# Инициализация клиента OpenAI
api_key = os.getenv("OPENAI_API_KEY")
is_test_mode = api_key and api_key.startswith("test_key")

if not is_test_mode:
    client = OpenAI(api_key=api_key)
else:
    client = None  # Заглушка для тестирования

def call_llm(model: str, prompt: str, tools: list | None = None, temperature: float = 0):
    """
    Вызов модели OpenAI ChatCompletion.
    Возвращает ответ и время задержки в миллисекундах.
    """
    t0 = time.time()
    
    # Заглушка для тестирования
    if is_test_mode:
        # Имитируем ответ на основе промпта
        if "классификатор" in prompt.lower():
            content = "simple_faq"
        else:
            content = "Это тестовый ответ от ассистента. API ключ не настроен для реальных запросов к OpenAI."
        latency_ms = 100  # Имитируем небольшую задержку
        return content, latency_ms
    
    rsp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        tools=tools or [],
        temperature=temperature,
    )
    content = rsp.choices[0].message.content.strip()
    latency_ms = int((time.time() - t0) * 1000)
    return content, latency_ms
