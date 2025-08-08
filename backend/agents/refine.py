"""
Refine-Paraphraser: легкая пост-обработка ответа (о3-mini)
- Полирует стиль
- Сохраняет факты и ссылки
- Делает текст более кратким и понятным
"""
from backend.openai_helpers import call_llm


REFINE_PROMPT = (
    "Отредактируй ответ ассистента: сохрани факты и ссылки [n],\n"
    "улучши ясность и краткость, оформи подзаголовки. Верни только текст ответа.\n"
    "---\n{answer}\n---"
)


async def refine_answer(answer: str | None) -> str | None:
    if not answer:
        return answer
    try:
        content, _ = await call_llm("o3-mini", REFINE_PROMPT.format(answer=answer), temperature=0)
        return content.strip() if content else answer
    except Exception:
        return answer
