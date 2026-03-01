"""Problem solving and history endpoints."""
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_session,
    user_db_to_profile,
    AddToCalendarRequest,
    ProblemSolveRequest,
    ProblemSolveResponse,
)
from app.models.db.user import UserDB
from app.repositories.karma_plan import KarmaPlanRepository
from app.repositories.problem import ProblemHistoryRepository

logger = logging.getLogger(__name__)
router = APIRouter()

_karma_plan_repo = KarmaPlanRepository()
_problem_repo = ProblemHistoryRepository()


@router.get("/problems/history")
async def get_problems_history(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get problem history"""
    active_plan = await _karma_plan_repo.get_active(db, user.id)
    active_history_id = active_plan.problem_history_id if active_plan else None

    history = await _problem_repo.get_by_user(db, user.id)
    return {
        "history": [
            {
                "id": h.id,
                "problem_text": h.problem_text,
                "solution": h.solution_json,
                "is_active": bool(active_history_id and h.id == active_history_id),
                "created_at": h.created_at,
            }
            for h in history
        ]
    }


@router.post("/problem/solve", response_model=ProblemSolveResponse)
async def solve_problem_endpoint(
    payload: ProblemSolveRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Solve problem using AI agent and knowledge base"""
    from app.agents.problem_solver import ProblemSolverAgent
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings

    settings = get_settings()
    qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
    agent = ProblemSolverAgent(qdrant)

    session_id = payload.session_id or f"web_{user.id}_{uuid4().hex[:8]}"
    user_profile = user_db_to_profile(user)

    solution = await agent.analyze_problem(
        user_profile,
        payload.problem,
        session_id=session_id,
        diagnostic_answer=payload.diagnostic_answer,
    )

    solution["session_id"] = session_id

    if not solution.get("needs_clarification"):
        history_item = await _problem_repo.save(
            db,
            user_id=user.id,
            problem_text=payload.problem,
            solution_json=solution,
        )
        solution["history_id"] = history_item.id

    return solution


@router.post("/problem/add-to-calendar")
async def add_problem_to_calendar(
    _payload: AddToCalendarRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add 30-day plan steps to calendar"""
    active_plan = await _karma_plan_repo.get_active(db, user.id)
    if not active_plan:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Чтобы сохранить план на 30 дней, нужен активный проект. Давай запустим его — и план станет твоими задачами дня.",
                "cta_path": "/problem",
            },
        )

    return {
        "success": True,
        "count": 0,
        "message": "У тебя уже есть активный проект — план на 30 дней уже хранится там. Открой проект, и он будет вести тебя шаг за шагом.",
    }
