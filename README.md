# Rouch Karma Manager

Telegram-бот с Mini App для кармического менеджмента на основе учений "Алмазного огранщика" и кармического менеджмента.

## Архитектура

- **Backend**: FastAPI + PydanticAI + LangGraph + GroqCloud
- **Frontend**: React + Vite + Telegram Mini App SDK + react-big-calendar
- **Databases**: PostgreSQL, Qdrant (векторная БД), Redis
- **Deploy**: Docker Compose

## Быстрый старт

### 1. Настройка окружения

Скопируйте `.env.example` в `.env` и заполните переменные:

```bash
cp .env.example .env
```

Необходимые переменные:
- `POSTGRES_PASSWORD` - пароль для PostgreSQL
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота от @BotFather
- `GROQ_API_KEY` - API ключ от GroqCloud
- `WEBAPP_URL` - URL вашего Mini App

### 2. Запуск проекта

```bash
docker-compose up -d
```

### 3. Инициализация базы знаний

После первого запуска нужно загрузить базу знаний из `terms/` в Qdrant:

```bash
docker-compose exec backend python -m app.knowledge.init_knowledge
```

Это загрузит и проиндексирует:
- Корреляции из `diamond-correlations-table.md` (29 проблем-решений)
- Концепции из `diamond-concepts.md` (пустота, отпечатки, правила)
- Цитаты из `*-quotes.md`
- Практики из `yoga-*.md` и `karma-concepts.md`
- 8 правил КМ и 4 закона кармы

### 4. Миграции БД
 
 ```bash
-docker-compose exec backend alembic upgrade head
+make migrate-up
 ```
+
+Создание новой миграции (после изменения моделей):
+```bash
+make migrate-create m="название_миграции"
+```
+
+### 5. Обслуживание и сброс
+
+Если нужно очистить все данные (PostgreSQL, Qdrant) и начать с нуля:
+```bash
+make clean-data
+```
+
+Полный сброс (очистка данных + пересборка контейнеров без кеша):
+```bash
+make full-reset
+```
 
-### 5. Готово!
+### 6. Готово!
 Бот запущен и готов к работе. Найдите его в Telegram и отправьте `/start`.

## Разработка

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Структура проекта

```
rouch/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── agents/            # AI агенты (Daily Manager, Problem Solver)
│   │   ├── knowledge/         # Загрузка и работа с базой знаний
│   │   ├── models/            # Pydantic модели
│   │   ├── workflows/         # LangGraph workflows
│   │   ├── api/               # API endpoints + Telegram Bot
│   │   ├── scheduler/         # Крон для утренних/вечерних сообщений
│   │   └── main.py           # FastAPI приложение
│   └── data/
│       └── knowledge_base/    # Копия terms/ (монтируется из Docker)
│
├── frontend/                   # React Mini App
│   ├── src/
│   │   ├── pages/             # Страницы (Dashboard, Calendar, etc.)
│   │   ├── components/        # Компоненты
│   │   ├── hooks/             # React hooks (useTelegram, useCalendarData)
│   │   └── api/               # API клиент
│   └── nginx.conf
│
├── terms/                      # База знаний (парсится в Qdrant)
│   ├── diamond-concepts.md
│   ├── diamond-correlations-table.md
│   ├── karma-concepts.md
│   └── ...
│
└── docker-compose.yml
```

## Основные функции

### 1. Telegram Bot
- `/start` - Начать работу с ботом
- `/today` - Быстрый список действий на сегодня
- `/seed` - Быстро записать посеянное семя
- `/done` - Отметить действие выполненным
- `/app` - Открыть Mini App

### 2. Mini App

**📱 Dashboard**
- Цитата дня из базы знаний
- 4 персонализированных действия на день (сохраняются на день)
- Возможность отмечать действия выполненными
- Быстрый переход в Журнал Семян для записи выполненного действия
- Прогресс (стрик, количество семян)
- Сообщения от кармического менеджера

**📅 Календарь**
- Визуализация всех событий: семена, практики, действия с партнёрами
- Статистика за период (количество семян, практик, стрик)
- Просмотр по месяцам/неделям/дням
- Цветовая индикация типов событий

**👥 Партнёры**
- 4 дефолтные группы: Коллеги, Клиенты, Поставщики, Мир
- Создание кастомных групп
- Метод Жампы (отслеживание предпочтений)
- История взаимодействий

**🌱 Журнал семян**
- Запись посеянных семян
- Факторы силы (намерение, эмоция, понимание)
- Прогноз созревания (14-30 дней)
- Отслеживание результатов

**🧘 Практики**
- Йога (10 упражнений тибетской сердечной йоги)
- Медитация (созерцание смерти, работа с гневом)
- Этика (5 норм поведения)
- Рекомендации на основе проблем и ограничений

### 3. "Живой" менеджер

Автоматические сообщения 2 раза в день:

**Утро (7:30)**
- Мотивация и цитата
- 4 действия на день
- Упоминание прогресса

**Вечер (21:00)**
- Рефлексия дня
- Вечерняя цитата
- Поддержка и напоминания

### 4. Решение проблем

Поиск корреляций в базе знаний:
- Описание проблемы → поиск в Qdrant
- Кармическая причина
- Практическое решение
- План действий на 30 дней

## База знаний

Вся база знаний из `terms/` индексируется в Qdrant для семантического поиска:

- **Корреляции**: 29 проблем с решениями (финансы, отношения, здоровье)
- **Концепции**: Пустота, отпечатки, 4 правила, 7 качеств
- **Цитаты**: 100+ цитат с контекстом и тегами
- **Практики**: Йога, медитация, этика
- **Правила**: 8 правил КМ, 4 закона кармы

## API Endpoints

### Webapp
- `GET /api/me` - Профиль пользователя
- `GET /api/daily/actions` - 4 действия на день
- `GET /api/quote/daily` - Цитата дня
- `GET /api/seeds` - Список семян
- `POST /api/seeds` - Создать семя
- `GET /api/partners` - Список партнёров
- `GET /api/practices` - Доступные практики

### Calendar
- `GET /api/calendar/data` - События за период
- `GET /api/calendar/stats` - Статистика за период

## Технологии

**Backend:**
- FastAPI - веб-фреймворк
- PydanticAI - структурированные данные
- LangGraph - AI workflows
- GroqCloud - LLM inference (llama-3.1-70b)
- Qdrant - векторная база данных
- PostgreSQL - реляционная БД
- Redis - кеш
- aiogram - Telegram Bot API

**Frontend:**
- React 18
- TypeScript
- Vite
- react-big-calendar - календарь
- Telegram Mini App SDK
- React Router

## Roadmap

- [ ] Database schema и migrations (Alembic)
- [ ] Настоящая аутентификация через Telegram WebApp
- [ ] LLM генерация персонализированных действий
- [ ] Proper embedding model (sentence-transformers)
- [ ] Push-уведомления через Telegram
- [ ] Экспорт данных
- [ ] Шаринг прогресса
- [ ] Групповая карма для команд

## Лицензия

MIT

## Контакты

Основано на учениях:
- "Алмазный огранщик" - Геше Майкл Роуч
- "Кармический менеджмент" - Геше Майкл Роуч
- "Тибетская книга йоги" - Геше Майкл Роуч
