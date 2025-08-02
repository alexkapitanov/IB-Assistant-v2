#!/usr/bin/env python
"""
Ingest local files OR re-index objects already stored in MinIO.
Usage examples:

# 1. локальные файлы → bucket=ib-docs/questionnaires/
python scripts/index_files.py --paths ib-docs/questionnaires/*.pdf

# 2. переиндексировать всё, что уже лежит
python scripts/index_files.py --reindex bucket=ib-docs prefix=questionnaires/
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
import os
import uuid
import glob
import pathlib
import mimetypes
from typing import List

from minio import Minio
from qdrant_client import QdrantClient, models
from backend.embedding import get as embed
import pdfminer.high_level
import docx
from tqdm import tqdm

# Configuration
BUCKET_DEF = "ib-docs"
PREFIX_DEF = "questionnaires/"

# Clients
mc = Minio(
    os.getenv("MINIO_ENDPOINT", "minio:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    secure=False,
)
qc = QdrantClient(host=os.getenv("QDRANT_HOST", "qdrant"))

def ensure_collection(col: str = BUCKET_DEF):
    existing = [c.name for c in qc.get_collections().collections]
    if col not in existing:
        qc.create_collection(
            col,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

def extract_text_from_file(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or ""
    try:
        if "pdf" in mime or path.suffix.lower() == ".pdf":
            with open(path, "rb") as f:
                return pdfminer.high_level.extract_text(f, maxpages=20)
        if path.suffix.lower() == ".docx":
            doc = docx.Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        # Fallback to text if file parsing fails
        pass
    return path.read_text(encoding="utf-8", errors="ignore")

def _doc_exists(doc_id: str, col: str = BUCKET_DEF) -> bool:
    """Проверяет, существует ли документ с таким doc_id в коллекции."""
    try:
        res, _ = qc.scroll(
            collection_name=col,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id",  # Поиск по уникальному идентификатору документа
                        match=models.MatchValue(value=doc_id),
                    )
                ]
            ),
            limit=1,
        )
        return bool(res)
    except Exception:
        # Если коллекция не существует или другая ошибка, считаем, что документа нет
        return False

def vector_exists(doc_id: str, bucket: str = BUCKET_DEF) -> bool:
    """Проверяет существование вектора (документа) в коллекции Qdrant"""
    return _doc_exists(doc_id, bucket)

def ingest_path(path: pathlib.Path, bucket: str = BUCKET_DEF, prefix: str = PREFIX_DEF) -> bool:
    ensure_collection(bucket)
    key = f"{prefix}{path.name}"
    
    # Генерируем уникальный ID для документа на основе его ключа
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, key))

    # Проверяем, не был ли этот документ уже проиндексирован
    if _doc_exists(doc_id, bucket):
        return False # Пропускаем, если уже есть

    if not mc.bucket_exists(bucket):
        mc.make_bucket(bucket)
    
    try:
        mc.stat_object(bucket, key)
    except Exception:
        mc.fput_object(bucket, key, str(path))

    text = extract_text_from_file(path)
    vec = embed(text)
    
    # Добавляем doc_id в payload
    payload = {"s3_key": key, "doc_type": "questionnaire", "file_name": path.name, "text": text[:1000], "doc_id": doc_id}
    
    # Используем сгенерированный doc_id как ID точки
    point = models.PointStruct(id=doc_id, vector=vec, payload=payload)
    qc.upsert(collection_name=bucket, points=[point])
    return True

def ingest_minio_objects(bucket: str = BUCKET_DEF, prefix: str = PREFIX_DEF) -> int:
    indexed = 0
    for obj in mc.list_objects(bucket, prefix=prefix, recursive=True):
        key = obj.object_name
        
        # Проверяем существование по doc_id, сгенерированному из ключа
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, key))
        if _doc_exists(doc_id, bucket):
            continue
            
        data = mc.get_object(bucket, key).read()
        tmp = pathlib.Path("/tmp") / pathlib.Path(key).name
        tmp.write_bytes(data)
        if ingest_path(tmp, bucket, prefix):
            indexed += 1
        tmp.unlink(missing_ok=True)
    return indexed

def index_local_files(paths: List[str], bucket: str = BUCKET_DEF, prefix: str = PREFIX_DEF):
    """Index local files to MinIO and Qdrant"""
    all_files = []
    for path in paths:
        path_obj = pathlib.Path(path)
        if path_obj.is_file():
            all_files.append(path_obj)
        elif path_obj.is_dir():
            # Add all files from directory
            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    all_files.append(file_path)
        else:
            # Handle glob patterns
            all_files.extend([pathlib.Path(p) for p in glob.glob(path) if pathlib.Path(p).is_file()])
    
    indexed = 0
    for file_path in tqdm(all_files, desc="Indexing local files"):
        if ingest_path(file_path, bucket, prefix):
            indexed += 1
    
    print(f"Indexed {indexed} new vector(s) in collection {bucket}")

def reindex_minio_files(bucket: str = BUCKET_DEF, prefix: str = PREFIX_DEF):
    """Reindex files from MinIO"""
    indexed = ingest_minio_objects(bucket, prefix)
    print(f"Indexed {indexed} new vector(s) in collection {bucket}")

def main():
    parser = argparse.ArgumentParser(description="Index files to MinIO and Qdrant")
    parser.add_argument("--paths", nargs="+", help="Paths to files or directories to index")
    parser.add_argument("--reindex", action="store_true", help="Reindex files from MinIO")
    parser.add_argument("--bucket", default="ib-docs", help="MinIO bucket name")
    parser.add_argument("--prefix", default="questionnaires/", help="MinIO prefix")
    args = parser.parse_args()

    if args.reindex:
        reindex_minio_files(args.bucket, args.prefix)
    elif args.paths:
        index_local_files(args.paths, args.bucket, args.prefix)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
