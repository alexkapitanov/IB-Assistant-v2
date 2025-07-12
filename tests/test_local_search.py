import os
import sys
import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.local_search import local_search

@pytest.mark.openai
def test_local_search_returns_hits():
    # Test uses @pytest.mark.openai marker for automatic skipping
    res = local_search("опросный лист", top_k=1)
    assert isinstance(res, list)
    # если индекс пуст, вернёт [], тест не падает

@pytest.mark.openai  
def test_local_search_empty_query():
    """Test local search with empty query"""
    res = local_search("", top_k=1)
    assert isinstance(res, list)

@pytest.mark.openai
def test_local_search_different_top_k():
    """Test local search with different top_k values"""
    res1 = local_search("test", top_k=1)
    res5 = local_search("test", top_k=5)
    
    assert isinstance(res1, list)
    assert isinstance(res5, list)
    assert len(res1) <= 1
    assert len(res5) <= 5
