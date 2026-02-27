"""Calendar API endpoints"""
from fastapi import APIRouter, Depends, Query
from typing import Dict, Any
from datetime import date, datetime
from pydantic import BaseModel
from sqlalchemy import select, func, literal
import logging

from app.models.user import UserProfile
from app.api.webapp import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar", tags=["Calendar"])


class SeedCalendarItem(BaseModel):
    """Seed item for calendar view"""
    id: str
    timestamp: datetime
    action_type: str
    description: str
    partner_group: str = "world"


class PracticeCalendarItem(BaseModel):
    """Practice completion item for calendar view"""
    id: str
    timestamp: datetime
    name: str
    duration: int = 10


class PartnerActionCalendarItem(BaseModel):
    """Partner action item for calendar view"""
    id: str
    timestamp: datetime
    partner_name: str | None = None
    action: str
    completed: bool = False


class CalendarDataResponse(BaseModel):
    seeds: list[SeedCalendarItem]
    practices: list[PracticeCalendarItem]
    partnerActions: list[PartnerActionCalendarItem]


class TopPartnerStat(BaseModel):
    name: str
    count: int


class CalendarStatsResponse(BaseModel):
    seedsCount: int
    practicesCount: int
    partnerActionsCount: int
    streakDays: int
    topPartners: list[TopPartnerStat] = []


@router.get(
    "/data",
    response_model=CalendarDataResponse,
    summary="Get calendar data",
    description="Retrieve all calendar events (seeds, habits, practices, partner actions) for a date range"
)
async def get_calendar_data(
    start_date: date = Query(..., description="Start date for calendar range"),
    end_date: date = Query(..., description="End date for calendar range"),
    user: UserProfile = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all calendar events for the specified date period"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from app.models.db_models import SeedDB, PracticeDB, PartnerActionDB, PartnerDB
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, user.telegram_id)
            if not user_db:
                return {"seeds": [], "practices": [], "partnerActions": []}
            
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            
            # Get seeds
            seeds_result = await db.execute(
                select(SeedDB).where(
                    SeedDB.user_id == user_db.id,
                    SeedDB.timestamp >= start_dt,
                    SeedDB.timestamp <= end_dt
                )
            )
            seeds = [
                SeedCalendarItem(
                    id=s.id,
                    timestamp=s.timestamp,
                    action_type=s.action_type,
                    description=s.description,
                    partner_group=s.partner_group or "world",
                )
                for s in seeds_result.scalars().all()
            ]
            
            # Get practice completions (seeds with practice_id)
            practices_stmt = (
                select(SeedDB, PracticeDB)
                .outerjoin(PracticeDB, PracticeDB.id == SeedDB.practice_id)
                .where(
                    SeedDB.user_id == user_db.id,
                    SeedDB.practice_id.isnot(None),
                    SeedDB.timestamp >= start_dt,
                    SeedDB.timestamp <= end_dt,
                )
            )
            practices_rows = (await db.execute(practices_stmt)).all()
            practices: list[PracticeCalendarItem] = []
            for seed, practice in practices_rows:
                name = practice.name if practice else seed.practice_id or "Unknown"
                duration = practice.duration_minutes if practice else 10

                practices.append(
                    PracticeCalendarItem(
                        id=seed.id,
                        timestamp=seed.timestamp,
                        name=str(name),
                        duration=int(duration),
                    )
                )
            
            # Get partner actions
            actions_stmt = (
                select(PartnerActionDB, PartnerDB)
                .outerjoin(PartnerDB, PartnerDB.id == PartnerActionDB.partner_id)
                .where(
                    PartnerActionDB.user_id == user_db.id,
                    PartnerActionDB.timestamp >= start_dt,
                    PartnerActionDB.timestamp <= end_dt,
                )
            )
            actions_rows = (await db.execute(actions_stmt)).all()
            partner_actions: list[PartnerActionCalendarItem] = []
            for action_db, partner_db in actions_rows:
                partner_name = action_db.partner_name or (partner_db.name if partner_db is not None else None)
                partner_actions.append(
                    PartnerActionCalendarItem(
                        id=action_db.id,
                        timestamp=action_db.timestamp,
                        partner_name=partner_name,
                        action=action_db.action,
                        completed=bool(action_db.completed),
                    )
                )
            
            return {
                "seeds": seeds,
                "practices": practices,
                "partnerActions": partner_actions
            }
    except Exception as e:
        logger.error(f"Error getting calendar data for user {user.id}: {e}", exc_info=True)
        return {"seeds": [], "practices": [], "partnerActions": []}


@router.get("/stats", response_model=CalendarStatsResponse)
async def get_calendar_stats(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user: UserProfile = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get statistics for the period"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from app.models.db_models import SeedDB, PartnerActionDB, PartnerDB
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, user.telegram_id)
            if not user_db:
                return CalendarStatsResponse(
                    seedsCount=0,
                    practicesCount=0,
                    partnerActionsCount=0,
                    streakDays=0,
                    topPartners=[],
                ).model_dump()
            
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            
            # Count seeds
            seeds_count = await db.execute(
                select(func.count(SeedDB.id)).where(
                    SeedDB.user_id == user_db.id,
                    SeedDB.timestamp >= start_dt,
                    SeedDB.timestamp <= end_dt
                )
            )
            
            # Count practices (seeds with practice_id)
            practices_count = await db.execute(
                select(func.count(SeedDB.id)).where(
                    SeedDB.user_id == user_db.id,
                    SeedDB.practice_id.isnot(None),
                    SeedDB.timestamp >= start_dt,
                    SeedDB.timestamp <= end_dt
                )
            )
            
            # Count partner actions
            actions_count = await db.execute(
                select(func.count(PartnerActionDB.id)).where(
                    PartnerActionDB.user_id == user_db.id,
                    PartnerActionDB.timestamp >= start_dt,
                    PartnerActionDB.timestamp <= end_dt
                )
            )
            
            # Top partners
            partner_name_expr = func.coalesce(
                PartnerActionDB.partner_name,
                PartnerDB.name,
                literal("Unknown"),
            )
            top_partners_result = await db.execute(
                select(partner_name_expr.label("name"), func.count(PartnerActionDB.id).label("count"))
                .outerjoin(PartnerDB, PartnerDB.id == PartnerActionDB.partner_id)
                .where(
                    PartnerActionDB.user_id == user_db.id,
                    PartnerActionDB.timestamp >= start_dt,
                    PartnerActionDB.timestamp <= end_dt,
                )
                .group_by(partner_name_expr)
                .order_by(func.count(PartnerActionDB.id).desc())
                .limit(5)
            )
            top_partners = [{"name": name, "count": count} for name, count in top_partners_result.all()]
            
            return {
                "seedsCount": seeds_count.scalar() or 0,
                "practicesCount": practices_count.scalar() or 0,
                "partnerActionsCount": actions_count.scalar() or 0,
                "streakDays": user_db.streak_days,
                "topPartners": top_partners
            }
    except Exception as e:
        logger.error(f"Error getting calendar stats for user {user.id}: {e}", exc_info=True)
        return CalendarStatsResponse(
            seedsCount=0,
            practicesCount=0,
            partnerActionsCount=0,
            streakDays=0,
            topPartners=[],
        ).model_dump()
