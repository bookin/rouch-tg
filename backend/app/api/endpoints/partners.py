"""Partner endpoints."""
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_session,
    get_partner_service,
    PartnerGroupOut,
    PartnerOut,
    PartnersResponse,
    PartnerCreateRequest,
    PartnerCreateResponse,
)
from app.models.db.user import UserDB
from app.models.db.partner import PartnerDB
from app.models.partner import Partner
from app.services.partner_service import PartnerService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/partners", response_model=PartnersResponse)
async def get_partners(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    partner_svc: PartnerService = Depends(get_partner_service),
):
    """Get user's partner groups and partners"""
    await partner_svc.ensure_default_groups(db, user.id)

    groups_db = await partner_svc.get_groups(db, user.id)
    partners_db = await partner_svc.get_partners(db, user.id)

    groups = [
        PartnerGroupOut(
            id=g.id,
            name=g.name,
            icon=g.icon,
            description=g.description,
            universal_category=g.universal_category,
            is_default=bool(g.is_default),
        )
        for g in groups_db
    ]
    partners = [
        PartnerOut(
            id=p.id,
            name=p.name,
            group_id=p.group_id,
            telegram_username=p.telegram_username,
            phone=p.phone,
            notes=p.notes,
        )
        for p in partners_db
    ]

    return PartnersResponse(groups=groups, partners=partners).model_dump()


@router.post("/partners", response_model=PartnerCreateResponse)
async def create_partner_endpoint(
    payload: PartnerCreateRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    partner_svc: PartnerService = Depends(get_partner_service),
):
    """Create new partner"""
    await partner_svc.ensure_default_groups(db, user.id)

    group_db = await partner_svc.group_repo.get(db, payload.group_id)
    if not group_db or group_db.user_id != user.id:
        raise HTTPException(status_code=400, detail="Invalid partner group")

    partner = Partner(
        user_id=user.id,
        group_id=group_db.id,
        name=payload.name,
        telegram_username=payload.telegram_username,
        phone=payload.phone,
        notes=payload.notes,
    )
    partner_db = await partner_svc.create_partner(db, partner)

    return PartnerCreateResponse(success=True, partner_id=partner_db.id).model_dump()


@router.delete("/partners/{partner_id}")
async def delete_practice_endpoint(
    partner_id: str,
    db: AsyncSession = Depends(get_db_session),
    partner_svc: PartnerService = Depends(get_partner_service),
):
    """Удалить практику и все связанные семена"""
    try:
        result = await partner_svc.delete_partner(db, partner_id)
        return {"success": result}
    except Exception as e:
        logger.error(f"Error deleting practice: {e}", exc_info=True)
        return {"error": "Failed to delete practice"}
