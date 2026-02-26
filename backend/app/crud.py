"""CRUD operations for database"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List
from datetime import datetime, UTC
from uuid import uuid4

from app.models.db_models import (
    UserDB, SeedDB, PartnerDB, PartnerGroupDB,
    HabitDB, HabitCompletionDB, PartnerActionDB,
    ProblemHistoryDB, MessageLogDB,
    DailyTaskDB, DailyPlanDB,
)
from app.models.user import UserProfile
from app.models.seed import Seed, ACTION_TYPES
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


async def get_latest_message_log(
    db: AsyncSession,
    user_id: int,
    message_type: str,
    channel: str,
    date: datetime,
    karma_plan_id: str | None = None,
) -> MessageLogDB | None:
    """Get latest message log for user/type/channel/day (optionally for specific karma plan)."""
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = date.replace(hour=23, minute=59, second=59, microsecond=999)

    query = (
        select(MessageLogDB)
        .where(
            MessageLogDB.user_id == user_id,
            MessageLogDB.message_type == message_type,
            MessageLogDB.channel == channel,
            MessageLogDB.sent_at >= day_start,
            MessageLogDB.sent_at <= day_end,
        )
        .order_by(MessageLogDB.sent_at.desc())
        .limit(1)
    )

    if karma_plan_id is not None:
        query = query.where(MessageLogDB.karma_plan_id == karma_plan_id)
    else:
        query = query.where(MessageLogDB.karma_plan_id.is_(None))

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_message_log(
    db: AsyncSession,
    *,
    user_id: int,
    message_type: str,
    channel: str,
    payload: dict,
    karma_plan_id: str | None = None,
    daily_plan_id: str | None = None,
    sent_at: datetime | None = None,
) -> MessageLogDB:
    """Create new message log entry for caching and analytics."""
    log = MessageLogDB(
        id=str(uuid4()),
        user_id=user_id,
        karma_plan_id=karma_plan_id,
        daily_plan_id=daily_plan_id,
        message_type=message_type,
        channel=channel,
        payload=payload,
        sent_at=sent_at or datetime.now(UTC),
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def toggle_daily_task_completion(db: AsyncSession, user_id: int, task_id: int, completed: bool) -> bool:
    """
    Toggle completion status of a daily task.
    - Updates DailyTaskDB.
    - Creates/Deletes associated SeedDB record.
    - Updates UserDB stats (total_seeds).
    """
    # 1. Get the task with context
    result = await db.execute(
        select(DailyTaskDB, DailyPlanDB)
        .join(DailyPlanDB, DailyTaskDB.daily_plan_id == DailyPlanDB.id)
        .where(DailyTaskDB.id == task_id)
    )
    row = result.first()
    if not row:
        return False
        
    task, plan = row
    
    # Verify user ownership via KarmaPlan (needs another join or separate query)
    # Actually DailyPlanDB -> KarmaPlanDB -> user_id
    from app.models.db_models import KarmaPlanDB
    kp_result = await db.execute(
        select(KarmaPlanDB).where(KarmaPlanDB.id == plan.karma_plan_id)
    )
    karma_plan = kp_result.scalar_one_or_none()
    
    if not karma_plan or karma_plan.user_id != user_id:
        return False

    # 2. Update Task
    if task.completed == completed:
        return True # No change needed

    task.completed = completed
    task.completed_at = datetime.now(UTC) if completed else None
    
    # 3. Handle Seed
    if completed:
        # Derive action_type for seed строго из task.action_type
        raw_action_type = getattr(task, "action_type", None) or ""
        seed_action_type = raw_action_type.strip().lower()

        # Если по какой-то причине в задаче нет action_type,
        # мягко считаем это добрым действием
        if not seed_action_type:
            seed_action_type = "kindness"

        # Clamp to centralized ACTION_TYPES keys to avoid "плавающих" значений
        if seed_action_type not in ACTION_TYPES:
            seed_action_type = "kindness"

        partner_group = task.group or "project"

        # Create Seed
        seed = SeedDB(
            id=str(uuid4()),
            user_id=user_id,
            timestamp=datetime.now(UTC),
            action_type=seed_action_type,
            description=task.description,
            partner_id=getattr(task, "partner_id", None),
            partner_group=partner_group,
            intention_score=5,
            emotion_level=5,
            understanding=True,
            # Context links
            karma_plan_id=karma_plan.id,
            daily_plan_id=plan.id,
            daily_task_id=task.id,
            estimated_maturation_days=21,
            strength_multiplier=1.0,
        )
        db.add(seed)
        
        # Increment user seeds
        await increment_user_seeds_count(db, user_id)
        
    else:
        # Delete associated Seed
        # Find seed by daily_task_id
        await db.execute(
            delete(SeedDB).where(SeedDB.daily_task_id == task.id)
        )
        
        # Decrement user seeds
        # We need to decrement carefully
        user_result = await db.execute(select(UserDB).where(UserDB.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.total_seeds > 0:
            user.total_seeds -= 1
            user.updated_at = datetime.now(UTC)

    await db.flush()
    return True


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
