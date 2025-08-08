FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app

# Установим зависимости заранее для кеширования
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Копируем исходники
COPY backend /app/backend

EXPOSE 8000 9310 50051

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
