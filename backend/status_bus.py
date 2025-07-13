import asyncio, contextlib, redis.asyncio as redis, os, json
_r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), decode_responses=True)
CHANNEL="status_bus"

async def publish(thread_id:str, status:str):
    await _r.publish(CHANNEL, json.dumps({"thread":thread_id,"status":status}))

async def subscribe(thread_id:str):
    pubsub = _r.pubsub()
    await pubsub.subscribe(CHANNEL)
    async for msg in pubsub.listen():
        if msg["type"]!="message": continue
        data=json.loads(msg["data"])
        if data["thread"]==thread_id:
            yield data["status"]
