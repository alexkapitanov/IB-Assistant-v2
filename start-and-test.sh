#!/usr/bin/env bash
set -euo pipefail

export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

# Build & up
docker-compose up -d --build

# Wait for backend health
printf "Waiting for backend health"
for i in {1..30}; do
  if curl -fsS http://localhost:8000/health >/dev/null; then
    echo "\nBackend is healthy"; break
  fi
  printf '.'; sleep 2
  if [[ $i -eq 30 ]]; then echo "\nBackend healthcheck timeout"; exit 1; fi
done

# Run smoke test via test_runner if present
if [[ -f test_runner.py ]]; then
  echo "Running smoke test..."
  python3 test_runner.py "Что такое DLP-система и какие функции она выполняет?" || true
fi

# Run pytest
if [[ -f pytest.ini ]] || [[ -d tests ]]; then
  echo "Running pytest..."
  pytest -q || true
fi
