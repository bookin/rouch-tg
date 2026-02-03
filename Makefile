.PHONY: help up down restart logs init-knowledge clean

help:
	@echo "Rouch Karma Manager - Commands:"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make logs            - View logs"
	@echo "  make init-knowledge  - Initialize knowledge base in Qdrant"
	@echo "  make clean           - Clean volumes and rebuild"

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

migrate:
	docker-compose exec backend alembic upgrade head

clean:
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d
