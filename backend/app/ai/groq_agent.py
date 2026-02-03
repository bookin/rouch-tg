"""Groq AI Agent using Pydantic AI"""
from typing import Optional
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.groq import GroqModel
from app.config import get_settings


class MessageContext(BaseModel):
    """Context for message generation"""
    user_name: str
    user_focus: Optional[str] = None
    streak_days: int = 0
    total_seeds: int = 0
    time_of_day: str = "morning"  # morning, evening


class DailyMessage(BaseModel):
    """Structured daily message output"""
    greeting: str
    motivation: str
    actions: list[str]
    closing: str


def create_groq_agent() -> Agent[MessageContext, DailyMessage]:
    """
    Create Pydantic AI agent with Groq model
    
    Returns:
        Configured Agent instance
    """
    settings = get_settings()
    
    # Initialize Groq model
    model = GroqModel(
        model_name=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY
    )
    
    # Create agent with proper typing
    agent = Agent(
        model=model,
        deps_type=MessageContext,
        result_type=DailyMessage,
        system_prompt=(
            "Ты - мудрый кармический менеджер, основанный на философии Diamond Cutter. "
            "Твоя задача - помогать людям улучшать жизнь через понимание кармы и правильные действия. "
            "Говори дружелюбно, но мудро. Используй метафоры из алмазов и семян. "
            "Всегда включай конкретные действия для 4 групп партнёров: коллеги, клиенты, поставщики, мир."
        ),
    )
    
    @agent.system_prompt
    def add_context(ctx: RunContext[MessageContext]) -> str:
        """Add dynamic context to system prompt"""
        context = ctx.deps
        
        prompt = f"Пользователь: {context.user_name}\n"
        
        if context.user_focus:
            prompt += f"Текущий фокус: {context.user_focus}\n"
        
        if context.streak_days > 0:
            prompt += f"Серия практик: {context.streak_days} дней подряд\n"
        
        if context.total_seeds > 0:
            prompt += f"Всего посеяно семян: {context.total_seeds}\n"
        
        prompt += f"Время дня: {context.time_of_day}\n"
        
        return prompt
    
    return agent


# Global agent instance
_agent: Optional[Agent] = None


def get_groq_agent() -> Agent[MessageContext, DailyMessage]:
    """Get or create global agent instance"""
    global _agent
    
    if _agent is None:
        _agent = create_groq_agent()
    
    return _agent


async def generate_morning_message(
    user_name: str,
    focus: Optional[str] = None,
    streak_days: int = 0,
    total_seeds: int = 0
) -> DailyMessage:
    """
    Generate morning message using AI
    
    Args:
        user_name: User's first name
        focus: Current focus area
        streak_days: Days in a row with practice
        total_seeds: Total seeds planted
        
    Returns:
        Structured morning message
    """
    agent = get_groq_agent()
    
    context = MessageContext(
        user_name=user_name,
        user_focus=focus,
        streak_days=streak_days,
        total_seeds=total_seeds,
        time_of_day="morning"
    )
    
    prompt = (
        "Создай утреннее сообщение с мотивацией и планом на день. "
        "Включи 4 конкретных действия для разных групп партнёров. "
        "Будь воодушевляющим и практичным."
    )
    
    result = await agent.run(prompt, deps=context)
    return result.data


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
    agent = get_groq_agent()
    
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
    return result.data
