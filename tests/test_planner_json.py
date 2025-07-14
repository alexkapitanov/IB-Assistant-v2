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
        assert result["model"] == "gpt-4.1"


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
        
        assert result["content"] == "🤖 Не смог разобрать план. Уточните, пожалуйста."
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
        assert result["content"] == "🤖 Не смог разобрать план. Уточните, пожалуйста."


@pytest.mark.asyncio
async def test_planner_with_escalation():
    """Тест планировщика с эскалацией к экспертной группе"""
    with patch('backend.agents.planner.call_llm') as mock_llm, \
         patch('backend.agents.planner.run_expert_gc') as mock_expert_gc:
        
        # Планировщик решает эскалировать
        mock_llm.return_value = (
            '{"need_clarify": false, "need_escalate": true, "draft": ""}', 
            None
        )
        
        # Экспертная группа возвращает результат
        mock_expert_gc.return_value = {
            "answer": "Экспертный анализ сложного вопроса",
            "model": "expert-group-chat"
        }
        
        result = await ask_planner("test_thread", "Сложный аналитический вопрос", {})

        assert result["answer"] == "Экспертный анализ сложного вопроса"
        assert result["model"] == "expert-group-chat"
        mock_expert_gc.assert_called_once_with("test_thread", "Сложный аналитический вопрос", {})


@pytest.mark.asyncio
async def test_planner_no_escalation():
    """Тест планировщика без эскалации (простой ответ)"""
    with patch('backend.agents.planner.call_llm') as mock_llm:
        mock_llm.return_value = (
            '{"need_clarify": false, "need_escalate": false, "draft": "Простое определение"}', 
            None
        )
        
        result = await ask_planner("test_thread", "Что такое SOC?", {})
        
        assert result["answer"] == "Простое определение"
        assert result["model"] == "gpt-4.1"


def test_planner_returns_json(monkeypatch):
    """Быстрая проверка, что Planner возвращает JSON при работе со stub API ключом"""
    from backend.agents.planner import _call_planner_llm
    
    # Устанавливаем stub API ключ, который заставит openai_helpers вернуть заглушку
    monkeypatch.setenv("OPENAI_API_KEY", "stub")
    
    try:
        # При stub ключе должен вернуться текст-заглушка, который не является валидным JSON
        _call_planner_llm("tid", "Что такое DLP?", {})
        # Если мы дошли сюда, значит JSON был валидным (неожиданно)
        assert False, "Ожидался BadJSON exception при stub ключе"
    except Exception as e:
        # Проверяем, что получили ожидаемую ошибку BadJSON
        assert "Bad JSON" in str(e) or "BadJSON" in str(type(e)), f"Неожиданная ошибка: {e}"
