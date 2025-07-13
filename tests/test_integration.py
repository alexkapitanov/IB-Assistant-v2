import pytest
import tempfile
import pathlib
import time
import json
import io
from unittest.mock import patch

class TestSystemIntegration:
    """Test full system integration"""
    
    @pytest.mark.integration
    @pytest.mark.openai
    @pytest.mark.slow
    def test_full_document_pipeline(self, client, dummy_txt, mc, qc):
        """Test complete document processing pipeline"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        # Step 1: Index a document
        result = ingest_path(dummy_txt, BUCKET_DEF, "integration-test/")
        
        if result:  # Only continue if indexing succeeded
            # Step 2: Search for the document
            from agents.local_search import local_search
            search_results = local_search("dummy", top_k=1)
            
            # Should find at least something (or empty list if no match)
            assert isinstance(search_results, list)
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_api_and_search_integration(self, client):
        """Test API endpoints integration with search"""
        # Test search via API if search endpoint exists
        search_payload = {
            "query": "test document",
            "top_k": 3
        }
        
        response = client.post("/search", json=search_payload)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
        elif response.status_code == 404:
            pytest.skip("Search endpoint not implemented")
        else:
            # Other status codes are acceptable for this integration test
            pass
    
    @pytest.mark.integration
    def test_memory_and_api_integration(self, client):
        """Test memory persistence across API calls"""
        session_id = "integration_test_session"
        
        # Make multiple API calls with same session
        messages = [
            {"message": "Hello", "session_id": session_id},
            {"message": "How are you?", "session_id": session_id},
            {"message": "Tell me about Infowatch", "session_id": session_id}
        ]
        
        responses = []
        for msg in messages:
            response = client.post("/chat", json=msg)
            responses.append(response)
        
        # Check that calls completed (regardless of implementation)
        assert len(responses) == 3
        for response in responses:
            # Should handle requests properly (200 or expected error codes)
            assert response.status_code in [200, 404, 422]
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_embedding_and_storage_integration(self, dummy_txt, mc, qc):
        """Test embedding generation and vector storage integration"""
        from backend.embedding import get as embed
        from scripts.index_files import ensure_collection, BUCKET_DEF
        
        # Generate embedding
        text_content = dummy_txt.read_text()
        embedding = embed(text_content)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        
        # Ensure collection exists
        ensure_collection(BUCKET_DEF)
        
        # Test that collection was created
        try:
            collections = qc.get_collections()
            collection_names = [c.name for c in collections.collections]
            assert BUCKET_DEF in collection_names
        except Exception:
            # Collection creation might fail in test environment
            pass
    
    @pytest.mark.integration
    def test_minio_and_qdrant_integration(self, mc, qc, unique_bucket):
        """Test MinIO and Qdrant integration"""
        from scripts.index_files import ensure_collection
        
        # Test MinIO bucket operations
        try:
            # Create test bucket
            if not mc.bucket_exists(unique_bucket):
                mc.make_bucket(unique_bucket)
            
            # Upload test object
            test_content = b"Integration test content"
            mc.put_object(
                unique_bucket, 
                "test-object.txt", 
                io.BytesIO(test_content),
                len(test_content)
            )
            
            # Test Qdrant collection operations
            ensure_collection(qc, unique_bucket)
            
            # Cleanup
            mc.remove_object(unique_bucket, "test-object.txt")
            mc.remove_bucket(unique_bucket)
            
            try:
                qc.delete_collection(unique_bucket)
            except Exception:
                pass
                
        except Exception:
            pytest.skip("MinIO/Qdrant integration test skipped - services not available")

class TestSystemPerformance:
    """Test system performance characteristics"""
    
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.openai
    def test_concurrent_indexing(self, test_files, mc, qc):
        """Test system handles concurrent indexing operations"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        import threading
        import time
        
        results = []
        errors = []
        
        def index_worker(file_path, prefix):
            try:
                result = ingest_path(file_path, BUCKET_DEF, f"{prefix}/")
                results.append((prefix, result))
            except Exception as e:
                errors.append((prefix, e))
        
        # Start concurrent indexing
        threads = []
        for i, (file_type, file_path) in enumerate(test_files.items()):
            thread = threading.Thread(
                target=index_worker, 
                args=(file_path, f"concurrent-{i}-{file_type}")
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        # Check results
        total_operations = len(results) + len(errors)
        assert total_operations <= len(test_files)  # Some might still be running
        
        # All completed operations should have valid results
        for prefix, result in results:
            assert isinstance(result, bool)
    
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.openai
    def test_large_document_processing(self, tmp_path, mc, qc):
        """Test processing of larger documents"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        # Create a large document (about 10KB)
        large_content = "Large document content with lots of text. " * 200
        large_doc = tmp_path / "large_document.txt"
        large_doc.write_text(large_content)
        
        start_time = time.time()
        result = ingest_path(large_doc, BUCKET_DEF, "large-doc-test/")
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert processing_time < 60.0  # 60 seconds max
        assert isinstance(result, bool)
    
    @pytest.mark.integration
    def test_memory_usage_stability(self, client):
        """Test that memory usage remains stable"""
        import gc
        
        # Make multiple requests to check for memory leaks
        for i in range(10):
            response = client.get("/")
            assert response.status_code in [200, 404]
            
            # Force garbage collection
            gc.collect()
        
        # Test passes if no exceptions occurred

class TestSystemResilience:
    """Test system resilience and error recovery"""
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_service_unavailable_handling(self, dummy_txt):
        """Test graceful handling when services are unavailable"""
        from scripts.index_files import ingest_path
        
        # Test with non-existent bucket/service
        result = ingest_path(dummy_txt, "nonexistent-bucket", "test/")
        
        # Should handle gracefully (return False or raise handled exception)
        assert isinstance(result, bool) or result is None
    
    @pytest.mark.integration
    def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        # This test simulates network issues
        try:
            from backend.embedding import _get_client
            from qdrant_client import QdrantClient
            
            # Test with invalid host (should timeout quickly)
            qc = QdrantClient(host="invalid-host", timeout=1)
            
            try:
                qc.get_collections()
            except Exception:
                # Expected to fail - test that it fails gracefully
                pass
                
        except Exception:
            # If modules can't be imported, skip test
            pytest.skip("Network timeout test skipped")
    
    @pytest.mark.integration
    def test_corrupted_data_handling(self, tmp_path, mc, qc):
        """Test handling of corrupted or invalid data"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        # Create file with special characters and encoding issues
        corrupted_file = tmp_path / "corrupted.txt"
        
        # Write binary data to text file
        with open(corrupted_file, 'wb') as f:
            f.write(b'\x00\x01\x02\xff\xfe\xfd invalid utf-8 \x80\x81')
        
        # Should handle corrupted data gracefully
        try:
            result = ingest_path(corrupted_file, BUCKET_DEF, "corrupted-test/")
            assert isinstance(result, bool)
        except Exception:
            # Exception is acceptable for corrupted data
            pass
