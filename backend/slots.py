import re, redis, json, os
redis_url = os.getenv("REDIS_URL")
if redis_url:
    r = redis.Redis.from_url(redis_url, decode_responses=True)
else:
    r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), decode_responses=True)

def update(thread_id:str, msg:str):
    data = r.get(thread_id); data=json.loads(data) if data else {}
    # products
    m=re.findall(r"(Symantec|McAfee|Forcepoint|Trend Micro|InfoWatch)", msg, re.I)
    if m: data.setdefault("products", list(set([p.lower() for p in m])))
    # criteria
    if "критер" in msg.lower():
        data["criteria"]=msg.strip()
    r.set(thread_id, json.dumps(data), ex=86400)

def get(thread_id:str):
    raw=r.get(thread_id)
    return json.loads(raw) if raw else {}
