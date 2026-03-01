"""Service for account linking: email verification, telegram linking, token management."""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.account_link import AccountLinkTokenDB
from app.models.db.user import UserDB

logger = logging.getLogger(__name__)

EMAIL_VERIFY_TOKEN_EXPIRY_HOURS = 24
TELEGRAM_LINK_TOKEN_EXPIRY_HOURS = 1


class AccountLinkService:
    """Manages account linking tokens and operations."""

    # ── Token creation ──────────────────────────────────────────────

    async def create_email_verify_token(
        self, db: AsyncSession, user_id: int, email: str
    ) -> str:
        """Create a token for email verification. Invalidates previous tokens of same type."""
        await self._invalidate_tokens(db, user_id, "email_verify")

        token = secrets.token_urlsafe(32)
        token_obj = AccountLinkTokenDB(
            id=str(uuid4()),
            user_id=user_id,
            token=token,
            token_type="email_verify",
            target_email=email.lower().strip(),
            expires_at=datetime.now(UTC) + timedelta(hours=EMAIL_VERIFY_TOKEN_EXPIRY_HOURS),
        )
        db.add(token_obj)
        await db.flush()
        return token

    async def create_telegram_link_token(
        self, db: AsyncSession, user_id: int
    ) -> tuple[str, datetime]:
        """Create a token for linking a Telegram account. Used in deep link QR codes.

        Returns (token_string, expires_at).
        """
        await self._invalidate_tokens(db, user_id, "telegram_link")

        token = secrets.token_urlsafe(16)
        expires_at = datetime.now(UTC) + timedelta(hours=TELEGRAM_LINK_TOKEN_EXPIRY_HOURS)
        token_obj = AccountLinkTokenDB(
            id=str(uuid4()),
            user_id=user_id,
            token=token,
            token_type="telegram_link",
            expires_at=expires_at,
        )
        db.add(token_obj)
        await db.flush()
        return token, expires_at

    # ── Token validation ────────────────────────────────────────────

    async def validate_token(
        self, db: AsyncSession, token: str, expected_type: str
    ) -> AccountLinkTokenDB | None:
        """Validate a token: exists, not used, not expired, correct type."""
        result = await db.execute(
            select(AccountLinkTokenDB).where(
                AccountLinkTokenDB.token == token,
                AccountLinkTokenDB.token_type == expected_type,
                AccountLinkTokenDB.used_at.is_(None),
            )
        )
        token_obj = result.scalar_one_or_none()
        if not token_obj:
            return None
        if token_obj.expires_at < datetime.now(UTC):
            return None
        return token_obj

    async def mark_token_used(self, db: AsyncSession, token_obj: AccountLinkTokenDB) -> None:
        """Mark a token as used."""
        token_obj.used_at = datetime.now(UTC)
        await db.flush()

    async def validate_recently_used_token(
        self, db: AsyncSession, token: str, expected_type: str, max_age_minutes: int = 15
    ) -> AccountLinkTokenDB | None:
        """Find a token that was recently used (within max_age_minutes).

        Used for set-password-by-token: the email verify token was already used
        during verify-email, but we allow password setting within a short window.
        """
        result = await db.execute(
            select(AccountLinkTokenDB).where(
                AccountLinkTokenDB.token == token,
                AccountLinkTokenDB.token_type == expected_type,
                AccountLinkTokenDB.used_at.is_not(None),
            )
        )
        token_obj = result.scalar_one_or_none()
        if not token_obj or not token_obj.used_at:
            return None
        # Check the token was used recently
        if token_obj.used_at < datetime.now(UTC) - timedelta(minutes=max_age_minutes):
            return None
        return token_obj

    # ── Email verification ──────────────────────────────────────────

    async def verify_email_token(
        self, db: AsyncSession, token: str
    ) -> tuple[UserDB | None, str | None]:
        """Verify an email token. Returns (user, email) or (None, None).

        Sets the email on the user if they don't have one yet.
        Does NOT set password — that's a separate step.
        """
        token_obj = await self.validate_token(db, token, "email_verify")
        if not token_obj or not token_obj.target_email:
            return None, None

        user = await db.get(UserDB, token_obj.user_id)
        if not user:
            return None, None

        email = token_obj.target_email

        # Check if another user already has this email
        existing = await db.execute(
            select(UserDB).where(
                UserDB.email == email,
                UserDB.id != user.id,
            )
        )
        existing_user = existing.scalar_one_or_none()

        if existing_user:
            # Another account with this email exists — need merge flow
            # Mark token used but return both users for merge handling
            await self.mark_token_used(db, token_obj)
            return user, email

        # No conflict — just set email on current user
        user.email = email
        user.is_verified = True
        user.updated_at = datetime.now(UTC)
        await self.mark_token_used(db, token_obj)
        await db.flush()

        return user, email

    # ── Telegram linking ────────────────────────────────────────────

    async def verify_telegram_link_token(
        self, db: AsyncSession, token: str, telegram_id: int
    ) -> tuple[UserDB | None, UserDB | None]:
        """Verify a telegram link token. Returns (web_user, telegram_user_or_none).

        If telegram_id already belongs to another user, returns both for merge.
        Otherwise links telegram_id to the web user directly.
        """
        token_obj = await self.validate_token(db, token, "telegram_link")
        if not token_obj:
            return None, None

        web_user = await db.get(UserDB, token_obj.user_id)
        if not web_user:
            return None, None

        # Check if telegram_id already belongs to another user
        result = await db.execute(
            select(UserDB).where(
                UserDB.telegram_id == telegram_id,
                UserDB.id != web_user.id,
            )
        )
        existing_tg_user = result.scalar_one_or_none()

        if existing_tg_user:
            # Telegram account exists on different user — need merge
            await self.mark_token_used(db, token_obj)
            return web_user, existing_tg_user

        # No conflict — link telegram to web user
        web_user.telegram_id = telegram_id
        web_user.updated_at = datetime.now(UTC)
        await self.mark_token_used(db, token_obj)
        await db.flush()

        return web_user, None

    # ── Profile updates ─────────────────────────────────────────────

    async def set_password(
        self, db: AsyncSession, user_id: int, hashed_password: str
    ) -> bool:
        """Set or update the password for a user."""
        user = await db.get(UserDB, user_id)
        if not user:
            return False
        user.hashed_password = hashed_password
        user.updated_at = datetime.now(UTC)
        await db.flush()
        return True

    async def update_profile(
        self, db: AsyncSession, user_id: int, **fields: object
    ) -> UserDB | None:
        """Update allowed profile fields."""
        allowed = {
            "first_name", "occupation", "available_times", "daily_minutes",
            "current_habits", "physical_restrictions", "timezone",
            "morning_enabled", "evening_enabled", "current_focus",
        }
        user = await db.get(UserDB, user_id)
        if not user:
            return None
        for key, val in fields.items():
            if key in allowed and val is not None:
                setattr(user, key, val)
        user.updated_at = datetime.now(UTC)
        await db.flush()
        return user

    async def dismiss_link_prompt(self, db: AsyncSession, user_id: int) -> None:
        """Dismiss the miniapp account link prompt so it won't show again."""
        await db.execute(
            update(UserDB)
            .where(UserDB.id == user_id)
            .values(link_prompt_dismissed=True, updated_at=datetime.now(UTC))
        )
        await db.flush()

    async def get_user_by_email(self, db: AsyncSession, email: str) -> UserDB | None:
        """Find a user by email."""
        result = await db.execute(
            select(UserDB).where(UserDB.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    # ── Internals ───────────────────────────────────────────────────

    async def _invalidate_tokens(
        self, db: AsyncSession, user_id: int, token_type: str
    ) -> None:
        """Invalidate (mark used) all active tokens of a given type for a user."""
        await db.execute(
            update(AccountLinkTokenDB)
            .where(
                AccountLinkTokenDB.user_id == user_id,
                AccountLinkTokenDB.token_type == token_type,
                AccountLinkTokenDB.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
