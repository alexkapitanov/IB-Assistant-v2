import autogen, asyncio, json, time
from backend.agents.local_search import local_search
from backend.openai_helpers import call_llm

async def run_expert_gc(thread_id, user_q, slots):
    expert = autogen.AssistantAgent("Expert", llm_config={"model": "gpt-4.1"})
    critic = autogen.AssistantAgent("Critic", llm_config={"model": "gpt-4.1-mini"})
    search = autogen.AssistantAgent("Search", llm_config={"model": "o3-mini"})

    def _search_tool(prompt:str)->str:
        # prompt: "search for: ... k=5"
        q = prompt.replace("search for:","").strip()
        hits = local_search(q, 5)
        return "\n".join(h["text"] for h in hits)
    
    search.register_function(function_map={"local_search": _search_tool})

    gc = autogen.GroupChat(agents=[expert, critic, search], max_round=4)
    mgr = autogen.GroupChatManager(groupchat=gc)
    ans = await mgr.a_initiate_chat(expert, message=user_q)
    return {"answer": ans, "model": "gpt-4.1"}
