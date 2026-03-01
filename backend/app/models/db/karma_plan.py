"""KarmaPlan and KarmaPlanPartner database models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.db.user import UserDB
    from app.models.db.problem import ProblemHistoryDB
    from app.models.db.daily import DailyPlanDB
    from app.models.db.partner import PartnerDB


class KarmaPlanDB(Base):
    """Active Karmic Project plan"""
    __tablename__ = "karma_plans"
    __table_args__ = (
        Index("idx_karma_plans_user_status", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_history_id: Mapped[str] = mapped_column(ForeignKey("problem_history.id"))

    status: Mapped[str | None] = mapped_column(String, default="active", index=True)
    strategy_snapshot: Mapped[dict] = mapped_column(JSON)
    isolation_settings: Mapped[dict | None] = mapped_column(JSON)

    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_days: Mapped[int] = mapped_column(default=30)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped[UserDB] = relationship(back_populates="karma_plans")
    problem_history: Mapped[ProblemHistoryDB] = relationship(back_populates="karma_plan")
    daily_plans: Mapped[list[DailyPlanDB]] = relationship(back_populates="karma_plan", cascade="all, delete-orphan", lazy="selectin")
    partners_association: Mapped[list[KarmaPlanPartnerDB]] = relationship(back_populates="plan", cascade="all, delete-orphan", lazy="selectin")


class KarmaPlanPartnerDB(Base):
    """Many-to-Many link between KarmaPlan and Partner with category"""
    __tablename__ = "karma_plan_partners"

    plan_id: Mapped[str] = mapped_column(ForeignKey("karma_plans.id", ondelete="CASCADE"), primary_key=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"), primary_key=True)
    category: Mapped[str] = mapped_column(String, primary_key=True)

    # Relationships
    plan: Mapped[KarmaPlanDB] = relationship(back_populates="partners_association")
    partner: Mapped[PartnerDB] = relationship(lazy="joined")
