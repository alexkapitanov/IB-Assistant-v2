from backend.embedding import get as embed
from qdrant_client import QdrantClient, models
import os
import redis
import hashlib
import json
from opentelemetry import trace

_q = QdrantClient(host=os.getenv("QDRANT_HOST","qdrant"), port=6333)
_r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0)
tracer = trace.get_tracer(__name__)

def local_search(query:str, top_k:int=10, col:str="ib-docs", expected_tokens:int=1500):
    """
    Ищет в Qdrant наиболее релевантные документы, динамически подбирая k.
    Результаты кешируются в Redis на 30 минут.
    """
    # 1. Проверяем кеш
    cache_key = f"search:{hashlib.sha1(query.encode()).hexdigest()}"
    try:
        cached_result = _r.get(cache_key)
        if cached_result:
            print(f"CACHE HIT for query: {query[:30]}...")
            return json.loads(cached_result)
    except redis.exceptions.RedisError as e:
        print(f"⚠️ Redis cache read error: {e}")

    # 2. Если в кеше нет, выполняем поиск
    # Динамический подбор k: минимум 3, максимум top_k, 
    # и примерно 1 документ на каждые 400 токенов контекста
    k = min(top_k, max(3, expected_tokens // 400))
    
    vec = embed(query)
    try:
        with tracer.start_as_current_span("qdrant_search"):
            hits = _q.search(
                collection_name=col,
                query_vector=vec,
                limit=k,
                search_params=models.SearchParams(hnsw_ef=64),
            )
        results = [
            {"text": h.payload.get("text",""), "score": h.score, "meta": h.payload}
            for h in hits
        ]
        
        # 3. Сохраняем результат в кеш
        try:
            _r.set(cache_key, json.dumps(results), ex=1800) # 30 минут
        except redis.exceptions.RedisError as e:
            print(f"⚠️ Redis cache write error: {e}")
            
        return results
    except Exception as e:
        # Handle any Qdrant-related errors (collection missing, service down, etc.)
        if ("doesn't exist" in str(e) or 
            "Name or service not known" in str(e) or 
            "404" in str(e) or
            "Not Found" in str(e)):
            # Collection doesn't exist or Qdrant unavailable - return empty results
            return []
        raise
