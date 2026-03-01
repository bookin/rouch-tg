"""KarmaPlan repository."""
from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db.karma_plan import KarmaPlanDB, KarmaPlanPartnerDB
from app.repositories.base import BaseRepository


class KarmaPlanRepository(BaseRepository[KarmaPlanDB]):
    def __init__(self) -> None:
        super().__init__(KarmaPlanDB)

    async def get_active(self, db: AsyncSession, user_id: int) -> KarmaPlanDB | None:
        result = await db.execute(
            select(KarmaPlanDB)
            .options(
                selectinload(KarmaPlanDB.daily_plans),
                selectinload(KarmaPlanDB.partners_association),
                selectinload(KarmaPlanDB.problem_history),
            )
            .where(
                KarmaPlanDB.user_id == user_id,
                KarmaPlanDB.status == "active",
            )
            .order_by(KarmaPlanDB.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *, limit: int = 20
    ) -> list[KarmaPlanDB]:
        result = await db.execute(
            select(KarmaPlanDB)
            .where(KarmaPlanDB.user_id == user_id)
            .order_by(KarmaPlanDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_plan(
        self,
        db: AsyncSession,
        user_id: int,
        problem_history_id: str,
        strategy_snapshot: dict,
        duration_days: int = 30,
        project_partners: dict | None = None,
        isolation_settings: dict | None = None,
    ) -> KarmaPlanDB:
        """Create a new Karma Plan, deactivating any existing active plans."""
        # 1. Deactivate existing active plans
        await db.execute(
            update(KarmaPlanDB)
            .where(KarmaPlanDB.user_id == user_id, KarmaPlanDB.status == "active")
            .values(status="cancelled", updated_at=datetime.now(UTC))
        )

        # 2. Create new plan
        plan_id = str(uuid4())
        plan = KarmaPlanDB(
            id=plan_id,
            user_id=user_id,
            problem_history_id=problem_history_id,
            status="active",
            strategy_snapshot=strategy_snapshot,
            duration_days=duration_days,
            isolation_settings=isolation_settings,
            start_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(plan)

        # 2.1 Save partners mapping if provided
        if project_partners:
            for category, partner_ids in project_partners.items():
                for pid in partner_ids:
                    assoc = KarmaPlanPartnerDB(
                        plan_id=plan_id,
                        partner_id=pid,
                        category=category,
                    )
                    db.add(assoc)

        await db.flush()
        await db.refresh(plan)
        return plan
