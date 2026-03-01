.PHONY: help up down restart logs init-knowledge clean lint typecheck test

help:
	@echo "Rouch Karma Manager - Commands:"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make logs            - View logs"
	@echo "  make init-knowledge  - Initialize knowledge base in Qdrant"
	@echo "  make migrate-up      - Apply all pending database migrations"
	@echo "  make migrate-create  - Create a new migration revision (usage: make migrate-create m=\"message\")"
	@echo "  make clean-data      - Clear database volumes and re-initialize everything"
	@echo "  make full-reset      - Full purge: clear volumes, rebuild images without cache, and re-initialize"
	@echo "  make lint            - Run ruff linter on backend"
	@echo "  make typecheck       - Run mypy type checker on backend"
	@echo "  make test            - Run pytest on backend"

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

init-knowledge:
	docker-compose exec backend python -m app.knowledge.init_knowledge

migrate-up:
	docker-compose exec backend uv run alembic upgrade head

migrate-down:
	docker-compose exec backend uv run alembic downgrade -1


migrate-create:
	docker-compose exec backend uv run alembic revision --autogenerate -m "$(m)"

clean-data:
	docker-compose down -v
	docker-compose up -d
	@echo "Waiting for backend to start..."
	sleep 5
	$(MAKE) init-knowledge

full-reset:
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d
	@echo "Waiting for backend to start..."
	sleep 5
	$(MAKE) init-knowledge

clean: full-reset

lint:
	docker-compose exec backend uv run ruff check app/

lint-fix:
	docker-compose exec backend uv run ruff check --fix app/

typecheck:
	docker-compose exec backend uv run mypy app/ --ignore-missing-imports

test:
	docker-compose exec backend uv run pytest tests/ -v --tb=short
