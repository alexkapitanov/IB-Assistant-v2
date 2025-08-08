#!/usr/bin/env python3
import asyncio
import json
import os
from typing import List, Dict, Any

# Ensure local imports work
os.environ.setdefault("OPENAI_API_KEY", "stub")

# --- Dummy autogen stand-ins to simulate multi-agent chat ---
class DummyGroupChat:
    def __init__(self, agents, messages=None, max_round=15):
        self.agents = agents
        self.messages: List[Dict[str, Any]] = messages or []
        self.max_round = max_round

class DummyGroupChatManager:
    def __init__(self, groupchat, llm_config=None, is_termination_msg=None):
        self.gc = groupchat
        self.is_termination_msg = is_termination_msg or (lambda m: False)

    async def a_initiate_chat(self, recipient=None, message: str = ""):
        # Simulate a minimal conversation across agents
        # 1) Domain expert produces initial analysis
        self.gc.messages.append({"name": self.gc.agents[0].__dict__.get("name", "DomainExpert"), "content": f"Анализ: {message[:80]}..."})
        # 2) Search tool returns findings
        self.gc.messages.append({"name": "Search", "content": "Результаты поиска: пункт 1; пункт 2; пункт 3."})
        # 3) Critic evaluates
        self.gc.messages.append({"name": "Critic", "content": "Оценка: OK. Можно формировать финальный ответ."})
        # 4) Aggregator emits FINAL_ANSWER with TERMINATE
        self.gc.messages.append({"name": "Aggregator", "content": f"FINAL_ANSWER: Итоговый ответ по плану → {message.splitlines()[0]}\nTERMINATE"})
        return None

async def run_scenarios():
    # Import backend modules after setting OPENAI_API_KEY
    from backend.agents.planner import _build_plan
    from backend.agents.critic import ask_critic
    import backend.agents.expert_gc as egc

    # Monkeypatch GroupChat/Manager to dummy to avoid network calls
    egc.GroupChat = DummyGroupChat
    egc.GroupChatManager = DummyGroupChatManager

    scenarios = [
        {
            "title": "Простой вопрос (определение)",
            "question": "Что такое DLP?",
            "slots": {"topic": "DLP"},
            "force_escalate": False,
        },
        {
            "title": "Сравнение продуктов (эскалация)",
            "question": "Сравни Infowatch и Zecurion по критериям DLP и сделай вывод",
            "slots": {"topic": "DLP", "product": "Infowatch"},
            "force_escalate": True,
        },
        {
            "title": "План внедрения (глубокий анализ)",
            "question": "Сформируй план внедрения SIEM в банке с этапами и рисками",
            "slots": {"topic": "SIEM"},
            "force_escalate": True,
        },
    ]

    for sc in scenarios:
        print("\n=== ", sc["title"], "===", sep="")
        q = sc["question"]
        slots = sc["slots"]

        # 1) Planner
        plan = await _build_plan(q, slots, context=json.dumps({"summary": "", "slots": slots}, ensure_ascii=False))
        print("[Planner] need_clarify:", plan.get("need_clarify"), "need_escalate:", plan.get("need_escalate"))
        if plan.get("draft"):
            print("[Planner.draft]", plan["draft"])

        # 2) Critic (на draft)
        approved = False
        if plan.get("draft"):
            approved = await ask_critic(plan["draft"])  # bool
            print("[Critic] approved:", approved)

        # Решение об эскалации
        need_gc = sc["force_escalate"] or (plan.get("need_escalate") and not approved)

        if need_gc:
            # Подготовим план шагов для группы
            steps = plan.get("plan") or [
                "Понять контекст запроса",
                "Собрать сведения из базы знаний",
                "Сформировать вывод и рекомендации",
            ]
            # 3) Expert GC (DomainExpert, Search, Critic, Aggregator)
            resp = await egc.run_expert_gc("probe-thread", steps, {"slots": slots})
            # Распечатаем сообщения каждого агента
            # В Dummy мы сформировали их в egc.GroupChat.messages; доступ через менеджер отсутствует, так что повторим симуляцию
            # Для простоты — в DummyManager мы уже наполнили gc.messages; get it by running summarize flow again
            # Здесь альтернативно просто повторим имитацию, чтобы показать роли
            print("[DomainExpert] Анализ по теме:", slots.get("topic"))
            print("[Search] Результаты поиска: пункт 1; пункт 2; пункт 3.")
            print("[Critic] Оценка: OK")
            print("[Aggregator]", resp.get("content"))
        else:
            # 4) Ответ без эскалации
            print("[Assistant]", plan.get("draft", "(нет draft)"))

if __name__ == "__main__":
    asyncio.run(run_scenarios())
