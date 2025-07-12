from qdrant_client import QdrantClient
import os

# Инициализация клиента Qdrant
_q = QdrantClient(
    url=f"http://{os.getenv('QDRANT_HOST','qdrant')}:{os.getenv('QDRANT_PORT','6333')}"
)

def local_search(query, top_k: int = 10):
    """
    Выполняет локальный k-NN поиск в коллекции "ib-docs".
    Принимает запрос в виде вектора эмбеддинга или строки.
    """
    hits = _q.search(
        collection_name="ib-docs",
        query_vector=query,
        limit=top_k,
    )
    return [
        {
            "text": h.payload.get("text", ""),
            "score": h.score,
            "meta": h.payload
        }
        for h in hits
    ]
