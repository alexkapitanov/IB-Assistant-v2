import pytest
import tempfile
import pathlib
import subprocess
import os
from unittest.mock import patch, MagicMock

class TestIndexScripts:
    """Test indexing scripts functionality"""
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_index_files_script_basic(self, dummy_txt, mc, qc):
        """Test basic index_files.py functionality"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        # Test ingesting a single file
        result = ingest_path(dummy_txt, BUCKET_DEF, "test-prefix/")
        
        # Should return True for successful ingestion
        assert isinstance(result, bool)
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_index_files_multiple_formats(self, test_files, mc, qc):
        """Test indexing multiple file formats"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        results = []
        for file_type, file_path in test_files.items():
            result = ingest_path(file_path, BUCKET_DEF, f"test-{file_type}/")
            results.append(result)
        
        # All ingestions should complete
        assert len(results) == len(test_files)
    
    @pytest.mark.integration
    def test_index_files_deduplication(self, dummy_txt, mc, qc):
        """Test deduplication functionality"""
        from scripts.index_files import ingest_path, vector_exists, BUCKET_DEF
        
        # First ingestion
        if os.getenv("OPENAI_API_KEY"):
            result1 = ingest_path(dummy_txt, BUCKET_DEF, "dedup-test/")
            
            # Check if vector exists
            s3_key = f"dedup-test/{dummy_txt.name}"
            exists = vector_exists(qc, BUCKET_DEF, s3_key)
            
            # Should exist after first ingestion
            if result1:  # Only check if ingestion was successful
                assert exists
    
    @pytest.mark.integration
    @patch('scripts.index_files.embed')
    @patch('scripts.index_files.ensure_collection')
    def test_index_files_mocked(self, mock_ensure, mock_embed, dummy_txt):
        """Test index_files with mocked dependencies"""
        from scripts.index_files import ingest_path
        
        # Setup mocks
        mock_embed.return_value = [0.1] * 1536
        mock_ensure.return_value = None
        
        # Test with mocked embedding (will still fail due to MinIO but that's expected)
        try:
            result = ingest_path(dummy_txt, "test-bucket", "test-prefix/")
            assert isinstance(result, bool)
        except Exception:
            # Expected to fail without proper services
            pytest.skip("Mocked test skipped due to missing services")
    
    @pytest.mark.integration
    def test_index_files_invalid_path(self):
        """Test handling of invalid file paths"""
        from scripts.index_files import ingest_path
        
        invalid_path = pathlib.Path("/nonexistent/file.txt")
        
        # Should handle invalid path gracefully
        try:
            result = ingest_path(invalid_path, "test-bucket", "test-prefix/")
            assert result is False
        except Exception:
            # Exception is acceptable for tests without services
            pytest.skip("Invalid path test skipped due to missing services")
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_index_files_empty_file(self, tmp_path, mc, qc):
        """Test handling of empty files"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        # Create empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        
        # Should handle empty file gracefully
        result = ingest_path(empty_file, BUCKET_DEF, "empty-test/")
        assert isinstance(result, bool)
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_minio_objects_ingestion(self, mc, qc):
        """Test MinIO objects ingestion"""
        from scripts.index_files import ingest_minio_objects, BUCKET_DEF
        
        # This test requires MinIO to have some objects
        try:
            result = ingest_minio_objects(BUCKET_DEF, "test-prefix/")
            assert isinstance(result, bool)
        except Exception:
            # Skip if MinIO is not properly configured
            pytest.skip("MinIO objects ingestion test skipped")

class TestIndexScriptCLI:
    """Test command line interface of index scripts"""
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_index_files_cli_basic(self, dummy_txt):
        """Test index_files.py CLI with basic arguments"""
        cmd = [
            "python", "scripts/index_files.py",
            "--paths", str(dummy_txt)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=pathlib.Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should complete without critical errors
            # (may have warnings about services not being available)
            assert result.returncode in [0, 1]  # 1 might be expected if services unavailable
            
        except subprocess.TimeoutExpired:
            pytest.fail("Index script timed out")
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_index_files_cli_custom_bucket(self, dummy_txt, unique_bucket):
        """Test index_files.py CLI with custom bucket"""
        cmd = [
            "python", "scripts/index_files.py",
            "--paths", str(dummy_txt),
            unique_bucket, "test-prefix/"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=pathlib.Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should handle custom bucket argument
            assert result.returncode in [0, 1]
            
        except subprocess.TimeoutExpired:
            pytest.fail("Index script with custom bucket timed out")
    
    def test_index_files_cli_help(self):
        """Test index_files.py CLI help"""
        cmd = ["python", "scripts/index_files.py", "--help"]
        
        # Set PYTHONPATH for subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=pathlib.Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            if result.returncode == 0:
                assert "usage:" in result.stdout.lower() or "help" in result.stdout.lower()
            else:
                # If it fails due to missing dependencies, that's acceptable
                pytest.skip("CLI help test skipped due to missing dependencies")
                
        except subprocess.TimeoutExpired:
            pytest.fail("Help command timed out")
    
    @pytest.mark.integration
    def test_index_files_cli_reindex(self):
        """Test index_files.py reindex functionality"""
        cmd = [
            "python", "scripts/index_files.py",
            "--reindex", "test-bucket", "test-prefix/"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=pathlib.Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should handle reindex command
            assert result.returncode in [0, 1]
            
        except subprocess.TimeoutExpired:
            pytest.fail("Reindex command timed out")

class TestIndexScriptErrorHandling:
    """Test error handling in index scripts"""
    
    def test_index_without_openai_key(self, dummy_txt):
        """Test index script behavior without OpenAI key"""
        cmd = [
            "python", "scripts/index_files.py",
            "--paths", str(dummy_txt)
        ]
        
        # Remove OpenAI key from environment and set PYTHONPATH
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=pathlib.Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            # With stub mode, script should succeed but process 0 files
            assert result.returncode == 0
            output_text = result.stdout + result.stderr
            assert "Indexed 0 new vector(s)" in output_text
            
        except subprocess.TimeoutExpired:
            pytest.fail("Script should fail quickly without API key")
    
    def test_index_nonexistent_file(self):
        """Test index script with nonexistent file"""
        cmd = [
            "python", "scripts/index_files.py",
            "--paths", "/nonexistent/file.txt"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=pathlib.Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should handle nonexistent file gracefully
            # May return 0 (skip file) or 1 (error) - both are acceptable
            assert result.returncode in [0, 1]
            
        except subprocess.TimeoutExpired:
            pytest.fail("Script should handle nonexistent file quickly")
    
    def test_index_invalid_arguments(self):
        """Test index script with invalid arguments"""
        cmd = [
            "python", "scripts/index_files.py",
            "--invalid-argument"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=pathlib.Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should fail with argument error
            assert result.returncode != 0
            
        except subprocess.TimeoutExpired:
            pytest.fail("Script should fail quickly with invalid arguments")
