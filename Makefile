#.PHONY: docker docker-prod dev api-dev api-prod format lint generate doc doc-full test test-cov test-ci pre-push

# App runtime

install:
	poetry lock
	poetry install
	cd frontend && npm install
docker:
	docker compose --profile dev up

docker-prod:
	docker compose --profile prod up

dev:
	cd frontend && npm run dev

api-dev:
	ENV=dev poetry run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

api-prod:
	ENV=prod poetry run uvicorn backend.app.main:app

format:
	poetry run black backend/app
	poetry run isort backend/app

lint:
	poetry run ruff check backend/app

# Docs
generate:
	./tools/ci/run_all_ci_tasks.sh

doc:
	poetry run mkdocs build --strict


# Tests
test:
	poetry run pytest

test-cov:
	poetry run pytest --cov=backend --cov-report=term-missing -m "not system"

test-ci:
	poetry run pytest -m "not system" --cov=backend --cov-report=xml

pre-push: lint format test-cov