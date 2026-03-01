from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Iterable
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.coffee import (
    CoffeeMeditationRejoicedSeedDB,
    CoffeeMeditationSessionDB,
)
from app.models.db.daily import DailyPlanDB
from app.models.db.seed import (
    SeedDB,
)


@dataclass(frozen=True)
class LocalDayBounds:
    local_date: date
    utc_start: datetime
    utc_end: datetime


def get_user_zoneinfo(timezone_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def get_local_day_bounds(now_utc: datetime, user_tz: ZoneInfo) -> LocalDayBounds:
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=UTC)

    local_dt = now_utc.astimezone(user_tz)
    local_d = local_dt.date()

    start_local = datetime.combine(local_d, time(0, 0)).replace(tzinfo=user_tz)
    next_local = datetime.combine(local_d + timedelta(days=1), time(0, 0)).replace(
        tzinfo=user_tz
    )

    utc_start = start_local.astimezone(UTC)
    utc_end = next_local.astimezone(UTC) - timedelta(microseconds=1)

    return LocalDayBounds(local_date=local_d, utc_start=utc_start, utc_end=utc_end)


async def get_or_create_session(
    db: AsyncSession,
    *,
    user_id: int,
    local_date: date,
    karma_plan_id: str | None,
    daily_plan_id: str | None,
) -> CoffeeMeditationSessionDB:
    now_utc = datetime.now(UTC)
    new_id = str(uuid4())

    stmt = (
        pg_insert(CoffeeMeditationSessionDB)
        .values(
            id=new_id,
            user_id=user_id,
            local_date=local_date,
            karma_plan_id=karma_plan_id,
            daily_plan_id=daily_plan_id,
            started_at=now_utc,
            current_step=0,
            created_at=now_utc,
            updated_at=now_utc,
        )
        .on_conflict_do_update(
            constraint="uq_coffee_session_user_local_date",
            set_={
                "karma_plan_id": karma_plan_id,
                "daily_plan_id": daily_plan_id,
                "updated_at": now_utc,
            },
        )
        .returning(CoffeeMeditationSessionDB.id)
    )

    result = await db.execute(stmt)
    session_id = result.scalar_one()

    row = await db.execute(
        select(CoffeeMeditationSessionDB).where(CoffeeMeditationSessionDB.id == session_id)
    )
    session = row.scalar_one()
    await db.flush()
    return session


async def get_rejoiced_seed_ids(db: AsyncSession, *, session_id: str) -> list[str]:
    result = await db.execute(
        select(CoffeeMeditationRejoicedSeedDB.seed_id).where(
            CoffeeMeditationRejoicedSeedDB.session_id == session_id
        )
    )
    return list(result.scalars().all())


async def _filter_seed_ids_belonging_to_user(
    db: AsyncSession,
    *,
    user_id: int,
    seed_ids: Iterable[str],
) -> list[str]:
    ids = [sid for sid in seed_ids if sid]
    if not ids:
        return []

    result = await db.execute(
        select(SeedDB.id).where(
            SeedDB.user_id == user_id,
            SeedDB.id.in_(ids),
        )
    )
    return list(result.scalars().all())


async def set_rejoiced_seed_ids(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: int,
    seed_ids: Iterable[str],
) -> list[str]:
    allowed_ids = await _filter_seed_ids_belonging_to_user(
        db,
        user_id=user_id,
        seed_ids=seed_ids,
    )

    if allowed_ids:
        await db.execute(
            delete(CoffeeMeditationRejoicedSeedDB).where(
                CoffeeMeditationRejoicedSeedDB.session_id == session_id,
                CoffeeMeditationRejoicedSeedDB.seed_id.notin_(allowed_ids),
            )
        )
    else:
        await db.execute(
            delete(CoffeeMeditationRejoicedSeedDB).where(
                CoffeeMeditationRejoicedSeedDB.session_id == session_id
            )
        )

    for seed_id in allowed_ids:
        stmt = (
            pg_insert(CoffeeMeditationRejoicedSeedDB)
            .values(
                session_id=session_id,
                seed_id=seed_id,
            )
            .on_conflict_do_nothing(index_elements=["session_id", "seed_id"])
        )
        await db.execute(stmt)

    return allowed_ids


async def get_today_seeds(
    db: AsyncSession,
    *,
    user_id: int,
    utc_start: datetime,
    utc_end: datetime,
) -> list[SeedDB]:
    result = await db.execute(
        select(SeedDB)
        .where(
            SeedDB.user_id == user_id,
            SeedDB.timestamp >= utc_start,
            SeedDB.timestamp <= utc_end,
        )
        .order_by(SeedDB.timestamp.desc())
    )
    return list(result.scalars().all())


async def get_today_daily_plan(
    db: AsyncSession,
    *,
    karma_plan_id: str,
    utc_start: datetime,
    utc_end: datetime,
) -> DailyPlanDB | None:
    result = await db.execute(
        select(DailyPlanDB)
        .where(
            DailyPlanDB.karma_plan_id == karma_plan_id,
            DailyPlanDB.date >= utc_start,
            DailyPlanDB.date <= utc_end,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_progress(
    db: AsyncSession,
    *,
    session: CoffeeMeditationSessionDB,
    user_id: int,
    current_step: int | None,
    notes_draft: str | None,
    rejoiced_seed_ids: Iterable[str] | None,
) -> list[str]:
    if current_step is not None:
        session.current_step = max(0, int(current_step))

    if notes_draft is not None:
        session.notes_draft = notes_draft

    applied_seed_ids: list[str] = []
    if rejoiced_seed_ids is not None:
        applied_seed_ids = await set_rejoiced_seed_ids(
            db,
            session_id=session.id,
            user_id=user_id,
            seed_ids=rejoiced_seed_ids,
        )

    await db.flush()
    return applied_seed_ids


async def complete_session(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: int,
    notes: str | None,
    rejoice_seed_ids: Iterable[str],
) -> dict:
    result = await db.execute(
        select(CoffeeMeditationSessionDB).where(CoffeeMeditationSessionDB.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session or session.user_id != user_id:
        return {"ok": False, "reason": "not_found"}

    if session.completed_at is not None:
        return {"ok": True, "already_completed": True}

    final_seed_ids = await set_rejoiced_seed_ids(
        db,
        session_id=session.id,
        user_id=user_id,
        seed_ids=rejoice_seed_ids,
    )

    final_notes = notes if notes is not None else (session.notes_draft or None)

    now_utc = datetime.now(UTC)
    upd = (
        update(CoffeeMeditationSessionDB)
        .where(
            CoffeeMeditationSessionDB.id == session.id,
            CoffeeMeditationSessionDB.completed_at.is_(None),
        )
        .values(
            completed_at=now_utc,
            notes=final_notes,
            updated_at=now_utc,
        )
    )
    res = await db.execute(upd)
    if res.rowcount == 0:
        return {"ok": True, "already_completed": True}

    if final_seed_ids:
        for seed_id in final_seed_ids:
            seed_upd = (
                update(SeedDB)
                .where(
                    SeedDB.id == seed_id,
                    SeedDB.user_id == user_id,
                )
                .values(
                    rejoice_count=func.coalesce(SeedDB.rejoice_count, 0) + 1,
                    strength_multiplier=func.least(SeedDB.strength_multiplier * 1.2, 3.0),
                    last_rejoiced_at=now_utc,
                )
            )
            await db.execute(seed_upd)

    await db.flush()
    return {"ok": True, "already_completed": False, "rejoiced_seed_ids": final_seed_ids}
