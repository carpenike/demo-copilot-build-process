.PHONY: run test lint build docker-build clean

# Developer workflow commands for the Policy Chatbot

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80

lint:
	ruff check app/ tests/
	ruff format --check app/ tests/
	mypy app/

format:
	ruff check --fix app/ tests/
	ruff format app/ tests/

build:
	uv pip install -e ".[dev]"

docker-build:
	docker build -t policy-chatbot:latest .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env policy-chatbot:latest

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov
