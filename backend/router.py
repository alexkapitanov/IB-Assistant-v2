from backend.memory import get_mem, save_mem
from backend.agents.file_retrieval import get_file_link
from backend.agents.local_search import local_search
from backend.agents.planner import ask_planner
from backend.agents.critic import ask_critic
import sys
import os
# Добавляем путь к agents для корректного импорта
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agents.refine import refine
from backend.openai_helpers import call_llm
from backend.status_bus import publish
import backend.tracing # Импортируем для инициализации трейсинга
import backend.logging_config # Импортируем для настройки логирования
import structlog

log = structlog.get_logger()

DEF_INTENT_PROMPT = """
Ты — классификатор запросов по информационной безопасности (ИБ).
Определи назначение реплики пользователя.

Возможные категории:
  • get_file      — хочет получить файл (опросный лист, datasheet, PDF, чек-лист).
  • simple_faq    — краткий факт из области ИБ (термин, определение, аббревиатура,
                    «что такое DLP», «PCI DSS что требует»).
  • complex       — аналитический вопрос, сравнение продуктов, расчёт TCO,
                    интеграция, глубокая настройка.

Верни ОДНО слово без кавычек: get_file / simple_faq / complex
"""

def classify(user_q: str, slots: dict) -> str:
    """
    Классифицирует намерение пользователя на основе его запроса
    """
    try:
        prompt = f"{DEF_INTENT_PROMPT}\n\nЗапрос пользователя: {user_q}"
        res, _ = call_llm("o3-mini", prompt)
        
        # Очищаем ответ от лишних символов и приводим к нижнему регистру
        intent = res.strip().lower().replace('"', '').replace("'", "")
        
        # Проверяем, что ответ валидный
        if intent in ["get_file", "simple_faq", "complex"]:
            return intent
        else:
            # Если ответ некорректный, по умолчанию считаем complex
            return "complex"
            
    except Exception as e:
        log.error("classify.error", error=e)
        # В случае ошибки считаем запрос сложным
        return "complex"

def cheap_faq_answer(q: str, frags: list):
    """
    Быстрый FAQ-ответ для простых вопросов по ИБ
    """
    try:
        if not frags:
            return "Нет данных в базе знаний."
        
        ctx = "\n\n".join([
            f"- {f['text'][:500]}..." if len(f['text']) > 500 else f"- {f['text']}"
            for f in frags
            if f.get('text', '').strip()
        ])
        
        if not ctx:
            return "Нет данных в базе знаний."
        
        prompt = f"""Отвечай на вопрос по ИБ коротко (1-2 абзаца),
опираясь ТОЛЬКО на контекст. Если ответа нет — напиши
«Нет данных в базе знаний».

### Контекст
{ctx}
### Вопрос
{q}
"""
        
        response, _ = call_llm("o3-mini", prompt)
        return response.strip()
        
    except Exception as e:
        log.error("cheap_faq_answer.error", error=e)
        return "Произошла ошибка при обработке запроса."

async def handle_message(thread_id: str, user_q: str) -> dict:
    log.info("handle_message.start", thread_id=thread_id, user_q=user_q)
    slots = get_mem(thread_id)
    await publish(thread_id, "thinking")
    intent = classify(user_q, slots)
    log.info("handle_message.intent_classified", intent=intent)
    if intent == "get_file":
        link = get_file_link(user_q, slots.get("product"))
        if link:
            log.info("handle_message.file_found", link=link)
            return {"type": "chat", "role": "assistant", 
                    "content": f"Файл найден: [скачать]({link})", 
                    "intent": intent, "model": "none"}
        else:
            return {"type": "chat", "role": "system",
                    "content": "К сожалению, файл не найден."}
                    
    if intent == "simple_faq":
        await publish(thread_id, "searching")
        frags = local_search(user_q)[:3]
        log.info("handle_message.simple_faq.frags_found", count=len(frags))
        await publish(thread_id, "generating")
        draft = cheap_faq_answer(user_q, frags)
        
        # Проверяем уверенность в ответе
        is_confident = await ask_critic(draft)
        if not is_confident:
            log.warning("handle_message.simple_faq.low_confidence", draft=draft)
            return {"type": "chat", "role": "system",
                    "content": "🤔 Не уверен в полноте ответа, проверьте, пожалуйста."}
        
        # Улучшаем текст ответа
        refined_answer = await refine(draft)
        if not refined_answer:
            log.warning("handle_message.refine.empty_answer", draft=draft)
            return {"type": "chat", "role": "system",
                    "content": "Не удалось улучшить ответ, возвращаю черновик.",
                    "intent": intent, "model": "o3-mini"}
        
        return {"type": "chat", "role": "assistant", 
                "content": refined_answer, "intent": intent, "model": "o3-mini"}
    # complex → escalate
    await publish(thread_id, "generating")
    result = await ask_planner(thread_id, user_q, slots)
    log.info("handle_message.complex.planner_result", result=result)
    
    # Проверяем, что получили корректный ответ
    if not result or not result.get("answer"):
        return {"type": "chat", "role": "system",
                "content": "🤔 Я затруднился ответить. Уточните вопрос."}
    
    # Проверяем уверенность в ответе от планировщика
    answer_text = result.get("answer", "")
    is_confident = await ask_critic(answer_text)
    if not is_confident:
        log.warning("handle_message.complex.low_confidence", answer=answer_text)
        return {"type": "chat", "role": "system",
                "content": "🤔 Не уверен в полноте ответа, проверьте, пожалуйста."}
    
    # Улучшаем текст ответа
    refined_answer = await refine(answer_text)
    if not refined_answer:
        log.warning("handle_message.refine.empty_answer", draft=answer_text)
        return {"type": "chat", "role": "system",
                "content": "Не удалось улучшить ответ, возвращаю черновик.",
                "model": result.get("model", "unknown")}
    
    # Формируем ответ с цитатами (если есть)
    response = {
        "type": "chat",
        "role": "assistant", 
        "content": refined_answer,
        "model": result.get("model", "unknown")
    }
    
    # Добавляем цитаты, если они есть
    if "citations" in result:
        response["citations"] = result["citations"]
    
    return response
