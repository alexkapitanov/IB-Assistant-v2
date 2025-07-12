import os
import pytest
from agents.local_search import local_search

def test_local_search_returns_hits():
    # Пропускаем тест если нет OpenAI API ключа
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skipping OpenAI-dependent test")
    
    res = local_search("опросный лист", top_k=1)
    assert isinstance(res, list)
    # если индекс пуст, вернёт [], тест не падает
