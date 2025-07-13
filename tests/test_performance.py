import pytest
import time
import threading
import tempfile
import statistics
from concurrent.futures import ThreadPoolExecutor
import os

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class TestPerformance:
    """Performance benchmarks and stress tests"""
    
    @pytest.mark.slow
    @pytest.mark.openai
    def test_embedding_performance(self):
        """Test embedding generation performance"""
        from backend.embedding import get as embed
        
        texts = [
            "Short text",
            "Medium length text with some more content to process",
            "Long text " * 50,  # ~500 words
            "Very long document content " * 100,  # ~1000 words
            "Extremely long document with extensive content " * 200  # ~2000 words
        ]
        
        times = []
        
        for text in texts:
            start_time = time.time()
            result = embed(text)
            end_time = time.time()
            
            processing_time = end_time - start_time
            times.append(processing_time)
            
            assert isinstance(result, list)
            assert len(result) > 0
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Should process embeddings reasonably quickly
        assert avg_time < 5.0  # Average under 5 seconds
        assert max_time < 10.0  # Max under 10 seconds
        
        print(f"Embedding performance - Avg: {avg_time:.2f}s, Max: {max_time:.2f}s")
    
    @pytest.mark.slow
    @pytest.mark.openai
    def test_concurrent_embedding_performance(self):
        """Test concurrent embedding generation"""
        from backend.embedding import get as embed
        
        texts = [f"Concurrent test text number {i}" for i in range(5)]
        
        def embed_worker(text):
            start_time = time.time()
            result = embed(text)
            end_time = time.time()
            return end_time - start_time, len(result)
        
        # Test concurrent execution
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(embed_worker, text) for text in texts]
            results = [future.result() for future in futures]
        
        total_time = time.time() - start_time
        
        # Verify results
        for processing_time, embedding_length in results:
            assert processing_time < 10.0  # Each task under 10 seconds
            assert embedding_length > 0
        
        # Concurrent execution should be faster than sequential
        # (though this depends on API rate limiting)
        assert total_time < 30.0  # Total under 30 seconds
        
        print(f"Concurrent embedding - Total time: {total_time:.2f}s for {len(texts)} texts")
    
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.openai
    def test_indexing_performance(self, tmp_path):
        """Test document indexing performance"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        # Create test documents of various sizes
        files = []
        for i, size_multiplier in enumerate([1, 10, 50, 100]):
            content = f"Test document {i} content. " * (100 * size_multiplier)
            file_path = tmp_path / f"perf_test_{i}.txt"
            file_path.write_text(content)
            files.append((file_path, len(content)))
        
        times = []
        
        for file_path, content_size in files:
            start_time = time.time()
            result = ingest_path(file_path, BUCKET_DEF, f"perf-test-{file_path.stem}/")
            end_time = time.time()
            
            processing_time = end_time - start_time
            times.append((processing_time, content_size))
            
            assert isinstance(result, bool)
        
        # Performance analysis
        for processing_time, content_size in times:
            chars_per_second = content_size / processing_time if processing_time > 0 else 0
            print(f"Indexing performance - {content_size} chars in {processing_time:.2f}s ({chars_per_second:.0f} chars/s)")
            
            # Should process at least 1000 characters per second
            if processing_time > 0:
                assert chars_per_second > 1000 or content_size < 1000
    
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.openai
    def test_search_performance(self):
        """Test search performance"""
        from agents.local_search import local_search
        
        queries = [
            "simple query",
            "more complex search query with multiple terms",
            "specific technical documentation search",
            "infowatch security questionnaire analysis",
            "compliance and risk assessment documentation"
        ]
        
        times = []
        
        for query in queries:
            start_time = time.time()
            results = local_search(query, top_k=5)
            end_time = time.time()
            
            processing_time = end_time - start_time
            times.append(processing_time)
            
            assert isinstance(results, list)
            assert len(results) <= 5
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Search should be fast
        assert avg_time < 3.0  # Average under 3 seconds
        assert max_time < 5.0  # Max under 5 seconds
        
        print(f"Search performance - Avg: {avg_time:.2f}s, Max: {max_time:.2f}s")
    
    @pytest.mark.slow
    def test_memory_usage(self, client):
        """Test memory usage during API operations"""
        if not PSUTIL_AVAILABLE:
            pytest.skip("psutil not available - skipping memory usage test")
            
        import gc
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make multiple API requests
        for i in range(20):
            response = client.get("/")
            assert response.status_code in [200, 404]
            
            # Force garbage collection periodically
            if i % 5 == 0:
                gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage - Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB, Increase: {memory_increase:.1f}MB")
        
        # Memory increase should be reasonable (adjust threshold as needed)
        assert memory_increase < 100  # Less than 100MB increase
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_concurrent_api_requests(self, client):
        """Test API performance under concurrent load"""
        import concurrent.futures
        
        def make_request(request_id):
            start_time = time.time()
            response = client.get("/")
            end_time = time.time()
            return request_id, response.status_code, end_time - start_time
        
        # Make concurrent requests
        num_requests = 10
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [future.result() for future in futures]
        
        total_time = time.time() - start_time
        
        # Analyze results
        response_times = [result[2] for result in results]
        successful_requests = [r for r in results if r[1] in [200, 404]]
        
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        print(f"Concurrent API - {len(successful_requests)}/{num_requests} successful, "
              f"Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s, Total: {total_time:.2f}s")
        
        # Performance assertions
        assert len(successful_requests) >= num_requests * 0.8  # At least 80% success
        assert avg_response_time < 2.0  # Average response under 2 seconds
        assert max_response_time < 5.0  # Max response under 5 seconds
        assert total_time < 15.0  # Total time under 15 seconds

class TestStressTests:
    """Stress tests for system limits"""
    
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.openai
    def test_large_batch_indexing(self, tmp_path):
        """Test indexing large batch of documents"""
        from scripts.index_files import ingest_path, BUCKET_DEF
        
        # Create multiple test documents
        num_docs = 5  # Reasonable number for CI
        files = []
        
        for i in range(num_docs):
            content = f"Stress test document {i} with unique content. " * 20
            file_path = tmp_path / f"stress_test_{i}.txt"
            file_path.write_text(content)
            files.append(file_path)
        
        # Index all documents
        start_time = time.time()
        results = []
        
        for file_path in files:
            result = ingest_path(file_path, BUCKET_DEF, f"stress-test-{file_path.stem}/")
            results.append(result)
        
        total_time = time.time() - start_time
        successful_indexing = sum(1 for r in results if r)
        
        print(f"Batch indexing - {successful_indexing}/{num_docs} successful in {total_time:.2f}s")
        
        # Should complete within reasonable time
        assert total_time < 60.0  # Under 1 minute
        assert successful_indexing >= num_docs * 0.8  # At least 80% success
    
    @pytest.mark.slow
    def test_rapid_api_requests(self, client):
        """Test rapid succession of API requests"""
        num_requests = 50
        start_time = time.time()
        
        responses = []
        for i in range(num_requests):
            response = client.get("/")
            responses.append(response.status_code)
        
        total_time = time.time() - start_time
        successful_responses = [r for r in responses if r in [200, 404]]
        
        print(f"Rapid requests - {len(successful_responses)}/{num_requests} successful in {total_time:.2f}s")
        
        # Should handle rapid requests
        assert len(successful_responses) >= num_requests * 0.9  # At least 90% success
        assert total_time < 30.0  # Under 30 seconds
    
    @pytest.mark.slow
    @pytest.mark.openai
    def test_embedding_cache_stress(self):
        """Test embedding cache under stress"""
        from backend.embedding import get as embed
        
        # Generate same text multiple times (should use cache)
        text = "Cached stress test content"
        num_requests = 10
        
        times = []
        
        for i in range(num_requests):
            start_time = time.time()
            result = embed(text)
            end_time = time.time()
            
            times.append(end_time - start_time)
            assert isinstance(result, list)
        
        # Later requests should be faster due to caching
        first_request_time = times[0]
        avg_cached_time = statistics.mean(times[1:]) if len(times) > 1 else first_request_time
        
        print(f"Cache performance - First: {first_request_time:.2f}s, Avg cached: {avg_cached_time:.2f}s")
        
        # Cached requests should be significantly faster
        if len(times) > 1:
            assert avg_cached_time < first_request_time * 0.5  # At least 50% faster
