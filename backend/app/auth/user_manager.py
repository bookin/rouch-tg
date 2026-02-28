"""Custom UserManager with Telegram support"""
import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from sqlalchemy import select

from app.auth.database import get_user_db
from app.config import get_settings
from app.models.db_models import UserDB

logger = logging.getLogger(__name__)
settings = get_settings()


class UserManager(IntegerIDMixin, BaseUserManager[UserDB, int]):  # type: ignore[type-var]
    """Custom UserManager with Telegram user support"""

    reset_password_token_secret = settings.JWT_SECRET_KEY
    verification_token_secret = settings.JWT_SECRET_KEY

    async def on_after_register(self, user: UserDB, request: Optional[Request] = None):
        logger.info(f"User {user.id} registered (email: {user.email})")

    async def on_after_forgot_password(
        self, user: UserDB, token: str, request: Optional[Request] = None
    ):
        logger.info(f"User {user.id} forgot password. Reset token generated.")

    # ===== Custom methods for Telegram =====

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserDB]:
        """Find user by Telegram ID"""
        stmt = select(UserDB).where(UserDB.telegram_id == telegram_id)
        result = await self.user_db.session.execute(stmt)  # type: ignore[attr-defined]
        return result.scalar_one_or_none()  # type: ignore[return-value, no-any-return]

    async def get_or_create_telegram_user(self, user_info: dict) -> UserDB:
        """Get existing Telegram user or create a new one"""
        user = await self.get_by_telegram_id(user_info["telegram_id"])
        if user:
            # Update first_name/username if changed
            changed = False
            if user.first_name != user_info["first_name"]:
                user.first_name = user_info["first_name"]
                changed = True
            new_username = user_info.get("username")
            if user.username != new_username:
                user.username = new_username  # type: ignore[assignment]
                changed = True
            if changed:
                await self.user_db.session.flush()  # type: ignore[attr-defined]
            return user

        # Create new Telegram user
        from app.crud import ensure_default_partner_groups

        user = UserDB(
            telegram_id=user_info["telegram_id"],
            first_name=user_info["first_name"],
            username=user_info.get("username"),
            email=None,
            hashed_password="!telegram-no-password",
            is_active=True,
            is_verified=True,  # Telegram users are auto-verified
            is_superuser=False,
        )
        self.user_db.session.add(user)  # type: ignore[attr-defined]
        await self.user_db.session.flush()  # type: ignore[attr-defined]
        await self.user_db.session.refresh(user)  # type: ignore[attr-defined]

        # Ensure default partner groups for new user
        await ensure_default_partner_groups(self.user_db.session, user.id)  # type: ignore[attr-defined, arg-type]
        await self.user_db.session.flush()  # type: ignore[attr-defined]

        return user


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
