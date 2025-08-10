"""
Модуль для подсчета токенов в сообщениях
"""
from typing import Any, Dict, List

import tiktoken

DEFAULT_MODEL = "gpt-4.1-mini"


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Подсчитывает количество токенов в тексте для указанной модели.
    Для поддерживаемых моделей используется кодек cl100k_base.
    """
    try:
        # Все текущие разрешённые модели используют совместимый токенизатор
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Простая эвристика если tiktoken не работает
        return int(len(text.split()) * 1.3)  # Примерно 1.3 токена на слово


def count_messages_tokens(messages: List[Dict[str, Any]], model: str = DEFAULT_MODEL) -> int:
    """
    Подсчитывает общее количество токенов в списке сообщений
    """
    total = 0
    for message in messages:
        content = message.get("content", "")
        total += count_tokens(content, model)
        # Добавляем небольшой overhead на структуру сообщения
        total += 4  # ~4 токена на role, name и другие метаданные

    return total
