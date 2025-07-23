from backend.async_timeout import with_timeout
from backend import config
from backend.openai_helpers import browser_search

@with_timeout(lambda: config.WEB_SEARCH_TIMEOUT_SEC, "TIMEOUT")
async def web_search(query: str) -> str:
    """
    Markdown-строка из browser-поиска.
    При таймауте вернёт «TIMEOUT».
    """
    return await browser_search(query, k=5)
