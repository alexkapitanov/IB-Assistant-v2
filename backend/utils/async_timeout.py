import asyncio
from functools import wraps

def with_timeout(timeout_or_fn, timeout_result=None):
    """
    Декоратор для асинхронных функций с таймаутом.
    timeout_or_fn: число секунд или функция, возвращающая число секунд.
    timeout_result: возвращаемое значение при таймауте.
    """
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            from backend import metrics
            t = timeout_or_fn() if callable(timeout_or_fn) else timeout_or_fn
            try:
                return await asyncio.wait_for(fn(*args, **kwargs), timeout=t)
            except asyncio.TimeoutError:
                # инкрементируем метрику таймаутов websearch
                kind = fn.__name__ if fn.__name__ != "web_search" else "websearch"
                try:
                    metrics.TIMEOUT.labels(kind=kind).inc()
                except Exception:
                    pass
                return timeout_result
        return wrapper
    return decorator
