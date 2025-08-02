import pytest

@pytest.mark.integration
@pytest.fixture(scope="module")
def event_loop():
    """Фикстура event loop для асинхронных операций"""
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.mark.integration
def test_metrics_endpoint(client):
    """
    Проверяет, что эндпоинт /metrics отдает метрики Prometheus,
    включая кастомные метрики после взаимодействия с чатом через WebSocket.
    """
def test_metrics_endpoint(client):
    """
    Проверяет, что эндпоинт /metrics отдает метрики Prometheus,
    включая кастомные метрики после взаимодействия с чатом через WebSocket.
    """
    # Выполняем взаимодействие с WebSocket через TestClient
    with client.websocket_connect("/ws") as ws:
        # 1. Получаем session_id
        session_data = ws.receive_json()
        assert session_data.get("type") == "session"
        assert "sessionId" in session_data

        # 2. Отправляем сообщение в чат
        ws.send_json({"message": "Hello, how are you?"})

        # 3. Получаем ответы, пока не получим финальный ответ
        final_response_received = False
        for _ in range(50):
            try:
                msg = ws.receive_json(timeout=2)
            except Exception:
                break
            if msg.get("type") == "chat":
                final_response_received = True
                break
        assert final_response_received, "Не получен окончательный ответ чата"

    # Проверяем эндпоинт /metrics через TestClient
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text
    print(f"\n--- METRICS ---\n{metrics_text}\n--- END METRICS ---\n")

    # Проверяем наличие стандартных и кастомных метрик
    assert "ib_req_total" in metrics_text, "Метрика 'ib_req_total' не найдена"
    assert "ib_stage_latency_sec_bucket" in metrics_text, "Метрика 'ib_stage_latency_sec_bucket' не найдена"

