import asyncio
import logging
from collections import deque
from typing import Dict, Deque, AsyncGenerator

# Простой синглтон для хранения логов в памяти
class _LogStreamer:
    def __init__(self, max_log_size: int = 1000):
        """
        Инициализирует стример логов.
        :param max_log_size: Максимальное количество логов для хранения на одну сессию.
        """
        self.sessions: Dict[str, Deque[str]] = {}
        self.session_events: Dict[str, asyncio.Event] = {}
        self.max_log_size = max_log_size

    def _ensure_session_exists(self, session_id: str):
        """Убеждается, что для сессии существуют структуры данных."""
        if session_id not in self.sessions:
            self.sessions[session_id] = deque(maxlen=self.max_log_size)
            self.session_events[session_id] = asyncio.Event()

    def add_log(self, session_id: str, message: str):
        """
        Добавляет сообщение в лог для указанной сессии.
        """
        self._ensure_session_exists(session_id)
        
        self.sessions[session_id].append(message)
        # Уведомляем всех слушателей о новом логе
        self.session_events[session_id].set()

    async def log_generator(self, session_id: str) -> AsyncGenerator[str, None]:
        """
        Асинхронный генератор, который отдает логи для сессии.
        Отдает существующие логи, а затем ждет и отдает новые по мере их поступления.
        """
        self._ensure_session_exists(session_id)
        
        log_index = 0
        while True:
            # Отправляем все накопившиеся логи
            while log_index < len(self.sessions[session_id]):
                yield self.sessions[session_id][log_index]
                log_index += 1
            
            # Сбрасываем событие и ждем новых логов
            self.session_events[session_id].clear()
            await self.session_events[session_id].wait()

# Создаем единственный экземпляр стримера
log_streamer = _LogStreamer()


class SessionLogHandler(logging.Handler):
    """
    Обработчик для стандартного модуля logging, который перенаправляет
    логи в LogStreamer для конкретной сессии.
    """

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        # Устанавливаем простой форматтер, чтобы сообщения были читаемыми
        self.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    def emit(self, record):
        """
        Отправляет отформатированную запись лога в LogStreamer.
        """
        try:
            msg = self.format(record)
            log_streamer.add_log(self.session_id, msg)
        except Exception:
            self.handleError(record)

