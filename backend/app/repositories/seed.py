"""Seed repository — data access for SeedDB."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy import func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.seed import SeedDB
from app.repositories.base import BaseRepository


class SeedRepository(BaseRepository[SeedDB]):
    def __init__(self) -> None:
        super().__init__(SeedDB)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *, limit: int = 50
    ) -> list[SeedDB]:
        result = await db.execute(
            select(SeedDB)
            .where(SeedDB.user_id == user_id)
            .order_by(SeedDB.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        db: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SeedDB]:
        result = await db.execute(
            select(SeedDB)
            .where(
                SeedDB.user_id == user_id,
                SeedDB.timestamp >= start_date,
                SeedDB.timestamp <= end_date,
            )
            .order_by(SeedDB.timestamp.desc())
        )
        return list(result.scalars().all())

    async def get_by_daily_task(
        self, db: AsyncSession, user_id: int, task_id: int
    ) -> SeedDB | None:
        result = await db.execute(
            select(SeedDB)
            .where(SeedDB.user_id == user_id, SeedDB.daily_task_id == task_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_by_daily_task(
        self, db: AsyncSession, user_id: int, task_id: int
    ) -> int:
        result = await db.execute(
            select(sa_func.count())
            .select_from(SeedDB)
            .where(SeedDB.user_id == user_id, SeedDB.daily_task_id == task_id)
        )
        return result.scalar() or 0

    async def count_practice_seeds_today(
        self, db: AsyncSession, user_id: int, practice_id: str, now: datetime
    ) -> int:
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(sa_func.count())
            .select_from(SeedDB)
            .where(
                SeedDB.user_id == user_id,
                SeedDB.practice_id == practice_id,
                SeedDB.timestamp >= day_start,
            )
        )
        return result.scalar() or 0

    async def delete_by_daily_task(
        self, db: AsyncSession, user_id: int, task_id: int
    ) -> int:
        """Delete seeds linked to a daily task. Returns count deleted."""
        # Count first
        count = await self.count_by_daily_task(db, user_id, task_id)
        if count > 0:
            await db.execute(
                delete(SeedDB).where(
                    SeedDB.user_id == user_id,
                    SeedDB.daily_task_id == task_id,
                )
            )
            await db.flush()
        return count

    async def delete_by_practice(
        self, db: AsyncSession, user_id: int, practice_id: str
    ) -> int:
        """Delete seeds linked to a practice. Returns count deleted."""
        count_result = await db.execute(
            select(sa_func.count())
            .select_from(SeedDB)
            .where(SeedDB.user_id == user_id, SeedDB.practice_id == practice_id)
        )
        count = count_result.scalar() or 0
        if count > 0:
            await db.execute(
                delete(SeedDB).where(
                    SeedDB.user_id == user_id,
                    SeedDB.practice_id == practice_id,
                )
            )
            await db.flush()
        return count

    async def delete_by_user(self, db: AsyncSession, user_id: int) -> None:
        await db.execute(delete(SeedDB).where(SeedDB.user_id == user_id))
        await db.flush()
