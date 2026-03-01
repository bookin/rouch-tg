"""Daily service — business logic for daily plans and task completion."""
from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.db.seed import SeedDB
from app.models.seed import ACTION_TYPES
from app.repositories.daily import DailyPlanRepository, DailyTaskRepository
from app.repositories.seed import SeedRepository
from app.repositories.user import UserRepository


class DailyService:
    def __init__(
        self,
        daily_plan_repo: DailyPlanRepository | None = None,
        daily_task_repo: DailyTaskRepository | None = None,
        seed_repo: SeedRepository | None = None,
        user_repo: UserRepository | None = None,
    ) -> None:
        self.daily_plan_repo = daily_plan_repo or DailyPlanRepository()
        self.daily_task_repo = daily_task_repo or DailyTaskRepository()
        self.seed_repo = seed_repo or SeedRepository()
        self.user_repo = user_repo or UserRepository()

    async def toggle_task_completion(
        self, db: AsyncSession, user_id: int, task_id: int, completed: bool
    ) -> bool:
        """Toggle task completion, creating/deleting linked seed accordingly.

        Returns True if operation succeeded, False if task not found / not owned.
        """
        ownership = await self.daily_task_repo.verify_user_ownership(db, task_id, user_id)
        if not ownership:
            return False

        task, plan, karma_plan = ownership
        now_utc = datetime.now(UTC)

        actually_changed = await self.daily_task_repo.set_completed(
            db, task.id, completed, completed_at=now_utc
        )
        if not actually_changed:
            return True  # idempotent — already in desired state

        if completed:
            # Create seed for completed task
            raw_action_type = getattr(task, "action_type", None) or ""
            seed_action_type = raw_action_type.strip().lower()
            if not seed_action_type or seed_action_type not in ACTION_TYPES:
                seed_action_type = "kindness"

            partner_group = task.group or "project"

            existing = await self.seed_repo.get_by_daily_task(db, user_id, task.id)
            if not existing:
                seed = SeedDB(
                    id=str(uuid4()),
                    user_id=user_id,
                    timestamp=now_utc,
                    action_type=seed_action_type,
                    description=task.description,
                    partner_id=getattr(task, "partner_id", None),
                    partner_group=partner_group,
                    intention_score=5,
                    emotion_level=5,
                    understanding=True,
                    karma_plan_id=karma_plan.id,
                    daily_plan_id=plan.id,
                    daily_task_id=task.id,
                    estimated_maturation_days=21,
                    strength_multiplier=1.0,
                )
                db.add(seed)
                await self.user_repo.increment_seeds_count(db, user_id)
        else:
            # Delete associated seed(s)
            deleted_count = await self.seed_repo.delete_by_daily_task(db, user_id, task.id)
            if deleted_count > 0:
                await self.user_repo.decrement_seeds_count(db, user_id, deleted_count)

        await db.flush()
        return True
