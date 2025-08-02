import pytest
import requests

@pytest.mark.integration
def test_metrics_endpoint():
    txt = requests.get("http://localhost:9090/metrics").text
    assert "ib_req_total" in txt
