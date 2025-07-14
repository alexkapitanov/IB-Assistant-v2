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
  • complex       — аналитический вопрос, сравнение продуктов, расчёт TCO,
                    интеграция, глубокая настройка.

Верни ОДНО слово без кавычек: get_file / simple_faq / complex
"""

async def classify_intent(user_query: str) -> str:
    """
    Классифицирует намерение пользователя на основе его запроса
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        Одно из: "get_file", "simple_faq", "complex"
    """
    try:
        full_prompt = f"{INTENT_PROMPT}\n\nЗапрос пользователя: {user_query}"
        response, _ = await call_llm(full_prompt, model="o3-mini")
        
        # Очищаем ответ от лишних символов и приводим к нижнему регистру
        intent = response.strip().lower().replace('"', '').replace("'", "")
        
        # Проверяем, что ответ валидный
        if intent in ["get_file", "simple_faq", "complex"]:
            return intent
        else:
            # Если ответ некорректный, по умолчанию считаем complex
            return "complex"
            
    except Exception as e:
        print(f"❌ Error in classify_intent: {e}")
        # В случае ошибки считаем запрос сложным
        return "complex"

async def cheap_faq_answer(q: str) -> str:
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
        
        response, _ = await call_llm(prompt, model="o3-mini")
        return response.strip()
        
    except Exception as e:
        print(f"❌ Error in cheap_faq_answer: {e}")
        return "Произошла ошибка при обработке запроса."

async def route_query(user_query: str) -> dict:
    """
    Основная функция роутинга - классифицирует запрос и возвращает соответствующий ответ
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        Словарь с результатом обработки
    """
    
    # 1. Классифицируем интент
    intent = await classify_intent(user_query)
    
    # 2. Роутим в зависимости от интента
    if intent == "simple_faq":
        # Для простых вопросов - быстрый ответ по базе знаний
        answer = await cheap_faq_answer(user_query)
        return {"type": "chat", "role": "assistant", "content": answer}
        
    elif intent == "get_file":
        # Для запросов файлов - ищем ссылку
        from backend.agents.file_retrieval import get_file_link
        link = get_file_link(user_query)
        if link:
            return {"type": "chat", "role": "assistant", "content": f"Файл найден: [скачать]({link})"}
        else:
            return {"type": "chat", "role": "system", "content": "К сожалению, файл не найден."}
            
    elif intent == "complex":
        # Для сложных вопросов - эскалация на экспертную группу
        from agents.expert_gc import expert_group_chat
        result = await expert_group_chat(user_query)
        return {"type": "chat", "role": "assistant", "content": result.get("answer", "Эксперты готовят ответ...")}
        
    else:
        # Если интент не распознан, возвращаем сообщение по умолчанию
        return {"type": "chat", "role": "system", "content": "Не удалось определить ваш запрос. Попробуйте переформулировать."}
