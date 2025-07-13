"""
Тест для проверки stub-LLM режима
"""
import os
import pytest


def test_stub_llm_mode():
    """Проверяем, что stub-режим работает корректно"""
    # Устанавливаем stub ключ
    original_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["OPENAI_API_KEY"] = "stub"
        
        # Импортируем модуль после установки переменной окружения
        import importlib
        import backend.openai_helpers as h
        importlib.reload(h)
        
        # Тестируем stub-функцию
        result, latency = h.call_llm("o3-mini", "ping")
        
        assert result.startswith("[stub]")
        assert latency == 0
        assert "Тестовый ответ" in result
        
    finally:
        # Восстанавливаем исходное значение
        if original_key is not None:
            os.environ["OPENAI_API_KEY"] = original_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]


def test_stub_llm_with_different_prompts():
    """Проверяем, что stub отвечает на разные промпты"""
    original_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["OPENAI_API_KEY"] = "stub"
        
        import importlib
        import backend.openai_helpers as h
        importlib.reload(h)
        
        # Тестируем разные промпты
        result1, _ = h.call_llm("gpt-4", "Что такое AI?")
        result2, _ = h.call_llm("o3-mini", "Классификатор", tools=[])
        
        assert result1.startswith("[stub]")
        assert result2.startswith("[stub]")
        
    finally:
        if original_key is not None:
            os.environ["OPENAI_API_KEY"] = original_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
