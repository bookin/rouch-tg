"""User repository — data access for UserDB."""
from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.user import UserDB
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserDB]):
    def __init__(self) -> None:
        super().__init__(UserDB)

    async def get_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> UserDB | None:
        result = await db.execute(
            select(UserDB).where(UserDB.telegram_id == telegram_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> UserDB | None:
        result = await db.execute(
            select(UserDB).where(UserDB.email == email).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_telegram_user(
        self,
        db: AsyncSession,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
    ) -> UserDB:
        """Atomic upsert for Telegram users."""
        stmt = pg_insert(UserDB).values(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
            hashed_password="!telegram-no-password",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ).on_conflict_do_update(
            index_elements=["telegram_id"],
            set_={
                "first_name": first_name,
                "username": username,
                "updated_at": datetime.now(UTC),
            },
        )
        await db.execute(stmt)
        await db.flush()
        return await self.get_by_telegram_id(db, telegram_id)  # type: ignore[return-value]

    async def get_active_users(
        self,
        db: AsyncSession,
        *,
        morning_enabled: bool | None = None,
        evening_enabled: bool | None = None,
    ) -> list[UserDB]:
        query = select(UserDB)
        if morning_enabled is not None:
            query = query.where(UserDB.morning_enabled == morning_enabled)
        if evening_enabled is not None:
            query = query.where(UserDB.evening_enabled == evening_enabled)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_streak(self, db: AsyncSession, user_id: int, streak_days: int) -> None:
        user = await self.get(db, user_id)
        if user:
            user.streak_days = streak_days
            user.updated_at = datetime.now(UTC)
            await db.flush()

    async def increment_seeds_count(self, db: AsyncSession, user_id: int) -> None:
        user = await self.get(db, user_id)
        if user:
            user.total_seeds += 1
            user.updated_at = datetime.now(UTC)
            await db.flush()

    async def decrement_seeds_count(self, db: AsyncSession, user_id: int, count: int = 1) -> None:
        user = await self.get(db, user_id)
        if user:
            user.total_seeds = max(0, int(user.total_seeds or 0) - count)
            user.updated_at = datetime.now(UTC)
            await db.flush()
