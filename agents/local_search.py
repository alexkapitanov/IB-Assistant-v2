from backend.embedding import get as embed
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
import os

_q = QdrantClient(host=os.getenv("QDRANT_HOST","qdrant"), port=6333)

def local_search(query:str, top_k:int=10, col:str="ib-docs"):
    vec = embed(query)
    try:
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
    except (UnexpectedResponse, ResponseHandlingException) as e:
        if "doesn't exist" in str(e) or "Name or service not known" in str(e):
            # Collection doesn't exist or Qdrant unavailable - return empty results
            return []
        raise
