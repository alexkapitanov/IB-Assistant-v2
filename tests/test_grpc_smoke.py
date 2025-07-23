import asyncio, json, grpclib
import pytest
from backend.chat_pb2 import ChatMessage
from backend.chat_grpc import ChatStub
from backend.grpc_server import Chat
from grpclib.server import Server
import socket

def _service_available(host: str, port: int) -> bool:
    try:
        socket.create_connection((host, port), timeout=1)
        return True
    except Exception:
        return False

@pytest.mark.asyncio
async def test_grpc_echo(monkeypatch):
    # Мокируем handle_message где он импортирован - в chat_core
    from backend import chat_core
    
    async def _echo(tid, msg, slots, logger):
        return {"type":"chat","role":"assistant","content":msg}
    
    monkeypatch.setattr(chat_core, "handle_message", _echo)

    # Используем порт 50052 для тестов, чтобы не конфликтовать с основным сервером
    test_port = 50052
    
    # Запускаем локальный gRPC сервер для теста
    server = Server([Chat()])
    
    try:
        await server.start("localhost", test_port)
        
        async with grpclib.client.Channel(host="localhost", port=test_port) as channel:
            stub = ChatStub(channel)

            # Создаем список сообщений
            messages = [ChatMessage(role="user", content="ping")]

            # Вызываем метод Stream с сообщениями
            responses = await stub.Stream(messages)

            # Проверяем, что получили один ответ
            assert len(responses) == 1
            # Проверяем содержимое ответа
            assert responses[0].content == "ping"
    finally:
        server.close()
        await server.wait_closed()
