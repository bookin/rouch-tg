"""AI module with Pydantic AI agents"""
from .daily_agent import (
    get_daily_agent,
    generate_morning_message,
    generate_evening_message,
    MessageContext,
    DailyMessage
)
from .problem_agent import (
    get_problem_agent,
    solve_problem,
    ProblemContext,
    ProblemSolution
)

__all__ = [
    "get_daily_agent",
    "generate_morning_message",
    "generate_evening_message",
    "MessageContext",
    "DailyMessage",
    "get_problem_agent",
    "solve_problem",
    "ProblemContext",
    "ProblemSolution"
]
