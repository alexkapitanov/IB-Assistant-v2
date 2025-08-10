import asyncio
import base64
import gzip
import hashlib
import json
import time
from typing import Any, Dict, Optional

import redis
import os

from backend import config, metrics
from backend.openai_helpers import browser_search
from backend.utils.async_timeout import with_timeout


# Lazy Redis client (decode_responses to store JSON strings)
_r: Optional[redis.Redis] = None


def _get_redis() -> Optional[redis.Redis]:
    global _r
    if _r is not None:
        return _r
    try:
        url = os.getenv("REDIS_URL")
    except Exception:
        url = None
    try:
        if url:
            _r = redis.Redis.from_url(url, decode_responses=True)
        else:
            _r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)), decode_responses=True)
        # ping lazily when used
    except Exception:
        _r = None
    return _r


def canonicalize_query(text: str, slots: Optional[dict] = None) -> str:
    q = " ".join((text or "").strip().split()).lower()
    if slots:
        topic = (slots.get("topic") or "").strip()
        product = (slots.get("product") or "").strip()
        if topic:
            q += f"|topic:{topic.lower()}"
        if product:
            q += f"|product:{product.lower()}"
    return q


def cache_key(q: str) -> str:
    return f"ws:{hashlib.sha1(q.encode()).hexdigest()}"


def _encode_payload(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    if len(data) > 100_000:  # 100KB threshold
        gz = gzip.compress(data.encode("utf-8"))
        return "z:" + base64.b64encode(gz).decode("ascii")
    return data


def _decode_payload(s: str) -> Any:
    if s.startswith("z:"):
        gz = base64.b64decode(s[2:])
        return json.loads(gzip.decompress(gz).decode("utf-8"))
    return json.loads(s)


def get_cached(q: str) -> Optional[Any]:
    r = _get_redis()
    if not r:
        return None
    try:
        s = r.get(cache_key(q))
        if not s:
            return None
        return _decode_payload(s)
    except Exception:
        return None


def set_cached(q: str, payload: Any, ttl: int) -> None:
    r = _get_redis()
    if not r:
        return
    try:
        r.set(cache_key(q), _encode_payload(payload), ex=int(ttl))
    except Exception:
        pass


def set_cached_negative(q: str, ttl: int) -> None:
    # Store legacy-compatible negative: string "TIMEOUT"
    set_cached(q, "TIMEOUT", ttl)


def acquire_lock(key: str, ttl: int = 30) -> bool:
    r = _get_redis()
    if not r:
        return True  # no redis → no lock
    try:
        return bool(r.set(f"{key}.lock", "1", nx=True, ex=int(ttl)))
    except Exception:
        return True


def _del_lock(key: str) -> None:
    r = _get_redis()
    if not r:
        return
    try:
        r.delete(f"{key}.lock")
    except Exception:
        pass


def wait_for_fill(key: str, timeout: float = 5.0) -> Optional[Any]:
    r = _get_redis()
    if not r:
        return None
    deadline = time.monotonic() + float(timeout)
    while time.monotonic() < deadline:
        try:
            s = r.get(key)
            if s:
                try:
                    return _decode_payload(s)
                finally:
                    # даже если вернули — lock можно не трогать (его снимет первичный воркер по finally)
                    ...
        except Exception:
            return None
        time.sleep(0.2)
    return None


@with_timeout(lambda: config.WEB_SEARCH_TIMEOUT_SEC, "TIMEOUT")
async def web_search(query: str, *, slots: Optional[dict] = None) -> Any:
    """
    Выполняет web-поиск с Redis-кэшем. Возвращает dict вида:
    {"summary": "...", "sources": [...], "ts": 1234567890.0} или {"status":"TIMEOUT"}.
    """
    q = canonicalize_query(query, slots)
    key = cache_key(q)

    cached = get_cached(q)
    if cached:
        try:
            metrics.WEB_CACHE_HIT.inc()
        except Exception:
            pass
        return cached

    try:
        metrics.WEB_CACHE_MISS.inc()
    except Exception:
        pass

    lock_acquired = acquire_lock(key, int(config.WEB_CACHE_LOCK_SEC))
    if not lock_acquired:
        waited = wait_for_fill(key, timeout=5.0)
        if waited:
            try:
                metrics.WEB_CACHE_HIT_AFTER_WAIT.inc()
            except Exception:
                pass
            return waited

    ttl = int(config.WEB_CACHE_TTL_SEC)
    neg_ttl = int(config.WEB_CACHE_NEG_TTL_SEC)
    t0 = time.monotonic()
    try:
        md = await browser_search(query, k=5)
        dt = time.monotonic() - t0
        try:
            metrics.WEB_SEARCH_LATENCY.observe(dt)
        except Exception:
            pass

        if not md:
            set_cached_negative(q, neg_ttl)
            try:
                metrics.WEB_CACHE_STORE_NEG.inc()
            except Exception:
                pass
            return "TIMEOUT"

        # Формируем payload; для совместимости кладём markdown в summary
        payload: Dict[str, Any] = {"summary": md, "sources": [], "ts": time.time()}
        set_cached(q, payload, ttl)
        try:
            metrics.WEB_CACHE_STORE.inc()
        except Exception:
            pass
        return payload
    finally:
        _del_lock(key)
