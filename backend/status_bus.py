import json, os, redis.asyncio as aioredis, asyncio, logging
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
    # Публикация в Redis или локальную очередь
    if _redis_pub:
        try:
            await _redis_pub.publish(_channel, msg)
        except Exception:
            logging.warning("Redis publish failed, using local queue", exc_info=False)
    # fallback to local in-memory queue
    q = _local_queues.setdefault(thread_id, asyncio.Queue())
    q.put_nowait({"thread": thread_id, "stage": stage, "detail": detail})
    import time
    from backend import metrics
    start = time.monotonic()
    # Метрики: latency и throughput для статус-буса
    elapsed = time.monotonic() - start
    try:
        metrics.LAT.labels(stage=stage).observe(elapsed)
        metrics.STATUS_BUS_THROUGHPUT.labels(stage=stage).inc()
    except Exception:
        pass
    # Публикация в Redis или локальную очередь
    if _redis_pub:
        try:
            await _redis_pub.publish(_channel, msg)
        except Exception:
            logging.warning("Redis publish failed, using local queue", exc_info=False)
    else:
        # fallback to local in-memory queue
        q = _local_queues.setdefault(thread_id, asyncio.Queue())
        q.put_nowait({"thread": thread_id, "stage": stage, "detail": detail})
    # Метрики: latency и throughput для статус-буса
    elapsed = time.monotonic() - start
    try:
        metrics.LAT.labels(stage=stage).observe(elapsed)
        metrics.STATUS_BUS_THROUGHPUT.labels(stage=stage).inc()
    except Exception:
        pass

async def listen(thread_id:str):
    # Listen to Redis or fallback to local queue
    if _redis_sub:
        try:
            pubsub = _redis_sub.pubsub()
            await pubsub.subscribe(_channel)
            async for m in pubsub.listen():
                if m.get("type") == "message":
                    data = json.loads(m.get("data", "{}"))
                    if data.get("thread") == thread_id:
                        yield data
            return
        except Exception:
            logging.warning("Redis subscribe failed, using local queue", exc_info=False)
    # fallback to local in-memory queue
    q = _local_queues.setdefault(thread_id, asyncio.Queue())
    while True:
        data = await q.get()
        yield data
        
# Alias for backward compatibility
subscribe = listen
