import autogen, asyncio, time, json, logging
from backend.openai_helpers import call_llm
from agents.expert_gc import expert_group_chat
from backend.json_utils import safe_load, BadJSON
from backend.chat_db import log_raw          # для аудита

logger = logging.getLogger(__name__)

PROMPT = """
Ты — Planner-агент ассистента по информационной безопасности.
На основе вопроса пользователя и уже известных слотов реши, что делать.

Верни ОДИН объект JSON БЕЗ комментариев:
{
 "need_clarify":   true/false,   # нужен ли уточняющий вопрос?
 "clarify":        "текст вопроса" | "",
 "need_escalate":  true/false,   # нужна ли глубокая цепочка Expert GC?
 "draft":          "краткий ответ, если escalate=false"
}

Требования:
* не добавляй никаких полей кроме указанных;
* если в базе знаний мало фактов или вопрос требует сравнения/
  интеграции/расчёта — ставь need_escalate=true;
* если вопрос исчерпывается определением (например «Что такое SOC?») —
  можешь вернуть draft и need_escalate=false.
"""

def _call_planner_llm(thread_id: str, user_q: str, slots: dict):
    raw, _ = call_llm("gpt-4o", f"{PROMPT}\nВопрос: {user_q}\nСлоты: {slots}")
    log_raw(thread_id, 0, "gpt-4o", raw)       # turn_index=0 = технический
    return safe_load(raw)

async def ask_planner(thread_id, user_q, slots):
    try:
        plan = _call_planner_llm(thread_id, user_q, slots)
    except BadJSON as e:
        logger.warning("Bad JSON from planner: %s", e)
        return {"type": "chat", "role": "system",
                "content": "🤖 Не смог разобрать план. Уточните, пожалуйста."}
    
    # Если нужна уточняющая информация
    if plan.get("need_clarify"):
        return {"answer": plan.get("clarify"), "follow_up": True, "model": "gpt-4o"}
    # Если эскалация не требуется
    if not plan.get("need_escalate"):
        return {"answer": plan.get("draft", ""), "model": "gpt-4o"}
    # Иначе эскалируем к экспертной цепочке
    final = await expert_group_chat(user_q)
    return final
