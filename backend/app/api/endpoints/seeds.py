"""Seeds (karma journal) endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_session,
    get_seed_service,
    SeedCreateRequest,
    SeedCreateResponse,
)
from app.models.db.user import UserDB
from app.models.seed import Seed
from app.repositories.karma_plan import KarmaPlanRepository
from app.services.seed_service import SeedService

logger = logging.getLogger(__name__)
router = APIRouter()

_karma_plan_repo = KarmaPlanRepository()


@router.get("/seeds")
async def get_seeds(
    limit: int = 50,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    seed_svc: SeedService = Depends(get_seed_service),
):
    """Get user's seeds"""
    try:
        seeds_db = await seed_svc.get_user_seeds(db, user.id, limit=limit)

        seeds = [
            {
                "id": seed.id,
                "timestamp": seed.timestamp.isoformat() if seed.timestamp else None,
                "action_type": seed.action_type,
                "description": seed.description,
                "partner_group": seed.partner_group,
                "intention_score": seed.intention_score,
                "emotion_level": seed.emotion_level,
                "strength_multiplier": seed.strength_multiplier,
                "estimated_maturation_days": seed.estimated_maturation_days,
            }
            for seed in seeds_db
        ]

        return {"seeds": seeds}
    except Exception as e:
        logger.error(f"Error getting seeds for user {user.id}: {e}", exc_info=True)
        return {"seeds": []}


@router.post("/seeds", response_model=SeedCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_seed_endpoint(
    payload: SeedCreateRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    seed_svc: SeedService = Depends(get_seed_service),
):
    """Create new seed"""
    try:
        active_plan = await _karma_plan_repo.get_active(db, user.id)
        if not active_plan:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Сейчас у тебя нет активного проекта. Давай сначала мягко соберём его в разделе «Проблема», и после этого семена будут работать стабильно.",
                    "cta_path": "/problem",
                },
            )

        seed = Seed(
            user_id=user.id,
            action_type=payload.action_type,
            description=payload.description,
            partner_group=payload.partner_group,
            intention_score=payload.intention_score,
            emotion_level=payload.emotion_level,
            understanding=payload.understanding,
            estimated_maturation_days=payload.estimated_maturation_days,
            strength_multiplier=payload.strength_multiplier,
            karma_plan_id=active_plan.id,
        )
        seed_db = await seed_svc.create_seed(db, seed)
        await seed_svc.user_repo.increment_seeds_count(db, user.id)
        return SeedCreateResponse(success=True, seed_id=seed_db.id).model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating seed via API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
