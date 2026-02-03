"""SQLAlchemy ORM models for database"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, JSON, ForeignKey, LargeBinary, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class UserDB(Base):
    """User database model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_onboarding_update = Column(DateTime, nullable=True)
    last_morning_message = Column(DateTime, nullable=True)
    last_evening_message = Column(DateTime, nullable=True)
    
    # Relationships
    seeds = relationship("SeedDB", back_populates="user", lazy="selectin")
    habits = relationship("HabitDB", back_populates="user", lazy="selectin")
    partners = relationship("PartnerDB", back_populates="user", lazy="selectin")


class SeedDB(Base):
    """Seed database model"""
    __tablename__ = "seeds"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    action_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    partner_id = Column(String, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True)
    partner_group = Column(String, default="world")
    
    intention_score = Column(Integer, default=5)
    emotion_level = Column(Integer, default=5)
    understanding = Column(Boolean, default=False)
    
    estimated_maturation_days = Column(Integer, default=21)
    strength_multiplier = Column(Float, default=1.0)
    
    # Relationships
    user = relationship("UserDB", back_populates="seeds")


class PartnerGroupDB(Base):
    """Partner group database model"""
    __tablename__ = "partner_groups"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    physical_intensity = Column(String, default="low")
    
    source = Column(String, nullable=True)


class HabitDB(Base):
    """User habit database model"""
    __tablename__ = "habits"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    practice_id = Column(String, ForeignKey("practices.id"), nullable=False)
    
    frequency = Column(String, default="daily")
    preferred_time = Column(String, default="morning")
    duration = Column(Integer, default=30)
    
    streak = Column(Integer, default=0)
    last_completed = Column(DateTime, nullable=True)
    completion_rate = Column(Float, default=0.0)
    
    user_restrictions = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("UserDB", back_populates="habits")


class HabitCompletionDB(Base):
    """Habit completion record"""
    __tablename__ = "habit_completions"
    
    id = Column(String, primary_key=True)
    habit_id = Column(String, ForeignKey("habits.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    duration_actual = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)


class PartnerActionDB(Base):
    """Partner action record"""
    __tablename__ = "partner_actions"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    partner_id = Column(String, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True)
    partner_name = Column(String, nullable=True)
    seed_id = Column(String, ForeignKey("seeds.id"), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    action = Column(Text, nullable=False)
    completed = Column(Boolean, default=False, index=True)

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
