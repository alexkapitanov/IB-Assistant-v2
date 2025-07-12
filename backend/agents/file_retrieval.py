import os
from minio import Minio
from qdrant_client import QdrantClient
import openai

# Инициализация клиентов MinIO и Qdrant
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    secure=False
)
qdrant_client = QdrantClient(
    url=f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}"
)


def get_file_link(query: str, product: str) -> str:
    """
    Попытка получить файл по точному ключу в MinIO, иначе семантический поиск в Qdrant.
    Возвращает presigned URL или None.
    """
    if not product:
        return None
    bucket = product

    # Попытка точного совпадения ключа
    object_name = query.strip()
    try:
        minio_client.stat_object(bucket, object_name)
        return minio_client.get_presigned_url(
            "GET", bucket, object_name
        )
    except Exception:
        pass

    # fallback: семантический поиск через векторизацию запроса
    embedding_resp = openai.Embedding.create(
        input=[query],
        model="text-embedding-ada-002"
    )
    vector = embedding_resp["data"][0]["embedding"]
    collection_name = f"{product}_files"
    try:
        results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=1,
        )
        if results:
            rec = results[0]
            payload = rec.payload or {}
            fallback_name = payload.get("path") or payload.get("key")
            if fallback_name:
                try:
                    minio_client.stat_object(bucket, fallback_name)
                    return minio_client.get_presigned_url(
                        "GET", bucket, fallback_name
                    )
                except Exception:
                    return None
    except Exception:
        return None

    return None
