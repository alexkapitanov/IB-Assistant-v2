import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from backend.agents.planner import _build_plan

@pytest.mark.asyncio
async def test_build_plan_parses_json_correctly():
    """
    Проверяет, что _build_plan корректно парсит JSON от LLM.
    """
    # Мокаем ответ от LLM
    mock_response = {
        "need_clarify": False,
        "clarify": "",
        "need_escalate": False,
        "draft": "Вот краткий ответ.",
        "plan": ["Шаг 1: Сделать что-то", "Шаг 2: Проверить результат"]
    }
    
    # Настраиваем мок для асинхронного вызова
    mock_call_llm = AsyncMock(return_value=(json.dumps(mock_response, ensure_ascii=False), 100))

    # Вызываем функцию с моком
    with patch('backend.agents.planner.call_llm', mock_call_llm):
        logger = MagicMock()
        plan = await _build_plan("какой-то вопрос", {}, logger)

    # Проверяем результат
    assert isinstance(plan, dict)
    assert plan["need_clarify"] is False
    assert "draft" in plan
    assert isinstance(plan["plan"], list)
    assert len(plan["plan"]) == 2
    assert plan["plan"][0] == "Шаг 1: Сделать что-то"
    
    # Проверяем, что LLM был вызван
    mock_call_llm.assert_called_once()
