"""Service for merging two user accounts into one."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db.coffee import CoffeeMeditationSessionDB
from app.models.db.karma_plan import KarmaPlanDB
from app.models.db.message_log import MessageLogDB
from app.models.db.partner import PartnerActionDB, PartnerDB, PartnerGroupDB
from app.models.db.practice import PracticeProgressDB
from app.models.db.problem import ProblemHistoryDB
from app.models.db.seed import SeedDB
from app.models.db.user import UserDB

logger = logging.getLogger(__name__)


class AccountMergeService:
    """Handles previewing and executing account merges."""

    async def preview_merge(
        self, db: AsyncSession, target_user_id: int, source_user_id: int
    ) -> dict[str, Any]:
        """Preview what will happen when merging source into target.

        Returns a dict describing both accounts' data and any conflicts.
        """
        target = await db.get(UserDB, target_user_id)
        source = await db.get(UserDB, source_user_id)
        if not target or not source:
            return {"error": "Один из аккаунтов не найден"}

        # Count data for each user
        target_data = await self._count_user_data(db, target_user_id)
        source_data = await self._count_user_data(db, source_user_id)

        # Check active project conflicts
        target_active_plan = await self._get_active_plan(db, target_user_id)
        source_active_plan = await self._get_active_plan(db, source_user_id)

        has_project_conflict = target_active_plan is not None and source_active_plan is not None

        return {
            "target": {
                "id": target.id,
                "first_name": target.first_name,
                "email": target.email,
                "telegram_id": target.telegram_id,
                "has_active_project": target_active_plan is not None,
                "active_project_problem": (
                    target_active_plan.problem_history.problem_text[:80]
                    if target_active_plan and target_active_plan.problem_history
                    else None
                ),
                **target_data,
            },
            "source": {
                "id": source.id,
                "first_name": source.first_name,
                "email": source.email,
                "telegram_id": source.telegram_id,
                "has_active_project": source_active_plan is not None,
                "active_project_problem": (
                    source_active_plan.problem_history.problem_text[:80]
                    if source_active_plan and source_active_plan.problem_history
                    else None
                ),
                **source_data,
            },
            "has_project_conflict": has_project_conflict,
        }

    async def execute_merge(
        self,
        db: AsyncSession,
        target_user_id: int,
        source_user_id: int,
        keep_project_from: int | None = None,
    ) -> bool:
        """Merge all data from source_user into target_user, then delete source.

        Args:
            target_user_id: The user that will remain.
            source_user_id: The user whose data will be transferred and then deleted.
            keep_project_from: If both have active projects, which user's project to keep active.
                              The other will be cancelled.
        """
        target = await db.get(UserDB, target_user_id)
        source = await db.get(UserDB, source_user_id)
        if not target or not source:
            logger.error(f"Merge failed: user not found (target={target_user_id}, source={source_user_id})")
            return False

        logger.info(f"Merging user {source_user_id} into {target_user_id}")

        # 1. Handle active project conflicts
        await self._resolve_project_conflict(db, target_user_id, source_user_id, keep_project_from)

        source_telegram_id = source.telegram_id
        source_email = source.email
        source_is_verified = source.is_verified

        source.telegram_id = None
        source.email = None
        await db.flush()

        # 2. Transfer telegram_id if target doesn't have one
        if not target.telegram_id and source_telegram_id:
            target.telegram_id = source_telegram_id

        # 3. Transfer email if target doesn't have one
        if not target.email and source_email:
            target.email = source_email
            target.is_verified = source_is_verified

        # 4. Transfer password if target doesn't have one
        if (not target.hashed_password or target.hashed_password == "!telegram-no-password") and source.hashed_password and source.hashed_password != "!telegram-no-password":
            target.hashed_password = source.hashed_password

        # 5. Merge progress counters
        target.total_seeds += source.total_seeds or 0
        target.completed_practices += source.completed_practices or 0
        target.streak_days = max(target.streak_days or 0, source.streak_days or 0)

        # 6. Transfer all FK-linked data
        await self._transfer_data(db, target_user_id, source_user_id)

        # 7. Update target timestamp
        target.updated_at = datetime.now(UTC)

        # 8. Clear source's unique fields before deletion to avoid constraint issues
        await db.flush()

        # 9. Delete source user (cascades will handle remaining FKs)
        await db.execute(delete(UserDB).where(UserDB.id == source_user_id))
        await db.flush()

        logger.info(f"Merge complete: user {source_user_id} merged into {target_user_id}")
        return True

    # ── Internals ───────────────────────────────────────────────────

    async def _count_user_data(self, db: AsyncSession, user_id: int) -> dict[str, int]:
        """Count data items belonging to a user."""
        counts: dict[str, int] = {}
        for label, model, col in [
            ("seeds_count", SeedDB, SeedDB.user_id),
            ("partners_count", PartnerDB, PartnerDB.user_id),
            ("problems_count", ProblemHistoryDB, ProblemHistoryDB.user_id),
            ("karma_plans_count", KarmaPlanDB, KarmaPlanDB.user_id),
            ("practices_count", PracticeProgressDB, PracticeProgressDB.user_id),
            ("coffee_sessions_count", CoffeeMeditationSessionDB, CoffeeMeditationSessionDB.user_id),
        ]:
            from sqlalchemy import func
            result = await db.execute(select(func.count()).where(col == user_id))
            counts[label] = result.scalar() or 0
        return counts

    async def _get_active_plan(self, db: AsyncSession, user_id: int) -> KarmaPlanDB | None:
        """Get the active karma plan for a user with problem_history eagerly loaded."""
        result = await db.execute(
            select(KarmaPlanDB)
            .options(selectinload(KarmaPlanDB.problem_history))
            .where(
                KarmaPlanDB.user_id == user_id,
                KarmaPlanDB.status == "active",
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def _resolve_project_conflict(
        self,
        db: AsyncSession,
        target_user_id: int,
        source_user_id: int,
        keep_project_from: int | None,
    ) -> None:
        """If both users have active projects, cancel the one not chosen."""
        target_plan = await self._get_active_plan(db, target_user_id)
        source_plan = await self._get_active_plan(db, source_user_id)

        if not target_plan or not source_plan:
            return  # No conflict

        # Decide which to cancel
        if keep_project_from == source_user_id:
            # Cancel target's project
            target_plan.status = "cancelled"
            target_plan.updated_at = datetime.now(UTC)
        else:
            # Default: cancel source's project (keep target's)
            source_plan.status = "cancelled"
            source_plan.updated_at = datetime.now(UTC)

        await db.flush()

    async def _transfer_data(
        self, db: AsyncSession, target_id: int, source_id: int
    ) -> None:
        """Transfer all FK-linked records from source to target."""
        # Seeds
        await db.execute(
            update(SeedDB).where(SeedDB.user_id == source_id).values(user_id=target_id)
        )
        # Partners & groups
        await db.execute(
            update(PartnerGroupDB).where(PartnerGroupDB.user_id == source_id).values(user_id=target_id)
        )
        await db.execute(
            update(PartnerDB).where(PartnerDB.user_id == source_id).values(user_id=target_id)
        )
        await db.execute(
            update(PartnerActionDB).where(PartnerActionDB.user_id == source_id).values(user_id=target_id)
        )
        # Problems
        await db.execute(
            update(ProblemHistoryDB).where(ProblemHistoryDB.user_id == source_id).values(user_id=target_id)
        )
        # Karma plans (+ daily plans cascade via FK)
        await db.execute(
            update(KarmaPlanDB).where(KarmaPlanDB.user_id == source_id).values(user_id=target_id)
        )
        # Practice progress (unique constraint on user_id + practice_id)
        # Find practice_ids that would conflict
        target_practices_q = select(PracticeProgressDB.practice_id).where(
            PracticeProgressDB.user_id == target_id
        )
        target_practices_result = await db.execute(target_practices_q)
        target_practice_ids = {row[0] for row in target_practices_result.all()}

        if target_practice_ids:
            # For conflicting practices: merge progress (keep best values) into target
            conflict_source_q = select(PracticeProgressDB).where(
                PracticeProgressDB.user_id == source_id,
                PracticeProgressDB.practice_id.in_(target_practice_ids),
            )
            conflict_source_result = await db.execute(conflict_source_q)
            conflict_source_rows = conflict_source_result.scalars().all()

            for src_progress in conflict_source_rows:
                tgt_q = select(PracticeProgressDB).where(
                    PracticeProgressDB.user_id == target_id,
                    PracticeProgressDB.practice_id == src_progress.practice_id,
                )
                tgt_result = await db.execute(tgt_q)
                tgt_progress = tgt_result.scalar_one_or_none()
                if tgt_progress:
                    tgt_progress.total_completions += src_progress.total_completions or 0
                    tgt_progress.streak_days = max(
                        tgt_progress.streak_days or 0, src_progress.streak_days or 0
                    )
                    tgt_progress.habit_score = max(
                        tgt_progress.habit_score or 0, src_progress.habit_score or 0
                    )
                    if src_progress.last_completed and (
                        not tgt_progress.last_completed
                        or src_progress.last_completed > tgt_progress.last_completed
                    ):
                        tgt_progress.last_completed = src_progress.last_completed
                    tgt_progress.is_habit = tgt_progress.is_habit or src_progress.is_habit

            # Delete conflicting source progress
            await db.execute(
                delete(PracticeProgressDB).where(
                    PracticeProgressDB.user_id == source_id,
                    PracticeProgressDB.practice_id.in_(target_practice_ids),
                )
            )
        # Transfer remaining non-conflicting progress
        await db.execute(
            update(PracticeProgressDB).where(PracticeProgressDB.user_id == source_id).values(user_id=target_id)
        )
        # Coffee meditation sessions (unique constraint on user_id + local_date)
        # First find dates that would conflict
        target_dates_q = select(CoffeeMeditationSessionDB.local_date).where(
            CoffeeMeditationSessionDB.user_id == target_id
        )
        target_dates_result = await db.execute(target_dates_q)
        target_dates = {row[0] for row in target_dates_result.all()}

        if target_dates:
            # Delete source sessions that would conflict
            await db.execute(
                delete(CoffeeMeditationSessionDB).where(
                    CoffeeMeditationSessionDB.user_id == source_id,
                    CoffeeMeditationSessionDB.local_date.in_(target_dates),
                )
            )
        # Transfer remaining non-conflicting sessions
        await db.execute(
            update(CoffeeMeditationSessionDB)
            .where(CoffeeMeditationSessionDB.user_id == source_id)
            .values(user_id=target_id)
        )
        # Message logs
        await db.execute(
            update(MessageLogDB).where(MessageLogDB.user_id == source_id).values(user_id=target_id)
        )

        await db.flush()
