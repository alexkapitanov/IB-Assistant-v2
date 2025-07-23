try:
    import autogen
except ImportError as e:
    # Создаем "пустышку", чтобы остальная часть файла могла быть импортирована
    # без ошибок, а реальная ошибка будет обработана в run_expert_gc.
    autogen = None

import asyncio, json, time
from backend.agents.local_search import local_search
from backend.agents.web_search import web_search
from backend.openai_helpers import call_llm
from backend.token_counter import count_tokens
from backend.settings import MODEL_LIMITS
from backend.async_timeout import with_timeout
from backend import config
import logging

# Конфигурация моделей для агентов
llm_config_expert = {"model": "gpt-4.1"}
llm_config_critic = {"model": "gpt-4.1-mini"}
llm_config_search = {"model": "o3-mini"}

FALLBACK_MSG = {
    "type": "chat",
    "role": "system",
    "content": "⚠️ Время вышло (5 мин). Ответ может быть неполным."
}

def _inject_plan(gc, plan_steps: list[str]):
    """Обновляет системное сообщение для следования плану"""
    gc.update_system_message(
        f"Следуй по шагам плана: {', '.join(plan_steps)}. "
        "Отмечай выполненный пункт галочкой ✓."
    )

@with_timeout(lambda: config.GC_TIMEOUT_SEC, FALLBACK_MSG)
async def run_expert_gc(thread_id, user_q, slots, plan, logger: logging.Logger):
    logger.info(f"Запуск экспертной группы для вопроса: '{user_q}'")
    
    if autogen is None:
        logger.error("Ошибка: модуль 'autogen' не был импортирован. Проверьте установку пакета pyautogen.", exc_info=False)
        return {
            "answer": "Ошибка сервера: компонент 'autogen' не найден. Невозможно запустить экспертную группу.",
            "model": "system-error",
            "citations": []
        }

    try:
        expert = autogen.AssistantAgent("Expert", llm_config=llm_config_expert)
        critic = autogen.AssistantAgent("Critic", llm_config=llm_config_critic)
        search = autogen.AssistantAgent("Search", llm_config=llm_config_search)
        logger.info("Агенты Expert, Critic, Search успешно созданы.")
    except NameError as e:
        logger.error("Ошибка: autogen не найден. Пожалуйста, проверьте установку.", exc_info=True)
        return {
            "answer": "Ошибка сервера: компонент 'autogen' не найден. Невозможно запустить экспертную группу.",
            "model": "system-error",
            "citations": []
        }
    except Exception as e:
        logger.error(f"Неожиданная ошибка при создании агентов autogen: {e}", exc_info=True)
        return {
            "answer": f"Ошибка сервера: не удалось создать агентов. {e}",
            "model": "system-error",
            "citations": []
        }

    search.register_function(name="web_search")(web_search)

    # Глобальные переменные для отслеживания цитат
    citations = []
    citation_counter = 1

    def _search_tool(prompt:str)->str:
        nonlocal citations, citation_counter
        logger.info(f"Инструмент поиска вызван с запросом: '{prompt}'")
        # Рассчитываем доступные токены для RAG
        # prompt: "search for: ..."
        q = prompt.replace("search for:","").strip()
        
        # Получаем лимит токенов для экспертной модели
        model_limit = MODEL_LIMITS.get(llm_config_expert["model"], 8192)
        
        # Считаем токены в текущем промпте/запросе
        prompt_tokens = count_tokens(q)
        
        # Оставляем ~1500 токенов для ответа модели
        expected_tokens = model_limit - prompt_tokens - 1500
        
        hits = local_search(q, top_k=15, expected_tokens=expected_tokens)
        logger.info(f"Найдено {len(hits)} фрагментов в локальном поиске.")
        
        # Оборачиваем каждый фрагмент в цитату и собираем источники
        formatted_results = []
        for h in hits:
            source_name = h["meta"].get("file_name", f"source_{citation_counter}")
            citations.append((citation_counter, source_name))
            formatted_results.append(f"{h['text']} [^{citation_counter}]")
            citation_counter += 1
        
        return "\n".join(formatted_results)
    
    search.register_function(function_map={"local_search": _search_tool})

    gc = autogen.GroupChat(agents=[expert, critic, search], max_round=7)
    mgr = autogen.GroupChatManager(groupchat=gc, llm_config=llm_config_expert)
    logger.info("Менеджер группового чата создан.")
    
    # Проверяем, есть ли план от планировщика и добавляем его в контекст
    context = plan.get("context", {})
    if context.get("plan"):
        _inject_plan(mgr, context["plan"])
        logger.info(f"План внедрен в Expert-GC: {context['plan']}")
    
    logger.info("Запуск чата...")
    
    # Запускаем групповой чат с начальным сообщением
    try:
        ans = await mgr.a_initiate_chat(expert, message=user_q)
        logger.info("Групповой чат успешно завершен.")
    except Exception as e:
        logger.error(f"Ошибка во время выполнения группового чата autogen: {e}", exc_info=True)
        return {
            "answer": f"Ошибка сервера: произошла ошибка в работе экспертной группы. {e}",
            "model": "system-error",
            "citations": citations
        }

    
    # Возвращаем последний ответ и модель, которая его сгенерировала, а также цитаты
    final_answer = ans.summary if hasattr(ans, 'summary') else str(ans)
    logger.info(f"Финальный ответ группы: '{final_answer[:150]}...'")
    return {
        "answer": final_answer, 
        "model": "expert-group-chat",
        "citations": citations  # Добавляем список цитат
    }
