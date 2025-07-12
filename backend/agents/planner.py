import autogen, asyncio, time, json
from backend.openai_helpers import call_llm
from backend.agents.expert_gc import run_expert_gc

async def ask_planner(thread_id, user_q, slots):
    # Формируем запрос к планировщику
    prompt = (
        f"Планировщик. Вопрос: {user_q}. Слоты:{slots}. "
        "Скажи JSON {need_clarify,bool,clarify?,need_escalate,bool}"
    )
    plan_txt, _ = call_llm("gpt-4o", prompt)
    plan = json.loads(plan_txt)
    # Если нужна уточняющая информация
    if plan.get("need_clarify"):
        return {"answer": plan.get("clarify"), "follow_up": True, "model": "gpt-4.1"}
    # Если эскалация не требуется
    if not plan.get("need_escalate"):
        return {"answer": plan.get("draft", ""), "model": "gpt-4.1"}
    # Иначе эскалируем к экспертной цепочке
    final = await run_expert_gc(thread_id, user_q, slots)
    return final
