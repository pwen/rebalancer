.PHONY: run db migrate upgrade downgrade docker-up docker-down

# Local dev (uses .env for DATABASE_URL)
run:
	uv run python app.py

db:
	docker compose up db -d

migrate:
	uv run flask db migrate -m "$(m)"

upgrade:
	uv run flask db upgrade

downgrade:
	uv run flask db downgrade

# Docker
docker-up:
	docker compose up --build -d

docker-up-logs:
	docker compose up --build

docker-down:
	docker compose down

docker-build:
	docker compose build --no-cache
