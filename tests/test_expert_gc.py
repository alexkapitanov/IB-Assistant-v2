"""
Тесты для экспертной группы (Expert Group Chat)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from agents.expert_gc import (
    ExpertAgent, CriticAgent, SearchAgent, 
    expert_group_chat, expert, critic, search
)

class TestExpertAgent:
    """Тесты эксперта по ИБ"""
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.call_llm')
    async def test_expert_basic_response(self, mock_llm):
        """Тест базового ответа эксперта"""
        mock_llm.return_value = ("DLP - это технология предотвращения утечек данных", None)
        
        expert_agent = ExpertAgent()
        result = await expert_agent.respond("Что такое DLP?")
        
        assert "DLP" in result
        assert "технология" in result
        mock_llm.assert_called_once()
    
    @pytest.mark.asyncio 
    @patch('agents.expert_gc.call_llm')
    async def test_expert_with_search_results(self, mock_llm):
        """Тест ответа эксперта с результатами поиска"""
        mock_llm.return_value = ("DLP системы контролируют передачу данных [1]", None)
        
        search_results = [
            {"text": "DLP - Data Loss Prevention технология"}
        ]
        
        expert_agent = ExpertAgent()
        result = await expert_agent.respond("Что такое DLP?", search_results=search_results)
        
        assert "[1]" in result or "DLP" in result
    
    def test_expert_update_system_message(self):
        """Тест обновления системного сообщения эксперта"""
        expert_agent = ExpertAgent()
        new_system = "Новый системный промпт"
        
        expert_agent.update_system_message(new_system)
        assert expert_agent.system_message == new_system

class TestCriticAgent:
    """Тесты критика"""
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.call_llm')
    async def test_critic_approves_answer(self, mock_llm):
        """Тест одобрения ответа критиком"""
        mock_llm.return_value = ("Ответ полный и корректный. OK", None)
        
        critic_agent = CriticAgent()
        result = await critic_agent.review("Хороший ответ", "Вопрос")
        
        assert result["is_sufficient"] == True
        assert result["needs_search"] == False
        assert result["action"] == "ok"
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.call_llm') 
    async def test_critic_requests_search(self, mock_llm):
        """Тест запроса дополнительного поиска критиком"""
        mock_llm.return_value = ("Недостаточно данных. ADD_SEARCH", None)
        
        critic_agent = CriticAgent()
        result = await critic_agent.review("Неполный ответ", "Сложный вопрос")
        
        assert result["needs_search"] == True
        assert result["is_sufficient"] == False
        assert result["action"] == "search"
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.call_llm')
    async def test_critic_requests_revision(self, mock_llm):
        """Тест запроса доработки критиком"""
        mock_llm.return_value = ("Нужна доработка терминологии", None)
        
        critic_agent = CriticAgent()
        result = await critic_agent.review("Ответ с ошибками", "Вопрос")
        
        assert result["needs_search"] == False
        assert result["is_sufficient"] == False
        assert result["action"] == "revise"

class TestSearchAgent:
    """Тесты поискового агента"""
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.local_search')
    async def test_search_basic(self, mock_search):
        """Тест базового поиска"""
        mock_search.return_value = [
            {"text": "DLP технология для предотвращения утечек", "score": 0.9},
            {"text": "Data Loss Prevention системы", "score": 0.8}
        ]
        
        search_agent = SearchAgent()
        results = await search_agent.search("search:DLP")
        
        assert len(results) == 2
        assert "DLP" in results[0]["text"]
        mock_search.assert_called_once_with("DLP", top_k=5)
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.local_search')
    async def test_search_long_text_truncation(self, mock_search):
        """Тест обрезания длинного текста до 40 слов"""
        long_text = " ".join([f"слово{i}" for i in range(50)])  # 50 слов
        mock_search.return_value = [
            {"text": long_text, "score": 0.9}
        ]
        
        search_agent = SearchAgent()
        results = await search_agent.search("search:тест")
        
        # Проверяем что текст обрезан до 40 слов + "..."
        result_words = results[0]["text"].replace("...", "").split()
        assert len(result_words) <= 40
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.local_search')
    async def test_search_without_prefix(self, mock_search):
        """Тест поиска без префикса search:"""
        mock_search.return_value = [{"text": "результат", "score": 0.9}]
        
        search_agent = SearchAgent()
        results = await search_agent.search("простой запрос")
        
        mock_search.assert_called_once_with("простой запрос", top_k=5)

class TestExpertGroupChat:
    """Тесты группового чата экспертов"""
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.search.search')
    @patch('agents.expert_gc.expert.respond')
    @patch('agents.expert_gc.critic.review')
    async def test_group_chat_single_iteration(self, mock_critic, mock_expert, mock_search):
        """Тест одной итерации группового чата"""
        mock_search.return_value = [{"text": "контекст", "score": 0.9}]
        mock_expert.return_value = "Экспертный ответ на вопрос"
        mock_critic.return_value = {
            "review": "OK",
            "needs_search": False,
            "is_sufficient": True,
            "action": "ok"
        }
        
        result = await expert_group_chat("Тестовый вопрос")
        
        assert result["answer"] == "Экспертный ответ на вопрос"
        assert result["model"] == "expert-group-chat"
        assert result["iterations"] == 1
        assert len(result["conversation_log"]) >= 3
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.search.search')
    @patch('agents.expert_gc.expert.respond')
    @patch('agents.expert_gc.critic.review')
    async def test_group_chat_with_additional_search(self, mock_critic, mock_expert, mock_search):
        """Тест группового чата с дополнительным поиском"""
        mock_search.return_value = [{"text": "контекст", "score": 0.9}]
        mock_expert.side_effect = ["Первый ответ", "Улучшенный ответ"]
        
        # Первая проверка требует дополнительный поиск, вторая одобряет
        mock_critic.side_effect = [
            {
                "review": "ADD_SEARCH нужно больше данных",
                "needs_search": True,
                "is_sufficient": False,
                "action": "search"
            },
            {
                "review": "OK теперь достаточно",
                "needs_search": False,
                "is_sufficient": True,
                "action": "ok"
            }
        ]
        
        result = await expert_group_chat("Сложный вопрос")
        
        assert result["answer"] == "Улучшенный ответ"
        assert result["iterations"] == 2
        assert mock_search.call_count >= 2  # Начальный + дополнительный поиск
        assert mock_expert.call_count == 2  # Первый + улучшенный ответ
    
    @pytest.mark.asyncio
    @patch('agents.expert_gc.search.search')
    @patch('agents.expert_gc.expert.respond')
    @patch('agents.expert_gc.critic.review')
    async def test_group_chat_max_iterations(self, mock_critic, mock_expert, mock_search):
        """Тест ограничения максимального количества итераций"""
        mock_search.return_value = [{"text": "контекст", "score": 0.9}]
        mock_expert.return_value = "Ответ требует доработки"
        
        # Критик всегда требует доработку (но не поиск)
        mock_critic.return_value = {
            "review": "Нужна доработка",
            "needs_search": False,
            "is_sufficient": False,
            "action": "revise"
        }
        
        result = await expert_group_chat("Вопрос", max_iterations=2)
        
        # Проверяем что не превысили лимит итераций
        assert result["iterations"] <= 2
        assert mock_critic.call_count <= 2

class TestAgentInstances:
    """Тесты глобальных экземпляров агентов"""
    
    def test_global_agents_exist(self):
        """Тест что глобальные экземпляры агентов созданы"""
        assert expert is not None
        assert critic is not None
        assert search is not None
        
        assert isinstance(expert, ExpertAgent)
        assert isinstance(critic, CriticAgent)
        assert isinstance(search, SearchAgent)
    
    def test_system_messages_applied(self):
        """Тест что системные сообщения применены к агентам"""
        assert "эксперт по информационной безопасности" in expert.system_message.lower()
        assert "критик" in critic.system_message.lower()
        assert "поиск-хелпер" in search.system_message.lower()
