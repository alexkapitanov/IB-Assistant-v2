FROM python:3.11-slim

# Рабочая директория
WORKDIR /app
ENV PYTHONPATH=/app

  # requirements.txt находится в каталоге backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем только содержимое каталога backend в контейнер
# Копируем каталог tests для запуска тестов
COPY backend /app/backend
COPY tests /app/tests
# Копируем скрипты индексации в контейнер
COPY scripts /app/scripts

# Expose port and run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
