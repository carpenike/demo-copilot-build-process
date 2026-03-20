.PHONY: run test lint format type-check build docker-build clean

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest ../tests/ -x -q --cov=app --cov-fail-under=80

lint:
	uvx ruff check app/
	uvx ruff format --check app/

format:
	uvx ruff format app/

type-check:
	mypy app/

build: lint type-check test

docker-build:
	docker build -t policy-chatbot:latest .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache .coverage htmlcov
