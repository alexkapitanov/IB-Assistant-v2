# --- Импорты ---
import os
import sys
import pytest
from unittest.mock import patch, AsyncMock
import socket
import uuid
from pathlib import Path
from minio import Minio
from qdrant_client import QdrantClient

# --- Мок Prometheus metrics server ---
@pytest.fixture
def mock_metrics_server():
    """Мокирует запуск Prometheus metrics server для тестов"""
    with patch('prometheus_client.start_http_server') as mock_server:
        yield mock_server
# --- Автоматическая настройка тестового окружения и мок Prometheus ---
@pytest.fixture(autouse=True)
def setup_test_env():
    """Автоматически настраивает окружение для всех тестов"""
    with patch('prometheus_client.start_http_server'):
        # Определяем режим CI
        is_ci_mode = os.getenv("CI_MODE", "false").lower() == "true"
        
        test_env = {
            'METRICS_PORT': '9090',
            'REDIS_URL': 'redis://localhost:6379',
            'MINIO_ENDPOINT': 'localhost:9000',
            'QDRANT_HOST': 'localhost',
            'QDRANT_PORT': '6333'
        }
        
        # В CI режиме включаем TESTING и отключаем OpenAI
        if is_ci_mode:
            test_env['TESTING'] = 'true'
            # Не устанавливаем OPENAI_API_KEY в CI режиме
        
        with patch.dict(os.environ, test_env):
            yield

# --- Мок WebSocket ---
@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    return ws

# --- Мок Redis ---
@pytest.fixture
def mock_redis():
    with patch('redis.asyncio.Redis') as mock:
        redis_instance = AsyncMock()
        mock.from_url.return_value = redis_instance
        yield redis_instance

# Добавляем корневую директорию в PYTHONPATH для импорта backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(autouse=True)
def reset_config():
    """Автоматически сбрасывать конфигурацию перед каждым тестом"""
    from backend import config
    if hasattr(config, 'config') and hasattr(config.config, 'reload'):
        config.config.reload()
    yield
    if hasattr(config, 'config') and hasattr(config.config, 'reload'):
        config.config.reload()

def _service_available(host: str, port: int) -> bool:
    try:
        socket.create_connection((host, port), timeout=1)
        return True
    except Exception:
        return False

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "integration: mark test as integration test requiring services")
    config.addinivalue_line("markers", "openai: mark test as requiring OpenAI API key")
    config.addinivalue_line("markers", "slow: mark test as slow running")

def pytest_collection_modifyitems(config, items):
    # Skip openai tests if no API key
    if not os.getenv("OPENAI_API_KEY"):
        skip_openai = pytest.mark.skip(reason="OPENAI_API_KEY not set")
        for item in items:
            if "openai" in item.keywords:
                item.add_marker(skip_openai)
    
    # Skip WebSocket integration tests in CI mode
    is_ci_mode = os.getenv("CI_MODE", "false").lower() == "true"
    if is_ci_mode:
        skip_ws_integration = pytest.mark.skip(reason="WebSocket integration tests skipped in CI mode")
        for item in items:
            # Пропускаем специфичные WebSocket интеграционные тесты в CI режиме
            if ("integration" in item.keywords and 
                any(test_name in str(item.fspath) for test_name in [
                    "test_fastapi_ws.py", "test_planner_json_fail.py", "test_error_report.py", "test_status_stream.py"
                ]) and
                any(test_func in item.name for test_func in [
                    "test_ws_integration", "test_planner_json_fail", "test_error_message_shown", "test_status_sequence"
                ])):
                item.add_marker(skip_ws_integration)
                
    # Skip script integration tests if MinIO or Qdrant unavailable
    minio_host, minio_port = os.getenv("MINIO_ENDPOINT", "localhost:9000").split(":")
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    if not (_service_available(minio_host, int(minio_port)) and _service_available(qdrant_host, qdrant_port)):
        skip_integration = pytest.mark.skip(reason="Integration services not available (MinIO or Qdrant)")
        for item in items:
            if "integration" in item.keywords and "test_scripts.py" in str(item.fspath):
                item.add_marker(skip_integration)

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient fixture"""
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)

@pytest.fixture(scope="session")
def mc():
    """MinIO client fixture"""
    return Minio(
        os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )

@pytest.fixture(scope="session")
def qc():
    """Qdrant client fixture"""
    return QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"))

@pytest.fixture
def dummy_pdf(tmp_path):
    f = tmp_path / "dummy.pdf"
    f.write_text("Dummy PDF for testing")
    return f

@pytest.fixture
def dummy_docx(tmp_path):
    f = tmp_path / "dummy.docx"
    f.write_text("Dummy DOCX for testing")
    return f

@pytest.fixture
def dummy_txt(tmp_path):
    f = tmp_path / "dummy.txt"
    f.write_text("Dummy TXT for testing")
    return f

@pytest.fixture
def test_files(tmp_path):
    files = {}
    for ext in ["pdf", "docx", "txt"]:
        p = tmp_path / f"test.{ext}"
        p.write_text(f"Test {ext} content")
        files[ext] = p
    return files

@pytest.fixture
def unique_bucket():
    return f"test-bucket-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def unique_prefix():
    return f"test-prefix-{uuid.uuid4().hex[:8]}/"

@pytest.fixture
def sample_embedding():
    return [0.1] * 1536

