"""Daily actions endpoints."""
import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, get_daily_service, UpdateActionCompletionRequest
from app.models.db.user import UserDB
from app.repositories.karma_plan import KarmaPlanRepository
from app.services.daily_service import DailyService

logger = logging.getLogger(__name__)
router = APIRouter()

_karma_plan_repo = KarmaPlanRepository()


@router.get(
    "/daily/actions",
    summary="Get daily actions",
    description="Retrieve personalized daily actions based on user profile and current focus",
)
async def get_daily_actions(user: UserDB = Depends(get_current_user)):
    """Get 4 daily actions"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.agents.daily_manager import DailyManagerAgent
    from app.config import get_settings

    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        agent = DailyManagerAgent(qdrant)

        actions = await agent.get_daily_actions(
            user_id=user.id,
            first_name=user.first_name,
            streak_days=user.streak_days,
            total_seeds=user.total_seeds,
        )

        return {"actions": actions}
    except Exception as e:
        logger.error(f"Error getting daily actions: {e}", exc_info=True)
        return {"actions": []}


@router.patch("/daily/actions/{action_id}")
async def update_action_completion(
    action_id: str,
    payload: UpdateActionCompletionRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    daily_svc: DailyService = Depends(get_daily_service),
):
    """Toggle daily action completion for project tasks (DailyTaskDB only)."""
    if not action_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid action id for project task")

    active_plan = await _karma_plan_repo.get_active(db, user.id)
    if not active_plan:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Сейчас у тебя нет активного проекта. Давай сначала мягко соберём его — и после этого можно будет отмечать шаги дня.",
                "cta_path": "/problem",
            },
        )

    daily_plan = await daily_svc.daily_plan_repo.get_by_karma_plan_and_date(
        db, active_plan.id, datetime.now(UTC)
    )
    if not daily_plan:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Я не вижу план на сегодня. Открой кофе‑медитацию — и я подхвачу всё аккуратно.",
                "cta_path": "/coffee",
            },
        )

    task_id = int(action_id)
    task = await daily_svc.daily_task_repo.get(db, task_id)
    if not task or task.daily_plan_id != daily_plan.id:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Этот шаг не относится к сегодняшнему дню проекта. Давай отметим всё прямо в кофе‑медитации — там будет проще.",
                "cta_path": "/coffee",
            },
        )

    await daily_svc.toggle_task_completion(db, user.id, task_id, payload.completed)
    return {"success": True}


@router.get(
    "/quote/daily",
    summary="Get daily quote",
    description="Retrieve a daily quote from the knowledge base relevant to user's current focus",
)
async def get_daily_quote(user: UserDB = Depends(get_current_user)):
    """Get quote for the day"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings

    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        quote = await qdrant.get_daily_quote(None)
        return quote
    except Exception as e:
        logger.error(f"Error getting daily quote: {e}", exc_info=True)
        return {
            "text": "Даяние приносит богатство, но не размер суммы важен, а щедрое состояние ума",
            "author": "Геше Майкл Роуч",
            "context": "О богатстве",
            "source": "diamond-concepts.md",
        }
