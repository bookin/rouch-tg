"""DailyPlan and DailyTask database models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.db.seed import SeedDB
    from app.models.db.karma_plan import KarmaPlanDB


class DailyPlanDB(Base):
    """Daily plan within a Karmic Project"""
    __tablename__ = "daily_plans"
    __table_args__ = (
        Index("idx_daily_plans_karma_plan_date", "karma_plan_id", "date"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    karma_plan_id: Mapped[str] = mapped_column(ForeignKey("karma_plans.id", ondelete="CASCADE"), index=True)

    day_number: Mapped[int] = mapped_column()
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    focus_quality: Mapped[str | None] = mapped_column(String)

    is_completed: Mapped[bool] = mapped_column(default=False)
    completion_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    karma_plan: Mapped[KarmaPlanDB] = relationship(back_populates="daily_plans")
    tasks: Mapped[list[DailyTaskDB]] = relationship(back_populates="daily_plan", cascade="all, delete-orphan", lazy="selectin")


class DailyTaskDB(Base):
    """Individual task within a Daily Plan"""
    __tablename__ = "daily_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    daily_plan_id: Mapped[str] = mapped_column(ForeignKey("daily_plans.id", ondelete="CASCADE"), index=True)

    description: Mapped[str] = mapped_column(Text)
    why: Mapped[str | None] = mapped_column(Text)
    group: Mapped[str | None] = mapped_column(String, default="project")
    partner_id: Mapped[str | None] = mapped_column(ForeignKey("partners.id", ondelete="SET NULL"))
    action_type: Mapped[str | None] = mapped_column(String, index=True)

    completed: Mapped[bool] = mapped_column(default=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    daily_plan: Mapped[DailyPlanDB] = relationship(back_populates="tasks")
    seeds: Mapped[list[SeedDB]] = relationship(back_populates="daily_task")
