from backend.memory import get_mem, save_mem
from backend.agents.file_retrieval import get_file_link
from backend.agents.local_search import local_search
from backend.agents.planner import ask_planner
from backend.openai_helpers import call_llm
from backend.status_bus import publish

DEF_INTENT_PROMPT = """
Ты классификатор. Категории: get_file, simple_faq, complex.
Верни ровно одно слово.
"""

def classify(user_q:str, slots:dict)->str:
    prompt = f"{DEF_INTENT_PROMPT}\nQ: {user_q}\nA:"
    res,_ = call_llm("o3-mini", prompt)
    return res.strip()

def cheap_faq_answer(q:str, frags:list):
    ctx = "\n".join(f["text"] for f in frags)
    prompt = f"Ответь коротко на русском, используя факты:\n===КОНТЕКСТ===\n{ctx}\n===ВОПРОС===\n{q}\n"
    ans,_ = call_llm("o3-mini", prompt, temperature=0.2)
    return ans

async def handle_message(thread_id: str, user_q: str) -> dict:
    slots = get_mem(thread_id)
    await publish(thread_id, "thinking")
    intent = classify(user_q, slots)         # implement in this module using o3-mini
    if intent == "get_file":
        link = get_file_link(user_q, slots.get("product"))
        if link:
            return {"answer": f"Файл найден: [скачать]({link})", "intent": intent, "model": "none"}
    if intent == "simple_faq":
        await publish(thread_id, "searching")
        frags = local_search(user_q)[:3]
        await publish(thread_id, "generating")
        draft = cheap_faq_answer(user_q, frags)   # o3-mini
        return {"answer": draft, "intent": intent, "model": "o3-mini"}
    # complex → escalate
    await publish(thread_id, "generating")
    result = await ask_planner(thread_id, user_q, slots)
    
    # Проверяем, что получили корректный ответ
    if not result or not result.get("answer"):
        return {"type": "chat", "role": "system",
                "content": "🤔 Я затруднился ответить. Уточните вопрос."}
    
    return result
