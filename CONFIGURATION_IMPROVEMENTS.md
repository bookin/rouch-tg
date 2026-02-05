# Configuration & FastAPI Improvements

## ✅ Изменения в конфигурации (Pydantic Settings)

### 1. **Правильное использование Pydantic Settings**

#### ❌ Было (НЕПРАВИЛЬНО):
```python
class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "default")  # ❌ Не использует Pydantic!
    MORNING_HOUR: int = 7  # ❌ Нельзя настроить через .env
    
    class Config:
        env_file = ".env"
```

#### ✅ Стало (ПРАВИЛЬНО):
```python
class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="postgresql://...",
        description="PostgreSQL connection URL"
    )
    MORNING_HOUR: int = Field(
        default=7, 
        ge=0, 
        le=23,
        description="Morning message hour"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
```

**Преимущества:**
- ✅ Автоматическая валидация (MORNING_HOUR: 0-23)
- ✅ Типобезопасность
- ✅ Документация полей
- ✅ Не нужен `os.getenv()` - Pydantic сам читает .env

---

### 2. **Новые настройки в config.py**

#### Добавлено 40+ настроек:

```python
# Application
APP_NAME: str
APP_VERSION: str
DEBUG: bool
ENVIRONMENT: str  # development/production

# Database Pool
DB_POOL_SIZE: int = 5
DB_MAX_OVERFLOW: int = 10
DB_ECHO: bool = False

# Redis Cache TTL
REDIS_CACHE_TTL: int = 3600
REDIS_QUOTE_CACHE_TTL: int = 86400
REDIS_CORRELATION_CACHE_TTL: int = 7200

# Telegram Rate Limiting
TELEGRAM_RATE_LIMIT: int = 30
TELEGRAM_MESSAGE_DELAY: float = 0.05

# AI/LLM
GROQ_TEMPERATURE: float = 0.7
GROQ_MAX_TOKENS: int = 2048

# Scheduler
SCHEDULER_ENABLED: bool = True
SCHEDULER_CHECK_INTERVAL: int = 60

# Morning/Evening можно включить/выключить
MORNING_ENABLED: bool = True
EVENING_ENABLED: bool = True

# CORS (больше не "*")
CORS_ORIGINS: List[str]
CORS_ALLOW_CREDENTIALS: bool

# API
API_PREFIX: str = "/api"
DOCS_URL: str = "/docs"
REDOC_URL: str = "/redoc"

# Security
SECRET_KEY: str

# Logging
LOG_LEVEL: str = "INFO"
```

---

### 3. **Улучшенный .env.example**

#### ❌ Было:
```env
DATABASE_URL=postgresql://...
TELEGRAM_BOT_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_api_key
```

#### ✅ Стало:
```env
# ===========================================
# Application Settings
# ===========================================
APP_NAME="Rouch Karma Manager"
DEBUG=false
ENVIRONMENT=production

# ===========================================
# Database (PostgreSQL)
# ===========================================
DATABASE_URL=postgresql://...
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# ===========================================
# Knowledge Base
# ===========================================
KNOWLEDGE_BASE_PATH=data/knowledge_base

# ===========================================
# Problem Solver Agent tuning
# ===========================================
PROBLEM_SOLVER_CORRELATIONS_LIMIT=3
PROBLEM_SOLVER_CONCEPTS_LIMIT=2
PROBLEM_SOLVER_RULES_LIMIT=3
PROBLEM_SOLVER_PRACTICES_LIMIT=3

# ===========================================
# Scheduler Settings
# ===========================================
SCHEDULER_ENABLED=true
SCHEDULER_CHECK_INTERVAL=60

# Morning Messages (user's local time)
MORNING_ENABLED=true
MORNING_HOUR=7
MORNING_MINUTE=30

# Evening Messages (user's local time)
EVENING_ENABLED=true
EVENING_HOUR=21
EVENING_MINUTE=0

# ===========================================
# CORS Settings
# ===========================================
CORS_ORIGINS=["http://localhost:5180","https://your-domain.com"]

# ... и еще 30+ настроек
```

**Преимущества:**
- ✅ Структурированный файл с разделами
- ✅ Комментарии для каждой секции
- ✅ Все настройки в одном месте
- ✅ Легко редактировать

---

## ✅ Изменения в FastAPI

### 4. **Правильная конфигурация CORS**

#### ❌ Было (НЕБЕЗОПАСНО):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Разрешено ВСЁ!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### ✅ Стало (БЕЗОПАСНО):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ✅ Только разрешенные домены
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # ✅ Конкретные методы
    allow_headers=["*"],
)
```

---

### 5. **FastAPI app из settings**

#### ❌ Было:
```python
app = FastAPI(
    title="Rouch Karma Manager API",
    version="0.1.0",
    lifespan=lifespan
)
```

#### ✅ Стало:
```python
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=settings.DOCS_URL if settings.ENVIRONMENT != "production" else None,
    redoc_url=settings.REDOC_URL if settings.ENVIRONMENT != "production" else None,
    debug=settings.DEBUG
)
```

**Что это дает:**
- ✅ В production можно отключить `/docs` и `/redoc`
- ✅ Версия из .env
- ✅ Debug mode настраивается

---

### 6. **API Endpoints с правильной документацией**

#### ❌ Было:
```python
@router.get("/me")
async def get_user_profile(user = Depends(get_current_user)):
    return user
```

#### ✅ Стало:
```python
@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get user profile",
    description="Retrieve the current authenticated user's profile information"
)
async def get_user_profile(user: UserProfile = Depends(get_current_user)):
    """Get current user profile with all settings and progress"""
    return user
```

**Swagger/ReDoc теперь показывает:**
- ✅ Summary и description
- ✅ Response model (схема ответа)
- ✅ Типы данных

---

### 7. **Правильные HTTP Status Codes**

#### ❌ Было:
```python
@router.post("/seeds")
async def create_seed(seed: Seed):
    # ... create seed
    return created_seed  # ❌ Возвращает 200 вместо 201
```

#### ✅ Стало:
```python
@router.post(
    "/seeds",
    response_model=Seed,
    status_code=status.HTTP_201_CREATED,  # ✅ 201 Created
    summary="Plant a new seed"
)
async def create_seed(seed: Seed):
    # ... create seed
    return created_seed
```

---

### 8. **Response Models**

Добавлены Pydantic модели для ответов:

```python
class CalendarEvent(BaseModel):
    """Calendar event model"""
    id: str
    title: str
    start: datetime
    end: datetime
    type: str
    description: str = ""


class CalendarStats(BaseModel):
    """Calendar statistics model"""
    total_seeds: int
    completed_habits: int
    active_practices: int
    partner_actions: int
    streak_days: int
```

**Использование:**
```python
@router.get("/stats", response_model=CalendarStats)
async def get_calendar_stats():
    return {
        "total_seeds": 100,
        "completed_habits": 50,
        # ...
    }
```

---

### 9. **Query Parameters с описанием**

#### ❌ Было:
```python
@router.get("/data")
async def get_calendar_data(
    start_date: date,
    end_date: date
):
    pass
```

#### ✅ Стало:
```python
@router.get("/data")
async def get_calendar_data(
    start_date: date = Query(..., description="Start date for calendar range"),
    end_date: date = Query(..., description="End date for calendar range")
):
    pass
```

---

### 10. **Tags для группировки в документации**

```python
router = APIRouter(prefix="/api", tags=["Mini App"])  # ✅ Группа "Mini App"
router = APIRouter(prefix="/api/calendar", tags=["Calendar"])  # ✅ Группа "Calendar"

@app.get("/", tags=["System"])  # ✅ Группа "System"
@app.get("/health", tags=["System"])
```

**В Swagger теперь 3 секции:**
- 📱 Mini App
- 📅 Calendar
- ⚙️ System

---

## 📊 Сравнение До/После

| Аспект | До | После |
|--------|----|----|
| **Настройки** | 14 параметров | 40+ параметров |
| **Валидация** | ❌ Нет | ✅ Pydantic валидация |
| **CORS** | ❌ `allow_origins=["*"]` | ✅ Конкретные домены |
| **Docs в production** | ✅ Доступны | ✅ Можно отключить |
| **Response models** | ❌ Нет | ✅ Везде |
| **Status codes** | ⚠️ Только 200 | ✅ 200, 201, 404, etc |
| **API docs** | ⚠️ Минимальные | ✅ Полные описания |
| **Type safety** | ⚠️ Частичная | ✅ Полная |
| **.env** | ⚠️ Плоский | ✅ Структурированный |

---

## 🚀 Как использовать

### 1. Настройка через .env:

```env
# Можно легко переключать режимы
ENVIRONMENT=development
DEBUG=true
DOCS_URL=/docs

# В production
ENVIRONMENT=production
DEBUG=false
DOCS_URL=null  # Docs отключены
```

### 2. Настройка времени сообщений:

```env
# Отправлять в 6:00 и 22:30
MORNING_HOUR=6
MORNING_MINUTE=0
EVENING_HOUR=22
EVENING_MINUTE=30

# Или отключить утренние сообщения
MORNING_ENABLED=false
```

### 3. Настройка CORS:

```env
# Development
CORS_ORIGINS=["http://localhost:5180","http://localhost:3000"]

# Production
CORS_ORIGINS=["https://rouch.app","https://www.rouch.app"]
```

### 4. Database pooling:

```env
# Для больших нагрузок
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Для разработки с логами
DB_ECHO=true
```

---

## ✅ Итого улучшено

### Config (Pydantic Settings):
1. ✅ Убран `os.getenv()` - Pydantic сам читает .env
2. ✅ Добавлена валидация (ge, le)
3. ✅ Добавлены описания полей
4. ✅ Современный `model_config` вместо `class Config`
5. ✅ 40+ настраиваемых параметров

### FastAPI:
1. ✅ CORS безопасность
2. ✅ Response models везде
3. ✅ Правильные status codes
4. ✅ Полная документация endpoints
5. ✅ Tags для группировки
6. ✅ Query params с описанием
7. ✅ Docs можно отключить в production

### .env.example:
1. ✅ Структурирован по разделам
2. ✅ Комментарии для каждой секции
3. ✅ Все возможные настройки
4. ✅ Примеры значений

**Проект теперь соответствует best practices FastAPI и Pydantic!** 🎉
