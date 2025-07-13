import pytest
from backend.agents.planner import ask_planner
from backend.json_utils import BadJSON
from unittest.mock import patch
import asyncio


@pytest.mark.asyncio
async def test_planner_with_valid_json():
    """Тест планировщика с корректным JSON ответом"""
    # Мокаем call_llm чтобы вернуть корректный JSON
    with patch('backend.agents.planner.call_llm') as mock_llm:
        mock_llm.return_value = ('{"need_clarify": false, "draft": "Тестовый ответ"}', None)
        
        result = await ask_planner("test_thread", "Тестовый вопрос", {})
        
        assert "answer" in result
        assert result["answer"] == "Тестовый ответ"
        assert result["model"] == "gpt-4o"


@pytest.mark.asyncio 
async def test_planner_with_clarification():
    """Тест планировщика с требованием уточнения"""
    with patch('backend.agents.planner.call_llm') as mock_llm:
        mock_llm.return_value = (
            '{"need_clarify": true, "clarify": "Уточните, пожалуйста, ваш вопрос"}', 
            None
        )
        
        result = await ask_planner("test_thread", "Неточный вопрос", {})
        
        assert "answer" in result
        assert result["answer"] == "Уточните, пожалуйста, ваш вопрос"
        assert result["follow_up"] == True


@pytest.mark.asyncio
async def test_planner_with_bad_json():
    """Тест планировщика с некорректным JSON"""
    with patch('backend.agents.planner.call_llm') as mock_llm:
        # Возвращаем некорректный JSON
        mock_llm.return_value = ('This is not JSON at all, just text', None)
        
        result = await ask_planner("test_thread", "Тестовый вопрос", {})
        
        assert result["content"] == "🤖 Пока не понял формулировку, уточните пожалуйста."
        assert result["type"] == "chat"
        assert result["role"] == "system"


@pytest.mark.asyncio
async def test_planner_with_malformed_json():
    """Тест планировщика с почти корректным JSON"""
    with patch('backend.agents.planner.call_llm') as mock_llm:
        # JSON с синтаксической ошибкой
        mock_llm.return_value = ('{"need_clarify": true, "clarify": "Ответ", }', None)
        
        result = await ask_planner("test_thread", "Тестовый вопрос", {})
        
        # Должен вернуть системное сообщение об ошибке
        assert result["content"] == "🤖 Пока не понял формулировку, уточните пожалуйста."
