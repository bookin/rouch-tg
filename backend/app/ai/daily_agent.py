"""Daily AI Agent using Pydantic AI"""
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from sqlalchemy import select
from app.ai.models import get_model
from app.utils.typing_loader import broadcast_status
from app.database import AsyncSessionLocal
from app.models.db_models import PartnerDB


class MessageContext(BaseModel):
    """Context for message generation"""
    user_name: str
    user_focus: Optional[str] = None
    streak_days: int = 0
    total_seeds: int = 0
    time_of_day: str = "morning"  # morning, evening
    plan_strategy: Optional[dict] = None  # Karma Plan strategy snapshot
    project_partners: Optional[dict[str, dict[str, str]]] = None  # {category: {partner_id: name}}
    isolation_settings: Optional[dict[str, dict]] = None  # {source: {is_isolated: true}, ...}
    partner_contact_types: Optional[dict[str, str]] = None  # {partner_id: "online"/"physical"}


class PartnerInfo(BaseModel):
    """Информация о партнёре, доступная через tool get_partner_by_id."""
    id: str
    name: str
    notes: Optional[str] = None


class ProjectAction(BaseModel):
    """Структурированная задача проекта (элемент project_actions в DailyMessage)."""
    group: str = Field(
        ..., description="Группа партнёра: 'source', 'ally', 'protege', 'world' или 'project' для общих шагов"
    )
    description: str = Field(
        ..., description="Одно конкретное действие на сегодня в рамках Кармического Проекта"
    )
    why: str = Field(
        ..., description="Краткое кармическое объяснение, зачем это действие важно именно для этого проекта"
    )
    partner_id: Optional[str] = Field(
        default=None,
        description=(
            "ID конкретного партнёра для этого шага. "
            "Если шаг про конкретного человека, выбери один из id из project_partners для соответствующей категории. "
            "Если шаг общий и не привязан к одному человеку — оставь пустым."
        ),
    )
    partner_name: Optional[str] = Field(
        default=None,
        description=(
            "Человекочитаемое имя партнёра для текста сообщения. "
            "При необходимости получи его через инструмент get_partner_by_id(partner_id). "
            "Для общих шагов оставь пустым."
        ),
    )
    action_type: str = Field(
        ...,
        description=(
            "Качество, которое тренирует это действие: одно из 'giving', 'kindness', 'patience', "
            "'effort', 'concentration', 'wisdom'."
        ),
    )


class DailyMessage(BaseModel):
    """Structured daily message output"""
    greeting: str
    motivation: str
    actions: list[str]
    project_actions: list[ProjectAction] | None = None
    closing: str


def create_daily_agent() -> Agent[MessageContext, DailyMessage]:
    """
    Create Pydantic AI agent with configured model
    
    Returns:
        Configured Agent instance
    """
    # Initialize configured model
    model = get_model()
    
    # Create agent with proper typing
    agent = Agent(
        model=model,
        deps_type=MessageContext,
        output_type=DailyMessage,
        system_prompt=(
            "Ты - мудрый кармический менеджер, основанный на философии Diamond Cutter. "
            "Твоя задача - помогать людям улучшать жизнь через понимание кармы и правильные действия. "
            "Говори дружелюбно, но мудро. Используй метафоры из алмазов и семян. "
            "Если у пользователя есть Активный Кармический Проект (Karma Plan), твои советы и действия "
            "должны быть СТРОГО направлены на реализацию его стратегии (STOP/START/GROW). "
            "Иначе включай действия для 4 универсальных категорий партнёров. "
            "\n\nКатегории партнёров:\n"
            "- source (Источник) — тот, кто даёт ресурсы, возможности, поддержку.\n"
            "- ally (Соратник) — партнёр, с кем вы вместе двигаете дела.\n"
            "- protege (Подопечный) — тот, кому ты помогаешь расти и развиваться.\n"
            "- world (Внешний мир) — незнакомые люди, общество в целом.\n"
            "В `project_actions.group` всегда используй эти значения или 'project' для общих шагов без конкретного партнёра.\n"
            "\nСТРУКТУРА project_partners:\n"
            "В контексте тебе передаётся project_partners = {category: {partner_id: partner_name}}.\n"
            "partner_id — технический идентификатор партнёра, partner_name — его человекочитаемое имя.\n"
            "При выборе конкретного человека для шага используй ИМЕННО partner_id в поле ProjectAction.partner_id.\n"
            "\nTOOLS ДЛЯ ПАРТНЁРОВ:\n"
            "У тебя есть инструмент get_partner_by_id(partner_id), который по id возвращает объект с полями id, name, notes.\n"
            "Если тебе нужно вставить в текст сообщения имя или учесть заметку о партнёре, сначала вызови этот инструмент.\n"
            "\nКАЧЕСТВА ДЕЙСТВИЙ (action_type):\n"
            "- giving — даяние и щедрость; посеять богатство, щедро помогая другим.\n"
            "- kindness — доброта и этика; честно помогать, не вредить, соблюдать внутренние принципы.\n"
            "- patience — терпение; мягко выдерживать сложных людей и ситуации без раздражения.\n"
            "- effort — усердие; прилагать стабильные усилия и доводить начатое до конца.\n"
            "- concentration — концентрация; учиться удерживать внимание и делать одно дело осознанно.\n"
            "- wisdom — мудрость; размышлять о причинах, учиться и видеть глубинный смысл происходящего.\n"
            "В каждом ProjectAction подбирай такой action_type, который лучше всего описывает семя, "
            "которое сажает это действие.\n"
            "\нФОРМА PROJECT_ACTIONS:\n"
            "- group = 'source' | 'ally' | 'protege' | 'world' | 'project'.\n"
            "- description — конкретный шаг на сегодня.\n"
            "- why — короткое кармическое объяснение.\n"
            "- partner_id — если шаг про конкретного человека, укажи один из id из project_partners для этой категории; "
            "если шаг общий, оставь partner_id пустым.\n"
            "- partner_name — опциональное человекочитаемое имя (можешь получить его через get_partner_by_id), "
            "для общих шагов оставь пустым.\n"
            "- action_type — одно из: 'giving', 'kindness', 'patience', 'effort', 'concentration', 'wisdom'.\n"
            "\nВАЖНО ПРО ИЗОЛЯЦИЮ И ТИПЫ КОНТАКТА:\n"
            "1. Проверяй `isolation_settings` для каждой категории.\n"
            "   - Если категория помечена как изолированная (`is_isolated: true`), НЕ предлагай социальные действия.\n"
            "   - Вместо этого предлагай: МЕНТАЛЬНЫЕ семена (пожелания счастья), АНОНИМНУЮ помощь, или действия для категории 'Внешний мир'.\n"
            "2. Проверяй `partner_contact_types` для конкретных имен.\n"
            "   - Если контакт `online`: предлагай ТОЛЬКО цифровые действия (написать, позвонить, перевести деньги, оставить комментарий).\n"
            "   - ЗАПРЕЩЕНО предлагать встретиться, сходить на кофе, обнять и т.д. для online-партнеров.\n"
            "3. Если нет ограничений - предлагай разнообразные действия."
        ),
    )

    @agent.tool
    async def get_partner_by_id(ctx: RunContext[MessageContext], partner_id: str) -> PartnerInfo:
        """Получить информацию о партнёре по его ID."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PartnerDB).where(PartnerDB.id == partner_id))
            partner = result.scalar_one_or_none()
            if not partner:
                return PartnerInfo(id=partner_id, name="Неизвестный партнёр", notes=None)
            return PartnerInfo(id=partner.id, name=partner.name, notes=partner.notes)

    @agent.system_prompt
    def add_context(ctx: RunContext[MessageContext]) -> str:
        """Add dynamic context to system prompt"""
        context = ctx.deps
        
        prompt = f"Пользователь: {context.user_name}\n"
        
        if context.user_focus:
            prompt += f"Текущий фокус: {context.user_focus}\n"
        
        if context.plan_strategy:
            prompt += "\n--- АКТИВНЫЙ КАРМИЧЕСКИЙ ПРОЕКТ ---\n"
            prompt += f"Проблема: {context.plan_strategy.get('problem_text', 'Не указана')}\n"
            prompt += f"STOP (что прекратить): {context.plan_strategy.get('stop_action')}\n"
            prompt += f"START (что начать): {context.plan_strategy.get('start_action')}\n"
            prompt += f"GROW (как поливать): {context.plan_strategy.get('grow_action')}\n"
            
            if context.isolation_settings:
                prompt += "\nНастройки изоляции (где НЕТ партнеров):\n"
                for cat, settings in context.isolation_settings.items():
                    if settings.get('is_isolated'):
                        prompt += f"- {cat.upper()}: ИЗОЛИРОВАН (только ментальные/анонимные действия)\n"
            
            if context.project_partners:
                prompt += "\nПартнеры проекта (id → имя):\n"
                for cat, partners in context.project_partners.items():
                    prompt += f"- {cat.upper()}:\n"
                    for pid, name in partners.items():
                        ctype = "physical"
                        if context.partner_contact_types:
                            ctype = context.partner_contact_types.get(pid, "physical")
                        prompt += f"  id={pid} — {name} ({ctype})\n"
            
            prompt += "Твоя задача на утро: сгенерировать 4 конкретных микро-действия на сегодня, " \
                      "которые помогут пользователю реализовать эту стратегию. " \
                      "Действия должны быть простыми, выполнимыми за день и разнообразными.\n" \
                      "Строго следуй ограничениям изоляции и типа контактов (online/physical)!\n"
            prompt += "-----------------------------------\n"
        
        if context.streak_days > 0:
            prompt += f"Серия практик: {context.streak_days} дней подряд\n"
        
        if context.total_seeds > 0:
            prompt += f"Всего посеяно семян: {context.total_seeds}\n"
        
        prompt += f"Время дня: {context.time_of_day}\n"
        
        return prompt
    
    return agent


# Global agent instance
_agent: Optional[Agent] = None


def get_daily_agent() -> Agent[MessageContext, DailyMessage]:
    """Get or create global agent instance"""
    global _agent
    
    if _agent is None:
        _agent = create_daily_agent()
    
    return _agent


async def generate_morning_message(
    user_name: str,
    focus: Optional[str] = None,
    streak_days: int = 0,
    total_seeds: int = 0,
    plan_strategy: Optional[dict] = None,
    project_partners: Optional[dict[str, dict[str, str]]] = None,
    isolation_settings: Optional[dict] = None,
    partner_contact_types: Optional[dict[str, str]] = None,
) -> DailyMessage:
    """
    Generate morning message using AI
    
    Args:
        user_name: User's first name
        focus: Current focus area
        streak_days: Days in a row with practice
        total_seeds: Total seeds planted
        plan_strategy: Active Karma Plan strategy
        project_partners: Кармические партнёры проекта в формате {category: {partner_id: partner_name}}
        isolation_settings: Isolation flags per category
        partner_contact_types: Contact types (online/physical) for partners keyed by partner_id
        
    Returns:
        Structured morning message
    """
    agent = get_daily_agent()
    
    context = MessageContext(
        user_name=user_name,
        user_focus=focus,
        streak_days=streak_days,
        total_seeds=total_seeds,
        time_of_day="morning",
        plan_strategy=plan_strategy,
        project_partners=project_partners,
        isolation_settings=isolation_settings,
        partner_contact_types=partner_contact_types
    )
    
    if plan_strategy:
        prompt = (
            "Создай утреннее сообщение с мотивацией и стратегическим планом для участника Кармического Проекта. "
            "Включи 4 конкретных действия (tasks), которые продвинут его стратегию сегодня. "
            "Если переданы project_partners (id → имя), используй ИМЕННО partner_id для привязки шага к конкретному человеку. "
            "При необходимости получай имя и заметки о партнёре через инструмент get_partner_by_id(partner_id). "
            "УЧИТЫВАЙ настройки изоляции и типы контактов (online/physical). "
            "Будь сфокусированным на его цели. "
            "Отдельно сформируй project_actions — 4 задачи на сегодня с полями group, description, why, "
            "partner_id (id выбранного партнёра или null для общего шага), опциональным partner_name и "
            "action_type (одно из: 'giving', 'kindness', 'patience', 'effort', 'concentration', 'wisdom')."
        )
    else:
        prompt = (
            "Создай утреннее сообщение с мотивацией и планом на день. "
            "Включи 4 конкретных действия для разных групп партнёров. "
            "Будь воодушевляющим и практичным."
        )
    
    await broadcast_status("🌅 Генерирую утреннее напутствие...")
    result = await agent.run(prompt, deps=context)
    return result.output


async def generate_evening_message(
    user_name: str,
    seeds_today: int = 0,
    actions_completed: int = 0
) -> DailyMessage:
    """
    Generate evening reflection message using AI
    
    Args:
        user_name: User's first name
        seeds_today: Seeds planted today
        actions_completed: Actions completed today
        
    Returns:
        Structured evening message
    """
    agent = get_daily_agent()
    
    context = MessageContext(
        user_name=user_name,
        streak_days=0,
        total_seeds=seeds_today,
        time_of_day="evening"
    )
    
    prompt = (
        f"Создай вечернее сообщение для рефлексии. "
        f"Сегодня пользователь посеял {seeds_today} семян и выполнил {actions_completed} действий. "
        f"Поддержи и напомни о важности благодарности. "
        f"Будь спокойным и мудрым."
    )
    
    await broadcast_status("🌙 Подвожу итоги дня...")
    result = await agent.run(prompt, deps=context)
    return result.output
