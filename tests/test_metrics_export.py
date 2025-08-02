import pytest
import requests
import time
import json
import asyncio
import websockets

# Фикстура для event loop, если тесты запускаются не через pytest-asyncio
@pytest.fixture(scope="module")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.mark.integration
def test_metrics_endpoint():
    """
    Проверяет, что эндпоинт /metrics отдает метрики Prometheus,
    включая кастомные метрики после взаимодействия с чатом через WebSocket.
    """
    # Даем бэкенду время на запуск
    time.sleep(5)

    async def chat_and_generate_metrics():
        uri = "ws://localhost:8000/ws"
        try:
            async with websockets.connect(uri, open_timeout=20) as websocket:
                # 1. Получаем session_id
                session_message = await websocket.recv()
                session_data = json.loads(session_message)
                assert session_data.get("type") == "session"
                assert "sessionId" in session_data

                # 2. Отправляем сообщение в чат
                chat_message = {"message": "Hello, how are you?"}
                await websocket.send(json.dumps(chat_message))

                # 3. Получаем ответы, пока не получим финальный ответ
                # Мы ожидаем несколько status сообщений и потом chat
                final_response_received = False
                timeout_count = 0
                max_messages = 50  # Максимум сообщений, чтобы избежать бесконечного цикла
                
                while not final_response_received and timeout_count < max_messages:
                    try:
                        response_message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response_data = json.loads(response_message)
                        print(f"Received message: {response_data}")
                        
                        if response_data.get("type") == "chat":
                            final_response_received = True
                        elif response_data.get("type") == "status":
                            # Просто логируем статус сообщения
                            pass
                            
                        timeout_count += 1
                        
                    except asyncio.TimeoutError:
                        print("Timeout waiting for message, breaking...")
                        break
                
                # Закрываем соединение
                await websocket.close()

        except Exception as e:
            assert False, f"Ошибка во время взаимодействия с WebSocket: {e}"

    # Запускаем асихронную часть в новом event loop
    asyncio.run(chat_and_generate_metrics())

    # Небольшая пауза, чтобы метрики успели обработаться
    time.sleep(1)

    # Проверяем эндпоинт /metrics
    try:
        response = requests.get("http://localhost:9090/metrics", timeout=10)
        response.raise_for_status()
        metrics_text = response.text
        print(f"\n--- METRICS ---\n{metrics_text}\n--- END METRICS ---\n")

        # Проверяем наличие стандартных и кастомных метрик
        assert "ib_req_total" in metrics_text, "Метрика 'ib_req_total' не найдена"
        assert "ib_stage_latency_sec_bucket" in metrics_text, "Метрика 'ib_stage_latency_sec_bucket' не найдена"

    except requests.exceptions.RequestException as e:
        assert False, f"Не удалось подключиться к эндпоинту /metrics: {e}"

