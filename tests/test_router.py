"""
Тесты для роутера интентов
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from agents.router import classify_intent, cheap_faq_answer, route_query

class TestIntentClassifier:
    """Тесты классификатора интентов"""
    
    @pytest.mark.asyncio
    @patch('agents.router.call_llm', new_callable=AsyncMock)
    async def test_classify_get_file_intent(self, mock_llm):
        """Тест классификации намерения получить файл"""
        mock_llm.return_value = ("get_file", None)
        
        result = await classify_intent("Нужен опросный лист по DLP")
        assert result == "get_file"
    
    @pytest.mark.asyncio
    @patch('agents.router.call_llm', new_callable=AsyncMock)
    async def test_classify_simple_faq_intent(self, mock_llm):
        """Тест классификации простого FAQ вопроса"""
        mock_llm.return_value = ("simple_faq", None)
        
        result = await classify_intent("Что такое DLP?")
        assert result == "simple_faq"
    
    @pytest.mark.asyncio
    @patch('agents.router.call_llm', new_callable=AsyncMock)
    async def test_classify_complex_intent(self, mock_llm):
        """Тест классификации сложного аналитического вопроса"""
        mock_llm.return_value = ("complex", None)
        
        result = await classify_intent("Сравни DLP решения по TCO и возможностям интеграции")
        assert result == "complex"
    
    @pytest.mark.asyncio
    @patch('agents.router.call_llm', new_callable=AsyncMock)
    async def test_classify_invalid_response_defaults_to_complex(self, mock_llm):
        """Тест что некорректный ответ классификатора приводит к complex"""
        mock_llm.return_value = ("invalid_intent", None)
        
        result = await classify_intent("Какой-то запрос")
        assert result == "complex"
    
    @pytest.mark.asyncio
    @patch('agents.router.call_llm', new_callable=AsyncMock)
    async def test_classify_error_defaults_to_complex(self, mock_llm):
        """Тест что ошибка в классификации приводит к complex"""
        mock_llm.side_effect = Exception("LLM error")
        
        result = await classify_intent("Какой-то запрос")
        assert result == "complex"

class TestFAQAnswer:
    """Тесты быстрых FAQ ответов"""
    
    @pytest.mark.asyncio
    @patch('agents.router.call_llm', new_callable=AsyncMock)
    @patch('agents.router.local_search')
    async def test_cheap_faq_with_context(self, mock_search, mock_llm):
        """Тест FAQ ответа с найденным контекстом"""
        mock_search.return_value = [
            {"text": "DLP - это технология предотвращения утечек данных"},
            {"text": "DLP системы контролируют передачу конфиденциальной информации"}
        ]
        mock_llm.return_value = ("DLP - это технология предотвращения утечек данных, которая контролирует передачу конфиденциальной информации.", None)
        
        result = await cheap_faq_answer("Что такое DLP?")
        assert "DLP" in result
        assert "технология" in result
    
    @pytest.mark.asyncio
    @patch('agents.router.local_search')
    async def test_cheap_faq_no_context(self, mock_search):
        """Тест FAQ ответа без найденного контекста"""
        mock_search.return_value = []
        
        result = await cheap_faq_answer("Что такое неизвестная технология?")
        assert result == "Нет данных в базе знаний."
    
    @pytest.mark.asyncio
    @patch('agents.router.local_search')
    async def test_cheap_faq_empty_context(self, mock_search):
        """Тест FAQ ответа с пустым контекстом"""
        mock_search.return_value = [{"text": ""}, {"text": "   "}]
        
        result = await cheap_faq_answer("Вопрос")
        assert result == "Нет данных в базе знаний."
    
    @pytest.mark.asyncio
    @patch('agents.router.local_search')
    async def test_cheap_faq_error_handling(self, mock_search):
        """Тест обработки ошибок в FAQ ответах"""
        mock_search.side_effect = Exception("Search error")
        
        result = await cheap_faq_answer("Вопрос")
        assert "ошибка" in result.lower()

class TestRouter:
    """Тесты основного роутера"""
    
    @pytest.mark.asyncio
    @patch('agents.router.classify_intent', new_callable=AsyncMock)
    @patch('agents.router.cheap_faq_answer', new_callable=AsyncMock)
    async def test_route_simple_faq(self, mock_faq, mock_classify):
        """Тест роутинга простого FAQ вопроса"""
        mock_classify.return_value = "simple_faq"
        mock_faq.return_value = "DLP - это технология предотвращения утечек"
        
        result = await route_query("Что такое DLP?")
        assert result["type"] == "chat"
        assert "DLP" in result["content"]
    
    @pytest.mark.asyncio
    @patch('agents.router.classify_intent', new_callable=AsyncMock)
    @patch('backend.agents.file_retrieval.get_file_link')
    async def test_route_get_file(self, mock_get_file, mock_classify):
        """Тест роутинга запроса на получение файла"""
        mock_classify.return_value = "get_file"
        mock_get_file.return_value = "/files/dlp_survey.pdf"
        
        result = await route_query("Нужен опросный лист по DLP")
        assert result["type"] == "chat"
        assert "скачать" in result["content"]
        assert "/files/dlp_survey.pdf" in result["content"]

    @pytest.mark.asyncio
    @patch('agents.router.classify_intent', new_callable=AsyncMock)
    @patch('agents.router.cheap_faq_answer', new_callable=AsyncMock)
    @patch('agents.expert_gc.expert_group_chat', new_callable=AsyncMock)
    async def test_route_complex_query(self, mock_expert_group_chat, mock_cheap_faq_answer, mock_classify_intent):
        """Тест роутинга сложного запроса к эксперту"""
        mock_classify_intent.return_value = "complex"
        mock_expert_group_chat.return_value = {"answer": "Ответ эксперта"}
        
        result = await route_query("Сложный вопрос")
        
        mock_classify_intent.assert_called_once_with("Сложный вопрос")
        mock_cheap_faq_answer.assert_not_called()
        mock_expert_group_chat.assert_called_once_with("Сложный вопрос")
        assert result["content"] == "Ответ эксперта"
