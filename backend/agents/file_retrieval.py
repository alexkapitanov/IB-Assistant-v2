"""
FileRetrieval-tool: выдаёт presigned URL на PDF/Docx по ИБ-продуктам.
"""
__doc__ = "FileRetrieval-tool: выдаёт presigned URL на PDF/Docx по ИБ-продуктам."

import os
from minio import Minio
from qdrant_client import QdrantClient

# Инициализация клиентов MinIO и Qdrant
mc = Minio(
    os.getenv("MINIO_ENDPOINT", "minio:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    secure=False
)
bucket = "ib-docs"
qc = QdrantClient(
    host=os.getenv("QDRANT_HOST", "qdrant"),
    port=int(os.getenv("QDRANT_PORT", "6333"))
)

def _presign(key, ttl=3600):
    return mc.get_presigned_url("GET", bucket, key, expires=ttl)

async def get_file_link(query, product=None):
    # Формируем slug и ключ
    slug = query.lower().replace(" ", "_")
    key = f"questionnaires/{slug}.pdf"
    # Попытка точного совпадения
    try:
        mc.stat_object(bucket, key)
        return {
            "type": "chat",
            "role": "assistant", 
            "content": f"📎 Документ доступен для скачать: {_presign(key)}",
            "intent": "get_file"
        }
    except Exception:
        pass
    # Семантический поиск в Qdrant
    hits = qc.search(
        collection_name="ib-docs",
        query_vector=query,
        filter={"must": [{"key": "doc_type", "match": {"value": "questionnaire"}}]},
        limit=1
    )
    if hits:
        key = hits[0].payload.get("s3_key")
        if key:
            try:
                mc.stat_object(bucket, key)
                return {
                    "type": "chat",
                    "role": "assistant", 
                    "content": f"📎 Документ доступен для скачать: {_presign(key)}",
                    "intent": "get_file"
                }
            except Exception:
                return None
    return {
        "type": "chat",
        "role": "assistant",
        "content": "📄 Файл не найден. Попробуйте уточнить название.",
        "intent": "file_not_found"
    }
