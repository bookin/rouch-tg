"""SQLAlchemy ORM models for database"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Date,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    LargeBinary,
    PrimaryKeyConstraint,
    UniqueConstraint,
    func,
    BigInteger,
    Sequence,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.database import Base
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable

class UserDB(SQLAlchemyBaseUserTable[int], Base):
    """User database model with FastAPI Users integration"""
    __tablename__ = "users"
    
    # Integer PK (not UUID)
    id = Column(Integer, primary_key=True, index=True)
    
    # Override fastapi-users base columns for hybrid auth
    email = Column(String(320), unique=True, index=True, nullable=True)
    hashed_password = Column(String(1024), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    is_superuser = Column(Boolean, nullable=False, server_default="false")
    is_verified = Column(Boolean, nullable=False, server_default="false")
    
    # Telegram-specific
    telegram_id = Column(Integer, unique=True, index=True, nullable=True)
    first_name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    
    # Onboarding
    occupation = Column(String, default="employee")
    available_times = Column(JSON, default=lambda: [])
    daily_minutes = Column(Integer, default=30)
    current_habits = Column(JSON, default=lambda: [])
    physical_restrictions = Column(String, nullable=True)
    
    # Progress
    streak_days = Column(Integer, default=0)
    total_seeds = Column(Integer, default=0)
    completed_practices = Column(Integer, default=0)
    
    # Settings
    timezone = Column(String, default="UTC")
    morning_enabled = Column(Boolean, default=True)
    evening_enabled = Column(Boolean, default=True)
    current_focus = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_onboarding_update = Column(DateTime(timezone=True), nullable=True)
    last_morning_message = Column(DateTime(timezone=True), nullable=True)
    last_evening_message = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    seeds = relationship("SeedDB", back_populates="user", lazy="selectin")
    partners = relationship("PartnerDB", back_populates="user", lazy="selectin")
    problem_history = relationship("ProblemHistoryDB", back_populates="user", lazy="selectin")
    # daily_tasks = relationship("DailyTaskDB", back_populates="user", lazy="selectin")
    karma_plans = relationship("KarmaPlanDB", back_populates="user", lazy="selectin")
    practice_progress = relationship("PracticeProgressDB", back_populates="user", lazy="selectin")


class SeedDB(Base):
    """Seed database model"""
    __tablename__ = "seeds"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    action_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    partner_id = Column(String, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True)
    partner_group = Column(String, default="world")
    
    intention_score = Column(Integer, default=5)
    emotion_level = Column(Integer, default=5)
    understanding = Column(Boolean, default=False)
    
    estimated_maturation_days = Column(Integer, default=21)
    strength_multiplier = Column(Float, default=1.0)

    rejoice_count = Column(Integer, default=0)
    last_rejoiced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Context links (Requested by user)
    karma_plan_id = Column(String, ForeignKey("karma_plans.id", ondelete="SET NULL"), nullable=True)
    daily_plan_id = Column(String, ForeignKey("daily_plans.id", ondelete="SET NULL"), nullable=True)
    daily_task_id = Column(Integer, ForeignKey("daily_tasks.id", ondelete="SET NULL"), nullable=True)
    practice_id = Column(String, ForeignKey("practices.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("UserDB", back_populates="seeds")
    daily_task = relationship("DailyTaskDB", back_populates="seeds")


class CoffeeMeditationSessionDB(Base):
    __tablename__ = "coffee_meditation_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_coffee_session_user_local_date"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    local_date = Column(Date, nullable=False, index=True)

    karma_plan_id = Column(String, ForeignKey("karma_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    daily_plan_id = Column(String, ForeignKey("daily_plans.id", ondelete="SET NULL"), nullable=True, index=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    notes_draft = Column(Text, nullable=True)
    current_step = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("UserDB", lazy="selectin")
    rejoiced_seeds = relationship(
        "CoffeeMeditationRejoicedSeedDB",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CoffeeMeditationRejoicedSeedDB(Base):
    __tablename__ = "coffee_meditation_rejoiced_seeds"

    session_id = Column(
        String,
        ForeignKey("coffee_meditation_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seed_id = Column(
        String,
        ForeignKey("seeds.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("CoffeeMeditationSessionDB", back_populates="rejoiced_seeds")


class PartnerGroupDB(Base):
    """Partner group database model"""
    __tablename__ = "partner_groups"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    universal_category = Column(String, default="world")
    is_default = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PartnerDB(Base):
    """Partner database model"""
    __tablename__ = "partners"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    group_id = Column(String, ForeignKey("partner_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    preferences = Column(JSON, default=list)
    important_dates = Column(JSON, default=list)
    
    seeds_count = Column(Integer, default=0)
    last_action_date = Column(DateTime, nullable=True)
    
    telegram_username = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    contact_type = Column(String, default="physical")  # physical, online, mental
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("UserDB", back_populates="partners")


class PracticeDB(Base):
    """Practice template database model"""
    __tablename__ = "practices"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    duration_minutes = Column(Integer, nullable=False)
    requires_morning = Column(Boolean, default=False)
    requires_silence = Column(Boolean, default=False)
    physical_intensity = Column(String, default="low")    # 'low', 'medium', 'high'
    
    difficulty = Column(Integer, default=1)
    max_completions_per_day = Column(Integer, default=1)
    habit_min_streak_days = Column(Integer, default=14)
    habit_min_score = Column(Integer, default=70)
    steps = Column(JSON, default=list)           # list of step strings
    contraindications = Column(JSON, default=list) # list of contraindication tags
    benefits = Column(Text, nullable=True)
    tags = Column(JSON, default=list)             # list of tag strings
    
    source = Column(String, nullable=True)


class PartnerActionDB(Base):
    """Partner action record"""
    __tablename__ = "partner_actions"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    partner_id = Column(String, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True)
    partner_name = Column(String, nullable=True)
    seed_id = Column(String, ForeignKey("seeds.id"), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    action = Column(Text, nullable=False)
    completed = Column(Boolean, default=False, index=True)

class PracticeProgressDB(Base):
    """Practice progress tracking for habit transformation"""

    __tablename__ = "practice_progress"

    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    practice_id = Column(String, ForeignKey("practices.id"), nullable=False)

    # Progress metrics
    habit_score = Column(Integer, default=0)  # 0-100, автоматизация
    streak_days = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)

    # Metadata
    last_completed = Column(DateTime(timezone=True), nullable=True)
    is_habit = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)
    karma_plan_id = Column(String, ForeignKey("karma_plans.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("UserDB", back_populates="practice_progress")
    practice = relationship("PracticeDB", lazy="selectin")

    # Unique constraint
    __table_args__ = (Index('idx_user_practice_progress', 'user_id', 'practice_id', unique=True),)


class ProblemHistoryDB(Base):
    """Problem history database model"""
    __tablename__ = "problem_history"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_text = Column(Text, nullable=False)
    solution_json = Column(JSON, nullable=False)
    diagnostic_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("UserDB", back_populates="problem_history")
    karma_plan = relationship("KarmaPlanDB", back_populates="problem_history", uselist=False)


class KarmaPlanDB(Base):
    """Active Karmic Project plan"""
    __tablename__ = "karma_plans"

    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_history_id = Column(String, ForeignKey("problem_history.id"), nullable=False)

    status = Column(String, default="active", index=True) # active, completed, cancelled
    strategy_snapshot = Column(JSON, nullable=False) # {stop, start, grow, ...}
    isolation_settings = Column(JSON, nullable=True) # {source: {is_isolated: true}, ...}
    
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    duration_days = Column(Integer, default=30)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("UserDB", back_populates="karma_plans")
    problem_history = relationship("ProblemHistoryDB", back_populates="karma_plan")
    daily_plans = relationship("DailyPlanDB", back_populates="karma_plan", cascade="all, delete-orphan", lazy="selectin")
    partners_association = relationship("KarmaPlanPartnerDB", back_populates="plan", cascade="all, delete-orphan", lazy="selectin")


class KarmaPlanPartnerDB(Base):
    """Many-to-Many link between KarmaPlan and Partner with category"""
    __tablename__ = "karma_plan_partners"

    plan_id = Column(String, ForeignKey("karma_plans.id", ondelete="CASCADE"), primary_key=True)
    partner_id = Column(String, ForeignKey("partners.id", ondelete="CASCADE"), primary_key=True)
    category = Column(String, nullable=False, primary_key=True) # source, ally, protege, world

    # Relationships
    plan = relationship("KarmaPlanDB", back_populates="partners_association")
    partner = relationship("PartnerDB", lazy="joined")


class DailyPlanDB(Base):
    """Daily plan within a Karmic Project"""
    __tablename__ = "daily_plans"

    id = Column(String, primary_key=True)
    karma_plan_id = Column(String, ForeignKey("karma_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    day_number = Column(Integer, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    focus_quality = Column(String, nullable=True) # e.g. "Giving", "Ethics"
    # tasks = Column(JSON, default=list) # Removed in favor of DailyTaskDB
    
    is_completed = Column(Boolean, default=False)
    completion_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    karma_plan = relationship("KarmaPlanDB", back_populates="daily_plans")
    tasks = relationship("DailyTaskDB", back_populates="daily_plan", cascade="all, delete-orphan", lazy="selectin")


class DailyTaskDB(Base):
    """Individual task within a Daily Plan"""
    __tablename__ = "daily_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    daily_plan_id = Column(String, ForeignKey("daily_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    description = Column(Text, nullable=False)
    why = Column(Text, nullable=True)
    group = Column(String, default="project") # project, source, ally, protege, world
    partner_id = Column(String, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String, nullable=True, index=True)
    
    completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    order = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    daily_plan = relationship("DailyPlanDB", back_populates="tasks")
    seeds = relationship("SeedDB", back_populates="daily_task")


# class DailySuggestionDB(Base):
#     """Daily AI suggestion database model"""
#     __tablename__ = "daily_suggestions"
#
#     id = Column(String, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
#     group = Column(String, nullable=False)
#     description = Column(Text, nullable=False)
#     why = Column(Text, nullable=False)
#     completed = Column(Boolean, default=False, index=True)
#     date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
#     seed_id = Column(String, ForeignKey("seeds.id", ondelete="SET NULL"), nullable=True)
#
#     # Relationships
#     user = relationship("UserDB", back_populates="daily_suggestions")


class MessageLogDB(Base):
    """Log of generated messages (morning, evening, etc.) for caching and analytics"""
    __tablename__ = "message_logs"

    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    karma_plan_id = Column(String, ForeignKey("karma_plans.id", ondelete="CASCADE"), nullable=True, index=True)
    daily_plan_id = Column(String, ForeignKey("daily_plans.id", ondelete="CASCADE"), nullable=True, index=True)

    message_type = Column(String, nullable=False, index=True)  # morning, evening, etc.
    channel = Column(String, nullable=False, default="system")  # telegram, webapp, system
    payload = Column(JSON, nullable=False)  # full structured message payload

    sent_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# LangGraph Checkpoint Tables
class LangGraphCheckpointDB(Base):
    """LangGraph checkpoints"""
    __tablename__ = "checkpoints"
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id"),
        {"extend_existing": True}
    )
    
    thread_id = Column(String, nullable=False)
    checkpoint_id = Column(String, nullable=False)
    parent_checkpoint_id = Column(String, nullable=True)
    type = Column(String, nullable=True)
    checkpoint = Column(LargeBinary, nullable=False)
    metadata_ = Column("metadata", LargeBinary, nullable=False)

class LangGraphCheckpointBlobDB(Base):
    """LangGraph checkpoint blobs"""
    __tablename__ = "checkpoint_blobs"
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id", "type"),
        {"extend_existing": True}
    )
    
    thread_id = Column(String, nullable=False)
    checkpoint_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    blob = Column(LargeBinary, nullable=False)

class LangGraphCheckpointWriteDB(Base):
    """LangGraph checkpoint writes"""
    __tablename__ = "checkpoint_writes"
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id", "task_id", "idx"),
        {"extend_existing": True}
    )
    
    thread_id = Column(String, nullable=False)
    checkpoint_id = Column(String, nullable=False)
    task_id = Column(String, nullable=False)
    idx = Column(Integer, nullable=False)
    channel = Column(String, nullable=False)
    type = Column(String, nullable=True)
    blob = Column(LargeBinary, nullable=False)
