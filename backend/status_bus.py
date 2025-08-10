import asyncio
import json
import logging
import os

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL","redis://redis:6379")
_channel  = "status_bus"

_local_queues: dict[str, asyncio.Queue] = {}
try:
    _redis_pub  = aioredis.from_url(REDIS_URL, decode_responses=True)
    _redis_sub  = aioredis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    logging.warning("Redis not available, using local queues for status_bus", exc_info=False)
    _redis_pub = None
    _redis_sub = None

async def publish(thread_id:str, stage:str, detail:str|None=None):
    msg = json.dumps({"thread":thread_id, "stage":stage, "detail":detail})

    import time

    from backend import metrics
    start = time.monotonic()

    # Всегда буферизуем в локальную очередь (для ранних статусов до подписки)
    q = _local_queues.setdefault(thread_id, asyncio.Queue())
    q.put_nowait({"thread": thread_id, "stage": stage, "detail": detail})

    # И пробуем опубликовать в Redis (для межпроцессного обмена)
    if _redis_pub:
        try:
            await _redis_pub.publish(_channel, msg)
        except Exception:
            logging.warning("Redis publish failed (ignored, local buffer used)", exc_info=False)

    # Метрики: latency и throughput для статус-буса
    elapsed = time.monotonic() - start
    try:
        if hasattr(metrics, 'LAT'):
            metrics.LAT.labels(stage=stage).observe(elapsed)
        if hasattr(metrics, 'STATUS_BUS_THROUGHPUT'):
            metrics.STATUS_BUS_THROUGHPUT.labels(stage=stage).inc()
    except Exception:
        pass

async def listen(thread_id:str):
    """Единый слушатель: читает из локальной очереди, а Redis-сообщения зеркалит в неё.

    Это позволяет не терять ранние статусы, опубликованные до старта подписчика.
    """
    q = _local_queues.setdefault(thread_id, asyncio.Queue())

    # Если доступен Redis — запустим фонового подписчика, который кладёт сообщения в локальную очередь
    async def _redis_to_local():
        if not _redis_sub:
            return
        try:
            pubsub = _redis_sub.pubsub()
            await pubsub.subscribe(_channel)
            async for m in pubsub.listen():
                if m.get("type") == "message":
                    data = json.loads(m.get("data", "{}"))
                    if data.get("thread") == thread_id:
                        q.put_nowait(data)
        except Exception:
            logging.warning("Redis subscribe failed, continuing with local queue only", exc_info=False)

    # Стартуем подписку, но игнорируем ошибки — локальная очередь остаётся источником истины
    if _redis_sub:
        asyncio.create_task(_redis_to_local())

    while True:
        data = await q.get()
        yield data
        
# Alias for backward compatibility
subscribe = listen

# Backward-compatibility sync wrapper used in some tests
def post(thread_id: str, stage: str, detail: str | None = None):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(publish(thread_id, stage, detail))
