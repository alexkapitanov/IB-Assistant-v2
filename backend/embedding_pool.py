import asyncio
import os
from openai import AsyncOpenAI

# --- Клиент OpenAI ---
# Используем Async-клиент для асинхронных операций
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "text-embedding-ada-002"  # Модель для эмбеддингов

# --- Очередь и воркер ---
# Очередь для задач на получение эмбеддингов
queue = asyncio.Queue()
BATCH_SIZE = 16  # Размер батча для отправки в API

async def worker():
    """
    Воркер, который накапливает задачи из очереди,
    обрабатывает их батчем и возвращает результаты.
    """
    while True:
        # Собираем задачи в батч
        batch = []
        try:
            # Ждем первую задачу с таймаутом, чтобы не блокироваться вечно
            first_item = await asyncio.wait_for(queue.get(), timeout=1.0)
            batch.append(first_item)
            # Быстро собираем остальные задачи, если они есть
            while len(batch) < BATCH_SIZE:
                batch.append(queue.get_nowait())
        except asyncio.TimeoutError:
            continue # Если задач нет, просто ждем дальше
        except asyncio.QueueEmpty:
            pass # Если очередь опустела, обрабатываем то, что есть

        if not batch:
            continue

        # Разделяем тексты и фьючерсы
        texts_to_embed = [text for text, _ in batch]
        futures = [fut for _, fut in batch]

        try:
            # Выполняем запрос к OpenAI API
            response = await client.embeddings.create(model=MODEL, input=texts_to_embed)
            vectors = response.data

            # Распределяем результаты по фьючерсам
            for future, vector in zip(futures, vectors):
                future.set_result(vector.embedding)
        except Exception as e:
            print(f"❌ Error processing embedding batch: {e}")
            # В случае ошибки завершаем все фьючерсы в батче с ошибкой
            for future in futures:
                if not future.done():
                    future.set_exception(e)

# --- Запуск воркера ---
# Глобальная переменная для отслеживания, запущен ли воркер
_worker_task = None

def _ensure_worker_started():
    """Проверяет, что воркер запущен. Если нет - запускает его."""
    global _worker_task
    if _worker_task is None or _worker_task.done():
        try:
            _worker_task = asyncio.create_task(worker())
        except RuntimeError:
            # Если нет активного event loop, воркер будет запущен при первом вызове
            pass

async def get_embedding_async(text: str) -> list[float]:
    """
    Асинхронная функция для получения эмбеддинга текста.
    Добавляет текст в очередь и ждет результата от воркера.
    """
    # Убираем лишние пробелы и переносы строк
    text = text.strip().replace("\n", " ")
    if not text:
        # Возвращаем пустой вектор для пустых строк
        return []

    # Убеждаемся, что воркер запущен
    _ensure_worker_started()

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    await queue.put((text, future))
    return await future
