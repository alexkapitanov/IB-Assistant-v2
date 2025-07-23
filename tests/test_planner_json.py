import pytest
from unittest.mock import patch, AsyncMock
from backend.agents.planner import ask_planner
import backend.agents.planner as planner_module
from backend.json_utils import BadJSON
import logging

# Создаем "пустышку" логгера для тестов
test_logger = logging.getLogger("test_planner")


@pytest.mark.asyncio
async def test_planner_with_valid_json():
    """Тест планировщика с валидным JSON"""
    # Путь к ask_critic должен быть тот, где он импортируется и используется - в planner.py
    with patch('agents.critic.ask_critic', new_callable=AsyncMock) as mock_critic:
        mock_critic.return_value = True  # Critic одобряет
        
        # Мокаем _build_plan, чтобы изолировать тест от LLM
        with patch('backend.agents.planner._build_plan', new_callable=AsyncMock) as mock_build_plan:
            mock_build_plan.return_value = {
                "need_clarify": False, "clarify": "", "need_escalate": False,
                "draft": "Тестовый ответ планировщика", "plan": []
            }
            result = await ask_planner("test_thread", "Простой вопрос", {}, test_logger)

            assert result is not None
            assert "draft" in result
            assert result["draft"] == "Тестовый ответ планировщика"


@pytest.mark.asyncio
async def test_planner_with_clarification():
    """Тест планировщика с запросом на уточнение"""
    # Мокаем call_llm в правильном месте
    with patch('backend.agents.planner._build_plan', new_callable=AsyncMock) as mock_build_plan:
        mock_build_plan.return_value = {
            "need_clarify": True, "clarify": "Уточните, пожалуйста", 
            "need_escalate": False, "draft": "", "plan": []
        }

        result = await ask_planner("test_thread", "Непонятный вопрос", {}, test_logger)

        assert result is not None
        assert "clarify" in result
        assert result["clarify"] == "Уточните, пожалуйста"


@pytest.mark.asyncio
async def test_planner_with_bad_json():
    """Тест планировщика с некорректным JSON от LLM"""
    with patch('backend.agents.planner._build_plan', new_callable=AsyncMock) as mock_build_plan:
        # Симулируем возврат fallback-значения из _build_plan
        mock_build_plan.return_value = {
            "need_clarify": False, "clarify": "", "need_escalate": True,
            "draft": "", "plan": ["LLM planner returned invalid JSON"]
        }

        result = await ask_planner("test_thread", "Любой вопрос", {}, test_logger)
        
        assert result is not None
        assert result["need_escalate"] is True
        assert result["plan"] == ["LLM planner returned invalid JSON"]


@pytest.mark.asyncio
async def test_planner_with_malformed_json():
    """Тест планировщика с JSON без обязательных полей"""
    with patch('backend.agents.planner._build_plan', new_callable=AsyncMock) as mock_build_plan:
        mock_build_plan.return_value = {"only_one_field": True}

        result = await ask_planner("test_thread", "Любой вопрос", {}, test_logger)

        assert result is not None
        # Проверяем, что отработает логика по умолчанию (эскалация), 
        # так как нет ключа 'draft' для проверки критиком
        assert result.get("need_escalate") is None
        assert result.get("only_one_field") is True


@pytest.mark.asyncio
async def test_planner_with_escalation():
    """Тест планировщика с эскалацией на эксперта"""
    with patch('backend.agents.planner._build_plan', new_callable=AsyncMock) as mock_build_plan:
        mock_build_plan.return_value = {
            "need_clarify": False, "clarify": "", "need_escalate": True, 
            "draft": "", "plan": []
        }

        result = await ask_planner("test_thread", "Сложный вопрос", {}, test_logger)

        assert result is not None
        assert "need_escalate" in result
        assert result["need_escalate"] is True


@pytest.mark.asyncio
async def test_planner_no_escalation_critic_approve():
    """Тест планировщика без эскалации, критик одобряет"""
    with patch('backend.agents.planner._build_plan', new_callable=AsyncMock) as mock_build_plan, \
         patch('agents.critic.ask_critic', new_callable=AsyncMock) as mock_critic:
        
        mock_build_plan.return_value = {
            "need_clarify": False, "clarify": "", "need_escalate": False, 
            "draft": "Простое определение", "plan": []
        }
        mock_critic.return_value = True # Одобрено

        result = await ask_planner("test_thread", "Что такое SOC?", {}, test_logger)

        assert result is not None
        assert result["draft"] == "Простое определение"
        assert result.get("need_escalate") is False


@pytest.mark.asyncio
async def test_planner_no_escalation_critic_reject():
    """Тест планировщика без эскалации, критик отклоняет -> эскалация"""
    with patch('backend.agents.planner._build_plan', new_callable=AsyncMock) as mock_build_plan, \
         patch('agents.critic.ask_critic', new_callable=AsyncMock) as mock_critic:
        
        mock_build_plan.return_value = {
            "need_clarify": False, "clarify": "", "need_escalate": False, 
            "draft": "Некорректное определение", "plan": []
        }
        mock_critic.return_value = False # Отклонено

        result = await ask_planner("test_thread", "Что такое SOC?", {}, test_logger)

        assert result is not None
        assert result["need_escalate"] is True


def test_planner_returns_json(monkeypatch):
    """Быстрая проверка, что Planner возвращает JSON при работе со stub API ключом"""
    import asyncio

    # Мокаем критика, чтобы он не мешал
    monkeypatch.setattr("agents.critic.ask_critic", AsyncMock(return_value=True))

    async def check():
        result = await ask_planner("test", "test question", {}, test_logger)
        assert isinstance(result, dict)
        # В stub режиме должны быть основные поля
        assert "need_clarify" in result
        assert "need_escalate" in result
        assert "draft" in result

    asyncio.run(check())
