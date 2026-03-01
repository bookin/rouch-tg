"""Problem history repository."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.problem import ProblemHistoryDB
from app.repositories.base import BaseRepository


class ProblemHistoryRepository(BaseRepository[ProblemHistoryDB]):
    def __init__(self) -> None:
        super().__init__(ProblemHistoryDB)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, *, limit: int = 20
    ) -> list[ProblemHistoryDB]:
        result = await db.execute(
            select(ProblemHistoryDB)
            .where(ProblemHistoryDB.user_id == user_id)
            .order_by(ProblemHistoryDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save(
        self,
        db: AsyncSession,
        user_id: int,
        problem_text: str,
        solution_json: dict,
        diagnostic_json: dict | None = None,
    ) -> ProblemHistoryDB:
        clean_solution = dict(solution_json) if solution_json else {}
        if diagnostic_json is None and "diagnostic" in clean_solution:
            diagnostic_json = clean_solution.pop("diagnostic")

        history = ProblemHistoryDB(
            id=str(uuid4()),
            user_id=user_id,
            problem_text=problem_text,
            solution_json=clean_solution,
            diagnostic_json=diagnostic_json,
        )
        db.add(history)
        await db.flush()
        await db.refresh(history)
        return history

    async def delete_by_user(self, db: AsyncSession, user_id: int) -> None:
        from sqlalchemy import delete
        await db.execute(delete(ProblemHistoryDB).where(ProblemHistoryDB.user_id == user_id))
        await db.flush()
