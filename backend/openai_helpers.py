import os, openai, time

# Инициализация ключа OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

def call_llm(model: str, prompt: str, tools: list | None = None, temperature: float = 0):
    """
    Вызов модели OpenAI ChatCompletion.
    Возвращает ответ и время задержки в миллисекундах.
    """
    t0 = time.time()
    rsp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        tools=tools or [],
        temperature=temperature,
    )
    content = rsp.choices[0].message.content.strip()
    latency_ms = int((time.time() - t0) * 1000)
    return content, latency_ms
