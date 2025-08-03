import pytest
pytest.skip("WebSocket-тесты устарели, использовать unit-тест chat_stream", allow_module_level=True)

@pytest.mark.integration
@pytest.fixture(scope="module")
def event_loop():
    """Фикстура event loop для асинхронных операций"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Тест WebSocket соединения с правильной обработкой ответов (мок chat_stream)"""
    with patch('backend.chat_core.chat_stream') as mock_chat:
        async def mock_stream(*args, **kwargs):
            websocket = args[1]
            await websocket.send_json({
                "type": "chat",
                "message": "Mocked chat response!"
            })
        mock_chat.side_effect = mock_stream

        with client.websocket_connect("/ws") as websocket:
            test_message = {"message": "Hello, how are you?"}
            websocket.send_json(test_message)
            # Ждём type == chat
            for _ in range(5):
                data = websocket.receive_json()
                if data.get("type") == "chat":
                    assert "message" in data
                    break
            else:
                pytest.fail("Не получен chat-ответ от сервера")

@pytest.mark.asyncio
async def test_metrics_with_mock_chat():
    """Тест с мокированием chat handler"""
    with patch('backend.chat_core.chat_stream') as mock_chat:
        async def mock_stream(*args, **kwargs):
            websocket = args[1]
            await websocket.send_json({
                "type": "chat",
                "message": "I'm doing well, thank you!"
            })
        mock_chat.side_effect = mock_stream

        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"message": "Hello!"})
            # Ждём type == chat
            for _ in range(5):
                response = websocket.receive_json()
                if response.get("type") == "chat":
                    assert "message" in response
                    break
            else:
                pytest.fail("Не получен chat-ответ от сервера")


