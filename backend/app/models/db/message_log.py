"""MessageLog database model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MessageLogDB(Base):
    """Log of generated messages (morning, evening, etc.) for caching and analytics"""
    __tablename__ = "message_logs"
    __table_args__ = (
        Index("idx_message_logs_user_type_channel_sent", "user_id", "message_type", "channel", "sent_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    karma_plan_id: Mapped[str | None] = mapped_column(ForeignKey("karma_plans.id", ondelete="CASCADE"), index=True)
    daily_plan_id: Mapped[str | None] = mapped_column(ForeignKey("daily_plans.id", ondelete="CASCADE"), index=True)

    message_type: Mapped[str] = mapped_column(String, index=True)
    channel: Mapped[str] = mapped_column(String, default="system")
    payload: Mapped[dict] = mapped_column(JSON)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
