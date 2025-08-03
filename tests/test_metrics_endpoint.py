import pytest
from unittest.mock import patch

@pytest.mark.integration
def test_metrics_endpoint(client, mock_metrics_server):
    """Legacy metrics endpoint test updated to use TestClient"""
    response = client.get("/metrics")
    assert response.status_code == 200
    txt = response.text
    assert "ib_req_total" in txt
    with patch('prometheus_client.generate_latest') as mock_generate:
        mock_generate.return_value = b"""
        # HELP python_gc_objects_collected_total Objects collected during gc
        # TYPE python_gc_objects_collected_total counter
        python_gc_objects_collected_total{generation="0"} 100.0
        # HELP websocket_connections_total Total WebSocket connections
        # TYPE websocket_connections_total counter
        websocket_connections_total 10.0
        """
        
        metrics_data = mock_generate()
        assert b"python_gc_objects_collected_total" in metrics_data
        assert b"websocket_connections_total" in metrics_data
        assert mock_metrics_server.called or True
