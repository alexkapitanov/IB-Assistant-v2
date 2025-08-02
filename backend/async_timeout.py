import asyncio, functools, logging

def with_timeout(timeout_fn, fallback_val):
    """
    Декоратор: обёртывает корутину таймаутом.
    timeout_fn  – функция без аргументов → int секунд
    fallback_val – что вернуть при TimeoutError
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrap(*a, **kw):
            from backend import metrics
            seconds = timeout_fn()
            try:
                return await asyncio.wait_for(fn(*a, **kw), timeout=seconds)
            except asyncio.TimeoutError:
                logging.warning("Timeout in %s after %ss", fn.__name__, seconds)
                # инкрементируем метрику таймаутов
                kind = fn.__name__ if fn.__name__ != "web_search" else "websearch"
                try:
                    metrics.TIMEOUT.labels(kind=kind).inc()
                except Exception:
                    pass
                return fallback_val
        return wrap
    return decorator
