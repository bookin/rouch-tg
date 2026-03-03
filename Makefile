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

mypy:
	docker-compose exec backend uv run mypy app/ --ignore-missing-imports

mypy-stats:
	@docker-compose exec backend uv run mypy app/ --ignore-missing-imports --show-error-codes --no-color-output \
	| awk '/error:/{total++; if (match($$0, /\[[^]]+\][[:space:]]*$$/)) { code=substr($$0, RSTART+1, RLENGTH-2); sub(/[[:space:]]*$$/, "", code); c[code]++ }} END{ printf "TOTAL: %d\n", total; for (k in c) printf "%d %s\n", c[k], k }' \
	| (IFS= read -r header; total=$${header#TOTAL: }; printf '\033[1;31m%s\033[0m\n' "$$header"; sort -nr | awk -v total="$$total" 'BEGIN{red=sprintf("%c[31m",27); yellow=sprintf("%c[33m",27); green=sprintf("%c[32m",27); reset=sprintf("%c[0m",27)} {n=$$1; pct=(total>0?100*n/total:0); color=(n>=50?red:(n>=15?yellow:green)); printf "%s%4d%s %-14s %5.1f%%\n", color, n, reset, $$2, pct }')

test:
	docker-compose exec backend uv run pytest tests/ -v --tb=short
