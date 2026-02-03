# SQLAlchemy & Alembic - Критичные исправления

## Найденные проблемы (по документации)

### 1. ❌ Устаревший `declarative_base()` (SQLAlchemy 1.x API)

**Было:**
```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

**Проблема:** SQLAlchemy 2.0 рекомендует `DeclarativeBase`

**Исправлено:**
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass
```

### 2. ❌ Alembic НЕ настроен для Async

**Было:**
```python
def run_migrations_online():
    connectable = engine_from_config(...)  # Sync engine!
    with connectable.connect() as connection:
        context.configure(connection=connection)
```

**Проблема:** Используется синхронный engine, но БД работает через asyncpg!

**Исправлено:**
```python
def run_migrations_online():
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    
    async def run_async_migrations():
        connectable = create_async_engine(url)
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    
    asyncio.run(run_async_migrations())
```

### 3. ❌ Неправильные JSON defaults

**Было:**
```python
available_times = Column(JSON, default=list)
current_habits = Column(JSON, default=list)
```

**Проблема:** `default=list` создает один список для всех записей! (mutable default)

**Исправлено:**
```python
available_times = Column(JSON, default=lambda: [])
current_habits = Column(JSON, default=lambda: [])
```

### 4. ❌ Отсутствие pool настроек

**Было:**
```python
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
```

**Проблема:** 
- `future=True` устарело в 2.0
- Нет pool настроек
- echo=True в production

**Исправлено:**
```python
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Production
    pool_pre_ping=True,  # Verify connections
    pool_size=5,
    max_overflow=10
)
```

### 5. ❌ N+1 Query Problem в relationships

**Было:**
```python
seeds = relationship("SeedDB", back_populates="user")
```

**Проблема:** Lazy loading вызывает N+1 queries

**Исправлено:**
```python
seeds = relationship("SeedDB", back_populates="user", lazy="selectin")
```

### 6. ❌ Отсутствие CASCADE и индексов

**Было:**
```python
user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
```

**Проблема:**
- Нет CASCADE delete
- Нет индексов на часто запрашиваемых полях

**Исправлено:**
```python
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), 
                 nullable=False, index=True)
timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
action_type = Column(String, nullable=False, index=True)
```

### 7. ❌ Отсутствие ORDER BY в CRUD

**Было:**
```python
select(SeedDB).where(SeedDB.user_id == user_id).limit(limit)
```

**Проблема:** Без ORDER BY результат непредсказуем

**Исправлено:**
```python
select(SeedDB)
    .where(SeedDB.user_id == user_id)
    .order_by(SeedDB.timestamp.desc())
    .limit(limit)
```

### 8. ❌ autoflush в session

**Было:**
```python
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

**Проблема:** autoflush=True по умолчанию может вызывать лишние флуши

**Исправлено:**
```python
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False  # Explicit control
)
```

## Соответствие документации SQLAlchemy 2.0

| Требование | Было | Стало |
|------------|------|-------|
| **DeclarativeBase** | ❌ declarative_base() | ✅ DeclarativeBase |
| **Async Engine** | ⚠️ Partial | ✅ Full async |
| **Pool Settings** | ❌ None | ✅ Configured |
| **Indexes** | ❌ Missing | ✅ Added |
| **CASCADE** | ❌ Missing | ✅ Added |
| **Lazy Loading** | ⚠️ Default | ✅ selectin |
| **JSON Defaults** | ❌ Mutable | ✅ Lambda |
| **ORDER BY** | ❌ Missing | ✅ Added |

## Соответствие документации Alembic

| Требование | Было | Стало |
|------------|------|-------|
| **Async Support** | ❌ Sync only | ✅ Async |
| **target_metadata** | ✅ Correct | ✅ Correct |
| **compare_type** | ❌ Missing | ✅ Added |
| **compare_server_default** | ❌ Missing | ✅ Added |

## Best Practices применены

### 1. Connection Pooling
```python
pool_pre_ping=True  # Проверка соединений перед использованием
pool_size=5         # Базовый размер пула
max_overflow=10     # Максимум дополнительных соединений
```

### 2. Eager Loading
```python
lazy="selectin"  # Эффективная загрузка связей
```

### 3. Indexes
```python
user_id = Column(..., index=True)      # Для WHERE
timestamp = Column(..., index=True)    # Для ORDER BY
action_type = Column(..., index=True)  # Для фильтров
```

### 4. Foreign Key Constraints
```python
ForeignKey("users.id", ondelete="CASCADE")  # Каскадное удаление
ForeignKey("partners.id", ondelete="SET NULL")  # Null при удалении
```

### 5. Query Optimization
```python
.order_by(SeedDB.timestamp.desc())  # Явная сортировка
.limit(1)  # Для unique queries
```

## Создание миграций

### 1. Автогенерация
```bash
alembic revision --autogenerate -m "Initial migration"
```

### 2. Применение
```bash
alembic upgrade head
```

### 3. Откат
```bash
alembic downgrade -1
```

### 4. История
```bash
alembic history
alembic current
```

## Проверка

### 1. Async работает
```python
# engine использует asyncpg
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

### 2. Alembic async
```python
# env.py использует async engine
async with connectable.connect() as connection:
    await connection.run_sync(do_run_migrations)
```

### 3. Индексы созданы
```sql
-- После миграции
SHOW INDEX FROM seeds;
-- Должны быть индексы на user_id, timestamp, action_type
```

### 4. CASCADE работает
```sql
-- При удалении пользователя
DELETE FROM users WHERE id = 1;
-- Автоматически удалятся все seeds
```

## Оптимизации производительности

### До:
- N+1 queries при загрузке relationships
- Отсутствие индексов = full table scan
- Mutable defaults = shared state bugs
- Sync alembic с async БД = несоответствие

### После:
- ✅ Eager loading через selectin
- ✅ Индексы на всех частых запросах
- ✅ Lambda defaults для JSON
- ✅ Полностью async stack

## Итого исправлено: 8 критичных проблем

1. ✅ Modern SQLAlchemy 2.0 API
2. ✅ Async Alembic integration
3. ✅ Правильные JSON defaults
4. ✅ Connection pooling
5. ✅ Eager loading для relationships
6. ✅ CASCADE constraints
7. ✅ Индексы для оптимизации
8. ✅ ORDER BY в queries

**База данных полностью оптимизирована!** 🚀
