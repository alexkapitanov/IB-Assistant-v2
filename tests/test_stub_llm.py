"""
Тест для проверки stub-LLM режима
"""
import os
import pytest
import asyncio


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
        result, latency = asyncio.run(h.call_llm("o3-mini", "ping"))
        assert "[stub]" in result
        assert latency == 0
    finally:
        # Возвращаем исходный ключ
        if original_key is None:
            del os.environ["OPENAI_API_KEY"]
        else:
            os.environ["OPENAI_API_KEY"] = original_key
        importlib.reload(h)


def test_stub_llm_with_different_prompts():
    """Проверяем, что stub отвечает на разные промпты"""
    original_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["OPENAI_API_KEY"] = "stub"

        import importlib
        import backend.openai_helpers as h
        importlib.reload(h)

        # Тестируем разные промпты
        result1, _ = asyncio.run(h.call_llm("gpt-4", "Что такое AI?"))
        result2, _ = asyncio.run(h.call_llm("o3-mini", "Что такое DLP?"))

        assert result1 != result2
        assert "[stub]" in result1
        assert "[stub]" in result2
    finally:
        # Возвращаем исходный ключ
        if original_key is None:
            del os.environ["OPENAI_API_KEY"]
        else:
            os.environ["OPENAI_API_KEY"] = original_key
        importlib.reload(h)
