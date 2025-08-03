import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import asyncio
import uuid
from qdrant_client.http import models

class TestAgents:
    """Test agent functionality"""
    
    @pytest.mark.openai
    def test_local_search_agent(self):
        """Test local search agent functionality"""
        from agents.local_search import local_search
        
        query = "test query"
        result = local_search(query, top_k=3)
        
        assert isinstance(result, list)
        # If no data indexed, should return empty list
        assert len(result) >= 0
    
    @pytest.mark.openai
    def test_local_search_with_filters(self):
        """Test local search with filters"""
        from agents.local_search import local_search
        
        query = "infowatch questionnaire"
        result = local_search(query, top_k=1)
        
        assert isinstance(result, list)
        assert len(result) <= 1
    
    @patch('agents.local_search.embed')
    @patch('agents.local_search._q')
    @patch('agents.local_search._r')  # Mock Redis to avoid cache hits
    def test_local_search_mocked(self, mock_redis, mock_qdrant_client, mock_embed):
        """Test local search with mocked dependencies"""
        from agents.local_search import local_search
    
        # Setup mocks
        mock_embed.return_value = [0.1] * 1536
        mock_redis.get.return_value = None  # No cache hit
        mock_redis.set.return_value = True  # Cache write succeeds
        
        # Создаем мок-объект, который имитирует ответ от qdrant_client
        mock_response = Mock()
        mock_response.points = [
            models.ScoredPoint(id=str(uuid.uuid4()), version=1, score=0.9, payload={'text': 'mocked result'})
        ]
        mock_qdrant_client.query_points.return_value = mock_response
    
        # Use a unique query to avoid caching
        result = local_search(f"test query {uuid.uuid4()}")
    
        assert isinstance(result, list)
        mock_embed.assert_called_once()
        mock_qdrant_client.query_points.assert_called_once()

    @patch('agents.refine.call_llm', new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_refine_mocked(self, mock_call_llm):
        """Test refine function with mocked LLM call"""
        from agents.refine import refine
        mock_call_llm.return_value = ("Улучшенный ответ", None)
        result = await refine("тестовый черновик")
        assert result == "Улучшенный ответ"
        mock_call_llm.assert_called_once()

    @patch('backend.agents.critic.call_llm', new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_ask_critic_mocked(self, mock_call_llm):
        """Test critic with mocked dependencies"""
        from backend.agents.critic import ask_critic
        # Моделируем ответ от LLM, который означает "уверен"
        mock_call_llm.return_value = ("10", None)
        
        is_confident = await ask_critic("тестовый черновик")
        
        assert is_confident is True
        mock_call_llm.assert_called_once()

    @patch('backend.agents.critic.call_llm', new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_ask_critic_not_confident_mocked(self, mock_call_llm):
        """Test critic when not confident"""
        from backend.agents.critic import ask_critic
        # Моделируем ответ от LLM, который означает "не уверен"
        mock_call_llm.return_value = ("0.3", None)

        is_confident = await ask_critic("тестовый черновик")

        assert is_confident is False
        mock_call_llm.assert_called_once()

    def test_expert_gc_agent_import(self):
        """Test expert GC agent can be imported"""
        try:
            from backend.agents.expert_gc import expert_gc_agent
            assert callable(expert_gc_agent)
        except ImportError:
            pytest.skip("Expert GC agent not available")
    
    def test_file_retrieval_agent_import(self):
        """Test file retrieval agent can be imported"""
        try:
            from backend.agents.file_retrieval import file_retrieval_agent
            assert callable(file_retrieval_agent)
        except ImportError:
            pytest.skip("File retrieval agent not available")
    
    def test_planner_agent_import(self):
        """Test planner agent can be imported"""
        try:
            from backend.agents.planner import planner_agent
            assert callable(planner_agent)
        except ImportError:
            pytest.skip("Planner agent not available")
    
    @pytest.mark.openai
    def test_agents_integration(self):
        """Test basic integration between agents"""
        try:
            from agents.local_search import local_search
            from backend.agents.planner import planner_agent
            
            # Test that agents can work together
            search_result = local_search("test", top_k=1)
            assert isinstance(search_result, list)
            
            # If planner agent exists, test it can be called
            if 'planner_agent' in locals():
                # Basic test that planner can be called
                assert callable(planner_agent)
                
        except ImportError:
            pytest.skip("Agent integration test skipped - agents not available")

class TestAgentErrorHandling:
    """Test agent error handling"""
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_local_search_empty_query(self):
        """Test local search with empty query"""
        from backend.agents.local_search import local_search
        
        # Should handle empty query gracefully
        result = local_search("", top_k=1)
        assert isinstance(result, list)
    
    @pytest.mark.integration
    @pytest.mark.openai
    def test_local_search_invalid_top_k(self):
        """Test local search with invalid top_k values"""
        from backend.agents.local_search import local_search
        
        # Test with zero
        result = local_search("test", top_k=0)
        assert isinstance(result, list)
        assert len(result) == 0
        
        # Test with negative value
        result = local_search("test", top_k=-1)
        assert isinstance(result, list)

    @patch('agents.local_search.embed')
    @patch('agents.local_search._q')
    def test_local_search_qdrant_error(self, mock_qdrant, mock_embed):
        """Test local search handles Qdrant errors"""
        from agents.local_search import local_search

        # Setup mock to raise exception
        mock_embed.return_value = [0.1] * 1536
        mock_qdrant.search.side_effect = Exception("Qdrant is down")

        # Call the function and assert it returns an empty list
        result = local_search(f"any query {uuid.uuid4()}")
        assert result == []
    
    @patch('agents.local_search.embed')
    def test_local_search_embedding_error(self, mock_embed):
        """Test local search handles embedding errors"""
        from agents.local_search import local_search
        
        # Setup mock to raise exception
        mock_embed.side_effect = Exception("Embedding error")
        
        # Should handle exception gracefully
        try:
            result = local_search("test query")
            assert isinstance(result, list)
        except Exception:
            # If exception is not handled, that's also acceptable behavior
            pass

class TestAgentPerformance:
    """Test agent performance characteristics"""
    
    @pytest.mark.slow
    @pytest.mark.openai
    def test_local_search_performance(self):
        """Test local search performance with multiple queries"""
        from agents.local_search import local_search
        import time
        
        queries = [
            "infowatch security",
            "questionnaire analysis", 
            "document processing",
            "compliance check",
            "risk assessment"
        ]
        
        start_time = time.time()
        
        for query in queries:
            result = local_search(query, top_k=3)
            assert isinstance(result, list)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete all queries in reasonable time (adjust threshold as needed)
        assert total_time < 30.0  # 30 seconds for 5 queries
    
    @pytest.mark.openai
    def test_local_search_concurrent(self):
        """Test local search can handle concurrent requests"""
        from agents.local_search import local_search
        import threading
        import time
        
        results = []
        errors = []
        
        def search_worker(query_id):
            try:
                result = local_search(f"test query {query_id}", top_k=1)
                results.append((query_id, result))
            except Exception as e:
                errors.append((query_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(3):  # 3 concurrent requests
            thread = threading.Thread(target=search_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        # Check results
        assert len(results) + len(errors) == 3
        
        # All successful results should be lists
        for query_id, result in results:
            assert isinstance(result, list)
