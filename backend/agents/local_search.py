import os

from qdrant_client import QdrantClient

from backend.embedding import get as get_embedding
from typing import Any, Dict, List

# Инициализация клиента Qdrant
_q = QdrantClient(
    url=f"http://{os.getenv('QDRANT_HOST','qdrant')}:{os.getenv('QDRANT_PORT','6333')}"
)


def local_search(query: str | list[float], top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Выполняет локальный k-NN поиск в коллекции "ib-docs".
    Принимает запрос в виде строки и преобразует его в вектор эмбеддинга.
    """
    try:
        # Если query - строка, преобразуем в вектор эмбеддинга
        if isinstance(query, str):
            query_vector = get_embedding(query)
        else:
            query_vector = query

        hits = _q.query_points(
            collection_name="ib-docs",
            query=query_vector,
            limit=top_k,
        ).points
        results: List[Dict[str, Any]] = []
        for h in hits:
            payload = h.payload or {}
            text = payload.get("text", "") if isinstance(payload, dict) else ""
            results.append({"text": text, "score": h.score, "meta": payload})
        return results
    except Exception as e:
        print(f"❌ Error in local_search: {e}")
        # В случае ошибки возвращаем пустой результат
        return []
