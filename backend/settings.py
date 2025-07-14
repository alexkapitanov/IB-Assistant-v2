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
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Model Configuration
    chat_model: str = Field("gpt-4.1", env="CHAT_MODEL")
    router_model: str = Field("gpt-4.1-mini", env="ROUTER_MODEL") 
    expert_model: str = Field("gpt-4.1", env="EXPERT_MODEL")
    
    # External Services
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, env="QDRANT_API_KEY")
    qdrant_host: str = Field("localhost", env="QDRANT_HOST")  # Legacy compatibility
    
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    redis_host: str = Field("localhost", env="REDIS_HOST")  # Legacy compatibility
    
    # MinIO Configuration (legacy compatibility)
    minio_access_key: str = Field("minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("minioadmin", env="MINIO_SECRET_KEY")
    
    # Application Settings
    data_dir: str = Field("./data", env="DATA_DIR")
    port: int = Field(8000, env="PORT")
    environment: str = Field("development", env="ENVIRONMENT")
    
    # Performance and Limits
    max_tokens_per_session: int = Field(50000, env="MAX_TOKENS_PER_SESSION")
    rate_limit_requests: int = Field(10, env="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(60, env="RATE_LIMIT_WINDOW_SECONDS")
    
    # Features
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Legacy constants for backward compatibility
MAX_TOKENS_SESSION = 20_000

MODEL_LIMITS = {
    "gpt-4.1": 8192,
    "gpt-4.1-mini": 4096,
    "o3-mini": 4096,
}

RATE_LIMIT_REQUESTS_PER_WINDOW = 5
RATE_LIMIT_WINDOW_SECONDS = 10

@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()
