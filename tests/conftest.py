import os
import pytest
import sys
from pathlib import Path
import socket
import uuid
from minio import Minio
from qdrant_client import QdrantClient
import backend.metrics as _metrics
import threading
import time
import uvicorn

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Запускаем HTTP-сервер метрик на порту по умолчанию (9090)
_metrics.init()

# Запускаем FastAPI Uvicorn сервер для интеграционных тестов на localhost:8000
_thread = threading.Thread(
    target=lambda: uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="warning"),
    daemon=True,
)
_thread.start()
# Ждём, пока сервер поднимется
time.sleep(2)


@pytest.fixture(autouse=True)
def reset_config():
    """Автоматически сбрасывать конфигурацию перед каждым тестом."""
    from backend import config
    
    # Очищаем кэш перед тестом
    if hasattr(config, 'config') and hasattr(config.config, 'reload'):
        config.config.reload()
    
    yield
    
    # Очищаем кэш после теста
    if hasattr(config, 'config') and hasattr(config.config, 'reload'):
        config.config.reload()

# Helper function to check service availability
def _service_available(host: str, port: int) -> bool:
    try:
        socket.create_connection((host, port), timeout=1)
        return True
    except Exception:
        return False

# Skip integration tests if services are not available
def pytest_configure(config):
    """Configure pytest markers and skip conditions"""
    config.addinivalue_line("markers", "integration: mark test as integration test requiring services")
    config.addinivalue_line("markers", "openai: mark test as requiring OpenAI API key")
    config.addinivalue_line("markers", "slow: mark test as slow running")

def pytest_collection_modifyitems(config, items):
    """Auto-skip tests based on availability"""
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        skip_openai = pytest.mark.skip(reason="OPENAI_API_KEY not set")
        for item in items:
            if "openai" in item.keywords:
                item.add_marker(skip_openai)
    
    # Skip tests in test_scripts.py if MinIO/Qdrant services are not available
    minio_host, minio_port = os.getenv("MINIO_ENDPOINT", "minio:9000").split(":")
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    services_available = (
        _service_available(minio_host, int(minio_port)) and 
        _service_available(qdrant_host, qdrant_port)
    )
    if not services_available:
        skip_integration = pytest.mark.skip(reason="Integration services not available (MinIO or Qdrant)")
        for item in items:
            # Only skip index_scripts tests requiring external services
            if "integration" in item.keywords and str(item.fspath).endswith("test_scripts.py"):
                item.add_marker(skip_integration)

@pytest.fixture(scope="session")
def client():
    """FastAPI test client"""
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)

@pytest.fixture(scope="session")
def mc():
    """MinIO client fixture"""
    return Minio(
        os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )

@pytest.fixture(scope="session")
def qc():
    """Qdrant client fixture"""
    return QdrantClient(host=os.getenv("QDRANT_HOST", "qdrant"))

@pytest.fixture
def dummy_pdf(tmp_path):
    """Create a dummy PDF file for testing"""
    pdf = tmp_path / "dummy.pdf"
    pdf.write_text("Dummy Infowatch Questionnaire for testing")
    return pdf

@pytest.fixture
def dummy_docx(tmp_path):
    """Create a dummy DOCX file for testing"""
    docx = tmp_path / "dummy.docx"
    docx.write_text("Dummy Word document with Infowatch content")
    return docx

@pytest.fixture
def dummy_txt(tmp_path):
    """Create a dummy TXT file for testing"""
    txt = tmp_path / "dummy.txt"
    txt.write_text("Plain text file with test content for Infowatch system")
    return txt

@pytest.fixture
def test_files(tmp_path):
    """Create multiple test files of different formats"""
    files = {}
    files['pdf'] = tmp_path / "test.pdf"
    files['pdf'].write_text("PDF test content")
    
    files['docx'] = tmp_path / "test.docx"
    files['docx'].write_text("DOCX test content")
    
    files['txt'] = tmp_path / "test.txt"
    files['txt'].write_text("TXT test content")
    
    return files

@pytest.fixture
def unique_bucket():
    """Generate unique bucket name for tests"""
    return f"test-bucket-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def unique_prefix():
    """Generate unique prefix for tests"""
    return f"test-prefix-{uuid.uuid4().hex[:8]}/"

@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing"""
    return [0.1] * 1536  # OpenAI text-embedding-3-small dimension

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing"""
    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "embedding": [0.1] * 1536,
                "index": 0
            }
        ],
        "model": "text-embedding-3-small",
        "usage": {
            "prompt_tokens": 8,
            "total_tokens": 8
        }
    }
