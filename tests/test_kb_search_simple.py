#!/usr/bin/env python3
"""
Простой тест поиска диалогов внутри backend контейнера
"""
import pytest
from unittest.mock import patch, AsyncMock
from qdrant_client.http.models import ScoredPoint

# Поскольку мы тестируем из корня проекта, нужно добавить backend в путь
import sys
sys.path.append('.')

from backend.agents.kb_search import kb_search

@pytest.mark.parametrize("question", [
    "Что такое ИБ?",
    "Какие существуют угрозы безопасности?",
    "Как защититься от фишинга?"
])
@patch('backend.agents.kb_search.qdr')
@patch('backend.agents.kb_search.get_async_vec', new_callable=AsyncMock)
async def test_dialog_search_mocked(mock_get_async_vec, mock_qdr, question: str):
    """Тестируем логику kb_search с моками для внешних зависимостей."""
    
    # 1. Настраиваем мок для функции, получающей вектор эмбеддинга
    # Возвращаем вектор-пример
    mock_get_async_vec.return_value = [0.1] * 1536 

    # 2. Настраиваем мок для клиента Qdrant, который ищет в базе
    # Возвращаем пример найденной точки
    mock_qdr.search.return_value = [
        ScoredPoint(id='some-uuid', version=1, score=0.95, payload={'answer': 'Mocked answer', 'question': question})
    ]

    # 3. Вызываем тестируемую функцию
    status, result = await kb_search(question)

    # 4. Проверяем результат
    assert status == "reuse"
    assert result == 'Mocked answer'

    # 5. Убедимся, что наши моки были вызваны
    mock_get_async_vec.assert_awaited_once_with(question)
    mock_qdr.search.assert_called_once()

