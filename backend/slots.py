import re, redis, json, os, logging
_local_store: dict[str, dict] = {}
try:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        r = redis.Redis.from_url(redis_url, decode_responses=True)
    else:
        r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), decode_responses=True)
    # quick ping to verify connection
    try:
        r.ping()
    except Exception:
        logging.warning("Redis unavailable, using in-memory slots store")
        r = None
except Exception:
    logging.warning("Redis init failed, using in-memory slots store", exc_info=False)
    r = None

TOPIC_RE = re.compile(r"\b(DLP|SIEM|Zero\s+Trust|Linux\s+hardening|SOC)\b", re.I)

def update(thread_id:str, msg:str):
    if r:
        data = r.get(thread_id); data=json.loads(data) if data else {}
    else:
        data = _local_store.get(thread_id, {})
    # products
    m=re.findall(r"(Symantec|McAfee|Forcepoint|Trend Micro|InfoWatch)", msg, re.I)
    if m: data.setdefault("products", list(set([p.lower() for p in m])))
    # topics
    if m := TOPIC_RE.search(msg):
        data["topic"] = m.group(0)
    # criteria
    if "критер" in msg.lower():
        data["criteria"]=msg.strip()
    if r:
        r.set(thread_id, json.dumps(data), ex=86400)
    else:
        _local_store[thread_id] = data

def get(thread_id:str):
    if r:
        raw=r.get(thread_id)
        return json.loads(raw) if raw else {}
    return _local_store.get(thread_id, {})
