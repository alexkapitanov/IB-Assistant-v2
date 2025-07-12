import autogen, asyncio
from agents.expert_gc import run_expert_gc

async def ask_planner(thread_id, user_q, slots):
    """
    Planner agent (GPT-4.1) builds a plan and decides whether to escalate.
    If escalation is False, composes a short answer.
    If escalation is True, invokes expert generative chain.
    """
    # TODO: реализовать логику планирования с помощью autogen
    # Примерная схема:
    # plan = await autogen.build_plan(user_q, slots)
    # if not plan.escalate:
    #     return {"answer": plan.answer, "intent": "complex", "model": "gpt-4.1"}
    # else:
    #     return await run_expert_gc(thread_id, user_q, slots, plan)
    raise NotImplementedError("Planner logic not implemented")
