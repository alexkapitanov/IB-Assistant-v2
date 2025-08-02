import os
from typing import Optional, Dict, Any


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
                    "MODEL_GPT4": "gpt-4-turbo",
                    "MODEL_GPT4_MINI": "gpt-4.1-mini",
                    "MODEL_O3_MINI": "gpt-3.5-turbo",
                    "QDRANT_COLLECTION_NAME": "ib-documents",
                    "QDRANT_STAT_COLLECTION_NAME": "ib-dialog-stats",
                    "QDRANT_DIALOG_ARCHIVE_COLLECTION_NAME": "ib-dialog-archive",
                    "LOG_LEVEL": "INFO",
                    "ARCHIVE_DELETE_AFTER_BACKUP": "true",
                    "OPENAI_API_KEY": "stub",
                }
                value = defaults.get(name)

            if value is None:
                raise AttributeError(f"Configuration '{name}' not found in environment variables or defaults")
            
            # Преобразуем типы для числовых значений: сначала в int, потом в float
            if name.endswith('_SEC') or name.endswith('_TIMEOUT') or name.endswith('_DAYS'):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        pass
            
            self._cache[name] = value
        
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
