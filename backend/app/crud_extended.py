from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, UTC
from uuid import uuid4
from typing import Optional, List
from app.models.db_models import KarmaPlanDB, DailyPlanDB

async def create_karma_plan(
    db: AsyncSession,
    user_id: int,
    problem_history_id: str,
    strategy_snapshot: dict,
    duration_days: int = 30,
    project_partners: dict = None,
    isolation_settings: dict = None
) -> KarmaPlanDB:
    """Create a new Karma Plan (Karmic Project)"""
    from app.models.db_models import KarmaPlanDB, DailyPlanDB
    
    # 1. Deactivate existing active plans
    from sqlalchemy import update
    await db.execute(
        update(KarmaPlanDB)
        .where(KarmaPlanDB.user_id == user_id, KarmaPlanDB.status == "active")
        .values(status="cancelled", updated_at=datetime.now(UTC))
    )
    
    # 2. Create new plan
    plan_id = str(uuid4())
    plan = KarmaPlanDB(
        id=plan_id,
        user_id=user_id,
        problem_history_id=problem_history_id,
        status="active",
        strategy_snapshot=strategy_snapshot,
        duration_days=duration_days,
        isolation_settings=isolation_settings,
        start_date=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db.add(plan)
    
    # 2.1 Save partners mapping if provided
    if project_partners:
        from app.models.db_models import KarmaPlanPartnerDB
        for category, partner_ids in project_partners.items():
            for pid in partner_ids:
                assoc = KarmaPlanPartnerDB(
                    plan_id=plan_id,
                    partner_id=pid,
                    category=category
                )
                db.add(assoc)

    await db.flush()
    await db.refresh(plan)
    return plan


async def get_active_karma_plan(db: AsyncSession, user_id: int) -> Optional[KarmaPlanDB]:
    """Get user's currently active Karma Plan"""
    from app.models.db_models import KarmaPlanDB
    result = await db.execute(
        select(KarmaPlanDB)
        .where(KarmaPlanDB.user_id == user_id, KarmaPlanDB.status == "active")
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_daily_plan(db: AsyncSession, karma_plan_id: str, date: datetime) -> Optional[DailyPlanDB]:
    """Get daily plan for a specific date"""
    from app.models.db_models import DailyPlanDB
    
    # Compare by date only (ignoring time)
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = date.replace(hour=23, minute=59, second=59, microsecond=999)
    
    result = await db.execute(
        select(DailyPlanDB)
        .where(
            DailyPlanDB.karma_plan_id == karma_plan_id,
            DailyPlanDB.date >= day_start,
            DailyPlanDB.date <= day_end
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_daily_plan(
    db: AsyncSession,
    karma_plan_id: str,
    day_number: int,
    date: datetime,
    focus_quality: str,
    tasks: list,
    message_snapshot: Optional[dict] = None,
) -> DailyPlanDB:
    """Create a new daily plan"""
    from app.models.db_models import DailyPlanDB
    
    daily = DailyPlanDB(
        id=str(uuid4()),
        karma_plan_id=karma_plan_id,
        day_number=day_number,
        date=date,
        focus_quality=focus_quality,
        tasks=tasks,
        message_snapshot=message_snapshot,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db.add(daily)
    await db.flush()
    await db.refresh(daily)
    return daily
