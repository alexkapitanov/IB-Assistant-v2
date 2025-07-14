import pytest
from backend.router import handle_message
import asyncio
import uuid
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_router_returns_file_link(monkeypatch, dummy_pdf):
    """Test that router returns file link when requesting documents"""
    
    # Mock classify function to return get_file intent
    monkeypatch.setattr(
        "backend.router.classify",
        lambda user_q, slots: "get_file"
    )
    
    # Mock memory functions
    monkeypatch.setattr(
        "backend.router.get_mem",
        lambda thread_id: {}
    )
    
    monkeypatch.setattr(
        "backend.router.save_mem",
        lambda thread_id, data: None
    )
    
    # Mock status_bus publish to avoid Redis connection (must be async)
    async def mock_publish(thread_id, status):
        pass
    
    monkeypatch.setattr(
        "backend.router.publish",
        mock_publish
    )
    
    # Mock get_file_link directly in router module (since it's imported there)
    monkeypatch.setattr(
        "backend.router.get_file_link",
        lambda q, p: "http://minio/ib-docs/questionnaires/x.pdf"
    )
    
    thread = str(uuid.uuid4())
    resp = await handle_message(thread, "дай опросный лист Infowatch")
    
    assert "http" in resp["content"]
    assert "minio" in resp["content"]
    assert "скачать" in resp["content"]
    assert resp["intent"] == "get_file"
