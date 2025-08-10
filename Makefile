start-prod:
	@if [ -z "$$OPENAI_API_KEY" ]; then echo "ERROR: OPENAI_API_KEY is required"; exit 1; fi
	DISABLE_WEB_SEARCH=0 TESTING=false docker compose --profile prod up -d redis qdrant minio backend frontend grafana prometheus
test-e2e:
	OPENAI_BASE_URL=http://fake-openai:8081/v1 OPENAI_API_KEY=test_key_e2e DISABLE_WEB_SEARCH=1 E2E_MODE=1 docker compose --profile test up -d fake-openai redis qdrant backend
	# Wait for backend health
	for i in $$(seq 1 30); do \
		if curl -sf http://localhost:8000/health >/dev/null; then \
			echo "backend is healthy"; \
			break; \
		fi; \
		sleep 1; \
	done
	# WS readiness probe
	python3 scripts/ws_probe.py
	pytest -q tests/e2e_*_test.py
	docker compose --profile test down
# Helpers
PY_DIRS=backend agents scripts

.PHONY: lint typecheck test sweep sweep-clean fix archlint

# Lint Python (ruff + black) and Frontend (eslint + prettier)
lint:
	ruff check .
	black --check .
	@if [ -d frontend ]; then \
	  cd frontend && npm install --silent && npx eslint . --ext .js,.jsx,.ts,.tsx && npx prettier --check . ; \
	fi

# Type checking for Python (mypy) and Frontend (tsc)
typecheck:
	mypy $(PY_DIRS)
	@if [ -d frontend ]; then \
	  cd frontend && npm install --silent && npx tsc --noEmit ; \
	fi

# Run tests
test:
	pytest -q

# Clean caches and build artifacts
# Dry-run repository sweep
sweep:
	python3 tools/repo_sweep.py

# Clean caches and build artifacts (destructive)
sweep-clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov coverage build dist
	rm -rf frontend/node_modules frontend/dist frontend/.vite frontend/coverage

# Auto-fix formatting and lint issues
fix:
	ruff check --fix .
	black .
	@if [ -d frontend ]; then \
	  cd frontend && npm install --silent && npx prettier --write . && npx eslint . --ext .js,.jsx,.ts,.tsx --fix ; \
	fi

# Architecture lint checks
archlint:
	python3 tools/check_models.py
	python3 tools/check_forbidden_paths.py
	python3 tools/check_compose.py
