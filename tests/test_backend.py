import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from backend.embedding import get as embed, _get_client
from backend.memory import get_mem, save_mem

class TestEmbedding:
    """Test embedding functionality"""
    
    @pytest.mark.openai
    def test_embedding_get_with_api_key(self):
        """Test embedding generation with valid API key"""
        text = "Test text for embedding"
        result = embed(text)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(x, float) for x in result)
    
    def test_embedding_client_creation_without_api_key(self):
        """Test client creation fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                _get_client()
    
    @pytest.mark.openai
    def test_embedding_caching(self):
        """Test that identical texts return cached results"""
        text = "Cached text test"
        
        # First call
        result1 = embed(text)
        
        # Second call should use cache
        result2 = embed(text)
        
        assert result1 == result2
    
    @patch('backend.embedding._get_client')
    @patch('backend.embedding._r')
    def test_embedding_mock_response(self, mock_redis, mock_get_client):
        """Test embedding with mocked OpenAI response"""
        # Setup mock client and Redis
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_redis.get.return_value = None  # No cached value
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = embed("test text")
            
        assert result == [0.1] * 1536
        mock_client.embeddings.create.assert_called_once()

class TestMemory:
    """Test memory functionality"""
    
    def test_memory_set_and_get(self):
        """Test basic memory operations"""
        session_id = "test_session_1"
        test_data = {"key": "value", "number": 42}
        
        # Set memory
        save_mem(session_id, test_data)
        
        # Get memory
        result = get_mem(session_id)
        
        assert result == test_data
    
    def test_memory_get_nonexistent(self):
        """Test getting memory for non-existent session"""
        result = get_mem("nonexistent_session")
        assert result == {}
    
    def test_memory_clear(self):
        """Test clearing memory"""
        session_id = "test_session_2"
        test_data = {"data": "to_be_cleared"}
        
        # Set and verify
        save_mem(session_id, test_data)
        assert get_mem(session_id) == test_data
        
        # Clear by saving empty dict
        save_mem(session_id, {})
        assert get_mem(session_id) == {}
    
    def test_memory_update(self):
        """Test updating existing memory"""
        session_id = "test_session_3"
        initial_data = {"key1": "value1"}
        update_data = {"key1": "value1", "key2": "value2"}
        
        # Set initial data
        save_mem(session_id, initial_data)
        
        # Update with new data
        save_mem(session_id, update_data)
        
        # Should contain updated data
        result = get_mem(session_id)
        assert result == update_data
    
    def test_memory_multiple_sessions(self):
        """Test memory isolation between sessions"""
        session1 = "test_session_4"
        session2 = "test_session_5"
        data1 = {"session": "1"}
        data2 = {"session": "2"}
        
        # Set different data for different sessions
        save_mem(session1, data1)
        save_mem(session2, data2)
        
        # Verify isolation
        assert get_mem(session1) == data1
        assert get_mem(session2) == data2
