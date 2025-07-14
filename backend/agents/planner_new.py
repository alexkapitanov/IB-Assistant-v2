import autogen, asyncio, time, json, logging
from backend.openai_helpers import call_llm, count_tokens
from backend.memory import get_mem, save_mem
from backend.agents.critic import ask_critic
from backend.agents.expert_gc import run_expert_gc
from backend.json_utils import safe_load, BadJSON
from backend.chat_db import log_raw          # для аудита

# Alias for backward compatibility with tests
ask_expert_gc = run_expert_gc

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


async def _call_planner_llm(thread_id: str, user_q: str, slots: dict, history: list = None):
    # Добавляем историю в промпт, если она есть
    history_prompt = ""
    if history:
        history_prompt = "\nИстория итераций:\n" + "\n".join(json.dumps(h, ensure_ascii=False) for h in history)

    raw, _ = call_llm("gpt-4.1", f"{PROMPT}\nВопрос: {user_q}\nСлоты: {slots}{history_prompt}")
    try:
        # Убираем ```json и ```
        plan = json.loads(raw.replace("```json", "").replace("```", ""))
    except json.JSONDecodeError as e:
        raise BadJSON(f"Ошибка декодирования JSON: {e.msg}", raw) from e

    # Проверяем, что есть все обязательные поля
    if not all(k in plan for k in ("need_clarify", "clarify", "need_escalate", "draft")):
        raise BadJSON(f"Недостаточно полей в ответе планировщика: {raw}", raw)

    return plan

MAX_ITERATIONS = 3
async def _iterate_plan(thread_id: str, user_q: str, slots: dict):
    history = []
    for i in range(MAX_ITERATIONS):
        plan = await _call_planner_llm(thread_id, user_q, slots, history)
        history.append(plan)

        # Проверяем, нужно ли уточнение
        if plan.get("need_clarify"):
            return plan

        # Если эскалация не нужна, проверяем ответ критиком
        if not plan.get("need_escalate"):
            is_ok = await ask_critic(plan.get("draft", ""))
            if is_ok:
                return plan
            else:
                # Добавляем в историю и идем на новую итерацию
                history.append({"plan": plan, "critic": "Неполный ответ, нужно переделывать"})
        else:
            # Если планировщик сразу решил эскалировать, выходим
            return plan

    # Если после всех итераций не удалось получить хороший ответ, эскалируем
    return {"need_escalate": True, "draft": ""}


async def ask_planner(thread_id: str, user_q: str, slots: dict):
    """Основная функция-планировщик"""
    try:
        plan = await _iterate_plan(thread_id, user_q, slots)
        
        # Если нужна уточняющая информация
        if plan.get("need_clarify"):
            return {"answer": plan.get("clarify"), "follow_up": True, "model": "gpt-4.1"}
        # Если эскалация не требуется
        if not plan.get("need_escalate"):
            return {"answer": plan.get("draft", ""), "model": "gpt-4.1"}
        # Иначе эскалируем к экспертной цепочке
        final = await run_expert_gc(thread_id, user_q, slots)
        return final
        
    except BadJSON as e:
        logger.error(f"Planner failed to parse LLM response: {e.raw_json}")
        return {"type": "chat", "role": "system",
                "content": "🤖 Не смог разобрать план. Уточните, пожалуйста."}
