async def handle_message(thread_id: str, user_q: str, slots: dict):
    intent, conf = await _classify_intent(user_q, slots)
    logging.info("Intent: %s, conf: %.2f", intent, conf)

    # small_talk значит пользователь сказал «Привет» или «Спасибо»:
    if intent == "small_talk":
        return {"type":"chat","role":"assistant",
                "content":"Здравствуйте! Чем могу помочь?"}

    if intent == "file":
        if (key := slots.get("file_key")):
            from backend.agents.file_retrieval import get_file_link
            return await get_file_link(key)
        # если файла нет – продолжаем как request

    # intent == "request"
    from backend.agents.planner import ask_planner
    plan = await ask_planner(thread_id, user_q, slots)

    if plan["need_clarify"]:
        return {"type":"chat","role":"assistant",
                "content":plan["clarify"]}

    if plan["need_escalate"]:
        from backend.agents.expert_gc import run_expert_gc
        return await run_expert_gc(thread_id, user_q, slots, plan)

    return {"type":"chat","role":"assistant",
            "content":plan["draft"]}
