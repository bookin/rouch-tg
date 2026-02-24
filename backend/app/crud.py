"""CRUD operations for database"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime, UTC
from uuid import uuid4

from app.models.db_models import (
    UserDB, SeedDB, PartnerDB, PartnerGroupDB,
    HabitDB, HabitCompletionDB, PartnerActionDB,
    ProblemHistoryDB, DailySuggestionDB
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


from sqlalchemy.dialects.postgresql import insert as pg_insert


async def get_or_create_user(db: AsyncSession, telegram_id: int, first_name: str, username: str = None) -> UserDB:
    """Get existing user or create new one atomically"""
    stmt = pg_insert(UserDB).values(
        telegram_id=telegram_id,
        first_name=first_name,
        username=username,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ).on_conflict_do_update(
        index_elements=['telegram_id'],
        set_={
            'first_name': first_name,
            'username': username,
            'updated_at': datetime.now(UTC),
        }
    )
    
    await db.execute(stmt)
    await db.flush()
    return await get_user_by_telegram_id(db, telegram_id)


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
        universal_category=group.universal_category,
        is_default=group.is_default,
        user_id=group.user_id,
        created_at=group.created_at
    )
    db.add(group_db)
    await db.flush()
    await db.refresh(group_db)
    return group_db


async def get_default_partner_group_by_category(db: AsyncSession, user_id: int, category: str) -> Optional[PartnerGroupDB]:
    """Get default partner group for a universal category"""
    result = await db.execute(
        select(PartnerGroupDB).where(
            PartnerGroupDB.user_id == user_id,
            PartnerGroupDB.universal_category == category,
            PartnerGroupDB.is_default == True
        ).limit(1)
    )
    return result.scalar_one_or_none()


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
    now = datetime.now(UTC)
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


async def create_partner(db: AsyncSession, partner: Partner) -> PartnerDB:
    """Create new partner"""
    partner_db = PartnerDB(
        id=partner.id,
        user_id=partner.user_id,
        group_id=partner.group_id,
        name=partner.name,
        telegram_username=partner.telegram_username,
        phone=partner.phone,
        contact_type=partner.contact_type,
        notes=partner.notes,
        created_at=partner.created_at
    )
    db.add(partner_db)
    await db.flush()
    await db.refresh(partner_db)
    return partner_db


async def get_user_partners(db: AsyncSession, user_id: int) -> List[PartnerDB]:
    """Get user's partners"""
    result = await db.execute(
        select(PartnerDB).where(PartnerDB.user_id == user_id)
    )
    return result.scalars().all()


async def get_partners_by_universal_category(db: AsyncSession, user_id: int, category: str) -> List[PartnerDB]:
    """Get partners filtered by universal category"""
    result = await db.execute(
        select(PartnerDB)
        .join(PartnerGroupDB, PartnerDB.group_id == PartnerGroupDB.id)
        .where(
            PartnerDB.user_id == user_id,
            PartnerGroupDB.universal_category == category
        )
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
        user.updated_at = datetime.now(UTC)
        await db.flush()


async def increment_user_seeds_count(db: AsyncSession, user_id: int):
    """Increment user's total seeds count"""
    result = await db.execute(
        select(UserDB).where(UserDB.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.total_seeds += 1
        user.updated_at = datetime.now(UTC)
        await db.flush()


async def update_user_focus(db: AsyncSession, user_id: int, focus: str) -> bool:
    """Update user's current focus area"""
    result = await db.execute(
        select(UserDB).where(UserDB.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.current_focus = focus
        user.updated_at = datetime.now(UTC)
        await db.flush()
        return True
    return False


async def save_problem_history(
    db: AsyncSession, 
    user_id: int, 
    problem_text: str, 
    solution_json: dict,
    diagnostic_json: dict | None = None,
) -> ProblemHistoryDB:
    """Save problem solution to history"""
    # Не раздуваем solution_json: диагностические данные храним отдельно.
    clean_solution = dict(solution_json) if solution_json is not None else {}

    # Если diagnostic_json не передали явно, попробуем вытащить его из solution_json
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


async def get_problem_history(db: AsyncSession, user_id: int, limit: int = 20) -> List[ProblemHistoryDB]:
    """Get user's problem history"""
    result = await db.execute(
        select(ProblemHistoryDB)
        .where(ProblemHistoryDB.user_id == user_id)
        .order_by(ProblemHistoryDB.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def set_active_problem(db: AsyncSession, user_id: int, history_id: str) -> bool:
    """Set a specific problem as active and deactivate others"""
    from sqlalchemy import update
    # 1. Deactivate all
    await db.execute(
        update(ProblemHistoryDB)
        .where(ProblemHistoryDB.user_id == user_id)
        .values(is_active=False)
    )
    # 2. Activate one
    result = await db.execute(
        update(ProblemHistoryDB)
        .where(ProblemHistoryDB.user_id == user_id, ProblemHistoryDB.id == history_id)
        .values(is_active=True)
    )
    await db.flush()
    return result.rowcount > 0


async def get_daily_suggestions(db: AsyncSession, user_id: int, date: datetime) -> List[DailySuggestionDB]:
    """Get AI suggestions for a specific user and date"""
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = date.replace(hour=23, minute=59, second=59, microsecond=999)
    
    result = await db.execute(
        select(DailySuggestionDB)
        .where(
            DailySuggestionDB.user_id == user_id,
            DailySuggestionDB.date >= day_start,
            DailySuggestionDB.date <= day_end
        )
        .order_by(DailySuggestionDB.group.asc())
    )
    return result.scalars().all()


async def save_daily_suggestions(db: AsyncSession, user_id: int, suggestions: List[dict]):
    """Save newly generated AI suggestions"""
    objs = [
        DailySuggestionDB(
            id=str(uuid4()),
            user_id=user_id,
            group=s["group"],
            description=s["description"],
            why=s["why"],
            completed=False,
            date=datetime.now(UTC),
        )
        for s in suggestions
    ]
    db.add_all(objs)
    await db.flush()
    return objs


async def update_daily_suggestion_completion(db: AsyncSession, suggestion_id: str, completed: bool):
    """Update completion status of a daily suggestion"""
    from sqlalchemy import update
    await db.execute(
        update(DailySuggestionDB)
        .where(DailySuggestionDB.id == suggestion_id)
        .values(completed=completed)
    )
    await db.flush()


async def clear_today_suggestions(db: AsyncSession, user_id: int):
    """Delete all suggestions for today (e.g. when focus changes)"""
    from sqlalchemy import delete
    # today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    await db.execute(
        delete(DailySuggestionDB)
        .where(
            DailySuggestionDB.user_id == user_id
        )
    )
    await db.flush()


async def reset_user_progress(db: AsyncSession, user_id: int):
    """Reset all user progress and delete related data"""
    from sqlalchemy import delete
    
    # 1. Delete related records
    # Note: Order matters due to Foreign Keys if cascades aren't set everywhere
    
    # Dependent on Habits
    await db.execute(delete(HabitCompletionDB).where(HabitCompletionDB.user_id == user_id))
    
    # Dependent on Partners/Seeds
    await db.execute(delete(PartnerActionDB).where(PartnerActionDB.user_id == user_id))
    
    # Main entities
    await db.execute(delete(DailySuggestionDB).where(DailySuggestionDB.user_id == user_id))
    await db.execute(delete(ProblemHistoryDB).where(ProblemHistoryDB.user_id == user_id))
    await db.execute(delete(HabitDB).where(HabitDB.user_id == user_id))
    
    # Seeds can be linked to partners, but we delete seeds first to be safe or set null
    # Seeds have partner_id foreign key.
    await db.execute(delete(SeedDB).where(SeedDB.user_id == user_id))
    
    # Partners and Groups
    await db.execute(delete(PartnerDB).where(PartnerDB.user_id == user_id))
    await db.execute(delete(PartnerGroupDB).where(PartnerGroupDB.user_id == user_id))
    
    # 2. Reset User Fields
    result = await db.execute(
        select(UserDB).where(UserDB.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Onboarding
        user.occupation = "employee"
        user.available_times = []
        user.daily_minutes = 30
        user.current_habits = []
        user.physical_restrictions = None
        
        # Progress
        user.streak_days = 0
        user.total_seeds = 0
        user.completed_practices = 0
        
        # Settings
        user.current_focus = None
        
        # Timestamps
        user.last_onboarding_update = None
        user.last_morning_message = None
        user.last_evening_message = None

        user.updated_at = datetime.now(UTC)
        
    await db.flush()
