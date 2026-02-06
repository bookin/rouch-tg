"""Problem solving agent with Pydantic AI"""
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from app.ai.models import get_model


class ProblemIntakeContext(BaseModel):
    """Context for the intake (diagnostic) step before full problem solving"""
    problem_description: str
    user_name: str


class ProblemIntakeResult(BaseModel):
    """Result of the intake step used to guide further karmic analysis"""
    normalized_problem: str = Field(
        description="Краткая нормализованная формулировка проблемы пользователя"
    )
    sphere: Optional[str] = Field(
        default=None,
        description=(
            "Сфера проблемы (финансы, отношения, здоровье, работа/карьера, "
            "смысл/путь, эмоции/состояния, общая)"
        ),
    )
    desired_outcome: Optional[str] = Field(
        default=None,
        description="Желаемый результат пользователя в одном-двух предложениях",
    )
    clarity_level: str = Field(
        default="medium", description="Уровень ясности формулировки: high / medium / low"
    )
    needs_clarification: bool = Field(
        default=False,
        description="Нужно ли задать уточняющие вопросы перед финальным планом",
    )
    clarifying_questions: list[str] = Field(
        default_factory=list,
        description="Список из 0–3 коротких уточняющих вопросов, если формулировка размыта",
    )
    hypothesized_imprints: list[str] = Field(
        default_factory=list,
        description=(
            "Гипотеза о 1–3 ключевых отпечатках/паттернах (зависть, скупость, "
            "гнев, нечестность, раскол и т.п.), выведенных из описания проблемы"
        ),
    )


class ProblemContext(BaseModel):
    """Context for problem solving"""
    problem_description: str
    user_name: str
    correlations: list[dict] = Field(default_factory=list)
    concepts: list[dict] = Field(default_factory=list)
    # Дополнительные внутренние поля (используются для явного Intake)
    sphere: Optional[str] = Field(
        default=None,
        description="Сфера проблемы (финансы, отношения, здоровье, работа, смысл, эмоции)",
    )
    desired_outcome: Optional[str] = Field(
        default=None,
        description="Желаемый результат пользователя в свободной формулировке",
    )
    hypothesized_imprints: list[str] = Field(
        default_factory=list,
        description=(
            "Гипотеза о ключевых отпечатках (зависть, скупость, гнев и т.п.), "
            "на которые особенно стоит опереться в анализе",
        ),
    )
    # Отдельный слой знаний: правила и практики
    rules: list[dict] = Field(
        default_factory=list,
        description="Подборка правил кармического менеджмента, релевантных проблеме",
    )
    practices: list[dict] = Field(
        default_factory=list,
        description=(
            "Подборка практик (йога/медитация/упражнения), на которые можно опереться в плане"
        ),
    )


class ProblemSolution(BaseModel):
    """Structured problem solution"""
    problem_summary: str = Field(description="Краткое описание проблемы")
    root_cause: str = Field(description="Кармическая причина (что создало проблему)")
    imprint_logic: str = Field(description="Объяснение механизма: как именно этот отпечаток создает эту реальность")
    
    # 3-step action plan
    stop_action: str = Field(description="Что нужно ПРЕКРАТИТЬ делать (устранение негативного отпечатка)")
    start_action: str = Field(description="Что нужно НАЧАТЬ делать (противоположное действие)")
    grow_action: str = Field(description="Как 'поливать' семена (радость, кофе-медитация, системный подход)")
    
    practice_steps: list[str] = Field(description="Конкретный пошаговый план на 30 дней")
    expected_outcome: str = Field(description="Ожидаемый результат через 30-90 дней")
    timeline_days: int = Field(default=30, description="Срок до первых результатов")
    success_tip: str = Field(description="Совет для ускорения результата (коэффициент усиления)")
    # Новые поля (обратносуместимо, можно игнорировать на фронте)
    clarity_level: Optional[str] = Field(default=None, description="Уровень ясности проблемы: high / medium / low")
    karmic_pattern: Optional[str] = Field(default=None, description="Краткое описание 1–2 ключевых отпечатков и паттернов")
    seed_strategy_summary: Optional[str] = Field(default=None, description="Короткое резюме: какие семена мы сажаем и для кого")
    coffee_meditation_script: Optional[str] = Field(default=None, description="Короткий текст/сценарий для кофе-медитации")
    partner_actions: Optional[list[str]] = Field(default=None, description="До 4 действий для 4 кармических партнёров")
    # Поля для Q&A-режима (используются в Telegram/WebApp, можно игнорировать, если не нужны)
    needs_clarification: bool = Field(default=False, description="Нужно ли задать уточняющие вопросы перед финальным планом")
    clarifying_questions: list[str] = Field(
        default_factory=list,
        description="Список из 0–3 уточняющих вопросов, если проблема сформулирована размыто"
    )
def create_problem_agent() -> Agent[ProblemContext, ProblemSolution]:
    """Create problem-solving agent"""
    
    model = get_model()
    
    agent = Agent(
        model=model,
        deps_type=ProblemContext,
        output_type=ProblemSolution,
        system_prompt=(
            "Ты — кармический консультант системы Diamond Cutter (Геше Майкл Роуч) внутри приложения Rouch. "
            "Твоя задача — на основе проблемы пользователя и примеров из базы знаний (корреляции, концепции, правила, практики) "
            "выстроить глубокий кармический разбор по отпечаткам и дать реалистичный план действий. База знаний — это ПРИМЕРЫ, а не истина; "
            "ты обязан мыслить самостоятельно в рамках кармической логики, а не просто пересказывать строки."
            "\n\nРабочая оптика:\n"
            "- Мир исходит из отпечатков в уме (seeds), всё зависит от причины, посеянной в отношениях с другими.\n"
            "- Ключевые оси анализа: СФЕРА (финансы, отношения, здоровье, смысл/путь, работа/карьера, эмоции/состояния), "
            "ОТПЕЧАТОК (imprint: скупость, гнев, зависть, нечестность, раскол и т.п.), КАЧЕСТВО (из 7: даяние, нравственность, терпение, усилие, "
            "сосредоточение, мудрость, сострадание), ПРИНЦИП (закон/правило/формула).\n"
            "- Структурированные поля корреляций из Qdrant: category, sphere, imprint, quality, partners, principle, number.\n"
            "  Обязательно используй их для уточнения сферы, типа отпечатка и принципа решения.\n"
            "- Вспомогательные опоры: 4 закона кармы, 8 правил Кармического менеджмента, 7 базовых качеств ума.\n"
            "\nМетодология рассуждения (всегда проходи эти шаги внутренне):\n"
            "1) Intake (диагностика):\n"
            "   - Определи основную сферу проблемы пользователя (sphere) по описанию и по полю sphere/категория корреляций.\n"
            "   - Зафиксируй желаемый результат (desired_outcome) в терминах пользовательского запроса.\n"
            "   - Сформулируй корень проблемы в терминах отпечатков: какое отношение к другим повторяется в этой сфере.\n"
            "   - Используй hypothesized_imprints как отправную гипотезу, но можешь её скорректировать на основе корреляций и правил.\n"
            "2) Karmic linking (связь с базой знаний):\n"
            "   - Посмотри на найденные корреляции: problem, cause/imprint, solution, sphere, quality, partners, principle, number.\n"
            "   - Выбери 1–3 наиболее близких примера и на их основе уточни гипотезу о корне и механизме проекции.\n"
            "   - Используй правила и концепции для объяснения, ПОЧЕМУ именно такой отпечаток даёт такой результат (ссылаясь на принцип/правило).\n"
            "3) Solution synthesis (решение):\n"
            "   - Сформулируй STOP: конкретные формы поведения/мышления, которые подпитывают отпечаток и которые нужно прекратить.\n"
            "   - Сформулируй START: противоположные действия по отношению к другим людям в той же сфере.\n"
            "   - Сформулируй GROW: как радоваться, делать кофе-медитацию, фиксировать прогресс, чтобы семена проросли.\n"
            "   - Составь список из нескольких ключевых шагов (practice_steps), который пользователь сможет превратить в 30-дневный план.\n"
            "\nОформление ответа:\n"
            "- Все поля структуры ProblemSolution должны быть заполнены.\n"
            "- В root_cause и imprint_logic явно упоминай тип отпечатка и базовое качество (из 7), на котором строится решение.\n"
            "- В success_tip можешь дать 1–2 тонких совета (как усилить семена, какие ошибки не допустить).\n"
            "- В clarity_level оцени, насколько чётко сформулирована проблема (high / medium / low).\n"
            "- Если проблема сформулирована расплывчато, установи needs_clarification=true и заполни clarifying_questions (0–3 коротких уточняющих вопроса).\n"
            "- Если проблема достаточно ясна, оставь needs_clarification=false и clarifying_questions пустым списком.\n"
            "\nИспользуй предоставленные корреляции, правила, практики и концепции как точки опоры для рассуждений, "
            "но формируй решение, исходя из принципов кармического менеджмента, а не механического совпадения текста."
        ),
    )
    
    @agent.system_prompt
    def add_problem_context(ctx: RunContext[ProblemContext]) -> str:
        """Add problem context"""
        context = ctx.deps

        prompt = f"Проблема пользователя {context.user_name}: {context.problem_description}\n\n"

        if context.sphere or context.desired_outcome or context.hypothesized_imprints:
            prompt += "Внутренний анализ перед обращением к базе знаний:\n"
            if context.sphere:
                prompt += f"- Сфера проблемы: {context.sphere}\n"
            if context.desired_outcome:
                prompt += f"- Желаемый результат: {context.desired_outcome}\n"
            if context.hypothesized_imprints:
                prompt += "- Предполагаемые отпечатки: " + ", ".join(
                    context.hypothesized_imprints[:3]
                ) + "\n"
            prompt += "\n"

        if context.correlations:
            prompt += "Найденные корреляции из базы знаний (примеры, на которые можно опереться):\n"
            for corr in context.correlations[:3]:
                prompt += f"- Проблема: {corr.get('problem', '')}\n"
                prompt += (
                    "  Причина (cause / imprint): "
                    f"{corr.get('cause', '') or corr.get('imprint', '')}\n"
                )
                if corr.get("sphere"):
                    prompt += f"  Сфера: {corr.get('sphere', '')}\n"
                if corr.get("quality"):
                    prompt += f"  Качество (из 7): {corr.get('quality', '')}\n"
                if corr.get("principle"):
                    prompt += f"  Принцип: {corr.get('principle', '')}\n"
                if corr.get("number"):
                    prompt += f"  № в расширенной таблице: {corr.get('number', '')}\n"
                prompt += f"  Решение: {corr.get('solution', '')}\n\n"

        if context.concepts:
            prompt += "Связанные концепции:\n"
            for concept in context.concepts[:2]:
                prompt += (
                    f"- {concept.get('title', '')}: "
                    f"{concept.get('content', '')[:100]}...\n"
                )

        if context.rules:
            prompt += "\nКлючевые правила кармического менеджмента, на которые можно опереться:\n"
            for rule in context.rules[:2]:
                title = rule.get("title", "")
                number = rule.get("number")
                short = (rule.get("content", "") or "")[:180]
                if number is not None:
                    prompt += f"- Правило #{number}: {title}\n  {short}...\n"
                else:
                    prompt += f"- {title}: {short}...\n"

        if context.practices:
            prompt += "\nПрактики и упражнения, которые можно использовать в плане:\n"
            for practice in context.practices[:2]:
                name = practice.get("name") or practice.get("title", "")
                short = (practice.get("content", "") or "")[:180]
                prompt += f"- {name}: {short}...\n"

        return prompt
    
    return agent


def create_intake_agent() -> Agent[ProblemIntakeContext, ProblemIntakeResult]:
    """Create intake agent responsible for diagnostics and clarification needs"""

    model = get_model()

    agent = Agent(
        model=model,
        deps_type=ProblemIntakeContext,
        output_type=ProblemIntakeResult,
        system_prompt= ("""
Ты — кармический консультант системы Diamond Cutter, выполняющий только этап ПРИНЯТИЯ ПРОБЛЕМЫ (intake). 
Твоя задача — подготовить качественный вход для следующего кармического агента, а не решать проблему и не вести терапию.

Фокус: ты смотришь на проблему через призму кармического менеджмента:
- мир исходит из ментальных отпечатков (семян) в уме;
- отпечатки создаются тем, как человек относится к ДРУГИМ (действия, слова, мысли);
- важны не бытовые детали, а СФЕРА, КАРМИЧЕСКИЕ ПАРТНЁРЫ и ПОВТОРЯЮЩЕЕСЯ ПОВЕДЕНИЕ.

Твои выходные поля:
- sphere — сфера проблемы: финансы, отношения, здоровье, работа/карьера, смысл/путь, эмоции/состояния, общая;
- desired_outcome — главное, чего человек хочет в этой ситуации (1–2 предложения);
- clarity_level — high / medium / low;
- needs_clarification — нужно ли задавать уточняющие вопросы;
- clarifying_questions — 0–3 очень точных вопроса, если без них сложно увидеть корневой отпечаток;
- hypothesized_imprints — 1–3 гипотезы по отпечаткам (зависть, скупость, гнев, нечестность, раскол, жадность, равнодушие и т.п.).

Критерии ясности:
- high — по описанию понятно: 
  * В КАКОЙ СФЕРЕ проблема,
  * ЧТО именно не устраивает,
  * КАКОЙ результат человек хочет получить,
  * есть хотя бы один пример ситуации. 
  В этом случае НЕ задавай дополнительных вопросов: needs_clarification=false, clarifying_questions=[].
- medium — сфера понятна, но не хватает деталей, чтобы увидеть кармический паттерн (к кому и что человек делает, кого это задевает).
- low — очень общие слова без конкретики ("всё плохо", "нет денег", "ничего не хочется") и почти нет примеров.

Логика вопросов:
1) Задавай вопросы ТОЛЬКО если без них велика вероятность ошибиться со сферой или корневым отпечатком. 
   Твоя цель — помочь следующему агенту точнее увидеть семена и построить STOP/START/GROW-план, а не собрать красивое интервью.

2) Каждый вопрос должен явно помогать минимум по одной оси:
   - СФЕРА: уточнить, к какой из сфер (финансы/отношения/здоровье/работа/смысл/эмоции) реально относится ядро проблемы;
   - КАРМИЧЕСКИЕ ПАРТНЁРЫ: понять, кто основные "адресаты" поведения (он сам, коллеги, клиенты, поставщики, семья, мир);
   - ПОВТОРЯЮЩЕЕСЯ ПОВЕДЕНИЕ: выяснить, что человек обычно делает/говорит/думает по отношению к другим в этой сфере;
   - ЖЕЛАЕМЫЙ РЕЗУЛЬТАТ: прояснить, как будет выглядеть решённая ситуация с точки зрения внешней реальности.

   Если вопрос НЕ меняет понимание этих вещей — НЕ задавай его.

3) Примеры осмысленных вопросов:
   - уточнение СФЕРЫ, если она размыта или смешана;
   - вопрос о том, КОМУ в первую очередь больно или неудобно в этой ситуации (кармические партнёры);
   - вопрос о ТИПИЧНОМ ПОВЕДЕНИИ человека по отношению к людям в этой сфере (что он делает/не делает, говорит/не говорит);
   - уточнение ЖЕЛАЕМОГО РЕЗУЛЬТАТА своими словами ("что должно измениться, чтобы ты считал проблему решённой?").

4) Запрещённые ("глупые") вопросы:
   - общие и пустые: "расскажи подробнее", "приведи больше деталей";
   - дублирующие уже сказанное (перед вопросом проверь, нет ли уже ответа в описании проблемы);
   - биографические, которые не влияют на кармический анализ: возраст, город, должность, образование и т.п.;
   - про точные суммы, даты, сроки, если это не меняет понимание отпечатка (размер долга, точный доход и т.п.);
   - вопросы, которые звучат как обычная психотерапия или small talk и не помогают увидеть отношение к другим людям.

Работа с clarity_level и нуждой в уточнениях:
- если ясность HIGH — ставь clarity_level="high", needs_clarification=false, clarifying_questions=[];
- если ясность MEDIUM или LOW и 1–3 точных вопроса заметно улучшат понимание сферы/партнёров/поведения, 
  тогда:
  * ставь needs_clarification=true,
  * задай максимум 3 коротких вопроса, каждый строго по одному аспекту (сфера, партнёры, поведение, желаемый результат);
  * формулируй вопросы просто и по-деловому, без оценок и лишних слов.
- если даже при размытом описании уже можно разумно предположить сферу и отпечатки (например, классический кейс из кармического менеджмента), 
  допускается оставить needs_clarification=false и НЕ перегружать пользователя дополнительными вопросами.

Помни: твоя задача — НЕ максимально "выговорить" человека, а минимальным количеством чётких кармически осмысленных вопросов дать следующему агенту:
нормализованную формулировку, сферу, желаемый результат и рабочую гипотезу по отпечаткам.
        """)
        # system_prompt=(
        #     "Ты — кармический консультант системы Diamond Cutter, выполняющий только этап ПРИНЯТИЯ ПРОБЛЕМЫ (intake). "
        #     "Твоя задача — аккуратно классифицировать проблему, оценить её ЯСНОСТЬ и понять, какие уточнения реально нужны "
        #     "для дальнейшего кармического анализа. Ты НЕ даёшь финальный план и не заменяешь основной агент.\n\n"
        #     "Сферы для поля sphere: финансы, отношения, здоровье, работа/карьера, смысл/путь, эмоции/состояния, общая.\n"
        #     "Типы отпечатков (hypothesized_imprints): зависть, скупость, гнев, нечестность, раскол, жадность, равнодушие и "
        #     "другие сходные по смыслу шаблоны.\n\n"
        #     "Оцени ясность формулировки по трём уровням:\n"
        #     "- high — понятно, В КАКОЙ СФЕРЕ проблема, ЧТО именно не устраивает и КАКОЙ результат человек хочет. Есть хотя бы один пример.\n"
        #     "- medium — примерно ясно, но не хватает деталей (кто именно, сколько по времени, как выглядит успех).\n"
        #     "- low — общие слова без конкретики ('всё плохо', 'нет денег', 'ничего не хочется').\n\n"
        #     "Логика поля needs_clarification и вопросов:\n"
        #     "- если ясность high — ставь needs_clarification=false и НЕ задавай вопросов (clarifying_questions оставь пустым).\n"
        #     "- если ясность medium или low — можешь задать 1–3 конкретных вопроса, которые помогут кармическому менеджеру:\n"
        #     "  * уточнить СФЕРУ (финансы/отношения/здоровье/работа/смысл/эмоции);\n"
        #     "  * прояснить КАРМИЧЕСКИХ ПАРТНЁРОВ (кто страдает/на кого влияет ситуация: коллеги, клиенты, поставщики, семья, мир);\n"
        #     "  * увидеть ПОВТОРЯЮЩЕЕСЯ ПОВЕДЕНИЕ или отношение к другим (что человек делает/говорит/думает по отношению к людям в этой сфере);\n"
        #     "  * понять ЖЕЛАЕМЫЙ РЕЗУЛЬТАТ своими словами (что должно измениться, чтобы проблема считалась решённой).\n"
        #     "Избегай пустых общих вопросов вроде 'расскажи подробнее'. Каждый вопрос должен быть явно полезен следующему шагу: "
        #     "помочь найти корневой отпечаток и построить STOP/START/GROW-план."
        # ),
    )

    @agent.system_prompt
    def add_intake_context(ctx: RunContext[ProblemIntakeContext]) -> str:
        """Add intake context"""
        context = ctx.deps
        return (
            f"Пользователь {context.user_name} описал проблему так: "
            f"{context.problem_description}\n\n"
            "Твоя задача — помочь следующему кармическому агенту понять, с чем он имеет дело."
        )

    return agent


_problem_agent: Optional[Agent] = None
_intake_agent: Optional[Agent] = None


def get_problem_agent() -> Agent[ProblemContext, ProblemSolution]:
    """Get or create problem agent"""
    global _problem_agent
    
    if _problem_agent is None:
        _problem_agent = create_problem_agent()
    
    return _problem_agent


def get_problem_intake_agent() -> Agent[ProblemIntakeContext, ProblemIntakeResult]:
    """Get or create intake agent"""
    global _intake_agent

    if _intake_agent is None:
        _intake_agent = create_intake_agent()

    return _intake_agent


async def solve_problem(
    user_name: str,
    problem_description: str,
    correlations: list[dict],
    concepts: list[dict],
    rules: list[dict],
    practices: list[dict],
    sphere: Optional[str] = None,
    desired_outcome: Optional[str] = None,
    hypothesized_imprints: Optional[list[str]] = None,
) -> ProblemSolution:
    """
    Solve user's problem using AI and knowledge base
    
    Args:
        user_name: User's name
        problem_description: Description of the problem
        correlations: Related correlations from Qdrant
        concepts: Related concepts from Qdrant
        
    Returns:
        Structured solution with action plan
    """
    agent = get_problem_agent()

    context = ProblemContext(
        problem_description=problem_description,
        user_name=user_name,
        correlations=correlations,
        concepts=concepts,
        sphere=sphere,
        desired_outcome=desired_outcome,
        hypothesized_imprints=hypothesized_imprints or [],
        rules=rules,
        practices=practices,
    )

    prompt = (
        "Проанализируй проблему пользователя, опираясь на переданный внутренний анализ (sphere, desired_outcome, "
        "hypothesized_imprints) и найденные корреляции/правила/практики.\n"
        "1. Объясни кармическую причину (root_cause), явно назвав тип отпечатка и качество из 7.\n"
        "2. Раскрой механизм imprint_logic (как именно этот отпечаток создаёт текущую реальность), ссылаясь на принципы/правила.\n"
        "3. Сформулируй STOP, START и GROW действия в духе кармического менеджмента (противоположная естественной реакции стратегия).\n"
        "4. Составь список ключевых шагов (practice_steps), который пользователь сможет превратить в 30-дневный план.\n"
        "5. Дай совет по ускорению (success_tip) и при возможности зафиксируй clarity_level, karmic_pattern, "
        "seed_strategy_summary, coffee_meditation_script и partner_actions.\n"
        "Будь вдохновляющим, но очень точным в кармической логике."
    )

    result = await agent.run(prompt, deps=context)
    return result.output


async def solve_problem_intake(
    user_name: str,
    problem_description: str,
) -> ProblemIntakeResult:
    """Run dedicated intake agent to classify problem and detect clarification needs"""

    agent = get_problem_intake_agent()

    context = ProblemIntakeContext(
        problem_description=problem_description,
        user_name=user_name,
    )

    prompt = (
        "Сделай кармический intake-просмотр проблемы пользователя.\n"
        "1) Запиши нормализованную формулировку в normalized_problem (одно предложение, без воды).\n"
        "2) Определи sphere (финансы, отношения, здоровье, работа/карьера, смысл/путь, эмоции/состояния, общая).\n"
        "3) Опиши desired_outcome — главное, чего хочет пользователь в этой ситуации (одно-два предложения).\n"
        "4) Оцени clarity_level: high, medium или low.\n"
        "5) Если clarity_level medium или low и реально помогут уточнения, установи needs_clarification=true и "
        "сформулируй 1–3 очень конкретных вопроса в clarifying_questions. Если проблема уже достаточно ясна и подается кармическому анализу, "
        "оставь needs_clarification=false и clarifying_questions пустым списком.\n"
        "6) Предположи 1–3 ключевых отпечатка/паттерна (hypothesized_imprints) на языке кармического менеджмента "
        "(зависть, скупость, гнев, нечестность, раскол и т.п.).\n"
        "Не давай сейчас финальное решение или план действий — только подготовь почву для следующего агента."
    )

    result = await agent.run(prompt, deps=context)
    return result.output
