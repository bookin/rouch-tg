# LangGraph Migration Guide

## Изменения в коде

### 1. Обновление версий (requirements.txt)

**Было:**
```txt
langgraph==0.0.40
langchain==0.1.0
langchain-groq==0.0.1
pydantic-ai==0.0.13
groq==0.4.1
```

**Стало:**
```txt
langgraph==0.2.45
langchain==0.3.0
langchain-groq==0.2.0
pydantic-ai==0.0.14
groq==0.11.0
```

### 2. API Changes в onboarding.py

**Было (устаревший API):**
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(OnboardingWorkflowState)
workflow.add_node("intro", self._ask_occupation)
# ... другие ноды

# Устаревший способ!
workflow.set_entry_point("intro")
workflow.add_edge("summary", END)
```

**Стало (современный API):**
```python
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(OnboardingWorkflowState)
workflow.add_node("intro", self._ask_occupation)
# ... другие ноды

# Современный способ с START константой
workflow.add_edge(START, "intro")
workflow.add_edge("summary", END)
```

## Ключевые изменения

### ❌ Удалено
- `workflow.set_entry_point()` - устаревший метод

### ✅ Добавлено
- `START` константа - используется вместо `set_entry_point()`
- `workflow.add_edge(START, "node_name")` - новый способ установки точки входа

## Преимущества нового API

1. **Единообразие**: все edge определяются через `add_edge()`
2. **Явность**: `START` и `END` - явные константы
3. **Гибкость**: проще строить сложные графы с несколькими точками входа
4. **Совместимость**: работает с новыми фичами LangGraph (checkpointing, streaming, human-in-the-loop)

## Проверка работы

Запустите тест:
```bash
cd backend
python -m app.workflows.test_langgraph
```

Должно вывести: `✅ LangGraph API test passed!`

## Дополнительные возможности (опционально)

### Retry Policy
```python
from langgraph.errors import RetryPolicy

workflow.add_node(
    "api_call",
    risky_node,
    retry=RetryPolicy(max_attempts=3)
)
```

### Max Concurrency
```python
result = workflow.invoke(
    initial_state,
    config={"configurable": {"max_concurrency": 10}}
)
```

### Checkpointing (для resumable workflows)
```python
from langgraph.checkpoint import MemorySaver

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

## Миграция завершена ✅

Все изменения совместимы с текущим кодом. Тесты пройдены.
