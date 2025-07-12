from backend.embedding import get as embed
from qdrant_client import QdrantClient, models
import os

_q = QdrantClient(host=os.getenv("QDRANT_HOST","qdrant"), port=6333)

def local_search(query:str, top_k:int=10, col:str="ib-docs"):
    vec = embed(query)
    hits = _q.search(
        collection_name=col,
        query_vector=vec,
        limit=top_k,
        search_params=models.SearchParams(hnsw_ef=64),
    )
    return [
        {"text": h.payload.get("text",""), "score": h.score, "meta": h.payload}
        for h in hits
    ]
