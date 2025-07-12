from backend.memory import get_mem, save_mem
from agents.file_retrieval import get_file_link
from agents.local_search import local_search
from agents.planner import ask_planner

INTENT_PROMPT = "Classify user request: get_file / simple_faq / complex."

def classify(user_q: str, slots: dict) -> str:
    """Определение интента запроса с помощью модели o3-mini"""
    # TODO: реализовать классификацию используя o3-mini
    raise NotImplementedError("Intent classification not implemented")

def cheap_faq_answer(user_q: str, fragments: list) -> str:
    """Генерация краткого ответа на основе фрагментов с помощью o3-mini"""
    # TODO: реализовать простое FAQ-ответ используя o3-mini
    raise NotImplementedError("FAQ answering not implemented")

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
