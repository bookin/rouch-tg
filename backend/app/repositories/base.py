"""Base repository with generic CRUD operations."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Generic repository providing common data-access methods.

    Subclasses set ``model`` to the concrete SQLAlchemy model class.
    """

    model: type[ModelType]

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        result = await db.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        id: Any,
        obj_in: dict[str, Any],
    ) -> ModelType | None:
        await db.execute(
            update(self.model)
            .where(self.model.id == id)  # type: ignore[attr-defined]
            .values(**obj_in)
        )
        await db.flush()
        return await self.get(db, id)

    async def delete(self, db: AsyncSession, id: Any) -> bool:
        result = await db.execute(
            delete(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        await db.flush()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]
