"""Seed database model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.db.user import UserDB
    from app.models.db.daily import DailyTaskDB


class SeedDB(Base):
    """Seed database model"""
    __tablename__ = "seeds"
    __table_args__ = (
        Index("idx_seeds_user_timestamp", "user_id", "timestamp"),
        Index("idx_seeds_user_daily_task", "user_id", "daily_task_id"),
        Index("idx_seeds_user_practice_timestamp", "user_id", "practice_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    action_type: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)

    partner_id: Mapped[str | None] = mapped_column(ForeignKey("partners.id", ondelete="SET NULL"))
    partner_group: Mapped[str | None] = mapped_column(String, default="world")

    intention_score: Mapped[int] = mapped_column(default=5)
    emotion_level: Mapped[int] = mapped_column(default=5)
    understanding: Mapped[bool] = mapped_column(default=False)

    estimated_maturation_days: Mapped[int] = mapped_column(default=21)
    strength_multiplier: Mapped[float] = mapped_column(default=1.0)

    rejoice_count: Mapped[int] = mapped_column(default=0)
    last_rejoiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Context links
    karma_plan_id: Mapped[str | None] = mapped_column(ForeignKey("karma_plans.id", ondelete="SET NULL"))
    daily_plan_id: Mapped[str | None] = mapped_column(ForeignKey("daily_plans.id", ondelete="SET NULL"))
    daily_task_id: Mapped[int | None] = mapped_column(ForeignKey("daily_tasks.id", ondelete="SET NULL"))
    practice_id: Mapped[str | None] = mapped_column(ForeignKey("practices.id", ondelete="SET NULL"))

    # Relationships
    user: Mapped[UserDB] = relationship(back_populates="seeds")
    daily_task: Mapped[DailyTaskDB | None] = relationship(back_populates="seeds")
