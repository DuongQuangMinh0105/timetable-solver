.PHONY: up down logs test lint

up: ; docker compose up --build

down: ; docker compose down

logs: ; docker compose logs -f

test: ; uv run pytest

lint: ; uv run ruff check . ; uv run ruff format --check . ; uv run mypy