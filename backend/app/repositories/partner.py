"""Partner & PartnerGroup repositories."""
from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.partner import PartnerDB, PartnerGroupDB
from app.models.partner import DEFAULT_GROUPS
from app.repositories.base import BaseRepository


class PartnerGroupRepository(BaseRepository[PartnerGroupDB]):
    def __init__(self) -> None:
        super().__init__(PartnerGroupDB)

    async def get_by_user(self, db: AsyncSession, user_id: int) -> list[PartnerGroupDB]:
        result = await db.execute(
            select(PartnerGroupDB)
            .where(PartnerGroupDB.user_id == user_id)
            .order_by(PartnerGroupDB.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_default_by_category(
        self, db: AsyncSession, user_id: int, category: str
    ) -> PartnerGroupDB | None:
        result = await db.execute(
            select(PartnerGroupDB)
            .where(
                PartnerGroupDB.user_id == user_id,
                PartnerGroupDB.universal_category == category,
                PartnerGroupDB.is_default == True,  # noqa: E712
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def ensure_defaults(self, db: AsyncSession, user_id: int) -> list[PartnerGroupDB]:
        """Create 4 default partner groups if they don't exist yet."""
        existing = await db.execute(
            select(PartnerGroupDB).where(
                PartnerGroupDB.user_id == user_id,
                PartnerGroupDB.is_default == True,  # noqa: E712
            )
        )
        existing_groups = list(existing.scalars().all())
        if existing_groups:
            return existing_groups

        now = datetime.now(UTC)
        groups: list[PartnerGroupDB] = []
        for g in DEFAULT_GROUPS:
            groups.append(
                PartnerGroupDB(
                    id=str(uuid4()),
                    name=g["name"],
                    icon=g["icon"],
                    description=g["description"],
                    universal_category=g["universal_category"],
                    is_default=True,
                    user_id=user_id,
                    created_at=now,
                )
            )
        db.add_all(groups)
        await db.flush()
        return groups

    async def delete_by_user(self, db: AsyncSession, user_id: int) -> None:
        await db.execute(delete(PartnerGroupDB).where(PartnerGroupDB.user_id == user_id))
        await db.flush()


class PartnerRepository(BaseRepository[PartnerDB]):
    def __init__(self) -> None:
        super().__init__(PartnerDB)

    async def get_by_user(self, db: AsyncSession, user_id: int) -> list[PartnerDB]:
        result = await db.execute(
            select(PartnerDB).where(PartnerDB.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_universal_category(
        self, db: AsyncSession, user_id: int, category: str
    ) -> list[PartnerDB]:
        result = await db.execute(
            select(PartnerDB)
            .join(PartnerGroupDB, PartnerDB.group_id == PartnerGroupDB.id)
            .where(
                PartnerDB.user_id == user_id,
                PartnerGroupDB.universal_category == category,
            )
        )
        return list(result.scalars().all())

    async def delete_by_user(self, db: AsyncSession, user_id: int) -> None:
        await db.execute(delete(PartnerDB).where(PartnerDB.user_id == user_id))
        await db.flush()

    async def delete_by_id(self, db: AsyncSession, partner_id: str) -> bool:
        return await self.delete(db, partner_id)
