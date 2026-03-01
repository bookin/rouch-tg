"""Account linking token database model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AccountLinkTokenDB(Base):
    """Token for email verification and telegram account linking"""
    __tablename__ = "account_link_tokens"
    __table_args__ = (
        Index("idx_account_link_tokens_token", "token", unique=True),
        Index("idx_account_link_tokens_user_type", "user_id", "token_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String, unique=True)
    token_type: Mapped[str] = mapped_column(String)  # 'email_verify' | 'telegram_link'
    target_email: Mapped[str | None] = mapped_column(String)  # email being verified
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
