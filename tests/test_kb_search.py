import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from backend.agents.kb_search import kb_search, SIM_HARD, SIM_SOFT


class MockHit:
    """Мок для результата поиска Qdrant"""
    def __init__(self, score, payload):
        self.score = score
        self.payload = payload


def test_reuse(monkeypatch):
    """Тест сценария reuse - когда найден очень похожий диалог"""
    
    # Мокаем get_async_vec
    async def mock_get_async_vec(query):
        return [0.1, 0.2, 0.3]  # Dummy vector
    
    # Мокаем qdr.search для возврата высокого score
    def mock_search(collection_name, query_vector, limit):
        if collection_name == "dialogs":
            return [MockHit(0.98, {"answer": "Это готовый ответ из диалогов"})]
        return []
    
    # Применяем моки
    monkeypatch.setattr("backend.agents.kb_search.get_async_vec", mock_get_async_vec)
    monkeypatch.setattr("backend.agents.kb_search.qdr.search", mock_search)
    
    # Запускаем тест
    status, result = asyncio.run(kb_search("повтори"))
    
    # Проверяем результат
    assert status == "reuse"
    assert result == "Это готовый ответ из диалогов"


def test_escalate_low_score(monkeypatch):
    """Тест сценария escalate - когда score ниже порога"""
    
    # Мокаем get_async_vec
    async def mock_get_async_vec(query):
        return [0.1, 0.2, 0.3]
    
    # Мокаем qdr.search для возврата низкого score
    def mock_search(collection_name, query_vector, limit):
        if collection_name == "dialogs":
            return [MockHit(0.5, {"question": "Похожий вопрос", "answer": "Похожий ответ"})]
        elif collection_name == "docs":
            return [MockHit(0.7, {"text": "Документация по теме"})]
        return []
    
    # Применяем моки
    monkeypatch.setattr("backend.agents.kb_search.get_async_vec", mock_get_async_vec)
    monkeypatch.setattr("backend.agents.kb_search.qdr.search", mock_search)
    
    # Запускаем тест
    status, context = asyncio.run(kb_search("новый вопрос"))
    
    # Проверяем результат
    assert status == "escalate"
    assert "similar_dialogs" in context
    assert "rag" in context
    assert len(context["similar_dialogs"]) == 0  # score 0.5 < SIM_SOFT (0.60)
    assert len(context["rag"]) == 1


def test_escalate_with_similar_dialogs(monkeypatch):
    """Тест сценария escalate с похожими диалогами в контексте"""
    
    # Мокаем get_async_vec
    async def mock_get_async_vec(query):
        return [0.1, 0.2, 0.3]
    
    # Мокаем qdr.search
    def mock_search(collection_name, query_vector, limit):
        if collection_name == "dialogs":
            return [
                MockHit(0.75, {"question": "Похожий вопрос 1", "answer": "Ответ 1"}),
                MockHit(0.65, {"question": "Похожий вопрос 2", "answer": "Ответ 2"}),
                MockHit(0.55, {"question": "Неподходящий вопрос", "answer": "Ответ 3"})
            ]
        elif collection_name == "docs":
            return [MockHit(0.8, {"text": "Релевантная документация"})]
        return []
    
    # Применяем моки
    monkeypatch.setattr("backend.agents.kb_search.get_async_vec", mock_get_async_vec)
    monkeypatch.setattr("backend.agents.kb_search.qdr.search", mock_search)
    
    # Запускаем тест
    status, context = asyncio.run(kb_search("вопрос средней похожести"))
    
    # Проверяем результат
    assert status == "escalate"
    assert len(context["similar_dialogs"]) == 2  # Только с score >= SIM_SOFT (0.60)
    assert len(context["rag"]) == 1


def test_dynamic_k_calculation():
    """Тест динамического расчета k"""
    
    async def mock_get_async_vec(query):
        return [0.1, 0.2, 0.3]
    
    def mock_search(collection_name, query_vector, limit):
        # Проверяем, что limit соответствует ожидаемому k
        assert limit == 5  # max(3, min(10, 1500 // 400)) = max(3, min(10, 3)) = max(3, 3) = 3, но мы ожидаем 5 для 2000 tokens
        return []
    
    with patch("backend.agents.kb_search.get_async_vec", mock_get_async_vec):
        with patch("backend.agents.kb_search.qdr.search", mock_search):
            # Тест с большим expected_tokens
            asyncio.run(kb_search("тест", expected_tokens=2000))


def test_collection_error_handling(monkeypatch):
    """Тест обработки ошибок при поиске в коллекциях"""
    
    # Мокаем get_async_vec
    async def mock_get_async_vec(query):
        return [0.1, 0.2, 0.3]
    
    # Мокаем qdr.search для симуляции ошибки
    def mock_search(collection_name, query_vector, limit):
        if collection_name == "dialogs":
            raise Exception("Collection not found")
        elif collection_name == "docs":
            return [MockHit(0.8, {"text": "Документация"})]
        return []
    
    # Применяем моки
    monkeypatch.setattr("backend.agents.kb_search.get_async_vec", mock_get_async_vec)
    monkeypatch.setattr("backend.agents.kb_search.qdr.search", mock_search)
    
    # Запускаем тест
    status, context = asyncio.run(kb_search("тест ошибки"))
    
    # Проверяем, что функция продолжает работать даже при ошибке в dialogs
    assert status == "escalate"
    assert context["similar_dialogs"] == []
    assert len(context["rag"]) == 1
