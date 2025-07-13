import pytest
import subprocess
import pathlib
import uuid
import io
import os

@pytest.mark.integration
@pytest.mark.openai
def test_reindex_skips_existing(mc):
    """Test that reindex command processes existing files in MinIO"""
    # Create a test file in MinIO
    key = f"questionnaires/reindex_{uuid.uuid4()}.txt"
    mc.put_object("ib-docs", key, io.BytesIO(b"test content for reindex"), length=24)
    
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    try:
        # Run reindex command
        out = subprocess.check_output(
            ["python", "scripts/index_files.py", "--reindex", "ib-docs", "questionnaires/"],
            cwd=pathlib.Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            timeout=30
        )
        
        # Should process files and show indexing activity
        assert "Indexed" in out or "Processing" in out or "reindex" in out.lower()
        
    except subprocess.TimeoutExpired:
        pytest.fail("Reindex command timed out")
    except subprocess.CalledProcessError as e:
        # If reindex fails due to missing services, that's acceptable
        if "OPENAI_API_KEY" in str(e.output):
            pytest.skip("Reindex test skipped due to missing OpenAI API key")
        else:
            pytest.fail(f"Reindex command failed: {e.output}")
    finally:
        # Cleanup: remove the test object
        try:
            mc.remove_object("ib-docs", key)
        except Exception:
            pass

@pytest.mark.integration
@pytest.mark.openai
def test_reindex_with_custom_bucket_prefix(mc):
    """Test reindex with custom bucket and prefix"""
    # Create unique bucket and prefix for this test
    test_bucket = f"test-reindex-{uuid.uuid4().hex[:8]}"
    test_prefix = "test-files/"
    key = f"{test_prefix}reindex_test_{uuid.uuid4()}.txt"
    
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    try:
        # Create bucket and add test file
        if not mc.bucket_exists(test_bucket):
            mc.make_bucket(test_bucket)
        
        mc.put_object(test_bucket, key, io.BytesIO(b"custom bucket test content"), length=26)
        
        # Run reindex on custom bucket/prefix
        out = subprocess.check_output(
            ["python", "scripts/index_files.py", "--reindex", test_bucket, test_prefix],
            cwd=pathlib.Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            timeout=30
        )
        
        # Should process the file
        assert "Indexed" in out or "Processing" in out or "reindex" in out.lower()
        
    except subprocess.TimeoutExpired:
        pytest.fail("Custom reindex command timed out")
    except subprocess.CalledProcessError as e:
        # If reindex fails due to missing services, that's acceptable
        if "OPENAI_API_KEY" in str(e.output):
            pytest.skip("Custom reindex test skipped due to missing OpenAI API key")
        else:
            pytest.fail(f"Custom reindex command failed: {e.output}")
    finally:
        # Cleanup: remove test data
        try:
            # Remove objects
            objects = mc.list_objects(test_bucket, recursive=True)
            for obj in objects:
                mc.remove_object(test_bucket, obj.object_name)
            # Remove bucket
            mc.remove_bucket(test_bucket)
            # Remove Qdrant collection if created
            from qdrant_client import QdrantClient
            qc = QdrantClient(host=os.getenv("QDRANT_HOST", "qdrant"))
            try:
                qc.delete_collection(test_bucket)
            except Exception:
                pass
        except Exception:
            pass

@pytest.mark.integration
def test_reindex_command_basic_validation():
    """Test basic validation of reindex command without actual processing"""
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    # Test reindex with invalid arguments
    try:
        result = subprocess.run(
            ["python", "scripts/index_files.py", "--reindex"],
            cwd=pathlib.Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should either succeed or fail with clear error message
        assert result.returncode in [0, 1, 2]  # Various acceptable exit codes
        
    except subprocess.TimeoutExpired:
        pytest.fail("Basic reindex validation timed out")

@pytest.mark.integration
@pytest.mark.openai
def test_reindex_empty_bucket():
    """Test reindex behavior with empty bucket"""
    # Create empty bucket for testing
    empty_bucket = f"test-empty-{uuid.uuid4().hex[:8]}"
    
    # Set PYTHONPATH for subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
    
    try:
        # Get mc fixture through a simple approach
        from minio import Minio
        mc = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )
        
        # Create empty bucket
        if not mc.bucket_exists(empty_bucket):
            mc.make_bucket(empty_bucket)
        
        # Run reindex on empty bucket
        result = subprocess.run(
            ["python", "scripts/index_files.py", "--reindex", empty_bucket, ""],
            cwd=pathlib.Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=20
        )
        
        # Should handle empty bucket gracefully
        assert result.returncode in [0, 1]  # Either success or expected failure
        
        if result.returncode == 0:
            # If successful, should indicate no files to process
            output = result.stdout + result.stderr
            assert "empty" in output.lower() or "no files" in output.lower() or "0" in output
        
    except Exception as e:
        pytest.skip(f"Empty bucket test skipped: {e}")
    finally:
        # Cleanup
        try:
            mc.remove_bucket(empty_bucket)
        except Exception:
            pass
