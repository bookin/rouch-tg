"""Daily AI Agent using Pydantic AI"""
from typing import Optional
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from app.ai.models import get_model


class MessageContext(BaseModel):
    """Context for message generation"""
    user_name: str
    user_focus: Optional[str] = None
    streak_days: int = 0
    total_seeds: int = 0
    time_of_day: str = "morning"  # morning, evening
    plan_strategy: Optional[dict] = None  # Karma Plan strategy snapshot
    project_partners: Optional[dict[str, list[str]]] = None # {category: ["Name 1", "Name 2"]}


class DailyMessage(BaseModel):
    """Structured daily message output"""
    greeting: str
    motivation: str
    actions: list[str]
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
            "Иначе включай действия для 4 универсальных категорий партнёров: "
            "1. Источник (Source) - родители, учителя; "
            "2. Соратник (Ally) - коллеги, партнеры; "
            "3. Подопечный (Protege) - клиенты, подчиненные; "
            "4. Внешний мир (World) - незнакомцы, общество."
        ),
    )
    
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
            
            if context.project_partners:
                prompt += "Партнеры проекта:\n"
                for cat, names in context.project_partners.items():
                    prompt += f"- {cat.upper()}: {', '.join(names)}\n"
            
            prompt += "Твоя задача на утро: сгенерировать 3 конкретных микро-действия на сегодня, " \
                      "которые помогут пользователю реализовать эту стратегию. " \
                      "Действия должны быть простыми, выполнимыми за день и разнообразными (одно на STOP, одно на START, одно на партнеров).\n" \
                      "Если есть партнеры, обязательно используй их ИМЕНА в действиях для персонализации.\n"
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
    project_partners: Optional[dict[str, list[str]]] = None
) -> DailyMessage:
    """
    Generate morning message using AI
    
    Args:
        user_name: User's first name
        focus: Current focus area
        streak_days: Days in a row with practice
        total_seeds: Total seeds planted
        plan_strategy: Active Karma Plan strategy
        project_partners: Specific partners for the project
        
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
        project_partners=project_partners
    )
    
    if plan_strategy:
        prompt = (
            "Создай утреннее сообщение с мотивацией и стратегическим планом для участника Кармического Проекта. "
            "Включи 3 конкретных действия (tasks), которые продвинут его стратегию сегодня. "
            "Если переданы имена партнеров, используй их в формулировках задач. "
            "Будь сфокусированным на его цели."
        )
    else:
        prompt = (
            "Создай утреннее сообщение с мотивацией и планом на день. "
            "Включи 4 конкретных действия для разных групп партнёров. "
            "Будь воодушевляющим и практичным."
        )
    
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
    
    result = await agent.run(prompt, deps=context)
    return result.output
