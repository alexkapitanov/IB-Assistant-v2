import re, logging
from backend.openai_helpers import call_llm

CONFIDENCE_MIN = 0.65

def _score_to_float(txt: str) -> float | None:
    """
    Извлекает первое число 0…1 из произвольной строки Critic-агента.
    Примеры:
      "0.83 / 1"   -> 0.83
      "score:0.7"  -> 0.7
      "N/A"        -> None
    """
    m = re.search(r"(\d+(?:\.\d+)?)", txt)
    return float(m.group(1)) if m else None

async def ask_critic(text: str, logger: logging.Logger) -> bool:
    prompt = ("Оцени полноту и корректность ответа по ИБ одним числом 0-1.\n"
              "Только число, без объяснений.\n\n" + text)
    logger.info(f"Asking critic for text: '{text[:100]}...'")
    raw, _ = await call_llm("gpt-4.1-mini", prompt, temperature=0.0)
    score = _score_to_float(raw)
    logger.info(f"Critic returned score: {score} (raw: '{raw.strip()}')")
    if score is None:
        logging.warning("Critic returned non-numeric: %s", raw)
        return False
    return score >= CONFIDENCE_MIN
