"""
Expert Group Chat - системные промпты для экспертной группы по ИБ
Включает эксперта, критика и поисковика для глубокого анализа сложных вопросов
"""

from backend.agents.local_search import local_search
from backend.openai_helpers import call_llm
import json
import re

# Системные промпты для агентов
SYSTEM_EXPERT = """
Ты — ведущий эксперт по информационной безопасности (25+ лет опыта).
Пиши лаконично, без «воды», с примерами практик и ссылками на стандарты
(ISO 27001, ГОСТ Р 57580, PCI DSS, MITRE ATT&CK).  
Если используешь фрагменты RAG-поиска, интегрируй их в текст и
оставляй нумерованные сноски [1], [2]… (без URL — фронт вставит сам).
"""

SYSTEM_CRITIC = """
Ты — критик. Проверь ответ эксперта:
  • полнота (ничего ли не упущено по вопросу);
  • корректность терминов ИБ;
  • отсутствие галлюцинаций.
Если нужно дозапросить поисковик — скажи "ADD_SEARCH".
Если ответ достаточен — скажи "OK".
"""

SYSTEM_SEARCH = """
Ты — поиск-хелпер. Получив запрос формата
«search:<строка>», верни до 5 самых релевантных фрагментов
(до 40 слов каждый) из Qdrant, каждый на новой строке.
"""

class ExpertAgent:
    """Эксперт по информационной безопасности"""
    
    def __init__(self):
        self.system_message = SYSTEM_EXPERT
        self.conversation_history = []
    
    def update_system_message(self, new_system: str):
        """Обновляет системный промпт эксперта"""
        self.system_message = new_system
    
    async def respond(self, user_query: str, context: str = "", search_results: list = None) -> str:
        """
        Генерирует экспертный ответ на основе запроса и контекста
        
        Args:
            user_query: Вопрос пользователя
            context: Дополнительный контекст
            search_results: Результаты поиска для интеграции в ответ
            
        Returns:
            Экспертный ответ с возможными сносками
        """
        try:
            # Формируем полный промпт
            prompt_parts = [self.system_message]
            
            if search_results:
                search_context = "\n".join([
                    f"[{i+1}] {result.get('text', '')[:200]}..."
                    for i, result in enumerate(search_results[:5])
                    if result.get('text', '').strip()
                ])
                if search_context:
                    prompt_parts.append(f"\nКонтекст из базы знаний:\n{search_context}")
            
            if context:
                prompt_parts.append(f"\nДополнительный контекст:\n{context}")
            
            prompt_parts.append(f"\nВопрос: {user_query}")
            
            full_prompt = "\n".join(prompt_parts)
            
            response, _ = await call_llm(full_prompt, model="gpt-4.1")
            return response.strip()
            
        except Exception as e:
            print(f"❌ Error in ExpertAgent.respond: {e}")
            return "Произошла ошибка при формировании экспертного ответа."

class CriticAgent:
    """Критик для проверки ответов эксперта"""
    
    def __init__(self):
        self.system_message = SYSTEM_CRITIC
    
    def update_system_message(self, new_system: str):
        """Обновляет системный промпт критика"""
        self.system_message = new_system
    
    async def review(self, expert_answer: str, original_question: str) -> dict:
        """
        Проверяет ответ эксперта на полноту и корректность
        
        Args:
            expert_answer: Ответ эксперта для проверки
            original_question: Исходный вопрос пользователя
            
        Returns:
            Словарь с результатом проверки
        """
        try:
            prompt = f"""{self.system_message}

Исходный вопрос: {original_question}

Ответ эксперта:
{expert_answer}

Твоя оценка:"""
            
            response, _ = await call_llm(prompt, model="gpt-4.1-mini")
            review_text = response.strip()
            
            # Определяем нужен ли дополнительный поиск
            needs_search = "ADD_SEARCH" in review_text
            is_sufficient = "OK" in review_text and not needs_search
            
            return {
                "needs_search": needs_search,
                "is_sufficient": is_sufficient,
                "feedback": review_text
            }
            
        except Exception as e:
            print(f"❌ Error in CriticAgent.review: {e}")
            return {
                "review": "Ошибка при проверке ответа",
                "needs_search": False,
                "is_sufficient": True,
                "action": "ok"
            }

class SearchAgent:
    """Поисковый агент для получения релевантных фрагментов"""
    
    def __init__(self):
        self.system_message = SYSTEM_SEARCH
    
    def update_system_message(self, new_system: str):
        """Обновляет системный промпт поисковика"""
        self.system_message = new_system
    
    async def search(self, query: str, top_k: int = 5) -> list:
        """
        Выполняет поиск релевантных фрагментов
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            
        Returns:
            Список релевантных фрагментов
        """
        try:
            # Извлекаем поисковый запрос из формата "search:<строка>"
            if query.startswith("search:"):
                search_query = query[7:].strip()
            else:
                search_query = query
            
            # Выполняем поиск в Qdrant
            results = local_search(search_query, top_k=top_k)
            
            # Форматируем результаты согласно системному промпту
            formatted_results = []
            for result in results:
                text = result.get('text', '').strip()
                if text:
                    # Обрезаем до 40 слов
                    words = text.split()
                    if len(words) > 40:
                        text = ' '.join(words[:40]) + '...'
                    formatted_results.append({
                        'text': text,
                        'score': result.get('score', 0),
                        'meta': result.get('meta', {})
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error in SearchAgent.search: {e}")
            return []

# Создаем экземпляры агентов
expert = ExpertAgent()
critic = CriticAgent()
search = SearchAgent()

# Применяем системные промпты
expert.update_system_message(SYSTEM_EXPERT)
critic.update_system_message(SYSTEM_CRITIC)
search.update_system_message(SYSTEM_SEARCH)

async def expert_group_chat(user_query: str, max_iterations: int = 3) -> dict:
    """
    Основная функция группового чата экспертов
    
    Args:
        user_query: Вопрос пользователя
        max_iterations: Максимальное количество итераций обсуждения
        
    Returns:
        Финальный результат работы экспертной группы
    """
    conversation_log = []
    search_results = []
    
    try:
        # Начальный поиск контекста
        initial_search = await search.search(f"search:{user_query}")
        search_results.extend(initial_search)
        
        conversation_log.append({
            "agent": "search",
            "action": "initial_search",
            "query": user_query,
            "results_count": len(initial_search)
        })
        
        # Эксперт дает первоначальный ответ
        expert_answer = await expert.respond(user_query, search_results=search_results)
        conversation_log.append({
            "agent": "expert",
            "action": "initial_response",
            "content": expert_answer
        })
        
        # Итерации проверки и улучшения
        for iteration in range(max_iterations):
            # Критик проверяет ответ
            review = await critic.review(expert_answer, user_query)
            conversation_log.append({
                "agent": "critic",
                "action": "review",
                "iteration": iteration + 1,
                "review": review["review"],
                "decision": review["action"]
            })
            
            if review["is_sufficient"]:
                # Ответ достаточен
                break
            elif review["needs_search"]:
                # Нужен дополнительный поиск
                additional_search = await search.search(f"search:{user_query}")
                search_results.extend(additional_search)
                conversation_log.append({
                    "agent": "search",
                    "action": "additional_search",
                    "iteration": iteration + 1,
                    "results_count": len(additional_search)
                })
                
                # Эксперт дает улучшенный ответ
                expert_answer = await expert.respond(user_query, search_results=search_results)
                conversation_log.append({
                    "agent": "expert",
                    "action": "revised_response",
                    "iteration": iteration + 1,
                    "content": expert_answer
                })
            else:
                # Нужна доработка без дополнительного поиска
                expert_answer = await expert.respond(user_query, search_results=search_results)
                conversation_log.append({
                    "agent": "expert",
                    "action": "revised_response",
                    "iteration": iteration + 1,
                    "content": expert_answer
                })
        
        return {
            "answer": expert_answer,
            "model": "expert-group-chat",
            "iterations": len([log for log in conversation_log if log["agent"] == "critic"]),
            "search_results_used": len(search_results),
            "conversation_log": conversation_log
        }
        
    except Exception as e:
        print(f"❌ Error in expert_group_chat: {e}")
        return {
            "answer": "Произошла ошибка в работе экспертной группы.",
            "model": "expert-group-chat",
            "error": str(e),
            "conversation_log": conversation_log
        }
