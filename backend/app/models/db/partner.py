"""Partner and PartnerGroup database models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.db.user import UserDB


class PartnerGroupDB(Base):
    """Partner group database model"""
    __tablename__ = "partner_groups"
    __table_args__ = (
        Index("idx_partner_groups_user_category_default", "user_id", "universal_category", "is_default"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    icon: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    universal_category: Mapped[str | None] = mapped_column(String, default="world")
    is_default: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PartnerDB(Base):
    """Partner database model"""
    __tablename__ = "partners"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    group_id: Mapped[str] = mapped_column(ForeignKey("partner_groups.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    preferences: Mapped[list | None] = mapped_column(JSON, default=list)
    important_dates: Mapped[list | None] = mapped_column(JSON, default=list)

    seeds_count: Mapped[int] = mapped_column(default=0)
    last_action_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    telegram_username: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    contact_type: Mapped[str | None] = mapped_column(String, default="physical")

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped[UserDB] = relationship(back_populates="partners")


class PartnerActionDB(Base):
    """Partner action record"""
    __tablename__ = "partner_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    partner_id: Mapped[str | None] = mapped_column(ForeignKey("partners.id", ondelete="SET NULL"))
    partner_name: Mapped[str | None] = mapped_column(String)
    seed_id: Mapped[str | None] = mapped_column(ForeignKey("seeds.id"))

    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    action: Mapped[str] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(default=False, index=True)
