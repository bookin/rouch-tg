"""Coffee meditation endpoints."""
import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_session,
    get_daily_service,
    CoffeeProgressRequest,
    CoffeeCompleteRequest,
)
from app.models.db.user import UserDB
from app.models.db.coffee import CoffeeMeditationSessionDB
from app.models.db.daily import DailyPlanDB
from app.repositories.karma_plan import KarmaPlanRepository
from app.services.daily_service import DailyService

logger = logging.getLogger(__name__)
router = APIRouter()

_karma_plan_repo = KarmaPlanRepository()


@router.get("/coffee/today")
async def get_coffee_today(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    from app.coffee_meditation import get_local_day_bounds, get_rejoiced_seed_ids, get_today_daily_plan, get_today_seeds, get_user_zoneinfo

    active_plan = await _karma_plan_repo.get_active(db, user.id)
    if not active_plan:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Кофе‑медитация работает, когда есть активный проект. Давай сначала соберём его — это займёт несколько спокойных шагов.",
                "cta_path": "/problem",
            },
        )

    user_tz = get_user_zoneinfo(user.timezone)
    bounds = get_local_day_bounds(datetime.now(UTC), user_tz)

    daily_plan = await get_today_daily_plan(
        db,
        karma_plan_id=active_plan.id,
        utc_start=bounds.utc_start,
        utc_end=bounds.utc_end,
    )

    session_result = await db.execute(
        select(CoffeeMeditationSessionDB).where(
            CoffeeMeditationSessionDB.user_id == user.id,
            CoffeeMeditationSessionDB.local_date == bounds.local_date,
        )
    )
    session = session_result.scalar_one_or_none()
    rejoiced_seed_ids: list[str] = []
    if session:
        rejoiced_seed_ids = await get_rejoiced_seed_ids(db, session_id=session.id)

    seeds_db = await get_today_seeds(
        db,
        user_id=user.id,
        utc_start=bounds.utc_start,
        utc_end=bounds.utc_end,
    )

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
            "rejoice_count": seed.rejoice_count,
            "last_rejoiced_at": seed.last_rejoiced_at.isoformat() if seed.last_rejoiced_at else None,
        }
        for seed in seeds_db
    ]

    daily_data = None
    if daily_plan:
        tasks_data = []
        if daily_plan.tasks:
            sorted_tasks = sorted(
                daily_plan.tasks,
                key=lambda t: t.order if t.order is not None else 0,
            )
            tasks_data = [
                {
                    "id": str(t.id),
                    "description": t.description,
                    "why": t.why,
                    "group": t.group,
                    "completed": t.completed,
                }
                for t in sorted_tasks
            ]

        daily_data = {
            "id": daily_plan.id,
            "day_number": daily_plan.day_number,
            "focus_quality": daily_plan.focus_quality,
            "tasks": tasks_data,
            "is_completed": daily_plan.is_completed,
        }

    session_data = None
    if session:
        session_data = {
            "id": session.id,
            "current_step": session.current_step,
            "notes_draft": session.notes_draft,
            "notes": session.notes,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "rejoiced_seed_ids": rejoiced_seed_ids,
        }

    return {
        "has_active_project": True,
        "local_date": bounds.local_date.isoformat(),
        "utc_start": bounds.utc_start.isoformat(),
        "utc_end": bounds.utc_end.isoformat(),
        "session": session_data,
        "seeds": seeds,
        "daily_plan": daily_data,
    }


@router.post("/coffee/progress")
async def save_coffee_progress(
    payload: CoffeeProgressRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    from app.coffee_meditation import get_local_day_bounds, get_rejoiced_seed_ids, get_today_daily_plan, get_user_zoneinfo, get_or_create_session, save_progress

    active_plan = await _karma_plan_repo.get_active(db, user.id)
    if not active_plan:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Сейчас у тебя нет активного проекта. Давай сначала спокойно соберём его — и кофемедитация сразу оживёт.",
                "cta_path": "/problem",
            },
        )

    user_tz = get_user_zoneinfo(user.timezone)
    bounds = get_local_day_bounds(datetime.now(UTC), user_tz)

    daily_plan = await get_today_daily_plan(
        db,
        karma_plan_id=active_plan.id,
        utc_start=bounds.utc_start,
        utc_end=bounds.utc_end,
    )

    session = await get_or_create_session(
        db,
        user_id=user.id,
        local_date=bounds.local_date,
        karma_plan_id=active_plan.id,
        daily_plan_id=daily_plan.id if daily_plan else None,
    )

    await save_progress(
        db,
        session=session,
        user_id=user.id,
        current_step=payload.current_step,
        notes_draft=payload.notes_draft,
        rejoiced_seed_ids=payload.rejoiced_seed_ids,
    )

    rejoiced_seed_ids = await get_rejoiced_seed_ids(db, session_id=session.id)
    return {
        "success": True,
        "session": {
            "id": session.id,
            "current_step": session.current_step,
            "notes_draft": session.notes_draft,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "rejoiced_seed_ids": rejoiced_seed_ids,
        },
    }


@router.post("/coffee/complete")
async def complete_coffee(
    payload: CoffeeCompleteRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    daily_svc: DailyService = Depends(get_daily_service),
):
    from app.coffee_meditation import complete_session, get_local_day_bounds, get_today_daily_plan, get_user_zoneinfo, get_or_create_session

    active_plan = await _karma_plan_repo.get_active(db, user.id)
    if not active_plan:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Кофе‑медитация работает, когда есть активный проект. Давай сначала соберём его в разделе «Проблема».",
                "cta_path": "/problem",
            },
        )

    user_tz = get_user_zoneinfo(user.timezone)
    bounds = get_local_day_bounds(datetime.now(UTC), user_tz)

    daily_plan = await get_today_daily_plan(
        db,
        karma_plan_id=active_plan.id,
        utc_start=bounds.utc_start,
        utc_end=bounds.utc_end,
    )

    session = await get_or_create_session(
        db,
        user_id=user.id,
        local_date=bounds.local_date,
        karma_plan_id=active_plan.id,
        daily_plan_id=daily_plan.id if daily_plan else None,
    )

    result = await complete_session(
        db,
        session_id=session.id,
        user_id=user.id,
        notes=payload.notes,
        rejoice_seed_ids=payload.rejoiced_seed_ids,
    )

    if payload.complete_project_day and daily_plan:
        await db.execute(
            update(DailyPlanDB)
            .where(DailyPlanDB.id == daily_plan.id)
            .values(
                is_completed=True,
                completion_notes=payload.notes,
                updated_at=datetime.now(UTC),
            )
        )

        allowed_task_ids = {
            int(t.id) for t in (daily_plan.tasks or []) if getattr(t, "id", None) is not None
        }

        for task_id_str in payload.completed_task_ids:
            if not task_id_str.isdigit():
                continue
            task_id = int(task_id_str)
            if task_id not in allowed_task_ids:
                continue

            await daily_svc.toggle_task_completion(
                db,
                user_id=user.id,
                task_id=task_id,
                completed=True,
            )

    return {"success": True, "result": result}
