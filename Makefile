.PHONY: help up down restart logs init-knowledge clean

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
	docker-compose exec backend alembic upgrade head

migrate-create:
	docker-compose exec backend alembic revision --autogenerate -m "$(m)"

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
