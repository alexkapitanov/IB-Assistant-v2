import re, logging, json
from backend.openai_helpers import call_llm
from backend.memory import get_mem, save_mem
# from agents.slot_extractor import extract_slots # not used
from agents.dm_critic import ask_dm_critic
from backend.agents.kb_search import kb_search

_SMALL_TALK_PROMPT = """
Ты — ассистент по ИБ. Кратко и вежливо ответь на реплику пользователя.
Не задавай встречных вопросов, если это не просьба что-то повторить.
Не будь слишком многословным.
Сохраняй дружелюбный, но профессиональный тон.
Если пользователь здоровается, поздоровайся в ответ.
Если пользователь прощается, попрощайся.
Если пользователь благодарит, ответь вежливо.
===
ФРАЗА ПОЛЬЗОВАТЕЛЯ: «{q}»
"""

_INTENT_PROMPT = """
Ты ассистент по ИБ. Верни JSON без комментариев:
{{"intent":"small_talk|file|kb_search|request", "conf":0-1}}

intent:
  small_talk – приветствие, благодарность, извинение
  file       – просят PDF, чек-лист, шаблон
  kb_search  – спрашивают о ранее решённой задаче (FAQ, “у тебя же было…”)
  request    – аналитический / новый вопрос по ИБ
===
ФРАЗА: «{q}»
СЛОТЫ: {slots}
"""
_INT_MATCH = re.compile(r'"intent"\s*:\s*"([^"]+)"\s*,\s*"conf"\s*:\s*([\d.]+)')

async def _classify_intent(q:str, slots:dict)->tuple[str,float]:
    raw,_ = await call_llm("o3-mini", _INTENT_PROMPT.format(q=q, slots=json.dumps(slots)), temperature=0)
    m=_INT_MATCH.search(raw)
    if not m:
        logging.warning("Intent-parse fail: %s", raw.strip()[:120])
        return "request", 0.0
    return m.group(1), float(m.group(2))


async def handle_message(thread_id: str, user_q: str, slots: dict, logger: logging.Logger):
    logger.info(f"Classifying intent for: '{user_q}'")
    intent, conf = await _classify_intent(user_q, slots)
    logger.info(f"Intent classified as '{intent}' with confidence {conf:.2f}")

    if intent == "small_talk":
        logger.info("Handling as small_talk.")
        raw_response, _ = await call_llm("o3-mini", _SMALL_TALK_PROMPT.format(q=user_q), temperature=0.5)
        return {"type":"chat","role":"assistant",
                "content": raw_response.strip()}

    if intent == "file":
        if (key := slots.get("file_key")):
            from backend.agents.file_retrieval import get_file_link
            logger.info(f"Handling as file request for key: {key}")
            return await get_file_link(key)
        else: # fallback to planner
            logger.warning("File intent, но нет slot'а file_key. Переход к планировщику.")
            pass

    # kb_search, request and file fallback are handled via kb_search first
    # then planner if needed
    logger.info("Вызываем kb_search для поиска в базе знаний.")
    status, ctx = await kb_search(user_q)
    
    if status == "reuse":
        logger.info("kb_search нашел готовый ответ. Возвращаем его.")
        return {"type":"chat","role":"assistant","content":ctx}
    
    # status == "escalate" - передаем контекст планировщику
    logger.info("kb_search эскалирует к планировщику с дополнительным контекстом.")
    from backend.agents.planner import ask_planner
    
    # Объединяем slots с контекстом от kb_search
    enhanced_slots = slots.copy()
    enhanced_slots.update(ctx)  # ctx содержит similar_dialogs и rag
    
    plan = await ask_planner(thread_id, user_q, enhanced_slots, logger)

    if plan["need_clarify"]:
        logger.info(f"Планировщик требует уточнения: {plan['clarify']}")
        return {"type":"chat","role":"assistant",
                "content":plan["clarify"]}

    if plan["need_escalate"]:
        from backend.agents.expert_gc import run_expert_gc
        logger.info("Планировщик передаёт в экспертный чат.")
        out = await run_expert_gc(thread_id, user_q, slots, plan, logger)
        if out.get("role") == "system":
            # таймаут или авария — отдаём черновик
            plan["draft"] = "Черновой ответ: мы уточняем информацию, пожалуйста, подождите."
            plan["need_escalate"] = False
            return {"type":"chat","role":"assistant", "content":plan["draft"]}
        return out

    logger.info(f"Планировщик предложил черновик ответа: {plan['draft']}")
    return {"type":"chat","role":"assistant",
            "content":plan["draft"]}
