import os
from typing import Any, Dict


class Config:
    """Конфигурация приложения с ленивой инициализацией."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def __getattr__(self, name: str) -> Any:
        """Ленивая загрузка атрибутов конфигурации."""
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        if name not in self._cache:
            # Загружаем значение из переменной окружения
            value = os.getenv(name)
            if value is None:
                # Устанавливаем значения по умолчанию для ключевых параметров
                defaults = {
                    "DIALOG_TTL_DAYS": "90",
                    "ARCHIVE_BUCKET": "ib-assistant-archive",
                    "DB_PATH": "/data/chat.db",
                    "GC_TIMEOUT_SEC": "300",
                    "WEB_SEARCH_TIMEOUT_SEC": "20",
                    "WEB_CACHE_TTL_SEC": "86400",
                    "WEB_CACHE_NEG_TTL_SEC": "60",
                    "WEB_CACHE_LOCK_SEC": "30",
                    "MODEL_GPT4": "gpt-4.1",
                    "MODEL_GPT4_MINI": "gpt-4.1-mini",
                    "MODEL_O3_MINI": "o3-mini",
                    "QDRANT_COLLECTION_NAME": "ib-documents",
                    "QDRANT_STAT_COLLECTION_NAME": "ib-dialog-stats",
                    "QDRANT_DIALOG_ARCHIVE_COLLECTION_NAME": "ib-dialog-archive",
                    "LOG_LEVEL": "INFO",
                    "ARCHIVE_DELETE_AFTER_BACKUP": "true",
                    "OPENAI_API_KEY": "stub",
                    "CLARIFY_THRESHOLD": "0.6",
                    # PII/moderation flags
                    "PII_SCRUB_ENABLED": "1",
                    "SCRUB_BEFORE_PERSIST": "0",
                    "ENABLE_LLM_GUARD": "0",
                }
                value = defaults.get(name)

            if value is None:
                raise AttributeError(f"Configuration '{name}' not found in environment variables or defaults")

            # Преобразуем типы: *_SEC, *_TIMEOUT, *_DAYS → int; *_THRESHOLD → float
            out: Any = value
            if isinstance(value, str):
                if name.endswith('_SEC') or name.endswith('_TIMEOUT') or name.endswith('_DAYS'):
                    try:
                        out = int(value)
                    except (ValueError, TypeError):
                        pass
                elif name.endswith('_THRESHOLD'):
                    try:
                        out = float(value)
                    except (ValueError, TypeError):
                        pass

            self._cache[name] = out
        
        return self._cache[name]
    
    def reload(self):
        """Очистить кэш для перезагрузки конфигурации."""
        self._cache.clear()


# Создаем глобальный экземпляр
config = Config()


# Для обратной совместимости экспортируем атрибуты на уровне модуля
def __getattr__(name: str) -> Any:
    """Делегируем доступ к атрибутам модуля объекту config."""
    return getattr(config, name)
