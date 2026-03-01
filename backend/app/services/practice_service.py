"""Practice service — business logic for practice progress and habit tracking."""
from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.practice import PracticeProgressDB
from app.models.db.seed import SeedDB
from app.models.seed import Seed
from app.repositories.practice import PracticeProgressRepository
from app.repositories.seed import SeedRepository
from app.repositories.user import UserRepository


def calculate_habit_score(progress: PracticeProgressDB) -> int:
    """Calculate habit transformation score (0-100)."""
    streak_bonus = min(progress.streak_days * 2, 40)
    completion_bonus = min(progress.total_completions, 30)
    consistency_bonus = 30 if progress.streak_days >= 7 else 0
    return min(streak_bonus + completion_bonus + consistency_bonus, 100)


class PracticeService:
    def __init__(
        self,
        practice_repo: PracticeProgressRepository | None = None,
        seed_repo: SeedRepository | None = None,
        user_repo: UserRepository | None = None,
    ) -> None:
        self.practice_repo = practice_repo or PracticeProgressRepository()
        self.seed_repo = seed_repo or SeedRepository()
        self.user_repo = user_repo or UserRepository()

    async def get_user_progress(
        self, db: AsyncSession, user_id: int
    ) -> list[PracticeProgressDB]:
        return await self.practice_repo.get_all_for_user(db, user_id)

    async def update_progress(
        self, db: AsyncSession, user_id: int, practice_id: str
    ) -> tuple[PracticeProgressDB, bool]:
        """Update practice progress after completion.

        Returns (progress, actually_updated).
        """
        progress = await self.practice_repo.get_or_create(db, user_id, practice_id)
        now = datetime.now(UTC)

        max_per_day = 1
        if progress.practice:
            max_per_day = progress.practice.max_completions_per_day or 1

        if progress.last_completed and progress.last_completed.date() == now.date():
            if max_per_day <= 1:
                return progress, False
            today_count = await self.seed_repo.count_practice_seeds_today(
                db, user_id, practice_id, now
            )
            if today_count >= max_per_day:
                return progress, False

        progress.total_completions += 1

        if progress.last_completed:
            days_since = (now.date() - progress.last_completed.date()).days
            if days_since == 1:
                progress.streak_days += 1
            elif days_since > 1:
                progress.streak_days = 1
        else:
            progress.streak_days = 1

        progress.last_completed = now
        progress.habit_score = calculate_habit_score(progress)

        min_streak = 14
        min_score = 70
        if progress.practice:
            min_streak = progress.practice.habit_min_streak_days or 14
            min_score = progress.practice.habit_min_score or 70

        if progress.habit_score >= min_score and progress.streak_days >= min_streak:
            progress.is_habit = True

        await db.flush()
        return progress, True

    async def complete_and_create_seed(
        self,
        db: AsyncSession,
        user_id: int,
        practice_id: str,
        karma_plan_id: str | None = None,
        emotion_score: int = 5,
    ) -> dict:
        """Complete practice and create linked seed."""
        progress, actually_updated = await self.update_progress(db, user_id, practice_id)

        seed_db = None
        if actually_updated and karma_plan_id:
            seed = Seed(
                description=f"Практика: {progress.practice.name if progress.practice else 'Unknown'}",
                action_type="effort",
                user_id=user_id,
                timestamp=datetime.now(UTC),
                partner_id=None,
                partner_group="practice",
                intention_score=emotion_score,
                emotion_level=emotion_score,
                understanding=False,
                estimated_maturation_days=21,
                strength_multiplier=1.0,
                karma_plan_id=karma_plan_id,
            )
            from app.services.seed_service import SeedService
            seed_service = SeedService(self.seed_repo, self.user_repo)
            seed_db = await seed_service.create_seed(db, seed, practice_id=practice_id)
            await self.user_repo.increment_seeds_count(db, user_id)

        await db.flush()
        return {
            "progress": progress,
            "seed": seed_db,
            "actually_updated": actually_updated,
            "is_new_habit": progress.is_habit and progress.habit_score >= 70,
        }

    async def pause(self, db: AsyncSession, user_id: int, practice_id: str) -> bool:
        progress = await self.practice_repo.get_by_user_and_practice(db, user_id, practice_id)
        if not progress:
            return False
        progress.is_active = False
        await db.flush()
        return True

    async def resume(self, db: AsyncSession, user_id: int, practice_id: str) -> bool:
        progress = await self.practice_repo.get_by_user_and_practice(db, user_id, practice_id)
        if not progress:
            return False
        progress.is_active = True
        progress.is_hidden = False
        await db.flush()
        return True

    async def hide(self, db: AsyncSession, user_id: int, practice_id: str) -> bool:
        progress = await self.practice_repo.get_by_user_and_practice(db, user_id, practice_id)
        if not progress:
            return False
        progress.is_hidden = True
        await db.flush()
        return True

    async def reset(self, db: AsyncSession, user_id: int, practice_id: str) -> bool:
        progress = await self.practice_repo.get_by_user_and_practice(db, user_id, practice_id)
        if not progress:
            return False
        progress.streak_days = 0
        progress.habit_score = 0
        progress.total_completions = 0
        progress.last_completed = None
        progress.is_habit = False
        progress.is_active = True
        progress.is_hidden = False
        await db.flush()
        return True

    async def delete_all(
        self, db: AsyncSession, user_id: int, practice_id: str
    ) -> int:
        """Delete practice progress AND all related seeds. Returns deleted seeds count."""
        deleted_seeds = await self.seed_repo.delete_by_practice(db, user_id, practice_id)
        await self.practice_repo.delete_by_user_and_practice(db, user_id, practice_id)
        if deleted_seeds > 0:
            await self.user_repo.decrement_seeds_count(db, user_id, deleted_seeds)
        await db.flush()
        return deleted_seeds
