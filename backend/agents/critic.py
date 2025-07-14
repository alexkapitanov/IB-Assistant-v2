from backend.openai_helpers import call_llm

async def ask_critic(text: str) -> bool:
    """
    Оценивает полноту ответа по шкале от 0 до 1.
    Возвращает True, если оценка >= 0.7.
    """
    prompt = (
        "Оцени полноту ответа по теме Информационной Безопасности (от 0.0 до 1.0). "
        "ВЕРНИ ТОЛЬКО ЧИСЛО.\n"
        "---\n"
        f"{text}\n"
        "---"
    )
    
    # Используем o3-mini как быструю и дешевую модель для оценки
    score_raw, _ = await call_llm("o3-mini", prompt)
    
    try:
        # Убираем лишние символы и преобразуем в float
        score = float(score_raw.strip().replace(",", "."))
        return score >= 0.7
    except (ValueError, TypeError):
        # В случае невалидного ответа от LLM, считаем оценку низкой
        return False
