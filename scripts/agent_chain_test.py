import asyncio
import logging
import uuid

from backend.agents.critic import ask_critic
from backend.agents.dialog_manager import _classify_intent
from backend.agents.expert_gc import run_expert_gc
from backend.agents.planner import ask_planner

# Вопросы разного уровня сложности
QUESTIONS = [
    ("Что такое DLP?", "Простой вопрос (определение)"),
    ("Перечисли производителей SIEM-систем", "Список (средняя сложность)"),
    ("Сравни продукты InfoWatch Traffic Monitor и Zecurion DLP по функционалу", "Сложный вопрос (эскалация)"),
    ("Какие есть риски при внедрении DLP?", "Вопрос, требующий уточнения"),
]

async def run_chain(question, desc):
    print(f"\n=== {desc} ===\nВопрос: {question}")
    thread_id = str(uuid.uuid4())
    slots = {}  # Можно добавить product/topic для экспериментов
    logger = logging.getLogger("agent_chain_test")

    # Intent
    intent, conf = await _classify_intent(question, slots)
    print(f"[Intent] {intent} (conf={conf})")

    # Planner
    plan = await ask_planner(thread_id, question, slots, logger)
    print(f"[Planner] План: {plan}")

    # Уточнение
    if plan.get("need_clarify"):
        print(f"[Planner] Требуется уточнение: {plan['clarify']}")
        return

    # Эскалация
    if plan.get("need_escalate"):
        print("[Planner] Требуется эскалация, передаю в Expert-GC...")
        resp = await run_expert_gc(thread_id, plan["plan"], {"slots": slots})
        print(f"[Expert-GC] Ответ: {resp}")
        return

    # Draft есть, проверяем через Critic
    if plan.get("draft"):
        ok = await ask_critic(plan["draft"])
        print(f"[Critic] Оценка черновика: {'одобрено' if ok else 'отклонено'}")
        if ok:
            print(f"[ASSISTANT] Ответ: {plan['draft']}")
        else:
            print("[Critic] Черновик отклонён, требуется эскалация...")
            resp = await run_expert_gc(thread_id, plan["plan"], {"slots": slots})
            print(f"[Expert-GC] Ответ: {resp}")

async def main():
    for q, desc in QUESTIONS:
        await run_chain(q, desc)

if __name__ == "__main__":
    asyncio.run(main())
