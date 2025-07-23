import redis, os, json
import warnings
from backend.chat_db import log_message
from typing import Optional

# Глобальные переменные для ленивой инициализации
_redis_client: Optional[redis.Redis] = None
_redis_available = None
_memory_store = {}

def _get_redis_client():
    """Ленивая инициализация Redis клиента"""
    global _redis_client, _redis_available
    
    if _redis_available is None:
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            
            _redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, socket_timeout=5)
            # Проверяем подключение
            _redis_client.ping()
            _redis_available = True
        except (redis.ConnectionError, Exception):
            # Fallback: используем словарь в памяти для тестов
            _redis_client = None
            _redis_available = False
            warnings.warn("Redis not available, using in-memory storage for tests")
    
    return _redis_client if _redis_available else None

def get_mem(tid):
    """Получение памяти по идентификатору сессии"""
    redis_client = _get_redis_client()
    if redis_client:
        raw = redis_client.get(f"mem:{tid}")
        return json.loads(raw) if raw else {}
    else:
        return _memory_store.get(tid, {})

def save_mem(tid, slots, ttl=3600):
    """Сохранение памяти по идентификатору сессии с TTL"""
    redis_client = _get_redis_client()
    if redis_client:
        redis_client.set(f"mem:{tid}", json.dumps(slots), ex=ttl)
        # Снапшот слотов в SQLite
        log_message(tid, -1, "slot", json.dumps(slots))
    else:
        _memory_store[tid] = slots
        # Снапшот слотов в SQLite
        log_message(tid, -1, "slot", json.dumps(slots))
