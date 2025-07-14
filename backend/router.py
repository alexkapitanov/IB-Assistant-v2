from backend.memory import get_mem, save_mem
from backend.agents.file_retrieval import get_file_link
from backend.agents.local_search import local_search
from backend.agents.planner import ask_planner
from backend.openai_helpers import call_llm
from backend.status_bus import publish

DEF_INTENT_PROMPT = """
Ты — классификатор запросов по информационной безопасности (ИБ).
Определи назначение реплики пользователя.

Возможные категории:
  • get_file      — хочет получить файл (опросный лист, datasheet, PDF, чек-лист).
  • simple_faq    — краткий факт из области ИБ (термин, определение, аббревиатура,
                    «что такое DLP», «PCI DSS что требует»).
  • capabilities — запрос о возможностях ассистента («что ты умеешь», «что можешь»,
                    «какие у тебя функции», «помощь», «help»).
  • complex       — аналитический вопрос, сравнение продуктов, расчёт TCO,
                    интеграция, глубокая настройка.

Верни ОДНО слово без кавычек: get_file / simple_faq / capabilities / complex
"""

def classify(user_q: str, slots: dict) -> str:
    """
    Классифицирует намерение пользователя на основе его запроса
    """
    try:
        prompt = f"{DEF_INTENT_PROMPT}\n\nЗапрос пользователя: {user_q}"
        res, _ = call_llm("gpt-4o-mini", prompt)
        
        # Очищаем ответ от лишних символов и приводим к нижнему регистру
        intent = res.strip().lower().replace('"', '').replace("'", "")
        
        # Проверяем, что ответ валидный
        if intent in ["get_file", "simple_faq", "capabilities", "complex"]:
            return intent
        else:
            # Если ответ некорректный, по умолчанию считаем complex
            return "complex"
            
    except Exception as e:
        print(f"❌ Error in classify: {e}")
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
        
        response, _ = call_llm("gpt-4o-mini", prompt)
        return response.strip()
        
    except Exception as e:
        print(f"❌ Error in cheap_faq_answer: {e}")
        return "Произошла ошибка при обработке запроса."

def get_capabilities_answer() -> str:
    """
    Возвращает информацию о возможностях ассистента
    """
    return """🤖 **InfoSec Assistant v2** — ваш помощник по информационной безопасности

**Что я умею:**

📋 **Работа с файлами**
• Поиск и предоставление опросных листов, datasheets, PDF-документов
• Доступ к чек-листам по ИБ-продуктам

🔍 **Быстрые ответы (FAQ)**
• Определения терминов ИБ (DLP, SIEM, SOC и др.)
• Краткие факты о стандартах и нормативах
• Объяснение аббревиатур и концепций

🧠 **Аналитические задачи**
• Сравнение ИБ-решений по функциональности
• Расчёт TCO (совокупной стоимости владения)
• Рекомендации по интеграции систем
• Глубокий анализ конфигураций

⚡ **Технологии**
• Multi-agent система на базе AutoGen
• RAG с векторной базой данных Qdrant
• Поддержка реального времени через WebSocket

**Область знаний:** DLP, SIEM, SOC, стандарты ИБ, нормативы, уязвимости

Задавайте вопросы — помогу найти нужную информацию! 🛡️"""

async def handle_message(thread_id: str, user_q: str) -> dict:
    slots = get_mem(thread_id)
    await publish(thread_id, "thinking")
    intent = classify(user_q, slots)
    if intent == "get_file":
        link = get_file_link(user_q, slots.get("product"))
        if link:
            return {"answer": f"Файл найден: [скачать]({link})", "intent": intent, "model": "none"}
    if intent == "simple_faq":
        await publish(thread_id, "searching")
        frags = local_search(user_q)[:3]
        await publish(thread_id, "generating")
        draft = cheap_faq_answer(user_q, frags)
        return {"answer": draft, "intent": intent, "model": "gpt-4o-mini"}
    if intent == "capabilities":
        return {"answer": get_capabilities_answer(), "intent": intent, "model": "none"}
    # complex → escalate
    await publish(thread_id, "generating")
    result = await ask_planner(thread_id, user_q, slots)
    
    # Проверяем, что получили корректный ответ
    if not result or not result.get("answer"):
        return {"type": "chat", "role": "system",
                "content": "🤔 Я затруднился ответить. Уточните вопрос."}
    
    return result
