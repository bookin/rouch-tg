"""User service — business logic for user operations."""
from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.db.user import UserDB
from app.repositories.partner import PartnerGroupRepository
from app.repositories.user import UserRepository


class UserService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        partner_group_repo: PartnerGroupRepository | None = None,
    ) -> None:
        self.user_repo = user_repo or UserRepository()
        self.partner_group_repo = partner_group_repo or PartnerGroupRepository()

    async def get_or_create_telegram_user(
        self,
        db: AsyncSession,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
    ) -> UserDB:
        user = await self.user_repo.get_or_create_telegram_user(
            db, telegram_id, first_name, username
        )
        await self.partner_group_repo.ensure_defaults(db, user.id)
        await db.flush()
        return user

    async def get_by_id(self, db: AsyncSession, user_id: int) -> UserDB:
        user = await self.user_repo.get(db, user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def update_focus(self, db: AsyncSession, user_id: int, focus: str) -> UserDB:
        user = await self.user_repo.update(db, user_id, {"current_focus": focus})
        if not user:
            raise NotFoundException("User not found")
        return user

    async def get_active_users(
        self,
        db: AsyncSession,
        *,
        morning_enabled: bool | None = None,
        evening_enabled: bool | None = None,
    ) -> list[UserDB]:
        return await self.user_repo.get_active_users(
            db, morning_enabled=morning_enabled, evening_enabled=evening_enabled
        )

    async def reset_progress(self, db: AsyncSession, user_id: int) -> None:
        """Reset all user progress — delegates to sub-repos for each entity."""
        from app.repositories.practice import PracticeProgressRepository
        from app.repositories.seed import SeedRepository
        from app.repositories.partner import PartnerRepository
        from app.repositories.problem import ProblemHistoryRepository
        from app.models.db.partner import PartnerActionDB
        from sqlalchemy import delete

        practice_repo = PracticeProgressRepository()
        seed_repo = SeedRepository()
        partner_repo = PartnerRepository()
        problem_repo = ProblemHistoryRepository()

        await practice_repo.delete_by_user(db, user_id)
        await db.execute(delete(PartnerActionDB).where(PartnerActionDB.user_id == user_id))
        await problem_repo.delete_by_user(db, user_id)
        await seed_repo.delete_by_user(db, user_id)
        await partner_repo.delete_by_user(db, user_id)
        await self.partner_group_repo.delete_by_user(db, user_id)

        user = await self.user_repo.get(db, user_id)
        if user:
            user.occupation = "employee"
            user.available_times = []
            user.daily_minutes = 30
            user.current_habits = []
            user.physical_restrictions = None
            user.streak_days = 0
            user.total_seeds = 0
            user.completed_practices = 0
            user.last_onboarding_update = None
            user.last_morning_message = None
            user.last_evening_message = None
            user.updated_at = datetime.now(UTC)

        await db.flush()
