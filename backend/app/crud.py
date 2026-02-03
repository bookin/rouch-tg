"""CRUD operations for database"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from app.models.db_models import (
    UserDB, SeedDB, PartnerDB, PartnerGroupDB,
    HabitDB, HabitCompletionDB, PartnerActionDB
)
from app.models.user import UserProfile
from app.models.seed import Seed
from app.models.partner import Partner, PartnerGroup
from app.models.partner import DEFAULT_GROUPS


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[UserDB]:
    """Get user by Telegram ID with optimized query"""
    result = await db.execute(
        select(UserDB)
        .where(UserDB.telegram_id == telegram_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, telegram_id: int, first_name: str, username: str = None) -> UserDB:
    """Create new user"""
    user = UserDB(
        telegram_id=telegram_id,
        first_name=first_name,
        username=username
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_or_create_user(db: AsyncSession, telegram_id: int, first_name: str, username: str = None) -> UserDB:
    """Get existing user or create new one"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        user = await create_user(db, telegram_id, first_name, username)
    return user


async def get_active_users(db: AsyncSession, morning_enabled: bool = None, evening_enabled: bool = None) -> List[UserDB]:
    """Get active users for scheduled messages"""
    query = select(UserDB)
    
    if morning_enabled is not None:
        query = query.where(UserDB.morning_enabled == morning_enabled)
    
    if evening_enabled is not None:
        query = query.where(UserDB.evening_enabled == evening_enabled)
    
    result = await db.execute(query)
    return result.scalars().all()


async def create_seed(db: AsyncSession, seed: Seed) -> SeedDB:
    """Create new seed"""
    seed_db = SeedDB(
        id=seed.id,
        user_id=seed.user_id,
        timestamp=seed.timestamp,
        action_type=seed.action_type,
        description=seed.description,
        partner_id=seed.partner_id,
        partner_group=seed.partner_group,
        intention_score=seed.intention_score,
        emotion_level=seed.emotion_level,
        understanding=seed.understanding,
        estimated_maturation_days=seed.estimated_maturation_days,
        strength_multiplier=seed.strength_multiplier
    )
    db.add(seed_db)
    await db.flush()
    await db.refresh(seed_db)
    return seed_db


async def get_user_seeds(db: AsyncSession, user_id: int, limit: int = 50) -> List[SeedDB]:
    """Get user's seeds"""
    result = await db.execute(
        select(SeedDB)
        .where(SeedDB.user_id == user_id)
        .order_by(SeedDB.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_seeds_by_date_range(
    db: AsyncSession, 
    user_id: int, 
    start_date: datetime, 
    end_date: datetime
) -> List[SeedDB]:
    """Get seeds for date range"""
    result = await db.execute(
        select(SeedDB)
        .where(
            SeedDB.user_id == user_id,
            SeedDB.timestamp >= start_date,
            SeedDB.timestamp <= end_date
        )
        .order_by(SeedDB.timestamp.desc())
    )
    return result.scalars().all()


async def create_partner_group(db: AsyncSession, group: PartnerGroup) -> PartnerGroupDB:
    """Create partner group"""
    group_db = PartnerGroupDB(
        id=group.id,
        name=group.name,
        icon=group.icon,
        description=group.description,
        is_default=group.is_default,
        user_id=group.user_id,
        created_at=group.created_at
    )
    db.add(group_db)
    await db.flush()
    await db.refresh(group_db)
    return group_db


async def get_partner_groups(db: AsyncSession, user_id: int) -> List[PartnerGroupDB]:
    """Get all partner groups for user"""
    result = await db.execute(
        select(PartnerGroupDB)
        .where(PartnerGroupDB.user_id == user_id)
        .order_by(PartnerGroupDB.created_at.asc())
    )
    return result.scalars().all()


async def ensure_default_partner_groups(db: AsyncSession, user_id: int) -> List[PartnerGroupDB]:
    """Ensure the 4 default partner groups exist for a user"""
    existing = await db.execute(
        select(PartnerGroupDB).where(
            PartnerGroupDB.user_id == user_id,
            PartnerGroupDB.is_default == True,  # noqa: E712
        )
    )
    existing_groups = existing.scalars().all()
    if existing_groups:
        return existing_groups

    groups: list[PartnerGroupDB] = []
    now = datetime.utcnow()
    for g in DEFAULT_GROUPS:
        groups.append(
            PartnerGroupDB(
                id=str(uuid4()),
                name=g["name"],
                icon=g["icon"],
                description=g["description"],
                is_default=True,
                user_id=user_id,
                created_at=now,
            )
        )

    db.add_all(groups)
    await db.flush()
    return groups


async def get_user_partners(db: AsyncSession, user_id: int) -> List[PartnerDB]:
    """Get user's partners"""
    result = await db.execute(
        select(PartnerDB).where(PartnerDB.user_id == user_id)
    )
    return result.scalars().all()


async def update_user_streak(db: AsyncSession, user_id: int, streak_days: int):
    """Update user streak"""
    result = await db.execute(
        select(UserDB).where(UserDB.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.streak_days = streak_days
        user.updated_at = datetime.utcnow()
        await db.flush()


async def increment_user_seeds_count(db: AsyncSession, user_id: int):
    """Increment user's total seeds count"""
    result = await db.execute(
        select(UserDB).where(UserDB.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.total_seeds += 1
        user.updated_at = datetime.utcnow()
        await db.flush()
