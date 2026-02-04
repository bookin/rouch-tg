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


def create_problem_agent() -> Agent[ProblemContext, ProblemSolution]:
    """Create problem-solving agent"""
    
    model = get_model()
    
    agent = Agent(
        model=model,
        deps_type=ProblemContext,
        output_type=ProblemSolution,
        system_prompt=(
            "Ты - эксперт по кармическому менеджменту системы Diamond Cutter (Геше Майкл Роуч). "
            "Твоя задача - проанализировать проблему пользователя и дать глубокое решение, основанное на системе 'отпечатков' (seeds). "
            "\n\nМетодология:\n"
            "1. Идентифицируй КОРЕНЬ: какой негативный отпечаток из прошлого создал эту ситуацию сейчас. "
            "2. Объясни ЛОГИКУ: как именно 'мир из меня' работает в этом случае (механизм проекции). "
            "3. Решение 'STOP-START-GROW':\n"
            "   - STOP: что именно нужно перестать делать, чтобы не 'подпитывать' плохой отпечаток.\n"
            "   - START: какое противоположное действие создаст нужный результат.\n"
            "   - GROW: как правильно радоваться и 'поливать' семена (медитация кофе).\n"
            "\nИспользуй предоставленные корреляции и концепции как основу, но расширяй их глубоким пониманием системы."
        ),
    )
    
    @agent.system_prompt
    def add_problem_context(ctx: RunContext[ProblemContext]) -> str:
        """Add problem context"""
        context = ctx.deps
        
        prompt = f"Проблема пользователя {context.user_name}: {context.problem_description}\n\n"
        
        if context.correlations:
            prompt += "Найденные корреляции из базы знаний:\n"
            for corr in context.correlations[:3]:
                prompt += f"- Проблема: {corr.get('problem', '')}\n"
                prompt += f"  Причина: {corr.get('cause', '')}\n"
                prompt += f"  Решение: {corr.get('solution', '')}\n\n"
        
        if context.concepts:
            prompt += "Связанные концепции:\n"
            for concept in context.concepts[:2]:
                prompt += f"- {concept.get('title', '')}: {concept.get('content', '')[:100]}...\n"
        
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
    concepts: list[dict]
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
        concepts=concepts
    )
    
    prompt = (
        "Проанализируй проблему пользователя, используя корреляции и концепции.\n"
        "1. Объясни кармическую причину (root_cause).\n"
        "2. Раскрой механизм imprint_logic (почему это работает именно так).\n"
        "3. Сформулируй STOP, START и GROW действия.\n"
        "4. Составь план шагов и дай совет по ускорению (success_tip).\n"
        "Будь вдохновляющим, но очень точным в кармической логике."
    )
    
    result = await agent.run(prompt, deps=context)
    return result.output
