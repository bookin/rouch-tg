# Pydantic AI Integration

## Проблема

Pydantic AI был установлен в `requirements.txt`, но **нигде не использовался**. Все "агенты" были обычными Python классами без реальной LLM интеграции.

## Решение

Создана правильная интеграция Pydantic AI с Groq согласно официальной документации.

## Новая структура

### 1. AI модуль (`backend/app/ai/`)

```
backend/app/ai/
├── __init__.py              # Экспорты
├── groq_agent.py            # Daily Manager AI agent
└── problem_agent.py         # Problem Solver AI agent
```

### 2. Groq Agent (`groq_agent.py`)

**Structured Output:**
```python
class DailyMessage(BaseModel):
    greeting: str
    motivation: str
    actions: list[str]
    closing: str
```

**Type-safe Agent:**
```python
agent = Agent(
    model=GroqModel(model_name=settings.GROQ_MODEL, api_key=settings.GROQ_API_KEY),
    deps_type=MessageContext,
    result_type=DailyMessage,
    system_prompt="..."
)
```

**Features:**
- ✅ Dependency injection через `MessageContext`
- ✅ Structured responses с Pydantic валидацией
- ✅ Dynamic system prompts через `@agent.system_prompt`
- ✅ Type-safe с полной типизацией

### 3. Problem Agent (`problem_agent.py`)

**Structured Output:**
```python
class ProblemSolution(BaseModel):
    problem_summary: str
    root_cause: str
    opposite_action: str
    practice_steps: list[str]
    expected_outcome: str
    timeline_days: int = 30
```

**Context with Knowledge Base:**
```python
class ProblemContext(BaseModel):
    problem_description: str
    user_name: str
    correlations: list[dict]
    concepts: list[dict]
```

## Соответствие документации

### ✅ Type Safety
```python
Agent[MessageContext, DailyMessage]  # Generic типизация
RunContext[MessageContext]            # Типизированный контекст
```

### ✅ Dependency Injection
```python
@agent.system_prompt
def add_context(ctx: RunContext[MessageContext]) -> str:
    context = ctx.deps  # Типизированный доступ
    return f"User: {context.user_name}"
```

### ✅ Structured Responses
```python
result = await agent.run(prompt, deps=context)
result.data  # Валидированный DailyMessage
```

### ✅ Model Support
```python
from pydantic_ai.models.groq import GroqModel

model = GroqModel(
    model_name="llama-3.1-70b-versatile",
    api_key=settings.GROQ_API_KEY
)
```

## Интеграция в существующий код

### Daily Manager
```python
# Было: только workflow
result = await self.daily_flow.morning_workflow(user)

# Стало: AI + fallback
try:
    ai_message = await generate_morning_message(...)
    # Format with AI output
except Exception:
    # Fallback to workflow
    result = await self.daily_flow.morning_workflow(user)
```

### Problem Solver
```python
# Было: только correlations lookup
correlations = await self.qdrant.search_correlation(problem)

# Стало: AI + knowledge base
correlations = await self.qdrant.search_correlation(problem)
concepts = await self.qdrant.search_concepts(problem)
solution = await ai_solve_problem(
    problem_description=problem,
    correlations=correlations,
    concepts=concepts
)
```

## Преимущества

1. **Type Safety**: Полная типизация всех inputs/outputs
2. **Validation**: Automatic validation через Pydantic
3. **Fallback**: Graceful degradation если AI недоступен
4. **Testability**: Легко мокировать через dependency injection
5. **Observability**: Pydantic Logfire интеграция (опционально)

## Использование

### Генерация утреннего сообщения
```python
from app.ai import generate_morning_message

message = await generate_morning_message(
    user_name="Anton",
    focus="wealth",
    streak_days=7,
    total_seeds=25
)

print(message.greeting)      # str
print(message.actions)       # list[str] (4 actions)
print(message.motivation)    # str
```

### Решение проблемы
```python
from app.ai.problem_agent import solve_problem

solution = await solve_problem(
    user_name="Anton",
    problem_description="Нестабильные доходы",
    correlations=[...],
    concepts=[...]
)

print(solution.root_cause)        # Кармическая причина
print(solution.opposite_action)   # Что делать вместо этого
print(solution.practice_steps)    # Конкретные шаги
```

## Environment Variables

Убедись что установлен `GROQ_API_KEY`:

```bash
# .env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-70b-versatile
```

## Тестирование

```python
# Mock dependencies для тестов
from pydantic_ai import Agent

async def test_agent():
    agent = get_groq_agent()
    
    context = MessageContext(
        user_name="Test",
        time_of_day="morning"
    )
    
    result = await agent.run("Generate message", deps=context)
    
    assert isinstance(result.data, DailyMessage)
    assert len(result.data.actions) > 0
```

## Опциональные улучшения

### 1. Logfire Integration
```python
from pydantic_ai import Agent
from pydantic_logfire import LogfireHandler

agent = Agent(
    model=model,
    result_type=DailyMessage,
    logfire=LogfireHandler()  # Automatic tracing
)
```

### 2. Streaming Responses
```python
async with agent.run_stream(prompt, deps=context) as stream:
    async for chunk in stream:
        print(chunk)
```

### 3. Tool Calling (для будущего)
```python
@agent.tool
async def search_quotes(ctx: RunContext[MessageContext], topic: str) -> str:
    """Search quotes from Qdrant"""
    return await ctx.deps.qdrant.search_quote(topic)
```

## Миграция завершена ✅

Pydantic AI правильно интегрирован с:
- ✅ Groq model
- ✅ Type-safe agents
- ✅ Structured outputs
- ✅ Dependency injection
- ✅ Graceful fallbacks
