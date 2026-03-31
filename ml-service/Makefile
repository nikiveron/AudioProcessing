.PHONY: help install dev lint format test run docker-build docker-run clean

help:
	@echo "ML Audio Processor - Available commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Install with dev dependencies"
	@echo "  make lint         - Run Ruff linter"
	@echo "  make format       - Format code with Black"
	@echo "  make lint-fix     - Fix linting issues"
	@echo "  make test         - Run tests"
	@echo "  make run          - Run the service"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make clean        - Clean temporary files"

install:
	poetry install --no-dev

dev:
	poetry install

lint:
	poetry run ruff check app/

format:
	poetry run black app/

lint-fix:
	poetry run ruff check app/ --fix

test:
	poetry run pytest --cov=app

run:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t ml-service:latest .

docker-run:
	docker run -e KAFKA_BOOTSTRAP=kafka:9092 \
		-e MINIO_ENDPOINT=minio:9000 \
		-p 8000:8000 ml-service:latest

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov dist build *.egg-info

.DEFAULT_GOAL := help
