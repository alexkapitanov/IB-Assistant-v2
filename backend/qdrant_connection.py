from qdrant_client import QdrantClient
from backend.settings import get_settings
import logging

settings = get_settings()
qdr = None
try:
    qdr = QdrantClient(url=settings.qdrant_url)
    logging.info("Qdrant client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Qdrant client: {e}", exc_info=True)
    # raise e # Optional: re-raise the exception if the application cannot run without Qdrant
