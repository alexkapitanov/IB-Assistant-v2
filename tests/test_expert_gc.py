"""
Тесты для экспертной группы (Expert Group Chat)
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.expert_gc import (
    CriticAgent,
    ExpertAgent,
    SearchAgent,
    critic,
    expert,
    expert_group_chat,
    search,
)


def test_domain_factory():
    """Тест динамического создания доменных экспертов"""
    # Мокаем AssistantAgent, если нет API ключа
    with patch("backend.agents.expert_gc.AssistantAgent") as mock_agent:
        from backend.agents.expert_gc import create_domain_expert

        mock_expert = type(
            "MockExpert",
            (),
            {
                "name": None,
                "system_message": None,
                "llm_config": None,
            },
        )()

        def mock_create(name, llm_config, system_message):
            mock_expert.name = name
            mock_expert.system_message = system_message
            mock_expert.llm_config = llm_config
            return mock_expert

        mock_agent.side_effect = mock_create

        # Тест с темой Zero Trust
        ex = create_domain_expert({"topic": "Zero Trust"})
        assert "Zero Trust" in ex.system_message
        assert ex.name == "Zero Trust-Expert"

        # Тест с продуктом
        ex_product = create_domain_expert({"topic": "DLP", "product": "InfoWatch"})
        assert "DLP" in ex_product.system_message
        assert "InfoWatch" in ex_product.system_message
        assert ex_product.name == "InfoWatch-Expert"

        # Тест без темы (по умолчанию)
        ex_default = create_domain_expert({})
        assert "информационная безопасность" in ex_default.system_message
        assert ex_default.name == "информационная безопасность-Expert"


def test_aggregator_section():
    """Тест формирования раздела ссылок агрегатором"""
    from backend.prompts.system_messages import SYSTEM_AGGREGATOR

    # Проверяем, что системное сообщение содержит требования
    assert "### Ссылки" in SYSTEM_AGGREGATOR
    assert "[n]" in SYSTEM_AGGREGATOR
    assert "FINAL_ANSWER:" in SYSTEM_AGGREGATOR

    expected_sections = [
        "### Ссылки",
        "FINAL_ANSWER:",
        "[n]",  # Должны быть добавлены ссылки
    ]

    for section in expected_sections:
        assert section in SYSTEM_AGGREGATOR


@pytest.mark.asyncio
async def test_expert_gc_integration():
    """Тест интеграции expert_gc с новыми слотами"""

    with (
        patch("backend.agents.expert_gc.AssistantAgent") as mock_agent,
    patch("backend.agents.expert_gc.GroupChat") as _mock_gc,
        patch("backend.agents.expert_gc.GroupChatManager") as mock_mgr,
        patch("backend.agents.expert_gc.status_bus") as mock_status,
        patch("backend.agents.expert_gc.metrics"),
    ):
        # Настройка моков
        mock_expert = MagicMock()
        mock_expert.name = "DLP-Expert"
        mock_agent.return_value = mock_expert

        mock_manager = AsyncMock()
        mock_manager.a_initiate_chat.return_value = {"content": "Тестовый ответ"}
        mock_mgr.return_value = mock_manager

        mock_status.publish = AsyncMock()

        from backend.agents.expert_gc import run_expert_gc

        # Тестовые данные
        thread_id = "test123"
        plan = ["Анализ DLP", "Поиск документации", "Формирование ответа"]
        ctx = {"slots": {"topic": "DLP", "product": "InfoWatch"}}

        # Вызов функции
        _ = await run_expert_gc(thread_id, plan, ctx)

        # Проверки
        assert mock_agent.call_count == 4  # domain_expert + search + critic + aggregator
        assert mock_status.publish.call_count >= 3  # step статусы + done

        # Проверяем публикацию статусов
        status_calls = [call[0] for call in mock_status.publish.call_args_list]
        step_calls = [call for call in status_calls if len(call) > 1 and "step" in str(call[1])]
        assert len(step_calls) == len(plan)


class TestExpertAgent:
    """Старые тесты - оставляем для совместимости"""

    @pytest.mark.asyncio
    @patch("agents.expert_gc.call_llm", new_callable=AsyncMock)
    async def test_expert_basic_response(self, mock_llm):
        """Тест базового ответа эксперта"""
        pytest.skip("Старый тест - архитектура изменена")

    @pytest.mark.asyncio
    @patch("agents.expert_gc.call_llm", new_callable=AsyncMock)
    async def test_expert_with_search_results(self, mock_llm):
        """Тест ответа эксперта с результатами поиска"""
        pytest.skip("Старый тест - архитектура изменена")

    @pytest.mark.asyncio
    @patch("agents.expert_gc.call_llm", new_callable=AsyncMock)
    async def test_expert_no_results(self, mock_llm):
        """Тест ответа эксперта без результатов поиска"""
        mock_llm.return_value = ("Ничего не найдено", None)

        expert_agent = ExpertAgent()
        res = await expert_agent.respond("Что такое XYZ?")
        assert "ничего" in res.lower()

    def test_expert_update_system_message(self):
        """Тест обновления системного сообщения эксперта"""
        expert_agent = ExpertAgent()
        new_system = "Новый системный промпт"

        expert_agent.update_system_message(new_system)
        assert expert_agent.system_message == new_system


class TestCriticAgent:
    """Тесты критика"""

    @pytest.mark.asyncio
    @patch("agents.expert_gc.call_llm", new_callable=AsyncMock)
    async def test_critic_approves_answer(self, mock_llm):
        mock_llm.return_value = ("OK", None)

        critic_agent = CriticAgent()
        res = await critic_agent.review("Отличный ответ", "Вопрос")
        assert res["is_sufficient"] is True

    @pytest.mark.asyncio
    @patch("agents.expert_gc.call_llm", new_callable=AsyncMock)
    async def test_critic_requests_search(self, mock_llm):
        mock_llm.return_value = ("Недостаточно данных. ADD_SEARCH", None)

        critic_agent = CriticAgent()
        res = await critic_agent.review("Неполный ответ", "Сложный вопрос")
        assert res["needs_search"] is True
        assert res["is_sufficient"] is False

    @pytest.mark.asyncio
    @patch("agents.expert_gc.call_llm", new_callable=AsyncMock)
    async def test_critic_requests_revision(self, mock_llm):
        mock_llm.return_value = ("Нужна доработка терминологии", None)

        critic_agent = CriticAgent()
        res = await critic_agent.review("Ответ с ошибками", "Вопрос")
        assert res["needs_search"] is False
        assert res["is_sufficient"] is False
        assert "доработка" in res["feedback"]


class TestSearchAgent:
    """Тесты поискового агента"""

    @pytest.mark.asyncio
    @patch("agents.expert_gc.local_search")
    async def test_search_basic(self, mock_search):
        mock_search.return_value = [
            {"text": "DLP технология для предотвращения утечек", "score": 0.9},
            {"text": "Data Loss Prevention системы", "score": 0.8},
        ]

        search_agent = SearchAgent()
        results = await search_agent.search("search:DLP")

        assert len(results) == 2
        assert "DLP" in results[0]["text"]
        mock_search.assert_called_once_with("DLP", top_k=5)

    @pytest.mark.asyncio
    @patch("agents.expert_gc.local_search")
    async def test_search_long_text_truncation(self, mock_search):
        long_text = " ".join([f"слово{i}" for i in range(50)])  # 50 слов
        mock_search.return_value = [{"text": long_text, "score": 0.9}]

        search_agent = SearchAgent()
        results = await search_agent.search("search:тест")

        # Проверяем что текст обрезан до 40 слов + "..."
        result_words = results[0]["text"].replace("...", "").split()
        assert len(result_words) <= 40

    @pytest.mark.asyncio
    @patch("agents.expert_gc.local_search")
    async def test_search_without_prefix(self, mock_search):
        mock_search.return_value = [{"text": "результат", "score": 0.9}]

        search_agent = SearchAgent()
        await search_agent.search("простой запрос")

        mock_search.assert_called_once_with("простой запрос", top_k=5)


class TestExpertGroupChat:
    """Тесты группового чата экспертов"""

    @pytest.mark.asyncio
    @patch("agents.expert_gc.search.search")
    @patch("agents.expert_gc.expert.respond")
    @patch("agents.expert_gc.critic.review")
    async def test_group_chat_single_iteration(self, mock_critic, mock_expert, mock_search):
        mock_search.return_value = [{"text": "контекст", "score": 0.9}]
        mock_expert.return_value = "Экспертный ответ на вопрос"
        mock_critic.return_value = {
            "review": "OK",
            "needs_search": False,
            "is_sufficient": True,
            "action": "ok",
        }

        result = await expert_group_chat("Тестовый вопрос")

        assert result["answer"] == "Экспертный ответ на вопрос"
        assert result["model"] == "expert-group-chat"
        assert result["iterations"] == 1
        assert len(result["conversation_log"]) >= 3

    @pytest.mark.asyncio
    @patch("agents.expert_gc.search.search")
    @patch("agents.expert_gc.expert.respond")
    @patch("agents.expert_gc.critic.review")
    async def test_group_chat_with_additional_search(self, mock_critic, mock_expert, mock_search):
        mock_search.return_value = [{"text": "контекст", "score": 0.9}]
        mock_expert.side_effect = ["Первый ответ", "Улучшенный ответ"]

        # Первая проверка требует дополнительный поиск, вторая одобряет
        mock_critic.side_effect = [
            {
                "review": "ADD_SEARCH нужно больше данных",
                "needs_search": True,
                "is_sufficient": False,
                "action": "search",
            },
            {
                "review": "OK теперь достаточно",
                "needs_search": False,
                "is_sufficient": True,
                "action": "ok",
            },
        ]

        result = await expert_group_chat("Сложный вопрос")

        assert result["answer"] == "Улучшенный ответ"
        assert result["iterations"] == 2
        assert mock_search.call_count >= 2
        assert mock_expert.call_count == 2

    @pytest.mark.asyncio
    @patch("agents.expert_gc.search.search")
    @patch("agents.expert_gc.expert.respond")
    @patch("agents.expert_gc.critic.review")
    async def test_group_chat_max_iterations(self, mock_critic, mock_expert, mock_search):
        mock_search.return_value = [{"text": "контекст", "score": 0.9}]
        mock_expert.return_value = "Ответ требует доработки"

        # Критик всегда требует доработку (но не поиск)
        mock_critic.return_value = {
            "review": "Нужна доработка",
            "needs_search": False,
            "is_sufficient": False,
            "action": "revise",
        }

        result = await expert_group_chat("Вопрос", max_iterations=2)

        assert result["iterations"] <= 2
        assert mock_critic.call_count <= 2


class TestAgentInstances:
    """Тесты глобальных экземпляров агентов"""

    def test_global_agents_exist(self):
        assert expert is not None
        assert critic is not None
        assert search is not None

        assert isinstance(expert, ExpertAgent)
        assert isinstance(critic, CriticAgent)
        assert isinstance(search, SearchAgent)

    def test_system_messages_applied(self):
        assert "эксперт по информационной безопасности" in expert.system_message.lower()
        assert "критик" in critic.system_message.lower()
        assert "поиск-хелпер" in search.system_message.lower()
