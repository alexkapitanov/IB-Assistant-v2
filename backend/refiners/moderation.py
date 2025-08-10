import os
from typing import Literal

ENABLE_LLM_GUARD = os.getenv("ENABLE_LLM_GUARD", "0") == "1"

MOD_PROMPT = (
    "Классифицируй, безопасно ли показывать ответ пользователю.\n"
    "Категории: SAFE | SENSITIVE.\n"
    "Отнеси к SENSITIVE, если есть персональные данные (паспорт, телефоны, e-mail), "
    "платёжные реквизиты, секретные ключи или конфиденциальные внутренние сведения.\n"
    "Ответи ровно одним словом."
)


def classify_safe(llm, text: str) -> Literal["SAFE", "SENSITIVE"]:
    if not ENABLE_LLM_GUARD:
        return "SAFE"
    # Ожидаем, что llm имеет метод .complete(prompt) -> str
    try:
        resp = llm.complete(MOD_PROMPT + "\n---\n" + text[:4000])
    except Exception:
        return "SAFE"
    label = (resp.strip().upper() or "SAFE")
    return "SENSITIVE" if "SENSITIVE" in label else "SAFE"
