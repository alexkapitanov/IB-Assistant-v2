import os, openai, functools, hashlib, json, redis

# Отложенная инициализация OpenAI клиента
MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
_r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), decode_responses=True)

def _get_client():
    """Создает OpenAI клиент при первом вызове"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return openai.OpenAI(api_key=api_key)

def _cache_key(txt:str)->str:
    h=hashlib.sha1(txt.encode()).hexdigest()
    return f"emb:{MODEL}:{h}"

def get(text:str)->list[float]:
    text=text[:8192]          # safety
    key=_cache_key(text)
    if vec:=_r.get(key):
        return json.loads(vec)
    
    # Используем новый API OpenAI v1.0+
    client = _get_client()
    resp = client.embeddings.create(model=MODEL, input=text)
    vec = resp.data[0].embedding
    _r.set(key, json.dumps(vec), ex=60*60*24)
    return vec
