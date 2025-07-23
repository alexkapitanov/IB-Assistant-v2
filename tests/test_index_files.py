import os
import sys
import uuid
import tempfile
import pathlib
import time
import pytest
import socket

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.index_files import ingest_path, ingest_minio_objects, _doc_exists, BUCKET_DEF, PREFIX_DEF

# Skip tests if MinIO or Qdrant services are not reachable
def _service_available(host: str, port: int) -> bool:
    try:
        socket.create_connection((host, port), timeout=1)
        return True
    except Exception:
        return False

# Skip if OpenAI API key is not available
if not os.getenv("OPENAI_API_KEY"):
    pytest.skip("OPENAI_API_KEY not set, skipping OpenAI-dependent tests", allow_module_level=True)

minio_host, minio_port = os.getenv("MINIO_ENDPOINT", "minio:9000").split(":")
qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
if not (_service_available(minio_host, int(minio_port)) and _service_available(qdrant_host, qdrant_port)):
    pytest.skip("MinIO or Qdrant service not available", allow_module_level=True)

def test_ingest_local_and_skip(tmp_path):
    # Create a small text file
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("Hello world from test!")

    # Use a unique bucket for isolation
    bucket = f"test-bucket-{uuid.uuid4().hex}"
    prefix = f"tests-{uuid.uuid4().hex}/"

    # First ingestion should return True (new)
    assert ingest_path(test_file, bucket, prefix) is True

    # Second ingestion should skip (already indexed)
    assert ingest_path(test_file, bucket, prefix) is False

    # Check that _doc_exists returns True for the generated doc_id
    key = f"{prefix}{test_file.name}"
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, key))
    assert _doc_exists(doc_id, bucket)

    # ingest_minio_objects should skip already indexed objects
    count = ingest_minio_objects(bucket, prefix)
    assert count == 0


def test_reindex_minio(tmp_path):
    # Create two small txt files
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file1.write_text("Foo bar baz")
    file2.write_text("Another test file")

    bucket = f"reindex-bucket-{uuid.uuid4().hex}"
    prefix = f"retests-{uuid.uuid4().hex}/"

    # Ingest local files
    assert ingest_path(file1, bucket, prefix) is True
    assert ingest_path(file2, bucket, prefix) is True

    # Remove local copies to simulate only MinIO objects
    # Now reindex via MinIO
    re_count = ingest_minio_objects(bucket, prefix)
    assert re_count == 0  # already indexed
    
    # Create a new file directly in MinIO by re-uploading under a new name
    remote_file = tmp_path / "c.txt"
    remote_file.write_text("New remote file content")
    # Upload manually
    from minio import Minio
    mc = Minio(os.getenv("MINIO_ENDPOINT", "minio:9000"),
              access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
              secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
              secure=False)
    mc.fput_object(bucket, f"{prefix}{remote_file.name}", str(remote_file))

    # Now reindex objects: should index 1 new vector
    count_after = ingest_minio_objects(bucket, prefix)
    assert count_after == 1
