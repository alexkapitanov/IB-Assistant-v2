from backend.openai_helpers import call_llm

async def refine(text: str) -> str:
    """
    Улучшает текст ответа, делая его более гладким и читаемым,
    при этом сохраняя весь смысл и фактическую информацию.
    """
    prompt = f"Перепиши более гладко, не теряя смысл:\n{text}"
    out, _ = await call_llm("o3-mini", prompt, temperature=0.2)
    return out
