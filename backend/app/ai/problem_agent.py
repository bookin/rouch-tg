"""Problem solving agent with Pydantic AI"""
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.groq import GroqModel
from app.config import get_settings


class ProblemContext(BaseModel):
    """Context for problem solving"""
    problem_description: str
    user_name: str
    correlations: list[dict] = Field(default_factory=list)
    concepts: list[dict] = Field(default_factory=list)


class ProblemSolution(BaseModel):
    """Structured problem solution"""
    problem_summary: str
    root_cause: str
    opposite_action: str
    practice_steps: list[str]
    expected_outcome: str
    timeline_days: int = 30


def create_problem_agent() -> Agent[ProblemContext, ProblemSolution]:
    """Create problem-solving agent"""
    settings = get_settings()
    
    model = GroqModel(
        model_name=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY
    )
    
    agent = Agent(
        model=model,
        deps_type=ProblemContext,
        result_type=ProblemSolution,
        system_prompt=(
            "Ты - эксперт по кармическим корреляциям из Diamond Cutter. "
            "Твоя задача - найти кармическую причину проблемы и предложить 'противоположное действие'. "
            "Используй знания из базы корреляций. "
            "Всегда давай конкретные практические шаги."
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
        "Проанализируй проблему используя корреляции и концепции. "
        "Определи кармическую причину (что пользователь делал неправильно). "
        "Предложи 'противоположное действие' - что нужно делать вместо этого. "
        "Создай конкретный план на 30 дней."
    )
    
    result = await agent.run(prompt, deps=context)
    return result.data
