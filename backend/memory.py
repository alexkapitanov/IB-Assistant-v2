import redis, os, json
import warnings
from backend.chat_db import log_message

# Инициализация подключения к Redis с fallback для тестов
try:
    _r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)
    # Проверяем подключение
    _r.ping()
    _redis_available = True
except (redis.ConnectionError, Exception):
    # Fallback: используем словарь в памяти для тестов
    _r = None
    _redis_available = False
    _memory_store = {}
    warnings.warn("Redis not available, using in-memory storage for tests")

def get_mem(tid):
    """Получение памяти по идентификатору сессии"""
    if _redis_available:
        raw = _r.get(f"mem:{tid}")
        return json.loads(raw) if raw else {}
    else:
        return _memory_store.get(tid, {})

def save_mem(tid, slots, ttl=3600):
    """Сохранение памяти по идентификатору сессии с TTL"""
    if _redis_available:
        _r.set(f"mem:{tid}", json.dumps(slots), ex=ttl)
        # Снапшот слотов в SQLite
        log_message(tid, -1, "slot", json.dumps(slots))
    else:
        _memory_store[tid] = slots
        # Снапшот слотов в SQLite
        log_message(tid, -1, "slot", json.dumps(slots))
