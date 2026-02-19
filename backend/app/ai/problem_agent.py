"""Problem solving agent with Pydantic AI"""
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from app.ai.models import get_model


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


class PartnerCategoryGuide(BaseModel):
    """Guide for selecting a partner for a specific category"""
    category: str = Field(description="Universal category: source, ally, protege, world")
    title: str = Field(description="User-facing title for this category, e.g. 'Your Source of Life'")
    description: str = Field(description="Explanation of who fits here for this specific problem")
    examples: list[str] = Field(description="List of specific examples of people who could be partners")
    fallback_advice: str = Field(description="Advice if the user has NO ONE in this category (isolated). specific for this problem. e.g. 'Find an online forum' or 'Visualize ancestors'.")


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
    partner_actions: Optional[list[str]] = Field(default=None, description=(
        "До 4 действий, где пользователь помогает конкретным людям "
        "с аналогичной проблемой. Это всегда действия отдачи, "
        "а не получения поддержки."
    ))
    
    partner_selection_guide: Optional[list[PartnerCategoryGuide]] = Field(
        default=None,
        description="Guide for selecting partners for the 4 universal categories (Source, Ally, Protege, World) specific to this problem"
    )

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
            "   - Сгенерируй `partner_selection_guide` для 4 универсальных категорий специфично для этой проблемы:\n"
            "     1. Source (Источник): Кто выше / дает ресурсы (Родители, учителя, начальство, врачи).\n"
            "     2. Ally (Соратник): Кто на равных / партнеры (Супруги, коллеги, друзья, подрядчики).\n"
            "     3. Protege (Подопечный): Кто зависит / нуждается (Дети, клиенты, подчиненные, пациенты).\n"
            "     Для КАЖДОЙ категории обязательно заполни `fallback_advice` — что делать, если у человека НЕТ никого в этой группе (изоляция).\n"
            "     В случае изоляции предлагай:\n"
            "       - Ментальные практики (пожелание счастья, визуализация).\n"
            "       - Онлайн-волонтерство или помощь на форумах.\n"
            "       - Анонимные действия (уборка мусора, донаты).\n"
            "     4. World (Внешний мир): Далекие люди / конкуренты (Незнакомцы, общество, те, кто мешает).\n"
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
_problem_agent: Optional[Agent] = None


def get_problem_agent() -> Agent[ProblemContext, ProblemSolution]:
    """Get or create problem agent"""
    global _problem_agent
    
    if _problem_agent is None:
        _problem_agent = create_problem_agent()
    
    return _problem_agent


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
        """
        КРИТИЧЕСКОЕ ПРАВИЛО ДЛЯ partner_actions:

- Кармический партнёр — это человек, которому пользователь ПОМОГАЕТ,
  а не тот, кто помогает пользователю.

- partner_actions должны описывать только действия,
  где пользователь активно улучшает жизнь другого человека
  в той же сфере, где он хочет результата.

- НЕЛЬЗЯ:
  * просить поддержки
  * требовать понимания
  * ожидать изменений от других
  * просить не звонить / не писать / не мешать

- МОЖНО ТОЛЬКО:
  * помогать
  * защищать
  * облегчать
  * создавать условия
  * поддерживать
  * давать ресурс

- Каждый пункт partner_actions должен:
  1) назвать тип человека с похожей проблемой
  2) описать конкретное действие помощи
  3) быть формулировкой "я делаю для другого", а не "они делают для меня"

Если действия направлены на получение поддержки — это ошибка логики кармического менеджмента.
        """
    )

    result = await agent.run(prompt, deps=context)
    return result.output
