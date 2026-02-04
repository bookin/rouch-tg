# Быстрый старт Rouch Karma Manager

## Шаг 1: Подготовка

1. Убедитесь, что установлен Docker и Docker Compose
2. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

3. Отредактируйте `.env` и заполните:
   - `TELEGRAM_BOT_TOKEN` - получите у @BotFather в Telegram
   - `GROQ_API_KEY` - получите на https://console.groq.com
   - `POSTGRES_PASSWORD` - придумайте надежный пароль
   - `WEBAPP_URL` - URL где будет размещён Mini App (для локальной разработки можно использовать ngrok)

## Шаг 2: Запуск

```bash
# Запустить все сервисы
docker-compose up -d

# Или с помощью Makefile
make up
```

## Шаг 3: Инициализация базы знаний

После первого запуска загрузите базу знаний из `terms/` в Qdrant:

```bash
# Загрузить и проиндексировать базу знаний
docker-compose exec backend python -m app.knowledge.init_knowledge

# Или
make init-knowledge
```

Это загрузит:
- 29 корреляций проблема-решение
- 50+ концепций
- 100+ цитат
- 10+ практик
- 8 правил КМ + 4 закона кармы

## Шаг 4: Проверка

Откройте в браузере:
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:5180

## Шаг 5: Настройка Telegram Mini App

1. Откройте @BotFather в Telegram
2. Выберите своего бота
3. `/setmenubutton` - добавьте кнопку с URL вашего Mini App
4. `/setdomain` - укажите домен (для production)

## Шаг 6: Тестирование

1. Найдите своего бота в Telegram
2. Отправьте `/start`
3. Нажмите "Открыть приложение"

## Команды бота

- `/start` - Начать работу
- `/today` - Действия на сегодня
- `/seed` - Записать семя
- `/done` - Отметить выполненным
- `/app` - Открыть приложение

## Полезные команды

```bash
# Посмотреть логи
make logs

# Остановить
make down

# Перезапустить
make restart

# Очистка данных (PostgreSQL + Qdrant)
make clean-data

# Полная очистка и пересборка с нуля
make full-reset

# Миграции
make migrate-up
make migrate-create m="message"
```

## Разработка

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Бот не отвечает
- Проверьте `TELEGRAM_BOT_TOKEN` в `.env`
- Проверьте логи: `docker-compose logs backend`

### База знаний не загрузилась
- Убедитесь, что папка `terms/` смонтирована в контейнер
- Проверьте: `docker-compose exec backend ls -la data/knowledge_base`

### Mini App не открывается
- Проверьте `WEBAPP_URL` в `.env`
- Для локальной разработки используйте ngrok или похожий сервис

### Qdrant не работает
- Проверьте: `curl http://localhost:6333/health`
- Перезапустите: `docker-compose restart qdrant`

## Дальнейшие шаги

1. Настройте БД миграции (Alembic)
2. Добавьте реальных пользователей и данные
3. Кастомизируйте Daily Manager под свои нужды
4. Добавьте свои группы партнёров
5. Создайте свои практики

Наслаждайтесь! 🌱
