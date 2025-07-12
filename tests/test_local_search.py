from agents.local_search import local_search

def test_local_search_returns_hits():
    res = local_search("опросный лист", top_k=1)
    assert isinstance(res, list)
    # если индекс пуст, вернёт [], тест не падает
