# Rouch Karma Manager - Контрольный список тестирования

## 🧪 Pre-запуск проверка

### 1. Проверка окружения
- [ ] Docker установлен и запущен
- [ ] Docker Compose v2+ установлен
- [ ] Порты 5433, 6333, 6379, 8000, 5180 свободны
- [ ] Файл `.env` создан и заполнен

### 2. Проверка конфигурации `.env`
```bash
# Проверьте что все переменные заполнены:
cat .env
```
Должно содержать:
- [ ] `POSTGRES_PASSWORD` - не пустой
- [ ] `TELEGRAM_BOT_TOKEN` - от @BotFather
- [ ] `GROQ_API_KEY` - от console.groq.com
- [ ] `WEBAPP_URL` - ваш URL (ngrok или домен)

## 🚀 Тест запуска

### 3. Запуск сервисов
```bash
# Запустить все сервисы
docker-compose up -d

# Проверить что все поднялись
docker-compose ps
```
Должны быть running:
- [ ] rouch_postgres (healthy)
- [ ] rouch_qdrant
- [ ] rouch_redis
- [ ] rouch_backend
- [ ] rouch_frontend

### 4. Проверка логов
```bash
# Backend логи
docker-compose logs backend

# Должны увидеть:
# ✅ Database initialized
# ✅ Telegram bot started
# Uvicorn running on http://0.0.0.0:8000
```
- [ ] Нет ошибок при старте
- [ ] Database initialized
- [ ] Bot started

### 5. Инициализация базы знаний
```bash
docker-compose exec backend python -m app.knowledge.init_knowledge

# Должны увидеть:
# 🔄 Loading knowledge base...
# ✅ Loaded N knowledge items
# ✅ Indexed in Qdrant
# ✅ Test search successful
# 🎉 Initialization completed!
```
- [ ] База знаний загружена без ошибок
- [ ] Тест поиска прошёл успешно
- [ ] Видны количества по типам (correlations, concepts, quotes, etc.)

## 🤖 Тест Telegram Bot

### 6. Базовые команды

#### /start
- [ ] Бот отвечает приветствием
- [ ] Показывается кнопка "📱 Открыть приложение"
- [ ] Кнопка имеет WebApp (иконка ракеты)

#### /today
- [ ] Бот показывает список из 4 действий
- [ ] Действия разбиты по группам партнёров

#### /seed
- [ ] Бот просит описать посеянное семя
- [ ] После отправки текста - подтверждение с эмодзи 🌱
- [ ] Упоминается срок созревания (14-30 дней)

#### /done
- [ ] Бот просит номер или описание действия
- [ ] После отправки - подтверждение ✅
- [ ] Мотивационное сообщение

### 7. Диалоговый flow

**Тест /seed:**
1. [ ] Отправить `/seed`
2. [ ] Бот ждёт описание
3. [ ] Отправить "Помог коллеге с задачей"
4. [ ] Бот подтверждает и очищает состояние
5. [ ] Отправить любой текст - не должен обрабатываться как семя

**Тест /done:**
1. [ ] Отправить `/done`
2. [ ] Бот ждёт номер/описание
3. [ ] Отправить "1"
4. [ ] Бот подтверждает
5. [ ] Состояние очищено

## 📱 Тест Mini App

### 8. Открытие приложения
- [ ] Нажать кнопку "Открыть приложение"
- [ ] Открывается WebView
- [ ] Приложение загружается (не белый экран)
- [ ] Telegram цветовая схема применена

### 9. Dashboard (главная страница)
- [ ] Показывается приветствие с именем
- [ ] Карточка с цитатой отображается
- [ ] 4 действия на день показаны
- [ ] Каждое действие имеет: партнёр, описание, объяснение

### 10. Calendar (календарь)
- [ ] Открыть вкладку "📅 Календарь"
- [ ] Отображаются 4 карточки статистики (семена, практики, действия, стрик)
- [ ] Календарь рендерится (react-big-calendar)
- [ ] Можно переключать виды (месяц, неделя, день)
- [ ] Легенда внизу показывается

### 11. Навигация
- [ ] Bottom navigation bar видна
- [ ] 5 вкладок: Главная, Календарь, Партнёры, Журнал, Практики
- [ ] Активная вкладка подсвечена
- [ ] Переключение работает без перезагрузки
- [ ] URL меняется при переключении

### 12. Другие страницы
- [ ] Partners - открывается (пока заглушка)
- [ ] SeedJournal - открывается (пока заглушка)
- [ ] Practices - открывается (пока заглушка)

## 🔌 Тест API

### 13. Health checks
```bash
# Root endpoint
curl http://localhost:8000/
# Должен вернуть: {"app": "Rouch Karma Manager", "version": "0.1.0", "status": "running"}

# Health
curl http://localhost:8000/health
# Должен вернуть: {"status": "healthy"}

# API docs
open http://localhost:8000/docs
```
- [ ] Root endpoint работает
- [ ] Health check работает
- [ ] Swagger UI открывается

### 14. WebApp endpoints
```bash
# Daily quote
curl http://localhost:8000/api/quote/daily

# Daily actions
curl http://localhost:8000/api/daily/actions

# User profile
curl http://localhost:8000/api/me
```
- [ ] Quote возвращается с text, context, source
- [ ] Actions возвращает массив из 4 действий
- [ ] Me возвращает user profile

### 15. Calendar endpoints
```bash
# Calendar data
curl "http://localhost:8000/api/calendar/data?start_date=2026-01-01&end_date=2026-01-31"

# Calendar stats
curl "http://localhost:8000/api/calendar/stats?start_date=2026-01-01&end_date=2026-01-31"
```
- [ ] Data возвращает seeds, practices, partnerActions
- [ ] Stats возвращает counts и streak

## 🗄️ Тест баз данных

### 16. PostgreSQL
```bash
# Подключиться к БД
docker-compose exec postgres psql -U rouch_user -d rouch

# Проверить таблицы
\dt

# Должны быть таблицы:
# users, seeds, partners, partner_groups, practices, habits, habit_completions, partner_actions
```
- [ ] Все таблицы созданы
- [ ] Можно делать SELECT запросы

### 17. Qdrant
```bash
# Проверить health
curl http://localhost:6333/health

# Список коллекций
curl http://localhost:6333/collections
```
- [ ] Qdrant отвечает
- [ ] Коллекции созданы: correlations, concepts, quotes, practices, rules

### 18. Redis
```bash
# Подключиться к Redis
docker-compose exec redis redis-cli

# Проверить
PING
# Должно вернуть PONG
```
- [ ] Redis отвечает

## 🔍 Тест поиска (Qdrant)

### 19. Поиск корреляций
```python
# Через Python в контейнере
docker-compose exec backend python

from app.knowledge.qdrant_client import QdrantKnowledgeBase
from app.config import get_settings
import asyncio

async def test():
    settings = get_settings()
    qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
    
    # Поиск решения для проблемы
    results = await qdrant.search_correlation("нестабильные доходы")
    print(results)
    
    # Получить цитату
    quote = await qdrant.get_daily_quote()
    print(quote)

asyncio.run(test())
```
- [ ] Поиск корреляций работает
- [ ] Возвращаются релевантные результаты
- [ ] Цитаты загружаются

## 🧠 Тест AI компонентов

### 20. Daily Manager
```python
# Тест генерации утреннего сообщения
docker-compose exec backend python

from app.agents.daily_manager import DailyManagerAgent
from app.knowledge.qdrant_client import QdrantKnowledgeBase
from app.models.user import UserProfile
from app.config import get_settings
import asyncio

async def test():
    settings = get_settings()
    qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
    manager = DailyManagerAgent(qdrant)
    
    user = UserProfile(
        id=1,
        telegram_id=123,
        first_name="Test",
        occupation="employee",
        available_times=["morning"],
        daily_minutes=30
    )
    
    result = await manager.morning_message(user)
    print(result)

asyncio.run(test())
```
- [ ] Morning message генерируется
- [ ] Содержит quote, actions, message

## 📊 Тест производительности

### 21. Load test (опционально)
```bash
# Установить wrk или ab
# Apache Bench пример:
ab -n 1000 -c 10 http://localhost:8000/health
```
- [ ] API выдерживает нагрузку
- [ ] Latency приемлемая (<100ms для health)

## 🐛 Типичные проблемы и решения

### Backend не стартует
```bash
# Проверить логи
docker-compose logs backend

# Частые причины:
# - TELEGRAM_BOT_TOKEN не указан или неверный
# - Порт 8000 занят
# - PostgreSQL не готов (увеличить healthcheck timeout)
```

### База знаний не загружается
```bash
# Проверить что terms/ смонтирован
docker-compose exec backend ls -la data/knowledge_base

# Если пусто - проверить volumes в docker-compose.yml
# Должно быть: ./terms:/app/data/knowledge_base
```

### Frontend не открывается
```bash
# Проверить nginx
docker-compose logs frontend

# Проверить что порт 5180 доступен
curl http://localhost:5180
```

### Mini App белый экран
1. Проверить консоль браузера в Telegram
2. Убедиться что WEBAPP_URL указан правильно
3. Для ngrok - проверить что туннель активен
4. Проверить CORS в backend

### Qdrant не отвечает
```bash
# Перезапустить
docker-compose restart qdrant

# Проверить логи
docker-compose logs qdrant

# Очистить volume если нужно
docker-compose down -v
docker volume rm rouch_qdrant_data
docker-compose up -d
```

## ✅ Итоговый чеклист

После прохождения всех тестов:
- [ ] Все сервисы запущены и healthy
- [ ] База знаний загружена в Qdrant
- [ ] Telegram бот отвечает на все команды
- [ ] Mini App открывается и работает
- [ ] Навигация между страницами работает
- [ ] API endpoints возвращают данные
- [ ] Базы данных (PostgreSQL, Qdrant, Redis) доступны
- [ ] Логов без критических ошибок

**Проект готов к использованию! 🎉**

---

## 📝 Следующие шаги

После успешного тестирования:
1. Подключить реальных пользователей (см. PROJECT_REVIEW.md)
2. Заполнить базу данных тестовыми данными
3. Интегрировать GroqCloud LLM
4. Развернуть на production сервере
5. Настроить мониторинг

Создано: 2026-01-29
