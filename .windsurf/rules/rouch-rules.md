---
trigger: always_on
---

python - 3.12 / pep8

frontend - react 19.x / radix / tailwind / vite / typescript
backend - python 3.12 / pep8 / fastapi / alembic / postgresql

backend path - /Users/anton/Sites/rouch/backend
frontend path - /Users/anton/Sites/rouch/frontend
сервис запущен через `docker compose`

есть make команды для работы с alembic и просмотра логов, смотри команды в файле /Users/anton/Sites/rouch/Makefile

- не пытайся создавать фалы с миграциями, используй команду `make migrate-create -m "<description>"` для атоматического создания миграции после изминений схем в файлах моделей

- не пытайся сам применить миграции, используй команду `make migrate-up` для применения миграций

- обязательно смотри список skills перед выполнением задачи, если есть подходящие, используй их