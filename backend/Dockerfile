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

# Устанавливаем wget и grpc_health_probe
RUN apt-get update && apt-get install -y wget \
 && wget -qO /usr/local/bin/grpc_health_probe \
     https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.11/grpc_health_probe-linux-amd64 \
 && chmod +x /usr/local/bin/grpc_health_probe \
 && apt-get clean

# Expose port and run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
