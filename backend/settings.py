"""
Настройки системы
"""

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key for LLM access")
    
    # Model Configuration
    chat_model: str = Field("gpt-4.1", description="Chat model name")
    router_model: str = Field("gpt-4.1-mini", description="Router model name") 
    expert_model: str = Field("gpt-4.1", description="Expert model name")
    
    # External Services
    qdrant_url: str = Field("http://localhost:6333", description="Qdrant vector database URL")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant authentication key")
    qdrant_host: str = Field("localhost", description="Qdrant host (legacy)")  # Legacy compatibility
    
    redis_url: str = Field("redis://localhost:6379", description="Redis connection URL")
    redis_host: str = Field("localhost", description="Redis host (legacy)")  # Legacy compatibility
    
    # MinIO Configuration (legacy compatibility)
    minio_access_key: str = Field("minioadmin", description="MinIO access key")
    minio_secret_key: str = Field("minioadmin", description="MinIO secret key")
    
    # Application Settings
    data_dir: str = Field("./data", description="Directory for file storage")
    port: int = Field(8000, description="API server port")
    environment: str = Field("development", description="Environment name")
    
    # Performance and Limits
    max_tokens_per_session: int = Field(50000, description="Token limit per session")
    rate_limit_requests: int = Field(10, description="Rate limit requests per minute")
    rate_limit_window_seconds: int = Field(60, description="Rate limit window in seconds")
    
    # Features
    enable_metrics: bool = Field(True, description="Enable Prometheus metrics")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }

# Legacy constants for backward compatibility
MAX_TOKENS_SESSION = 20_000

MODEL_LIMITS = {
    "gpt-4.1": 8192,
    "gpt-4.1-mini": 4096,
    "o3-mini": 4096,
}

RATE_LIMIT_REQUESTS_PER_WINDOW = 5
RATE_LIMIT_WINDOW_SECONDS = 10

# Qdrant settings
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Redis settings from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()
