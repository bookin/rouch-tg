"""User database model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable

if TYPE_CHECKING:
    from app.models.db.seed import SeedDB
    from app.models.db.partner import PartnerDB
    from app.models.db.problem import ProblemHistoryDB
    from app.models.db.karma_plan import KarmaPlanDB
    from app.models.db.practice import PracticeProgressDB


class UserDB(SQLAlchemyBaseUserTable[int], Base):
    """User database model with FastAPI Users integration"""
    __tablename__ = "users"

    # Integer PK (not UUID)
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Override fastapi-users base columns for hybrid auth
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)  # type: ignore[assignment]
    hashed_password: Mapped[str | None] = mapped_column(String(1024))  # type: ignore[assignment]
    is_active: Mapped[bool] = mapped_column(server_default="true")
    is_superuser: Mapped[bool] = mapped_column(server_default="false")
    is_verified: Mapped[bool] = mapped_column(server_default="false")

    # Telegram-specific
    telegram_id: Mapped[int | None] = mapped_column(unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String)
    username: Mapped[str | None] = mapped_column(String)

    # Onboarding
    occupation: Mapped[str | None] = mapped_column(String, default="employee")
    available_times: Mapped[list | None] = mapped_column(JSON, default=list)
    daily_minutes: Mapped[int | None] = mapped_column(default=30)
    current_habits: Mapped[list | None] = mapped_column(JSON, default=list)
    physical_restrictions: Mapped[str | None] = mapped_column(String)

    # Progress
    streak_days: Mapped[int] = mapped_column(default=0)
    total_seeds: Mapped[int] = mapped_column(default=0)
    completed_practices: Mapped[int] = mapped_column(default=0)

    # Settings
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    morning_enabled: Mapped[bool] = mapped_column(default=True)
    evening_enabled: Mapped[bool] = mapped_column(default=True)
    current_focus: Mapped[str | None] = mapped_column(String)

    # Timestamps
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_onboarding_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_morning_message: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_evening_message: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    seeds: Mapped[list[SeedDB]] = relationship(back_populates="user", lazy="selectin")
    partners: Mapped[list[PartnerDB]] = relationship(back_populates="user", lazy="selectin")
    problem_history: Mapped[list[ProblemHistoryDB]] = relationship(back_populates="user", lazy="selectin")
    karma_plans: Mapped[list[KarmaPlanDB]] = relationship(back_populates="user", lazy="selectin")
    practice_progress: Mapped[list[PracticeProgressDB]] = relationship(back_populates="user", lazy="selectin")
