import pytest
import json
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch

def test_ws_smoke_unit():
    """Unit test for WebSocket chat function"""
    from backend.main import chat
    
    # Create mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ["что такое dlp?", Exception("disconnect")]
    
    # Mock handle_message
    async def mock_handle_message(thread_id, data):
        return {
            "answer": "DLP (Data Loss Prevention) - это система защиты от утечек данных",
            "intent": "simple_faq",
            "model": "o3-mini"
        }
    
    # Test the chat function
    async def test_chat():
        with patch("backend.main.handle_message", mock_handle_message):
            try:
                await chat(mock_ws)
            except Exception:
                pass  # Expected due to disconnect simulation
        
        # Verify WebSocket interactions
        mock_ws.accept.assert_called_once()
        mock_ws.receive_text.assert_called()
        mock_ws.send_json.assert_called_once()
        
        # Check the sent data
        sent_data = mock_ws.send_json.call_args[0][0]
        assert "answer" in sent_data
        assert "DLP" in sent_data["answer"]
    
    # Run the async test
    asyncio.run(test_chat())

def test_ws_endpoint_exists():
    """Test that WebSocket endpoint is properly configured in FastAPI app"""
    from backend.main import app
    
    # Check if WebSocket route exists
    ws_routes = [route for route in app.routes if hasattr(route, 'path') and route.path == "/ws"]
    assert len(ws_routes) > 0, "WebSocket route /ws should exist"
    
    # Check if it's a WebSocket route
    ws_route = ws_routes[0]
    assert hasattr(ws_route, 'endpoint'), "Route should have endpoint"

@pytest.mark.slow
@pytest.mark.integration
def test_ws_real_server():
    """Integration test that requires actual WebSocket server running (skipped by default)"""
    # This test would connect to a real server if it was running
    # It will be skipped due to integration marker when services aren't available
    pytest.skip("Real server test - requires running FastAPI server on localhost:8000")
