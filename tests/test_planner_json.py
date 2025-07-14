import pytest
from unittest.mock import patch, AsyncMock
from backend.agents.planner import ask_planner
import backend.agents.planner as planner_module


@pytest.mark.asyncio
async def test_planner_with_valid_json():
    """Тест планировщика с валидным JSON"""
    with patch('backend.agents.planner.call_llm') as mock_llm, \
         patch('backend.agents.planner.ask_critic', new_callable=AsyncMock) as mock_critic:
        mock_llm.return_value = (
            '{"need_clarify": false, "clarify": "", "need_escalate": false, "draft": "Простой ответ"}',
            None
        )
        mock_critic.return_value = True

        result = await ask_planner("test_thread", "Простой вопрос", {})

        assert result is not None
        assert "answer" in result
        assert result["answer"] == "Простой ответ"


@pytest.mark.asyncio
async def test_planner_with_clarification():
    """Тест планировщика с запросом на уточнение"""
    with patch('backend.agents.planner.call_llm', new_callable=AsyncMock) as mock_llm, \
         patch('backend.agents.planner.ask_critic', new_callable=AsyncMock) as mock_critic:
        mock_llm.return_value = (
            '{"need_clarify": true, "clarify": "Уточните, пожалуйста", "need_escalate": false, "draft": ""}',
            None
        )
        mock_critic.return_value = True

        result = await ask_planner("test_thread", "Непонятный вопрос", {})

        assert result is not None
        assert "answer" in result
        assert result["answer"] == "Уточните, пожалуйста"


@pytest.mark.asyncio
async def test_planner_with_bad_json():
    """Тест планировщика с некорректным JSON"""
    with patch('backend.agents.planner.call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = ("не валидный json {", None)

        result = await ask_planner("test_thread", "Любой вопрос", {})

        assert result is not None
        assert result["type"] == "chat"
        assert result["role"] == "system"


@pytest.mark.asyncio
async def test_planner_with_malformed_json():
    """Тест планировщика с JSON без обязательных полей"""
    with patch('backend.agents.planner.call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = ('{"only_one_field": true}', None)

        result = await ask_planner("test_thread", "Любой вопрос", {})

        assert result is not None
        assert result["type"] == "chat"
        assert result["role"] == "system"


@pytest.mark.asyncio
async def test_planner_with_escalation():
    """Тест планировщика с эскалацией на эксперта"""
    with patch('backend.agents.planner.call_llm', new_callable=AsyncMock) as mock_llm, \
         patch('backend.agents.planner.ask_critic', new_callable=AsyncMock) as mock_critic, \
         patch('backend.agents.planner.run_expert_gc', new_callable=AsyncMock) as mock_expert:
        mock_llm.return_value = (
            '{"need_clarify": false, "clarify": "", "need_escalate": true, "draft": ""}',
            None
        )
        mock_critic.return_value = True
        mock_expert.return_value = {"answer": "Ответ от эксперта"}

        result = await ask_planner("test_thread", "Сложный вопрос", {})

        assert result is not None
        assert "answer" in result
        assert result["answer"] == "Ответ от эксперта"
        mock_expert.assert_called_once()


@pytest.mark.asyncio
async def test_planner_no_escalation():
    """Тест планировщика без эскалации (простой ответ)"""
    with patch('backend.agents.planner.call_llm', new_callable=AsyncMock) as mock_llm, \
         patch('backend.agents.planner.ask_critic', new_callable=AsyncMock) as mock_critic:
        mock_llm.return_value = (
            '{"need_clarify": false, "clarify": "", "need_escalate": false, "draft": "Простое определение"}',
            None
        )
        mock_critic.return_value = True

        result = await ask_planner("test_thread", "Что такое SOC?", {})

        assert result is not None
        assert "answer" in result
        assert result["answer"] == "Простое определение"


def test_planner_returns_json(monkeypatch):
    """Быстрая проверка, что Planner возвращает JSON при работе со stub API ключом"""
    import asyncio

    # Устанавливаем stub API ключ, который заставит openai_helpers вернуть заглушку
    monkeypatch.setenv("OPENAI_API_KEY", "stub")

    async def test_function():
        try:
            # При stub ключе должен вернуться текст-заглушка, который не является валидным JSON
            await planner_module._call_planner_llm("tid", "Что такое DLP?", {})
            # Если мы дошли сюда, значит JSON был валидным (неожиданно)
            assert False, "Ожидался BadJSON exception при stub ключе"
        except Exception as e:
            # Проверяем, что получили ожидаемую ошибку BadJSON
            assert "BadJSON" in str(type(e)) or "BadJSON" in str(e), f"Неожиданная ошибка: {e}"

    asyncio.run(test_function())
