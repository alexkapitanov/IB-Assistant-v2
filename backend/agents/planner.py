import autogen, asyncio, time, json, logging
from backend.openai_helpers import call_llm
from backend.agents.expert_gc import run_expert_gc
from backend.json_utils import safe_load, BadJSON
from backend.chat_db import log_raw

logger = logging.getLogger(__name__)

PROMPT = """Ты планировщик. 
Верни ровно ОДИН объект JSON БЕЗ каких-либо пояснений:
{
 "need_clarify": true/false,
 "clarify": "...",
 "need_escalate": true/false,
 "draft": "..."
}
"""

def build_plan(user_q, slots, thread_id, turn):
    """Строит план с безопасным парсингом JSON"""
    txt, _ = call_llm("gpt-4o", f"{PROMPT}\nВопрос: {user_q}\nСлоты:{slots}")
    
    # Логируем сырой ответ модели
    log_raw(thread_id, turn, "gpt-4o", txt)
    
    return safe_load(txt)

async def ask_planner(thread_id, user_q, slots):
    try:
        # Получаем текущий номер хода для логирования
        turn = int(time.time() * 1000) % 1000000  # Простой способ получить уникальный номер
        
        plan = build_plan(user_q, slots, thread_id, turn)
        
        # Если нужна уточняющая информация
        if plan.get("need_clarify"):
            return {"answer": plan.get("clarify"), "follow_up": True, "model": "gpt-4o"}
        # Если эскалация не требуется
        if not plan.get("need_escalate"):
            return {"answer": plan.get("draft", ""), "model": "gpt-4o"}
        # Иначе эскалируем к экспертной цепочке
        final = await run_expert_gc(thread_id, user_q, slots)
        return final
        
    except BadJSON as e:
        logger.warning("Planner JSON fail: %s", e)
        return {
            "type": "chat",
            "role": "system", 
            "content": "🤖 Пока не понял формулировку, уточните пожалуйста."
        }
