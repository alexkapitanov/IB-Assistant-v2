import autogen, asyncio, json, time
from backend.agents.local_search import local_search
from backend.openai_helpers import call_llm
from backend.token_counter import count_tokens
from backend.settings import MODEL_LIMITS

# Конфигурация моделей для агентов
llm_config_expert = {"model": "gpt-4.1"}
llm_config_critic = {"model": "gpt-4.1-mini"}
llm_config_search = {"model": "o3-mini"}

async def run_expert_gc(thread_id, user_q, slots):
    expert = autogen.AssistantAgent("Expert", llm_config=llm_config_expert)
    critic = autogen.AssistantAgent("Critic", llm_config=llm_config_critic)
    search = autogen.AssistantAgent("Search", llm_config=llm_config_search)

    # Глобальные переменные для отслеживания цитат
    citations = []
    citation_counter = 1

    def _search_tool(prompt:str)->str:
        nonlocal citations, citation_counter
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
    
    # Запускаем групповой чат с начальным сообщением
    ans = await mgr.a_initiate_chat(expert, message=user_q)
    
    # Возвращаем последний ответ и модель, которая его сгенерировала, а также цитаты
    final_answer = ans.summary if hasattr(ans, 'summary') else str(ans)
    return {
        "answer": final_answer, 
        "model": "expert-group-chat",
        "citations": citations  # Добавляем список цитат
    }
