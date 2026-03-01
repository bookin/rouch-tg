"""Partner service — business logic for partners and partner groups."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.partner import PartnerDB, PartnerGroupDB
from app.models.partner import Partner, PartnerGroup
from app.repositories.partner import PartnerGroupRepository, PartnerRepository


class PartnerService:
    def __init__(
        self,
        partner_repo: PartnerRepository | None = None,
        group_repo: PartnerGroupRepository | None = None,
    ) -> None:
        self.partner_repo = partner_repo or PartnerRepository()
        self.group_repo = group_repo or PartnerGroupRepository()

    async def get_groups(self, db: AsyncSession, user_id: int) -> list[PartnerGroupDB]:
        return await self.group_repo.get_by_user(db, user_id)

    async def get_default_group_by_category(
        self, db: AsyncSession, user_id: int, category: str
    ) -> PartnerGroupDB | None:
        return await self.group_repo.get_default_by_category(db, user_id, category)

    async def ensure_default_groups(
        self, db: AsyncSession, user_id: int
    ) -> list[PartnerGroupDB]:
        return await self.group_repo.ensure_defaults(db, user_id)

    async def create_group(self, db: AsyncSession, group: PartnerGroup) -> PartnerGroupDB:
        group_db = PartnerGroupDB(
            id=group.id,
            name=group.name,
            icon=group.icon,
            description=group.description,
            universal_category=group.universal_category,
            is_default=group.is_default,
            user_id=group.user_id,
            created_at=group.created_at,
        )
        db.add(group_db)
        await db.flush()
        await db.refresh(group_db)
        return group_db

    async def get_partners(self, db: AsyncSession, user_id: int) -> list[PartnerDB]:
        return await self.partner_repo.get_by_user(db, user_id)

    async def get_partners_by_category(
        self, db: AsyncSession, user_id: int, category: str
    ) -> list[PartnerDB]:
        return await self.partner_repo.get_by_universal_category(db, user_id, category)

    async def create_partner(self, db: AsyncSession, partner: Partner) -> PartnerDB:
        partner_db = PartnerDB(
            id=partner.id,
            user_id=partner.user_id,
            group_id=partner.group_id,
            name=partner.name,
            telegram_username=partner.telegram_username,
            phone=partner.phone,
            contact_type=partner.contact_type,
            notes=partner.notes,
            created_at=partner.created_at,
        )
        db.add(partner_db)
        await db.flush()
        await db.refresh(partner_db)
        return partner_db
