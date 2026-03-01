"""Daily plan & task repositories."""
from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db.daily import DailyPlanDB, DailyTaskDB
from app.models.db.karma_plan import KarmaPlanDB
from app.repositories.base import BaseRepository


class DailyPlanRepository(BaseRepository[DailyPlanDB]):
    def __init__(self) -> None:
        super().__init__(DailyPlanDB)

    async def get_with_tasks(self, db: AsyncSession, plan_id: str) -> DailyPlanDB | None:
        result = await db.execute(
            select(DailyPlanDB)
            .options(selectinload(DailyPlanDB.tasks))
            .where(DailyPlanDB.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_by_karma_plan(
        self, db: AsyncSession, karma_plan_id: str
    ) -> list[DailyPlanDB]:
        result = await db.execute(
            select(DailyPlanDB)
            .options(selectinload(DailyPlanDB.tasks))
            .where(DailyPlanDB.karma_plan_id == karma_plan_id)
            .order_by(DailyPlanDB.day_number)
        )
        return list(result.scalars().all())

    async def get_by_karma_plan_and_date(
        self, db: AsyncSession, karma_plan_id: str, target_date: datetime
    ) -> DailyPlanDB | None:
        """Get the daily plan for a specific date within a karma plan."""
        from sqlalchemy import func as sa_func
        result = await db.execute(
            select(DailyPlanDB)
            .options(selectinload(DailyPlanDB.tasks))
            .where(
                DailyPlanDB.karma_plan_id == karma_plan_id,
                sa_func.date(DailyPlanDB.date) == target_date.date(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self, db: AsyncSession, karma_plan_id: str, date: datetime
    ) -> DailyPlanDB | None:
        """Get daily plan for a specific date using day start/end range."""
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        result = await db.execute(
            select(DailyPlanDB)
            .options(selectinload(DailyPlanDB.tasks))
            .where(
                DailyPlanDB.karma_plan_id == karma_plan_id,
                DailyPlanDB.date >= day_start,
                DailyPlanDB.date <= day_end,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_with_tasks(
        self,
        db: AsyncSession,
        karma_plan_id: str,
        day_number: int,
        date: datetime,
        focus_quality: str,
        tasks: list,
    ) -> DailyPlanDB:
        """Create a new daily plan with tasks."""
        daily = DailyPlanDB(
            id=str(uuid4()),
            karma_plan_id=karma_plan_id,
            day_number=day_number,
            date=date,
            focus_quality=focus_quality,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(daily)
        await db.flush()

        for i, task_data in enumerate(tasks):
            description = task_data if isinstance(task_data, str) else task_data.get("description", "")
            why = None
            group = "project"
            partner_id = None
            action_type = None

            if isinstance(task_data, dict):
                why = task_data.get("why")
                group = task_data.get("group", "project")
                partner_id = task_data.get("partner_id")
                action_type = task_data.get("action_type")

            task = DailyTaskDB(
                daily_plan_id=daily.id,
                description=description,
                why=why,
                group=group,
                partner_id=partner_id,
                action_type=action_type,
                order=i,
                completed=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(task)

        await db.flush()
        await db.refresh(daily)
        return daily


class DailyTaskRepository(BaseRepository[DailyTaskDB]):
    def __init__(self) -> None:
        super().__init__(DailyTaskDB)

    async def get_with_plan(
        self, db: AsyncSession, task_id: int
    ) -> tuple[DailyTaskDB, DailyPlanDB] | None:
        """Get task together with its parent plan."""
        result = await db.execute(
            select(DailyTaskDB, DailyPlanDB)
            .join(DailyPlanDB, DailyTaskDB.daily_plan_id == DailyPlanDB.id)
            .where(DailyTaskDB.id == task_id)
        )
        row = result.first()
        if not row:
            return None
        return row[0], row[1]

    async def verify_user_ownership(
        self, db: AsyncSession, task_id: int, user_id: int
    ) -> tuple[DailyTaskDB, DailyPlanDB, KarmaPlanDB] | None:
        """Get task + plan + karma_plan, verifying user owns it."""
        task_plan = await self.get_with_plan(db, task_id)
        if not task_plan:
            return None
        task, plan = task_plan

        kp_result = await db.execute(
            select(KarmaPlanDB).where(KarmaPlanDB.id == plan.karma_plan_id)
        )
        karma_plan = kp_result.scalar_one_or_none()
        if not karma_plan or karma_plan.user_id != user_id:
            return None
        return task, plan, karma_plan

    async def set_completed(
        self,
        db: AsyncSession,
        task_id: int,
        completed: bool,
        completed_at: datetime | None = None,
    ) -> bool:
        """Set completion status. Returns True if row was actually changed."""
        result = await db.execute(
            update(DailyTaskDB)
            .where(
                DailyTaskDB.id == task_id,
                DailyTaskDB.completed.is_(not completed),
            )
            .values(
                completed=completed,
                completed_at=completed_at if completed else None,
            )
        )
        await db.flush()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]
