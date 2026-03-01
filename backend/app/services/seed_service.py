"""Seed service — business logic for seed (karma journal) operations."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.seed import SeedDB
from app.models.seed import Seed
from app.repositories.seed import SeedRepository
from app.repositories.user import UserRepository


class SeedService:
    def __init__(
        self,
        seed_repo: SeedRepository | None = None,
        user_repo: UserRepository | None = None,
    ) -> None:
        self.seed_repo = seed_repo or SeedRepository()
        self.user_repo = user_repo or UserRepository()

    async def create_seed(
        self, db: AsyncSession, seed: Seed, practice_id: str | None = None
    ) -> SeedDB:
        seed_db = SeedDB(
            id=seed.id,
            user_id=seed.user_id,
            timestamp=seed.timestamp,
            action_type=seed.action_type,
            description=seed.description,
            partner_id=seed.partner_id,
            partner_group=seed.partner_group,
            intention_score=seed.intention_score,
            emotion_level=seed.emotion_level,
            understanding=seed.understanding,
            estimated_maturation_days=seed.estimated_maturation_days,
            strength_multiplier=seed.strength_multiplier,
            karma_plan_id=seed.karma_plan_id,
            daily_plan_id=seed.daily_plan_id,
            daily_task_id=seed.daily_task_id,
            practice_id=practice_id,
        )
        db.add(seed_db)
        await db.flush()
        await db.refresh(seed_db)
        return seed_db

    async def get_user_seeds(
        self, db: AsyncSession, user_id: int, *, limit: int = 50
    ) -> list[SeedDB]:
        return await self.seed_repo.get_by_user(db, user_id, limit=limit)

    async def get_by_date_range(
        self,
        db: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SeedDB]:
        return await self.seed_repo.get_by_date_range(db, user_id, start_date, end_date)
