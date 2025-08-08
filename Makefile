# Helpers
PY_DIRS=backend agents scripts

.PHONY: lint typecheck test sweep fix

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
sweep:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov coverage build dist
	rm -rf frontend/node_modules frontend/dist frontend/.vite frontend/coverage

# Auto-fix formatting and lint issues
fix:
	ruff check --fix .
	black .
	@if [ -d frontend ]; then \
	  cd frontend && npm install --silent && npx prettier --write . && npx eslint . --ext .js,.jsx,.ts,.tsx --fix ; \
	fi
