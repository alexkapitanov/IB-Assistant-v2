import pytest
from agents.dialog_manager import handle_message
import asyncio
import uuid
from unittest.mock import patch, MagicMock
import logging

test_logger = logging.getLogger("test_router")

@pytest.mark.asyncio
async def test_dialog_manager_returns_file_link(monkeypatch, dummy_pdf):
    """Test that dialog_manager returns file link when requesting documents with file_key in slots"""
    
    # Mock get_file_link function that should be called for file shortcuts
    async def mock_get_file_link(key):
        return {
            "type": "chat",
            "role": "assistant",
            "content": "📎 Документ доступен для скачать: http://minio/ib-docs/questionnaires/x.pdf",
            "intent": "get_file"
        }

    # Mock классификации интента для возврата "file"
    async def mock_classify_intent(q, slots):
        return "file", 0.95

    monkeypatch.setattr(
        "backend.agents.file_retrieval.get_file_link",
        mock_get_file_link
    )
    monkeypatch.setattr(
        "agents.dialog_manager._classify_intent",
        mock_classify_intent
    )
    
    thread = str(uuid.uuid4())
    # Slots with file_key should trigger file shortcut logic
    slots = {"file_key": "infowatch_questionnaire"}
    resp = await handle_message(thread, "любой текст", slots, test_logger)
    
    assert "http" in resp["content"]
    assert "minio" in resp["content"] 
    assert "скачать" in resp["content"]
    assert resp["intent"] == "get_file"
