import asyncio
from functools import wraps


def with_timeout(timeout_or_fn, timeout_result=None, kind="default"):
    """
    Декоратор для асинхронных функций с таймаутом.
    timeout_or_fn: число секунд или функция, возвращающая число секунд.
    timeout_result: возвращаемое значение при таймауте.
    kind: тип операции для метрик.
    """
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            from backend import metrics
            t = timeout_or_fn() if callable(timeout_or_fn) else timeout_or_fn
            # Безопасно приводим строковые значения к int, если пришли из env
            # Поддержим дробные секунды: преобразуем строку в float, затем оставим float/int
            try:
                if isinstance(t, str):
                    t = float(t)
            except Exception:
                pass
            try:
                return await asyncio.wait_for(fn(*args, **kwargs), timeout=t)
            except asyncio.TimeoutError:
                # инкрементируем метрику таймаутов
                try:
                    metrics.TIMEOUT.labels(kind=kind).inc()
                except Exception:
                    pass
                return timeout_result
        return wrapper
    return decorator
