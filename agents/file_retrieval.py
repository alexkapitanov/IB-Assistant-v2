"""
FileRetrieval-tool: выдаёт presigned URL на PDF/Docx по ИБ-продуктам.
"""
__doc__ = "FileRetrieval-tool: выдаёт presigned URL на PDF/Docx по ИБ-продуктам."

# Импортируем функциональность из backend
from backend.agents.file_retrieval import get_file_link, _presign

# Реэкспортируем основные функции для удобства использования
__all__ = ['get_file_link']
