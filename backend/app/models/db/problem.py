"""ProblemHistory database model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.db.user import UserDB
    from app.models.db.karma_plan import KarmaPlanDB


class ProblemHistoryDB(Base):
    """Problem history database model"""
    __tablename__ = "problem_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_text: Mapped[str] = mapped_column(Text)
    solution_json: Mapped[dict] = mapped_column(JSON)
    diagnostic_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user: Mapped[UserDB] = relationship(back_populates="problem_history")
    karma_plan: Mapped[KarmaPlanDB | None] = relationship(back_populates="problem_history", uselist=False)
