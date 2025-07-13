import autogen, asyncio, time, json, logging
from backend.openai_helpers import call_llm
from backend.agents.expert_gc import run_expert_gc
from backend.json_utils import safe_load, BadJSON
from backend.chat_db import log_raw          # для аудита

logger = logging.getLogger(__name__)

PROMPT = """Ты планировщик. Верни ровно ОДИН объект JSON
без комментариев и форматирования:
{
 "need_clarify": true/false,
 "clarify": "...",
 "need_escalate": true/false,
 "draft": "..."
}"""

def _call_planner_llm(thread_id: str, user_q: str, slots: dict):
    raw, _ = call_llm("gpt-4o", f"{PROMPT}\nВопрос: {user_q}\nСлоты: {slots}")
    log_raw(thread_id, 0, "gpt-4.1", raw)       # turn_index=0 = технический
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
    final = await run_expert_gc(thread_id, user_q, slots)
    return final
