from qdrant_client import QdrantClient
import os
from backend.embedding import get as get_embedding

# Инициализация клиента Qdrant
_q = QdrantClient(
    url=f"http://{os.getenv('QDRANT_HOST','qdrant')}:{os.getenv('QDRANT_PORT','6333')}"
)

def local_search(query, top_k: int = 10):
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
            
        hits = _q.search(
            collection_name="ib-docs",
            query_vector=query_vector,
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
    except Exception as e:
        print(f"❌ Error in local_search: {e}")
        # В случае ошибки возвращаем пустой результат
        return []
