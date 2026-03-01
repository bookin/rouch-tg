"""Practice progress repository."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db.practice import PracticeProgressDB
from app.repositories.base import BaseRepository


class PracticeProgressRepository(BaseRepository[PracticeProgressDB]):
    def __init__(self) -> None:
        super().__init__(PracticeProgressDB)

    async def get_by_user_and_practice(
        self, db: AsyncSession, user_id: int, practice_id: str
    ) -> PracticeProgressDB | None:
        result = await db.execute(
            select(PracticeProgressDB)
            .options(selectinload(PracticeProgressDB.practice))
            .where(
                PracticeProgressDB.user_id == user_id,
                PracticeProgressDB.practice_id == practice_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        db: AsyncSession,
        user_id: int,
        practice_id: str,
        karma_plan_id: str | None = None,
    ) -> PracticeProgressDB:
        progress = await self.get_by_user_and_practice(db, user_id, practice_id)
        if not progress:
            progress = PracticeProgressDB(
                id=str(uuid4()),
                user_id=user_id,
                practice_id=practice_id,
                karma_plan_id=karma_plan_id,
            )
            db.add(progress)
            await db.flush()
            await db.refresh(progress)
        return progress

    async def get_all_for_user(
        self, db: AsyncSession, user_id: int
    ) -> list[PracticeProgressDB]:
        result = await db.execute(
            select(PracticeProgressDB)
            .options(selectinload(PracticeProgressDB.practice))
            .where(PracticeProgressDB.user_id == user_id)
            .order_by(PracticeProgressDB.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_by_user_and_practice(
        self, db: AsyncSession, user_id: int, practice_id: str
    ) -> bool:
        result = await db.execute(
            delete(PracticeProgressDB).where(
                PracticeProgressDB.user_id == user_id,
                PracticeProgressDB.practice_id == practice_id,
            )
        )
        await db.flush()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    async def delete_by_user(self, db: AsyncSession, user_id: int) -> None:
        await db.execute(
            delete(PracticeProgressDB).where(PracticeProgressDB.user_id == user_id)
        )
        await db.flush()
