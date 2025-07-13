import os

def is_test_mode():
    """Проверка тестового режима"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    return api_key.startswith("test_key")
