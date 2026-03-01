"""Practice and PracticeProgress database models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.db.user import UserDB


class PracticeDB(Base):
    """Practice template database model"""
    __tablename__ = "practices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)

    duration_minutes: Mapped[int] = mapped_column()
    requires_morning: Mapped[bool] = mapped_column(default=False)
    requires_silence: Mapped[bool] = mapped_column(default=False)
    physical_intensity: Mapped[str | None] = mapped_column(String, default="low")

    difficulty: Mapped[int] = mapped_column(default=1)
    max_completions_per_day: Mapped[int] = mapped_column(default=1)
    habit_min_streak_days: Mapped[int] = mapped_column(default=14)
    habit_min_score: Mapped[int] = mapped_column(default=70)
    steps: Mapped[list | None] = mapped_column(JSON, default=list)
    contraindications: Mapped[list | None] = mapped_column(JSON, default=list)
    benefits: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)

    source: Mapped[str | None] = mapped_column(String)


class PracticeProgressDB(Base):
    """Practice progress tracking for habit transformation"""

    __tablename__ = "practice_progress"
    __table_args__ = (Index('idx_user_practice_progress', 'user_id', 'practice_id', unique=True),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))

    # Progress metrics
    habit_score: Mapped[int] = mapped_column(default=0)
    streak_days: Mapped[int] = mapped_column(default=0)
    total_completions: Mapped[int] = mapped_column(default=0)

    # Metadata
    last_completed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_habit: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_hidden: Mapped[bool] = mapped_column(default=False)
    karma_plan_id: Mapped[str | None] = mapped_column(ForeignKey("karma_plans.id", ondelete="SET NULL"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped[UserDB] = relationship(back_populates="practice_progress")
    practice: Mapped[PracticeDB] = relationship(lazy="selectin")
