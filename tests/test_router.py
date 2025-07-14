"""
Тесты для роутера интентов
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.router import classify_intent, cheap_faq_answer, route_query

class TestIntentClassifier:
    """Тесты классификатора интентов"""
    
    @patch('agents.router.call_llm')
    def test_classify_get_file_intent(self, mock_llm):
        """Тест классификации намерения получить файл"""
        mock_llm.return_value = ("get_file", None)
        
        result = classify_intent("Нужен опросный лист по DLP")
        assert result == "get_file"
    
    @patch('agents.router.call_llm')
    def test_classify_simple_faq_intent(self, mock_llm):
        """Тест классификации простого FAQ вопроса"""
        mock_llm.return_value = ("simple_faq", None)
        
        result = classify_intent("Что такое DLP?")
        assert result == "simple_faq"
    
    @patch('agents.router.call_llm')
    def test_classify_capabilities_intent(self, mock_llm):
        """Тест классификации запроса о возможностях"""
        mock_llm.return_value = ("capabilities", None)
        
        result = classify_intent("что ты умеешь?")
        assert result == "capabilities"
    
    @patch('agents.router.call_llm')
    def test_classify_complex_intent(self, mock_llm):
        """Тест классификации сложного аналитического вопроса"""
        mock_llm.return_value = ("complex", None)
        
        result = classify_intent("Сравни DLP решения по TCO и возможностям интеграции")
        assert result == "complex"
    
    @patch('agents.router.call_llm')
    def test_classify_invalid_response_defaults_to_complex(self, mock_llm):
        """Тест что некорректный ответ классификатора приводит к complex"""
        mock_llm.return_value = ("invalid_intent", None)
        
        result = classify_intent("Какой-то запрос")
        assert result == "complex"
    
    @patch('agents.router.call_llm')
    def test_classify_error_defaults_to_complex(self, mock_llm):
        """Тест что ошибка в классификации приводит к complex"""
        mock_llm.side_effect = Exception("LLM error")
        
        result = classify_intent("Какой-то запрос")
        assert result == "complex"

class TestFAQAnswer:
    """Тесты быстрых FAQ ответов"""
    
    @patch('agents.router.call_llm')
    @patch('agents.router.local_search')
    def test_cheap_faq_with_context(self, mock_search, mock_llm):
        """Тест FAQ ответа с найденным контекстом"""
        mock_search.return_value = [
            {"text": "DLP - это технология предотвращения утечек данных"},
            {"text": "DLP системы контролируют передачу конфиденциальной информации"}
        ]
        mock_llm.return_value = ("DLP - это технология предотвращения утечек данных, которая контролирует передачу конфиденциальной информации.", None)
        
        result = cheap_faq_answer("Что такое DLP?")
        assert "DLP" in result
        assert "технология" in result
    
    @patch('agents.router.local_search')
    def test_cheap_faq_no_context(self, mock_search):
        """Тест FAQ ответа без найденного контекста"""
        mock_search.return_value = []
        
        result = cheap_faq_answer("Что такое неизвестная технология?")
        assert result == "Нет данных в базе знаний."
    
    @patch('agents.router.local_search')
    def test_cheap_faq_empty_context(self, mock_search):
        """Тест FAQ ответа с пустым контекстом"""
        mock_search.return_value = [{"text": ""}, {"text": "   "}]
        
        result = cheap_faq_answer("Вопрос")
        assert result == "Нет данных в базе знаний."
    
    @patch('agents.router.local_search')
    def test_cheap_faq_error_handling(self, mock_search):
        """Тест обработки ошибок в FAQ ответах"""
        mock_search.side_effect = Exception("Search error")
        
        result = cheap_faq_answer("Вопрос")
        assert "ошибка" in result.lower()

class TestCapabilitiesAnswer:
    """Тесты ответов о возможностях ассистента"""
    
    def test_get_capabilities_answer(self):
        """Тест получения информации о возможностях"""
        from agents.router import get_capabilities_answer
        
        result = get_capabilities_answer()
        
        # Проверяем, что ответ содержит ключевые элементы
        assert "InfoSec Assistant v2" in result
        assert "Что я умею" in result
        assert "Работа с файлами" in result
        assert "Быстрые ответы" in result
        assert "Аналитические задачи" in result
        assert "DLP" in result
        assert "SIEM" in result
        assert "SOC" in result

class TestRouter:
    """Тесты основного роутера"""
    
    @patch('agents.router.classify_intent')
    @patch('agents.router.cheap_faq_answer')
    def test_route_simple_faq(self, mock_faq, mock_classify):
        """Тест роутинга простого FAQ вопроса"""
        mock_classify.return_value = "simple_faq"
        mock_faq.return_value = "DLP - это технология предотвращения утечек"
        
        result = route_query("Что такое DLP?")
        
        assert result["intent"] == "simple_faq"
        assert result["type"] == "faq"
        assert "DLP" in result["answer"]
        assert "needs_planning" not in result
    
    @patch('agents.router.classify_intent')
    def test_route_capabilities(self, mock_classify):
        """Тест роутинга запроса о возможностях"""
        mock_classify.return_value = "capabilities"
        
        result = route_query("что ты умеешь?")
        
        assert result["intent"] == "capabilities"
        assert result["type"] == "capabilities"
        assert "InfoSec Assistant v2" in result["answer"]
        assert "Что я умею" in result["answer"]
        assert "needs_planning" not in result
    
    @patch('agents.router.classify_intent')
    def test_route_get_file(self, mock_classify):
        """Тест роутинга запроса на получение файла"""
        mock_classify.return_value = "get_file"
        
        result = route_query("Нужен опросный лист по DLP")
        
        assert result["intent"] == "get_file"
        assert result["type"] == "planning_required"
        assert result["needs_planning"] == True
        assert "answer" not in result
    
    @patch('agents.router.classify_intent')
    def test_route_complex(self, mock_classify):
        """Тест роутинга сложного вопроса"""
        mock_classify.return_value = "complex"
        
        result = route_query("Сравни DLP решения по функциональности")
        
        assert result["intent"] == "complex"
        assert result["type"] == "planning_required"
        assert result["needs_planning"] == True
        assert "answer" not in result
