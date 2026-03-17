.PHONY: run test lint format build docker-build docker-run migrate help

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*##"}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Development ---

run: ## Start the development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# --- Testing ---

test: ## Run tests with coverage
	python -m pytest ../tests/ -x -q --cov=app --cov-report=term-missing --cov-fail-under=80

# --- Code Quality ---

lint: ## Run ruff linter
	uvx ruff check app/

format: ## Format code with ruff
	uvx ruff format app/

format-check: ## Check code formatting without modifying
	uvx ruff format --check app/

typecheck: ## Run mypy type checking
	mypy app/

check: lint format-check typecheck ## Run all code quality checks

# --- Database ---

migrate: ## Run database migrations
	alembic upgrade head

migrate-down: ## Rollback last migration
	alembic downgrade -1

# --- Docker ---

docker-build: ## Build Docker image
	docker build -t policy-chatbot:latest .

docker-run: ## Run Docker container locally
	docker run --rm -p 8000:8000 --env-file .env policy-chatbot:latest

# --- Celery ---

worker: ## Start Celery worker
	celery -A app.tasks.indexing:get_celery_app worker --loglevel=info
