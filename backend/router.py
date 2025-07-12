from backend.memory import get_mem, save_mem
from backend.agents.file_retrieval import get_file_link
from backend.agents.local_search import local_search
from backend.agents.planner import ask_planner
from backend.openai_helpers import call_llm

INTENT_SYSTEM = "Ты классификатор. Верни одно слово: get_file/simple_faq/complex."

def classify(user_q, slots):
    prompt = f"{INTENT_SYSTEM}\nQ: {user_q}\nA:"
    res, _ = call_llm("o3-mini", prompt)
    return res.strip()

def cheap_faq_answer(q, frags):
    ctx = "\n".join(f["text"] for f in frags)
    prompt = (
        f"Ответь кратко на русском, используя факты:\n"
        f"### Контекст\n{ctx}\n"
        f"### Вопрос\n{q}"
    )
    ans, _ = call_llm("o3-mini", prompt, temperature=0.3)
    return ans

async def handle_message(thread_id: str, user_q: str) -> dict:
    slots = get_mem(thread_id)
    intent = classify(user_q, slots)         # implement in this module using o3-mini
    if intent == "get_file":
        link = get_file_link(user_q, slots.get("product"))
        if link:
            return {"answer": f"Файл найден: [скачать]({link})", "intent": intent, "model": "none"}
    if intent == "simple_faq":
        frags = local_search(user_q)[:3]
        draft = cheap_faq_answer(user_q, frags)   # o3-mini
        return {"answer": draft, "intent": intent, "model": "o3-mini"}
    # complex → escalate
    return await ask_planner(thread_id, user_q, slots)
