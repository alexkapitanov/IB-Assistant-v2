import json
import logging
from backend.openai_helpers import call_llm
from backend.json_utils import safe_load

PLAN_PROMPT = """Ты — Planner-агент по информационной безопасности.
Верни ОДИН JSON без комментариев:
{{
 "need_clarify": bool,
 "clarify": "<вопрос или пусто>",
 "need_escalate": bool,
 "draft": "<краткий ответ или пусто>",
 "plan": ["шаг 1", "шаг 2", …]
}}
===
Вопрос: «{q}»
Слоты: {slots}
"""

async def _build_plan(q: str, slots: dict, logger: logging.Logger) -> dict:
    """
    Вызывает LLM для построения плана и безопасно парсит результат.
    """
    logger.info("Calling LLM to build a plan.")
    # `ensure_ascii=False` для корректной передачи кириллицы в JSON
    raw, _ = await call_llm("gpt-4.1", PLAN_PROMPT.format(q=q, slots=json.dumps(slots, ensure_ascii=False)), temperature=0)
    
    plan = safe_load(raw)
    
    # Проверка на случай, если LLM вернул пустой или невалидный JSON
    if not plan:
        logger.error(f"Planner LLM returned invalid JSON: {raw}")
        # Fallback в случае, если LLM вернул невалидный JSON
        return {
            "need_clarify": False,
            "clarify": "",
            "need_escalate": True, # Эскалация для ручного разбора
            "draft": "",
            "plan": ["LLM planner returned invalid JSON"]
        }
    
    logger.info(f"Plan received from LLM: {plan}")
    return plan

async def ask_planner(thread_id: str, user_q: str, slots: dict, logger: logging.Logger) -> dict:
    """
    Основная функция-планировщик. Определяет, что делать с запросом пользователя.
    Вызывает LLM для построения плана, затем проверяет его через критика.
    """
    logger.info(f"Building plan for: '{user_q}'")
    plan = await _build_plan(user_q, slots, logger)
    
    # Добавляем план в контекст для Expert-GC (если план существует)
    if "plan" in plan:
        plan["context"] = {"plan": plan["plan"]}

    # если draft готов и need_escalate=False — задаём Critic-проверку
    if not plan.get("need_escalate") and plan.get("draft"):
        logger.info(f"Draft found, sending to critic: '{plan['draft']}'")
        from agents.critic import ask_critic
        
        ok = await ask_critic(plan["draft"], logger)
        
        if ok:
            logger.info("Critic approved the draft.")
            return plan
        
        # иначе помечаем как need_escalate
        logger.warning("Critic rejected the draft, escalating.")
        plan["need_escalate"] = True

    return plan
