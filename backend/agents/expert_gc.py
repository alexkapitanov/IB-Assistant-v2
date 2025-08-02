try:
    import autogen
except ImportError:
    autogen = None

import asyncio
import json
from backend.agents.local_search import local_search
from backend.agents.web_search import web_search
from backend.prompts.system_messages import SYSTEM_EXPERT_TEMPLATE, SYSTEM_GENERAL_EXPERT, SYSTEM_AGGREGATOR
from backend import status_bus, config, metrics
import logging

# --- Фабрика для создания доменных экспертов ---

def create_domain_expert(slots: dict) -> "autogen.AssistantAgent":
    """Создает доменного эксперта на основе слотов."""
    if not autogen:
        raise ImportError("Модуль 'autogen' не найден. Пожалуйста, установите pyautogen.")

    product = slots.get("product")
    if product:
        name = f"{product.replace(' ', '_')}_Expert"
        system_message = SYSTEM_EXPERT_TEMPLATE.format(product=product)
    else:
        name = "General_Expert"
        system_message = SYSTEM_GENERAL_EXPERT
    
    return autogen.AssistantAgent(
        name,
        llm_config={"model": config.MODEL_GPT4}, # Используем модель из конфига
        system_message=system_message
    )

# --- Основная функция запуска Expert-GC ---

async def run_expert_gc(thread_id, user_q, slots, plan, logger: logging.Logger):
    """
    Запускает многоагентную группу для генерации ответа.
    Выбирает доменного эксперта, подключает Critic, Search и Aggregator.
    """
    metrics.EXPERT_GC_CALLS.inc()
    logger.info(f"Запуск экспертной группы для вопроса: '{user_q}'")

    if not autogen:
        logger.error("Autogen не импортирован, невозможно запустить Expert-GC.")
        return {"answer": "Ошибка сервера: компонент 'autogen' не доступен.", "model": "system-error", "citations": []}

    # 1. Создание агентов
    try:
        domain_expert = create_domain_expert(slots)
        # Для Search и Critic можно использовать более простые модели
        search_agent = autogen.AssistantAgent("Search_Tool", llm_config={"model": config.MODEL_O3_MINI})
        critic_agent = autogen.AssistantAgent("Critic", llm_config={"model": config.MODEL_GPT4_MINI})
        aggregator_agent = autogen.AssistantAgent("Aggregator", llm_config={"model": config.MODEL_GPT4_MINI}, system_message=SYSTEM_AGGREGATOR)
        logger.info(f"Агенты созданы. Эксперт: {domain_expert.name}")
    except Exception as e:
        logger.error(f"Ошибка при создании агентов: {e}", exc_info=True)
        return {"answer": f"Ошибка сервера при создании агентов: {e}", "model": "system-error", "citations": []}


    # 2. Регистрация инструментов
    citations = []
    citation_counter = 1
    def _search_tool(prompt: str) -> str:
        nonlocal citations, citation_counter
        logger.info(f"Инструмент поиска вызван с запросом: '{prompt}'")
        # ... (логика поиска остается прежней, но можно ее вынести в отдельную функцию)
        hits = local_search(prompt, top_k=7)
        if not hits:
            return "В базе знаний ничего не найдено."
        
        formatted_results = []
        for h in hits:
            source_name = h["meta"].get("file_name", f"source_{citation_counter}")
            citations.append({"id": citation_counter, "source": source_name})
            formatted_results.append(f"[{citation_counter}] {h['text']}")
            citation_counter += 1
        
        return "\n".join(formatted_results)
    
    search_agent.register_function(function_map={"local_search": _search_tool})

    # 3. Настройка группового чата
    agents = [domain_expert, search_agent, critic_agent, aggregator_agent]
    
    # Кастомный выбор следующего агента
    def custom_speaker_selection(last_speaker, groupchat):
        messages = groupchat.messages
        
        # Если последние сообщения от всех, кроме агрегатора, то слово ему
        if len(messages) > len(agents) -1:
             # Проверяем, говорили ли уже все, кроме агрегатора
            speakers_in_round = {msg.get('name') for msg in messages[-len(agents)+1:]}
            if {a.name for a in agents[:-1]}.issubset(speakers_in_round):
                 return aggregator_agent

        # Если это первый ход, то говорит эксперт
        if last_speaker is None:
            return domain_expert
        
        # Если последний говорил эксперт, то слово поиску
        if last_speaker.name == domain_expert.name:
            return search_agent
        
        # После поиска - критик
        if last_speaker.name == search_agent.name:
            return critic_agent

        # В остальных случаях - снова эксперт
        return domain_expert

    gc = autogen.GroupChat(
        agents=agents, 
        messages=[], 
        max_round=12,
        speaker_selection_method=custom_speaker_selection,
        allow_repeat_speaker=True
    )
    
    mgr = autogen.GroupChatManager(
        groupchat=gc,
        llm_config={"model": config.MODEL_GPT4},
    )

    # 4. Публикация статуса о шагах
    plan_steps = plan.get("context", {}).get("plan", [])
    total_steps = len(plan_steps)
    
    async def step_publisher(i, agent_name):
        step_info = plan_steps[i-1] if i <= total_steps else "Завершение"
        await status_bus.publish(thread_id, f"step {i}/{total_steps+1}: {step_info}", agent_name)

    # 5. Запуск чата
    final_answer = {}
    try:
        # Начальное сообщение для запуска
        initial_message = f"Вопрос пользователя: {user_q}\nПлан действий: {json.dumps(plan_steps)}"
        
        # Обертка для пошагового выполнения и публикации статуса
        async def chat_with_steps():
            await step_publisher(1, domain_expert.name)
            await mgr.a_initiate_chat(domain_expert, message=initial_message)
            
            # Публикуем статус для каждого шага в истории чата
            for i, msg in enumerate(mgr.chat_messages[domain_expert]):
                 # +2 потому что первый шаг уже был, и нумерация с 1
                await step_publisher(i + 2, msg.get("name", "unknown"))

            # Последний шаг - агрегация
            await step_publisher(total_steps + 1, aggregator_agent.name)

        # Запуск с таймаутом
        await asyncio.wait_for(chat_with_steps(), timeout=config.GC_TIMEOUT_SEC)

        # 6. Формирование финального ответа
        final_response_msg = next((msg for msg in reversed(gc.messages) if "FINAL_ANSWER:" in msg["content"]), None)
        
        if final_response_msg:
            answer_text = final_response_msg["content"].replace("FINAL_ANSWER:", "").strip()
            final_answer = {
                "answer": answer_text,
                "model": "expert-group-chat",
                "citations": citations
            }
        else:
             final_answer = {"answer": "Не удалось получить финальный ответ от группы.", "model": "system-error", "citations": citations}

    except asyncio.TimeoutError:
        logger.warning("Expert-GC timeout", exc_info=False)
        final_answer = {"answer": "Таймаут экспертной группы.", "model": "system-error", "citations": []}
    except Exception as e:
        logger.error(f"Ошибка в Expert-GC: {e}", exc_info=True)
        final_answer = {"answer": f"Ошибка сервера в Expert-GC: {e}", "model": "system-error", "citations": []}

    return final_answer

# Для теста с таймаутом: alias и обертка для auto_run_groupchat
auto_run_groupchat = run_expert_gc

async def run_chat_with_autogen(*args, **kwargs):
    """Обертка для вызова auto_run_groupchat с таймаутом из конфига"""
    try:
        # auto_run_groupchat может быть замокан тестом
        await asyncio.wait_for(auto_run_groupchat(*args, **kwargs), timeout=config.GC_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        return {"content": "Timeout"}
    # По умолчанию возвращаем структуру без Timeout
    return {"content": "Completed"}
