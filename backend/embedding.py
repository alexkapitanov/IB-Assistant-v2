import os, openai, functools, hashlib, json, redis

# Инициализация OpenAI клиента
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
_r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), decode_responses=True)

def _cache_key(txt:str)->str:
    h=hashlib.sha1(txt.encode()).hexdigest()
    return f"emb:{MODEL}:{h}"

def get(text:str)->list[float]:
    text=text[:8192]          # safety
    key=_cache_key(text)
    if vec:=_r.get(key):
        return json.loads(vec)
    
    # Используем новый API OpenAI v1.0+
    resp = client.embeddings.create(model=MODEL, input=text)
    vec = resp.data[0].embedding
    _r.set(key, json.dumps(vec), ex=60*60*24)
    return vec
