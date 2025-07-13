import pytest
from backend.router import handle_message
import asyncio
import uuid
from unittest.mock import patch, MagicMock
import anyio

def test_router_returns_file_link(monkeypatch, dummy_pdf):
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
    
    # Mock status_bus publish to avoid Redis connection
    monkeypatch.setattr(
        "backend.router.publish",
        lambda thread_id, status: None
    )
    
    # Mock get_file_link directly in router module (since it's imported there)
    monkeypatch.setattr(
        "backend.router.get_file_link",
        lambda q, p: "http://minio/ib-docs/questionnaires/x.pdf"
    )
    
    async def run_test():
        thread = str(uuid.uuid4())
        resp = await handle_message(thread, "дай опросный лист Infowatch")
        return resp
    
    resp = anyio.run(run_test)
    
    assert "http" in resp["answer"]
    assert "minio" in resp["answer"]
    assert "скачать" in resp["answer"]
    assert resp["intent"] == "get_file"
