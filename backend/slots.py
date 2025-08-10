import json
import logging
import os
import re

import redis
from typing import Any, Dict, Optional, cast

_local_store: Dict[str, Dict[str, Any]] = {}
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

# Помогаем mypy: r может быть None
R: Optional[redis.Redis] = cast(Optional[redis.Redis], r)

TOPIC_RE = re.compile(r"\b(DLP|SIEM|Zero\s+Trust|Linux\s+hardening|SOC)\b", re.I)

def update(thread_id: str, msg: str) -> None:
    if R is not None:
        raw = R.get(thread_id)
        data = json.loads(raw) if isinstance(raw, str) else {}
    else:
        data = _local_store.get(thread_id, {})
    # products
    m = re.findall(r"(Symantec|McAfee|Forcepoint|Trend Micro|InfoWatch)", msg, re.I)
    if m:
        data.setdefault("products", list(set([p.lower() for p in m])))
    # topics
    m_topic = TOPIC_RE.search(msg)
    if m_topic:
        data["topic"] = m_topic.group(0)
    # criteria
    if "критер" in msg.lower():
        data["criteria"] = msg.strip()
    if R is not None:
        R.set(thread_id, json.dumps(data), ex=86400)
    else:
        _local_store[thread_id] = data

def get(thread_id: str) -> Dict[str, Any]:
    if R is not None:
        raw = R.get(thread_id)
        return cast(Dict[str, Any], json.loads(raw)) if isinstance(raw, str) else {}
    else:
        return _local_store.get(thread_id, {})
