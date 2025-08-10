import pytest
import requests


@pytest.mark.integration
def test_metrics_names():
    """Test that all expected metrics are available"""
    try:
        txt = requests.get("http://localhost:9310/metrics").text
        assert "ib_timeout_total" in txt
        assert "ib_critic_score_bucket" in txt
        assert "sqlite_table_rows" in txt
        assert "qdrant_collection_points" in txt
    except requests.ConnectionError:
        pytest.skip("Metrics server not available on port 9310")
