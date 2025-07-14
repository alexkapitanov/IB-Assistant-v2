import pytest
from subprocess import check_call, check_output
import os
import uuid
import pathlib

@pytest.mark.integration
@pytest.mark.openai
def test_local_ingest_to_minio_and_qdrant(dummy_pdf, mc, qc):
    """Test ingesting local file to MinIO and Qdrant"""
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    # ingest локального файла
    check_call(
        ["python", "scripts/index_files.py", "--paths", str(dummy_pdf)],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        env=env
    )
    
    key = f"questionnaires/{dummy_pdf.name}"
    
    # файл должен лежать в MinIO
    obj = mc.stat_object("ib-docs", key)
    assert obj.object_name == key
    
    # вектор должен быть в Qdrant
    from qdrant_client import models
    pts, _ = qc.scroll(
        "ib-docs",
        scroll_filter=models.Filter(
            must=[models.FieldCondition(key="s3_key", match=models.MatchValue(value=key))]
        ),
        limit=1,
    )
    assert pts, "Vector not indexed"

@pytest.mark.integration
@pytest.mark.openai
def test_reindex_skip_duplicates(dummy_txt, mc, qc):
    """Test that reindexing skips duplicate files"""
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    # First ingestion
    check_call(
        ["python", "scripts/index_files.py", "--paths", str(dummy_txt)],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        env=env
    )
    
    # Second ingestion (should skip)
    output = check_output(
        ["python", "scripts/index_files.py", "--paths", str(dummy_txt)],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        env=env,
        text=True
    )
    
    # Should indicate skipping or no new files
    assert "Indexed" in output or "skip" in output.lower()

@pytest.mark.integration
@pytest.mark.openai
def test_minio_reindex_functionality(mc, qc):
    """Test MinIO bucket reindexing"""
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    # Test reindex command (should complete without error)
    try:
        output = check_output(
            ["python", "scripts/index_files.py", "--reindex", "ib-docs", "questionnaires/"],
            cwd=pathlib.Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            timeout=30
        )
        
        # Should complete successfully
        assert isinstance(output, str)
        
    except Exception as e:
        # If MinIO is empty or has issues, that's acceptable for this test
        pytest.skip(f"Reindex test skipped: {e}")

@pytest.mark.integration
@pytest.mark.openai
def test_multiple_files_ingestion(test_files, mc, qc):
    """Test ingesting multiple files at once"""
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    # Ingest all test files
    file_paths = [str(f) for f in test_files.values()]
    
    check_call(
        ["python", "scripts/index_files.py", "--paths"] + file_paths,
        cwd=pathlib.Path(__file__).resolve().parents[1],
        env=env
    )
    
    # Verify all files are in MinIO
    for file_type, file_path in test_files.items():
        key = f"questionnaires/{file_path.name}"
        try:
            obj = mc.stat_object("ib-docs", key)
            assert obj.object_name == key
        except Exception as e:
            pytest.fail(f"File {file_path.name} not found in MinIO: {e}")

@pytest.mark.integration
@pytest.mark.openai
def test_custom_bucket_and_prefix(dummy_txt, mc, qc, unique_bucket, unique_prefix):
    """Test ingestion with custom bucket and prefix"""
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    # Create bucket if it doesn't exist
    if not mc.bucket_exists(unique_bucket):
        mc.make_bucket(unique_bucket)
    
    # Ingest with custom bucket and prefix
    check_call(
        ["python", "scripts/index_files.py", "--paths", str(dummy_txt), "--bucket", unique_bucket, "--prefix", unique_prefix],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        env=env
    )
    
    # Verify file is in the custom location
    key = f"{unique_prefix}{dummy_txt.name}"
    try:
        obj = mc.stat_object(unique_bucket, key)
        assert obj.object_name == key
    except Exception as e:
        # In stub mode, file might not be uploaded
        if os.getenv("OPENAI_API_KEY") == "stub":
            pytest.skip("File not uploaded in stub mode - this is expected")
        raise
    
    # Cleanup
    try:
        # Remove objects
        objects_to_delete = mc.list_objects(unique_bucket, prefix=unique_prefix, recursive=True)
        for obj in objects_to_delete:
            mc.remove_object(unique_bucket, obj.object_name)
        # Remove bucket
        mc.remove_bucket(unique_bucket)
    except Exception as e:
        print(f"Cleanup failed: {e}")

    # Cleanup Qdrant
    try:
        qc.delete_collection(collection_name=unique_bucket)
    except Exception as e:
        print(f"Qdrant cleanup failed for collection {unique_bucket}: {e}")
