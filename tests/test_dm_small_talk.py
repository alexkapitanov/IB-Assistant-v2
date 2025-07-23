import pytest, asyncio, uuid
from agents.dialog_manager import handle_message
from backend.memory import save_mem
import logging

test_logger = logging.getLogger("test_dm")

@pytest.mark.asyncio
async def test_small_talk_loop(monkeypatch):
    # 1) классификатор даст unknown => follow-up
    async def mock_classify_intent(q, s):
        return ("unknown", 0.4)
    monkeypatch.setattr("agents.dialog_manager._classify_intent",
        mock_classify_intent)
    
    async def mock_ask_dm_critic(i, q):
        return 0.4
    monkeypatch.setattr("agents.dialog_manager.ask_dm_critic",
        mock_ask_dm_critic)
    
    # Mock ask_planner to avoid external calls
    async def mock_ask_planner(tid, user_q, slots, logger):
        return {"need_clarify": True, "clarify": "Пожалуйста, уточните ваш вопрос."}
    monkeypatch.setattr("backend.agents.planner.ask_planner", mock_ask_planner)

    # Mock kb_search to avoid event loop issues with embedding_pool
    async def mock_kb_search(q):
        return ("not_found", {})
    monkeypatch.setattr("agents.dialog_manager.kb_search", mock_kb_search)

    tid=str(uuid.uuid4())
    out = await handle_message(tid,"Расскажи", {}, test_logger)
    assert "уточните" in out["content"].lower()
