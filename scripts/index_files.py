#!/usr/bin/env python3
import sys
import os
import uuid
from pathlib import Path
from minio import Minio
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
import openai
from PyPDF2 import PdfReader

# Initialize MinIO client
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    secure=False
)

# Initialize Qdrant client
qdrant_client = QdrantClient(
    url=f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}"
)

# OpenAI settings
openai.api_key = os.getenv("OPENAI_API_KEY")

# Simple text chunker

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    words = text.split()
    chunks = []
    current = []
    current_len = 0
    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            chunks.append(" ".join(current))
            # keep overlap
            current = current[-overlap:]
            current_len = sum(len(w) + 1 for w in current)
    if current:
        chunks.append(" ".join(current))
    return chunks


def index_file(path: Path):
    # Determine bucket and object key
    bucket = path.parent.name
    object_name = path.name

    # Upload file to MinIO
    try:
        minio_client.bucket_exists(bucket)
    except Exception:
        minio_client.make_bucket(bucket)
    minio_client.fput_object(bucket, object_name, str(path))

    # Extract text from PDF
    reader = PdfReader(str(path))
    text = "".join([page.extract_text() or '' for page in reader.pages])

    # Chunk text
    chunks = chunk_text(text)

    # Create embeddings
    resp = openai.Embedding.create(input=chunks, model="text-embedding-ada-002")
    vectors = []
    for idx, data in enumerate(resp["data"]):
        vec = data["embedding"]
        point_id = f"{object_name}-{idx}"
        payload = {"s3_key": object_name, "chunk_index": idx}
        vectors.append(PointStruct(id=point_id, vector=vec, payload=payload))

    # Upsert into Qdrant
    collection_name = f"{bucket}_files"
    try:
        qdrant_client.get_collection(collection_name=collection_name)
    except Exception:
        # create collection with default params
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config={"size": len(vectors[0].vector), "distance": "Cosine"}
        )
    qdrant_client.upsert(collection_name=collection_name, points=vectors)


def main():
    if len(sys.argv) < 2:
        print("Usage: index_files.py <file1.pdf> [<file2.pdf> ...]")
        sys.exit(1)
    paths = [Path(p) for p in sys.argv[1:]]
    for path in paths:
        if not path.exists():
            print(f"File not found: {path}")
            continue
        print(f"Indexing {path}")
        index_file(path)
        print(f"Indexed {path}")


if __name__ == '__main__':
    main()
