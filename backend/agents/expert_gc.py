import autogen

async def run_expert_gc(thread_id: str, user_q: str, slots: dict, plan) -> dict:
    """
    Runs a GroupChat among planner, expert, critic, and search agents.
    Loops max 4 rounds and returns final expert answer.
    """
    # Configure agent roles
    gc = autogen.GroupChat(
        name=f"gc-{thread_id}",
        roles=[
            autogen.Role(name="planner", model="gpt-4.1"),
            autogen.Role(name="expert", model="gpt-4.1"),
            autogen.Role(name="critic", model="4.1-mini"),
            autogen.Role(name="search", model="o3-mini"),
        ],
        max_iterations=4,
    )

    # Initialize conversation
    gc.add_system_message(f"Plan: {plan}")
    gc.add_user_message(user_q)

    # Execute the multi-agent loop
    await gc.run()

    # Retrieve final message from expert agent
    expert_msgs = gc.get_messages(role="expert")
    final = expert_msgs[-1].content if expert_msgs else ""

    return {"answer": final, "intent": "complex", "model": "gpt-4.1"}
