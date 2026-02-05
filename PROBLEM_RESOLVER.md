# Problem Resolver / ProblemSolverAgent

## 1. Общее описание

`ProblemSolverAgent` ("problem resolver") — это слой, который отвечает за разбор пользовательской проблемы и выдачу структурированного кармического плана.

Он объединяет:
- **интерфейсы** Telegram‑бота и WebApp (Mini App),
- **векторную базу знаний Qdrant** (корреляции, концепции, правила, практики),
- **PydanticAI‑агента** (`ProblemAgent`) поверх LLM,
- **резервный workflow** (`ProblemSolverWorkflow`) на случай ошибок LLM/Qdrant.

Ключевая цель — по тексту проблемы пользователя построить:
- понятный разбор корня проблемы (по отпечаткам и качествам),
- план STOP/START/GROW,
- 30‑дневный список шагов,
- дополнительные подсказки (кларити, кофейная медитация, партнёры, Q&A‑режим).

---

## 2. Основные файлы и классы

- Backend, слой API:
  - `backend/app/api/webapp.py`
    - `POST /api/problem/solve` — входная точка WebApp для решения проблемы.
    - `ProblemSolveRequest` / `ProblemSolveResponse` — модели запроса/ответа.
  - `backend/app/api/bot.py`
    - хэндлеры Telegram‑бота для проблем (`ProblemState`, `process_problem_description` и Q&A‑режим).

- Backend, слой агента:
  - `backend/app/agents/problem_solver.py`
    - класс `ProblemSolverAgent`;
    - метод `analyze_problem(user, problem)` — основной вход;
    - метод `get_practice_recommendation` — отдельная выдача практик.

- Backend, слой ИИ‑агента:
  - `backend/app/ai/problem_agent.py`
    - класс `ProblemContext` — вход для PydanticAI‑агента;
    - класс `ProblemSolution` — типизированный выход агента;
    - функция `create_problem_agent()` — создание `Agent[ProblemContext, ProblemSolution]` с системным промптом;
    - функция `solve_problem(...)` — обёртка над `agent.run(...)`.

- Backend, слой знаний:
  - `backend/app/knowledge/loader.py`
    - `KnowledgeLoader` — парсит markdown‑файлы из `terms/`;
    - `_load_correlations`, `_load_extended_correlations` — загружают корреляции и обогащённые поля (`sphere`, `imprint`, `quality`, `partners`, `principle`, `number`, `problem_type`, `source_type`).
  - `backend/app/knowledge/qdrant.py`
    - `QdrantKnowledgeBase` — клиент Qdrant;
    - `search_correlation`, `search_concepts`, `search_practice`, `search_rules`.

- Frontend:
  - `frontend/src/api/client.ts`
    - `solveProblem(problem: string)` — вызов `/api/problem/solve`.
  - `frontend/src/pages/Problem.tsx`
    - UI для постановки проблемы и отображения плана;
    - поддержка Q&A‑режима и дополнительных слоёв (rules/practices).

---

## 3. Поток данных end‑to‑end

### 3.1. WebApp (Mini App)

1. Пользователь вводит текст проблемы на странице `Problem.tsx` и нажимает «Найти решение».
2. Frontend вызывает `solveProblem(problem)` → `POST /api/problem/solve`.
3. Эндпоинт `/problem/solve` в `webapp.py`:
   - получает текущего пользователя (`get_current_user`);
   - создаёт `QdrantKnowledgeBase(settings.QDRANT_URL)`;
   - создаёт `ProblemSolverAgent(qdrant)`;
   - вызывает `agent.analyze_problem(user, payload.problem)`.
4. `ProblemSolverAgent.analyze_problem`:
   - ищет корреляции/концепции/правила/практики в Qdrant;
   - собирает `ProblemContext` и вызывает `ai_solve_problem(...)`;
   - преобразует `ProblemSolution` в словарь с полями для фронта; добавляет исходные `correlations`, `concepts`, `rules`, `practices`.
5. Результат возвращается в `webapp.py`, где:
   - если `needs_clarification` **False**, решение сохраняется в историю пользователя (`save_problem_history`);
   - если `needs_clarification` **True**, решение **не сохраняется** (это только шаг уточнения).
6. Frontend в `Problem.tsx`:
   - если `needs_clarification == true` и есть `clarifying_questions`, показывает форму уточнения и ждёт ответы;
   - комбинирует исходную формулировку и ответы в один текст и делает **второй вызов** `solveProblem` (уже финальный);
   - отображает финальный план, историю, партнёров, блок с правилом и практикой.

### 3.2. Telegram

1. Пользователь отправляет проблему боту (команда `/solver` или через inline‑кнопки).
2. Хэндлеры в `backend/app/api/bot.py` переходят в состояние `ProblemState.waiting_for_description` и принимают текст.
3. Внутри `process_problem_description` вызывается `ProblemSolverAgent.analyze_problem`.
4. Логика такая же, как в WebApp: если `needs_clarification`, бот задаёт уточняющие вопросы (новое состояние FSM), потом по второму ответу строится финальное решение.

---

## 4. Слои знаний и их источники

### 4.1. Корреляции (correlations)

- Коллекция Qdrant: `correlations`.
- Источники:
  - `terms/diamond-correlations-table.md` — базовые корреляции «проблема ↔ причина ↔ решение».
  - `terms/diamond-correlations-extended.md` — расширенные корреляции с полями:
    - `sphere`, `imprint`, `quality`, `partners`, `principle`, `number`, `problem_type`, `source_type`.
- Загрузка:
  - `KnowledgeLoader` → `index_knowledge` в `QdrantKnowledgeBase`.
- Использование:
  - `QdrantKnowledgeBase.search_correlation(problem, limit=...)` → список словарей с обогащённой мета‑информацией.
  - Эти данные уходят в `ProblemContext.correlations` и в `ProblemSolution` (как `correlations` для фронта).

### 4.2. Концепции (concepts)

- Коллекция Qdrant: `concepts`.
- Источники: `terms/diamond-concepts.md`, `terms/karma-concepts.md` (концептуальные блоки, объясняющие теорию).
- Использование:
  - `QdrantKnowledgeBase.search_concepts(query, limit=...)` → `ProblemContext.concepts`.
  - Во фронте: блок «📖 Полезные концепции» с раскрывающимися детализированными описаниями.

### 4.3. Правила (rules)

- Коллекция Qdrant: `rules`.
- Источники: в первую очередь `terms/karma-concepts.md` (8 правил КМ, 4 закона кармы и др. правила).
- Загрузка: отдельный тип `KnowledgeItem` с `type="rule"`, полями `number`, `title`, `content` в `metadata`.
- Использование:
  - `QdrantKnowledgeBase.search_rules(query, limit=...)` → `ProblemContext.rules`.
  - В промпте агента правила используются как опорные «формулы» для объяснения, *почему* такой отпечаток даёт такой результат.
  - Во фронте: блок «📜 Правило, на котором основан план» (берётся первая запись из `result.rules`).

### 4.4. Практики (practices)

- Коллекция Qdrant: `practices`.
- Источники: практические части `terms/diamond-concepts.md` и `terms/karma-concepts.md` (йога, медитации, упражнения, дневные практики).
- Использование:
  - `QdrantKnowledgeBase.search_practice(need, restrictions, limit)`
    - возвращает `name`, `category`, `content`, `duration`, `score`.
  - В `ProblemContext.practices` — как опора для генерации 30‑дневного плана.
  - Во фронте: блок «🧘 Рекомендуемая практика дня» (первая практика из `result.practices`).

---

## 5. PydanticAI‑агент и промпты

### 5.1. Типы `ProblemContext` и `ProblemSolution`

Файл: `backend/app/ai/problem_agent.py`.

**ProblemContext**:
- `problem_description: str` — исходный текст проблемы;
- `user_name: str` — имя пользователя (для более живого ответа);
- `correlations: list[dict]` — топ‑корреляции по сходству;
- `concepts: list[dict]` — ключевые концепции для объяснений;
- `rules: list[dict]` — правила кармического менеджмента;
- `practices: list[dict]` — релевантные практики;
- опциональные поля для будущего явного intake (сфера, desired_outcome).

**ProblemSolution**:
- Базовые поля:
  - `problem_summary`, `root_cause`, `imprint_logic`;
  - `stop_action`, `start_action`, `grow_action`;
  - `practice_steps: list[str]`, `expected_outcome`, `timeline_days`, `success_tip`.
- Расширенные поля:
  - `clarity_level` — `high/medium/low` ясности формулировки;
  - `karmic_pattern` — 1–2 ключевых отпечатка/паттерна;
  - `seed_strategy_summary` — краткое резюме стратегии посева;
  - `coffee_meditation_script` — текст для кофейной медитации;
  - `partner_actions: list[str]` — до 4 действий для партнёров.
- Q&A‑режим:
  - `needs_clarification: bool` — запросить ли уточнения;
  - `clarifying_questions: list[str]` — до 3 коротких вопросов.

### 5.2. Системный промпт (system prompt)

Определён в `create_problem_agent()` в `problem_agent.py`.

Ключевые элементы промпта:
- Роль: «кармический консультант системы Diamond Cutter в приложении Rouch».
- Ориентация на отпечатки и 7 базовых качеств (даяние, нравственность, терпение, усилие, сосредоточение, мудрость, сострадание).
- Методология:
  - **Intake**: определить сферу, сформулировать корень проблемы в терминах отпечатков.
  - **Karmic linking**: опереться на корреляции (`problem, cause/imprint, solution, sphere, quality, principle, number`) и правила.
  - **Solution synthesis**: выдать STOP/START/GROW + план на 30 дней.
- Оформление:
  - заполнить все поля `ProblemSolution`;
  - явно указывать тип отпечатка и качество;
  - оценивать `clarity_level`;
  - при размытом запросе — ставить `needs_clarification=true` и формировать 0–3 уточняющих вопроса.

### 5.3. Дополнительный промпт при запуске агента

Функция `solve_problem(...)` в `problem_agent.py` передаёт в `agent.run` текстовую инструкцию:

- напомнить про шаги: объяснить `root_cause`, раскрыть `imprint_logic`, сформулировать STOP/START/GROW, составить план и дать `success_tip`;
- по возможности заполнить `clarity_level`, `karmic_pattern`, `seed_strategy_summary`, `coffee_meditation_script`, `partner_actions`.

---

## 6. Настройки и на что они влияют

Файл настроек: `backend/app/config.py` (класс `Settings`).

### 6.1. Лимиты ProblemSolverAgent

- `PROBLEM_SOLVER_CORRELATIONS_LIMIT` (по умолчанию `3`)
  - Сколько корреляций запрашивается из Qdrant в `ProblemSolverAgent.analyze_problem`.
  - Влияет на размер контекста для агента и на блок «⛓ Прямые корреляции» на фронте.

- `PROBLEM_SOLVER_CONCEPTS_LIMIT` (по умолчанию `2`)
  - Сколько концепций берётся из Qdrant.
  - Влияет на раздел «📖 Полезные концепции» и глубину теоретических объяснений.

- `PROBLEM_SOLVER_RULES_LIMIT` (по умолчанию `3`)
  - Сколько правил кармического менеджмента подтягивается на запрос.
  - Влияет на то, какие правила попадут в `ProblemContext.rules` и в блок «📜 Правило, на котором основан план».

- `PROBLEM_SOLVER_PRACTICES_LIMIT` (по умолчанию `3`)
  - Сколько практик подбирается под проблему/цель.
  - Влияет на разнообразие плана и на блок «🧘 Рекомендуемая практика дня».

Все эти переменные можно переопределить в `.env`:

```env
PROBLEM_SOLVER_CORRELATIONS_LIMIT=5
PROBLEM_SOLVER_CONCEPTS_LIMIT=3
PROBLEM_SOLVER_RULES_LIMIT=4
PROBLEM_SOLVER_PRACTICES_LIMIT=5
```

### 6.2. Настройки LLM

- `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_TEMPERATURE`, `AI_MAX_TOKENS`, `AI_BASE_URL` — влияют на то, какой провайдер и модель используются в `get_model()` и, соответственно, в `ProblemAgent`.

### 6.3. Настройки Qdrant

- `QDRANT_URL`, `QDRANT_COLLECTION_SIZE`, `QDRANT_API_KEY` — управляют клиентом `QdrantKnowledgeBase`.

---

## 7. Q&A‑режим (уточняющие вопросы)

- Если агент считает проблему размыто сформулированной, он:
  - ставит `needs_clarification = true`;
  - заполняет `clarifying_questions` (0–3 коротких, конкретных вопроса).

### 7.1. Telegram

- FSM состояние `ProblemState.waiting_for_clarification` в `bot.py`.
- Поток:
  1. Пользователь формулирует проблему → `analyze_problem` → агент запрашивает уточнения.
  2. Бот отправляет вопросы и переводит пользователя в состояние ожидания ответов.
  3. Пользователь отвечает одним/несколькими сообщениями, после чего строится финальный план.

### 7.2. WebApp

- В `Problem.tsx` хранится состояние:
  - `needsClarification`, `clarifyingQuestions`, `clarificationText`, `initialProblem`.
- Первый вызов `/problem/solve` может вернуть список вопросов.
- UI показывает блок «🧐 Нужно чуть больше деталей», перечисляет вопросы и даёт поле для объединённого ответа.
- Второй вызов `/problem/solve` с комбинированным текстом считается финальным, история обновляется.

---

## 8. Промпты для генерации таблиц корреляций

Таблицы корреляций (`diamond-correlations-table.md`, `diamond-correlations-extended.md`) и правила/практики в `diamond-concepts.md` и `karma-concepts.md` могут частично генерироваться или до‑формулировываться через LLM.

На момент написания этой документации **конкретные промпты генерации не зафиксированы в репозитории**. Рекомендуется:

- хранить используемые промпты в отдельном файле (например, `TERMS_GENERATION_PROMPTS.md`) с указанием:
  - исходного текста (фрагмент книги / конспекта),
  - задачи для модели (формат таблицы/правил/практик),
  - требований по стилю и терминологии.

Это позволит воспроизводимо расширять базу знаний и прозрачно понимать происхождение каждой строки в `terms/`.

---

## 9. Как модифицировать поведение ProblemResolver

- **Изменить глубину / ширину контекста**:
  - крутить `PROBLEM_SOLVER_*_LIMIT` в `.env`;
  - править промпт в `create_problem_agent()` (например, больше/меньше акцент на практиках или на теории).

- **Добавить новый слой знаний** (например, «кейсы бизнеса»):
  1. Добавить новый тип `KnowledgeItem` и его парсинг в `KnowledgeLoader`.
  2. Добавить коллекцию в `QdrantKnowledgeBase.index_knowledge` и метод `search_xxx`.
  3. Добавить список в `ProblemContext` и использовать его в `add_problem_context` и/или промптах.
  4. При желании — вывести в ответ `/problem/solve` дополнительным полем и отобразить на фронте.

- **Включить/выключить Q&A‑режим**:
  - по умолчанию логика заложена в промпт агента; можно ослабить/усилить критерии в текстовой инструкции (что считать «размытой проблемой»).

---

## 10. Краткий TL;DR для разработчика

- Входные точки: `/api/problem/solve` (WebApp), хэндлеры `ProblemState` (Telegram).
- Основная логика: `ProblemSolverAgent.analyze_problem` → Qdrant → `ai_solve_problem` → `ProblemSolution`.
- Агент: PydanticAI `Agent[ProblemContext, ProblemSolution]` с жёстко типизированным выводом и расширенным промптом.
- Слои знаний: корреляции, концепции, правила, практики — все сидят в Qdrant и приходят в контекст агента.
- Тонкая настройка: переменные `PROBLEM_SOLVER_*_LIMIT` в `.env`, параметры LLM и сами промпты в `problem_agent.py`.
- UX: поддержка уточняющих вопросов как в Telegram, так и в WebApp.
