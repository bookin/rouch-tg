"""Coffee Meditation database models."""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.db.user import UserDB


class CoffeeMeditationSessionDB(Base):
    __tablename__ = "coffee_meditation_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_coffee_session_user_local_date"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    local_date: Mapped[date_type] = mapped_column(index=True)

    karma_plan_id: Mapped[str | None] = mapped_column(ForeignKey("karma_plans.id", ondelete="SET NULL"), index=True)
    daily_plan_id: Mapped[str | None] = mapped_column(ForeignKey("daily_plans.id", ondelete="SET NULL"), index=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    notes_draft: Mapped[str | None] = mapped_column(Text)
    current_step: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[UserDB] = relationship(lazy="selectin")
    rejoiced_seeds: Mapped[list[CoffeeMeditationRejoicedSeedDB]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CoffeeMeditationRejoicedSeedDB(Base):
    __tablename__ = "coffee_meditation_rejoiced_seeds"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("coffee_meditation_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seed_id: Mapped[str] = mapped_column(
        ForeignKey("seeds.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[CoffeeMeditationSessionDB] = relationship(back_populates="rejoiced_seeds")
