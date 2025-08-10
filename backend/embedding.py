import hashlib
import json
import os
import warnings

import openai
import redis
from typing import Any, Dict, List, Union, cast

from backend.utils import is_test_mode

# Отложенная инициализация OpenAI клиента
MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
_r: Union[redis.Redis, Dict[str, str], None] = None

def _get_redis() -> Union[redis.Redis, Dict[str, str]]:
    """Ленивая инициализация Redis с обработкой ошибок"""
    global _r
    if _r is None:
        try:
            _r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), decode_responses=True)
            # Проверяем подключение
            if isinstance(_r, redis.Redis):
                _r.ping()
        except (redis.ConnectionError, Exception) as e:
            warnings.warn(f"Redis not available, using in-memory cache: {e}")
        _r = {}  # Используем простой словарь как fallback
    # mypy: гарантируем non-None возврат
    return _r

def _get_client():
    """Создает OpenAI клиент при первом вызове"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Stub-режим для CI и разработки
    if api_key == "stub":
        return None  # Будем обрабатывать это в get()
    
    if not api_key or api_key.startswith("test_"):
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return openai.OpenAI(api_key=api_key)

def _cache_key(txt:str)->str:
    h=hashlib.sha1(txt.encode()).hexdigest()
    return f"emb:{MODEL}:{h}"

def get(text: str) -> List[float]:
    text=text[:8192]          # safety
    key=_cache_key(text)
    
    # Получаем Redis или fallback
    cache = _get_redis()
    
    # Пытаемся получить из кеша
    try:
        if isinstance(cache, dict):
            # Простой словарь fallback
            if key in cache:
                return cast(List[float], json.loads(cache[key]))
        else:
            # Реальный Redis
            vec = cache.get(key)
            if isinstance(vec, str):
                return cast(List[float], json.loads(vec))
    except Exception as e:
        print(f"Cache read error: {e}")
    
    # Проверяем API ключ
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Stub-режим для CI и разработки
    if api_key == "stub":
        print(f"🔧 Stub embedding for: {text[:50]}...")
        # Создаем простой фиктивный вектор из хэша текста
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        # Создаем вектор размером 1536 (как у text-embedding-3-small)
        vec = [(hash_val + i) % 100 / 100.0 for i in range(1536)]
        
        # Сохраняем в кеш
        try:
            if isinstance(cache, dict):
                cache[key] = json.dumps(vec)
            else:
                cache.set(key, json.dumps(vec), ex=60*60*24)
        except Exception as e:
            print(f"Cache write error: {e}")
        
        return vec
    
    # Проверяем тестовый режим
    if is_test_mode():
        # Возвращаем фиктивный вектор для тестового режима
        print(f"🔧 Mock embedding for: {text[:50]}...")
        # Создаем простой фиктивный вектор из хэша текста
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        # Создаем вектор размером 1536 (как у text-embedding-3-small)
        vec = [(hash_val + i) % 100 / 100.0 for i in range(1536)]
        
        # Сохраняем в кеш
        try:
            if isinstance(cache, dict):
                cache[key] = json.dumps(vec)
            else:
                cache.set(key, json.dumps(vec), ex=60*60*24)
        except Exception as e:
            print(f"Cache write error: {e}")
        
        return vec
    
    # Используем новый API OpenAI v1.0+
    client = _get_client()
    if client is None:
        # Невозможен в обычном режиме, но для mypy подстрахуемся
        return []
    resp = client.embeddings.create(model=MODEL, input=text)
    vec = cast(List[float], resp.data[0].embedding)
    
    # Сохраняем в кеш
    try:
        if isinstance(cache, dict):
            cache[key] = json.dumps(vec)
        else:
            cache.set(key, json.dumps(vec), ex=60*60*24)
    except Exception as e:
        print(f"Cache write error: {e}")
    
    return vec
