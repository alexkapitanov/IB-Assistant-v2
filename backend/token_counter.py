"""
Модуль для подсчета токенов в сообщениях
"""
import tiktoken
from typing import List, Dict, Any

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Подсчитывает количество токенов в тексте для указанной модели
    """
    try:
        # Для большинства моделей OpenAI используем cl100k_base encoding
        if "gpt-4" in model or "o3" in model:
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            # Fallback для других моделей
            encoding = tiktoken.get_encoding("cl100k_base")
        
        return len(encoding.encode(text))
    except Exception:
        # Простая эвристика если tiktoken не работает
        return len(text.split()) * 1.3  # Примерно 1.3 токена на слово

def count_messages_tokens(messages: List[Dict[str, Any]], model: str = "gpt-4") -> int:
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
