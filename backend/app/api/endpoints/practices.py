"""Practice endpoints."""
import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, get_practice_service, PracticeCompleteRequest
from app.models.db.user import UserDB
from app.models.db.practice import PracticeDB
from app.repositories.karma_plan import KarmaPlanRepository
from app.services.practice_service import PracticeService

logger = logging.getLogger(__name__)
router = APIRouter()

_karma_plan_repo = KarmaPlanRepository()


@router.get("/practices")
async def get_practices(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=0, description="Limit results, 0 = all"),
):
    """Get all practices from PracticeDB (canonical source)"""
    try:
        stmt = select(PracticeDB).order_by(PracticeDB.category, PracticeDB.name)
        if limit > 0:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        practices_db = result.scalars().all()
        practices = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "duration": p.duration_minutes,
                "difficulty": p.difficulty,
                "physical_intensity": p.physical_intensity,
                "requires_morning": p.requires_morning,
                "requires_silence": p.requires_silence,
                "max_completions_per_day": p.max_completions_per_day,
                "steps": p.steps or [],
                "contraindications": p.contraindications or [],
                "benefits": p.benefits,
                "tags": p.tags or [],
            }
            for p in practices_db
        ]
        return {"practices": practices}
    except Exception as e:
        logger.error(f"Error getting practices: {e}", exc_info=True)
        return {"practices": []}


@router.post("/practices/{practice_id}/start")
async def start_practice_tracking(
    practice_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Начать отслеживание практики (PracticeDB must exist)"""
    try:
        practice_result = await db.execute(
            select(PracticeDB).where(PracticeDB.id == practice_id).limit(1)
        )
        practice = practice_result.scalar_one_or_none()
        if not practice:
            return {"error": "Practice not found in catalog"}

        active_plan = await _karma_plan_repo.get_active(db, user.id)
        plan_id = active_plan.id if active_plan else None

        progress = await practice_svc.practice_repo.get_or_create(
            db, user.id, practice_id, karma_plan_id=plan_id
        )

        return {
            "practice_id": practice_id,
            "tracking_started": True,
            "habit_score": progress.habit_score,
            "streak_days": progress.streak_days,
        }
    except Exception as e:
        logger.error(f"Error starting practice tracking: {e}", exc_info=True)
        return {"error": "Failed to start tracking"}


@router.post("/practices/{practice_id}/complete")
async def complete_practice(
    practice_id: str,
    request: PracticeCompleteRequest | None = None,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Отметить выполнение практики"""
    if request is None:
        request = PracticeCompleteRequest()

    try:
        active_plan = await _karma_plan_repo.get_active(db, user.id)

        result = await practice_svc.complete_and_create_seed(
            db,
            user_id=user.id,
            practice_id=practice_id,
            karma_plan_id=(active_plan.id if active_plan else None),
            emotion_score=request.emotion_score,
        )

        return {
            "practice_id": practice_id,
            "completed": result["actually_updated"],
            "habit_score": result["progress"].habit_score,
            "streak_days": result["progress"].streak_days,
            "is_habit": result["progress"].is_habit,
            "seed_created": result["seed"].id if result["seed"] else None,
            "is_new_habit": result["is_new_habit"],
        }
    except Exception as e:
        logger.error(f"Error completing practice: {e}", exc_info=True)
        return {"error": "Failed to complete practice"}


@router.get("/practices/progress")
async def get_practices_progress(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Получить прогресс всех практик (включая привычки)"""
    try:
        progress_list = await practice_svc.get_user_progress(db, user.id)

        today = datetime.now(UTC).date()

        result = []
        for progress in progress_list:
            practice = progress.practice
            max_per_day = (practice.max_completions_per_day if practice else 1) or 1

            can_complete_today = (
                progress.is_active
                and not progress.is_hidden
                and (
                    not progress.last_completed
                    or progress.last_completed.date() != today
                    or max_per_day > 1
                )
            )

            result.append(
                {
                    "practice_id": progress.practice_id,
                    "practice_name": practice.name if practice else "Unknown",
                    "practice_category": practice.category if practice else "",
                    "practice_duration": practice.duration_minutes if practice else 0,
                    "habit_score": progress.habit_score,
                    "streak_days": progress.streak_days,
                    "total_completions": progress.total_completions,
                    "last_completed": progress.last_completed.isoformat() if progress.last_completed else None,
                    "is_habit": progress.is_habit,
                    "is_active": progress.is_active,
                    "is_hidden": progress.is_hidden,
                    "can_complete_today": can_complete_today,
                    "habit_min_streak_days": practice.habit_min_streak_days if practice else 14,
                    "habit_min_score": practice.habit_min_score if practice else 70,
                }
            )

        return {"progress": result}
    except Exception as e:
        logger.error(f"Error getting practice progress: {e}", exc_info=True)
        return {"progress": []}


@router.post("/practices/{practice_id}/pause")
async def pause_practice_endpoint(
    practice_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Приостановить практику"""
    try:
        ok = await practice_svc.pause(db, user.id, practice_id)
        return {"success": ok}
    except Exception as e:
        logger.error(f"Error pausing practice: {e}", exc_info=True)
        return {"error": "Failed to pause practice"}


@router.post("/practices/{practice_id}/resume")
async def resume_practice_endpoint(
    practice_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Возобновить практику"""
    try:
        ok = await practice_svc.resume(db, user.id, practice_id)
        return {"success": ok}
    except Exception as e:
        logger.error(f"Error resuming practice: {e}", exc_info=True)
        return {"error": "Failed to resume practice"}


@router.post("/practices/{practice_id}/hide")
async def hide_practice_endpoint(
    practice_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Скрыть практику из списков"""
    try:
        ok = await practice_svc.hide(db, user.id, practice_id)
        return {"success": ok}
    except Exception as e:
        logger.error(f"Error hiding practice: {e}", exc_info=True)
        return {"error": "Failed to hide practice"}


@router.post("/practices/{practice_id}/reset")
async def reset_practice_endpoint(
    practice_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Сбросить прогресс практики"""
    try:
        ok = await practice_svc.reset(db, user.id, practice_id)
        return {"success": ok}
    except Exception as e:
        logger.error(f"Error resetting practice: {e}", exc_info=True)
        return {"error": "Failed to reset practice"}


@router.delete("/practices/{practice_id}")
async def delete_practice_endpoint(
    practice_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """Удалить практику и все связанные семена"""
    try:
        deleted_seeds = await practice_svc.delete_all(db, user.id, practice_id)
        return {"success": True, "deleted_seeds": deleted_seeds}
    except Exception as e:
        logger.error(f"Error deleting practice: {e}", exc_info=True)
        return {"error": "Failed to delete practice"}


def _build_recommend_query(strategy: dict | None) -> str:
    """Build Qdrant search query from active plan strategy or default"""
    if strategy:
        need = f"{strategy.get('problem_text', '')} {strategy.get('stop_action', '')} {strategy.get('start_action', '')} {strategy.get('grow_action', '')}".strip()
        if need:
            return need
    return "общее развитие, осознанность, кармические практики"


@router.get("/practices/recommend")
async def get_practice_recommendations(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    practice_svc: PracticeService = Depends(get_practice_service),
):
    """AI рекомендации практик (M6: единый источник для dashboard и бота)"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings

    try:
        existing_progress = await practice_svc.get_user_progress(db, user.id)
        existing_ids = {str(p.practice_id) for p in existing_progress}

        active_plan = await _karma_plan_repo.get_active(db, user.id)
        strategy = active_plan.strategy_snapshot if active_plan else None
        need = _build_recommend_query(strategy)

        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)

        recommendations = await qdrant.search_practice(
            need=need,
            restrictions=user.physical_restrictions.split(",") if user.physical_restrictions else None,
            limit=8,
        )

        filtered = [r for r in recommendations if str(r.get("id", "")) not in existing_ids]

        return {"recommendations": filtered[:6]}

    except Exception as e:
        logger.error(f"Error getting practice recommendations: {e}", exc_info=True)
        return {"recommendations": []}
