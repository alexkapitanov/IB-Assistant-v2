import json
import os
import warnings
from typing import Any, Dict, Optional, Union, cast

import redis

from backend.chat_db import log_message

# Глобальные переменные для ленивой инициализации
_redis_client: Optional[redis.Redis] = None
_redis_available: Optional[bool] = None
_memory_store: Dict[str, Dict[str, Any]] = {}

def _get_redis_client() -> Optional[redis.Redis]:
    """Ленивая инициализация Redis клиента"""
    global _redis_client, _redis_available
    
    if _redis_available is None:
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            
            _redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, socket_timeout=5)
            # Проверяем подключение
            try:
                # ping только если клиент создан
                assert _redis_client is not None
                _redis_client.ping()
            except Exception:
                _redis_client = None
                _redis_available = False
                warnings.warn("Redis not available, using in-memory storage for tests")
                return None
            _redis_available = True
        except (redis.ConnectionError, Exception):
            # Fallback: используем словарь в памяти для тестов
            _redis_client = None
            _redis_available = False
            warnings.warn("Redis not available, using in-memory storage for tests")
    
    return _redis_client if _redis_available else None

def get_mem(tid: str) -> Dict[str, Any]:
    """Получение памяти по идентификатору сессии"""
    redis_client = _get_redis_client()
    if redis_client:
        raw = redis_client.get(f"mem:{tid}")
        return cast(Dict[str, Any], json.loads(raw)) if isinstance(raw, str) else {}
    else:
        return _memory_store.get(tid, {})

def save_mem(tid: str, slots: Dict[str, Any], ttl: int = 3600) -> None:
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
