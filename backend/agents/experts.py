"""
Доменные эксперты для Expert-GC
"""
from autogen import AssistantAgent

# Конфигурация моделей
llm_config_expert = {"model": "gpt-4.1"}
llm_config_aggregator = {"model": "gpt-4.1-mini"}

PRODUCT_EXPERT_PROMPT = """Ты — ведущий эксперт по продукту {product}.
Твоя задача — дать точный и подробный ответ на вопрос пользователя, касающийся именно этого продукта.
Используй только предоставленные фрагменты из базы знаний (local_search) и результаты веб-поиска (web_search).
Каждое утверждение в ответе должно сопровождаться цитатой-сноской [¹], [²] и т.д.
Не придумывай информацию. Если ответа нет в источниках, сообщи об этом.
"""

GENERAL_EXPERT_PROMPT = """Ты — эксперт по общим вопросам информационной безопасности.
Твоя задача — дать развернутый ответ на вопрос пользователя, основываясь на лучших практиках.
Используй только предоставленные фрагменты из базы знаний (local_search) и результаты веб-поиска (web_search).
Каждое утверждение в ответе должно сопровождаться цитатой-сноской [¹], [²] и т.д.
Не придумывай информацию. Если ответа нет в источниках, сообщи об этом.
"""

AGGREGATOR_PROMPT = """Твоя роль — агрегатор доказательств.
Проанализируй весь диалог и выполни 2 задачи:
1.  Убедись, что все утверждения в финальном ответе эксперта подкреплены цитатами [¹]. Если нет, укажи на это эксперту.
2.  Собери все уникальные источники, на которые ссылаются эксперты, и оформи их в виде нумерованного списка под заголовком «Ссылки:».
Твой ответ должен содержать ТОЛЬКО этот список.
"""

def get_product_expert(product_name: str) -> AssistantAgent:
    """Возвращает агента, настроенного на конкретный продукт."""
    return AssistantAgent(
        "ProductExpert",
        llm_config=llm_config_expert,
        system_message=PRODUCT_EXPERT_PROMPT.format(product=product_name)
    )

def get_general_expert() -> AssistantAgent:
    """Возвращает агента с общими знаниями."""
    return AssistantAgent(
        "GeneralExpert",
        llm_config=llm_config_expert,
        system_message=GENERAL_EXPERT_PROMPT
    )

def get_evidence_aggregator() -> AssistantAgent:
    """Возвращает агента для сбора и проверки ссылок."""
    return AssistantAgent(
        "EvidenceAggregator",
        llm_config=llm_config_aggregator,
        system_message=AGGREGATOR_PROMPT
    )
