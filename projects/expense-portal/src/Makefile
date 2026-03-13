.PHONY: install run test lint format migrate docker-build docker-run worker-ocr worker-notify worker-integ worker-beat

# --- Development ---

install:
	uv pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload --port 8000

# --- Testing ---

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

# --- Linting ---

lint:
	ruff check app/ tests/
	mypy app/

format:
	ruff check --fix app/ tests/
	ruff format app/ tests/

# --- Database ---

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

# --- Docker ---

docker-build:
	docker build -t expense-portal:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env expense-portal:latest

# --- Celery Workers ---

worker-ocr:
	celery -A app.tasks.celery_app:celery_app worker -Q ocr -c 2 --loglevel=info

worker-notify:
	celery -A app.tasks.celery_app:celery_app worker -Q notifications -c 2 --loglevel=info

worker-integ:
	celery -A app.tasks.celery_app:celery_app worker -Q integrations -c 1 --loglevel=info

worker-beat:
	celery -A app.tasks.celery_app:celery_app beat --loglevel=info
