"""
Роутер интентов для классификации запросов и быстрых FAQ-ответов
"""
from backend.openai_helpers import call_llm
from agents.local_search import local_search

INTENT_PROMPT = """
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

def classify_intent(user_query: str) -> str:
    """
    Классифицирует намерение пользователя на основе его запроса
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        Одно из: "get_file", "simple_faq", "capabilities", "complex"
    """
    try:
        full_prompt = f"{INTENT_PROMPT}\n\nЗапрос пользователя: {user_query}"
        response, _ = call_llm(full_prompt, model="gpt-4o-mini")
        
        # Очищаем ответ от лишних символов и приводим к нижнему регистру
        intent = response.strip().lower().replace('"', '').replace("'", "")
        
        # Проверяем, что ответ валидный
        if intent in ["get_file", "simple_faq", "capabilities", "complex"]:
            return intent
        else:
            # Если ответ некорректный, по умолчанию считаем complex
            return "complex"
            
    except Exception as e:
        print(f"❌ Error in classify_intent: {e}")
        # В случае ошибки считаем запрос сложным
        return "complex"

def cheap_faq_answer(q: str) -> str:
    """
    Быстрый FAQ-ответ для простых вопросов по ИБ
    
    Args:
        q: Вопрос пользователя
        
    Returns:
        Короткий ответ на основе контекста из базы знаний
    """
    try:
        # Получаем релевантный контекст из базы знаний
        search_results = local_search(q, top_k=3)
        
        if not search_results:
            return "Нет данных в базе знаний."
        
        # Формируем контекст из найденных результатов
        ctx = "\n\n".join([
            f"- {result['text'][:500]}..." if len(result['text']) > 500 else f"- {result['text']}"
            for result in search_results
            if result.get('text', '').strip()
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
        
        response, _ = call_llm(prompt, model="gpt-4o-mini")
        return response.strip()
        
    except Exception as e:
        print(f"❌ Error in cheap_faq_answer: {e}")
        return "Произошла ошибка при обработке запроса."

def get_capabilities_answer() -> str:
    """
    Возвращает информацию о возможностях ассистента
    
    Returns:
        Описание возможностей InfoSec Assistant
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

def route_query(user_query: str) -> dict:
    """
    Основная функция роутинга - классифицирует запрос и возвращает соответствующий ответ
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        Словарь с результатом обработки
    """
    intent = classify_intent(user_query)
    
    result = {
        "intent": intent,
        "query": user_query
    }
    
    if intent == "simple_faq":
        # Для простых FAQ даем быстрый ответ
        result["answer"] = cheap_faq_answer(user_query)
        result["type"] = "faq"
    elif intent == "capabilities":
        # Для запросов о возможностях возвращаем описание функций
        result["answer"] = get_capabilities_answer()
        result["type"] = "capabilities"
    else:
        # Для get_file и complex передаем дальше в планировщик
        result["needs_planning"] = True
        result["type"] = "planning_required"
    
    return result
