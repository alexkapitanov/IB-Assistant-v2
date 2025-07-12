import redis, os, json

# Инициализация подключения к Redis
_r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)

def get_mem(tid):
    """Получение памяти по идентификатору сессии"""
    raw = _r.get(f"mem:{tid}")
    return json.loads(raw) if raw else {}

def save_mem(tid, slots, ttl=3600):
    """Сохранение памяти по идентификатору сессии с TTL"""
    _r.set(f"mem:{tid}", json.dumps(slots), ex=ttl)
