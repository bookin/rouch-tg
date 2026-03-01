"""Account linking, profile, and merge endpoints."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_users.jwt import generate_jwt
from fastapi_users.password import PasswordHelper
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.config import get_settings
from app.models.db.user import UserDB
from app.services.account_link import AccountLinkService
from app.services.account_merge import AccountMergeService

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

_link_svc = AccountLinkService()
_merge_svc = AccountMergeService()
_password_helper = PasswordHelper()


def _generate_jwt_for_user(user_id: int) -> str:
    """Generate a JWT access token for a user (same format as fastapi-users)."""
    data = {"sub": str(user_id), "aud": "fastapi-users:auth"}
    return generate_jwt(
        data,
        secret=settings.JWT_SECRET_KEY,
        lifetime_seconds=3600 * 24,
    )


# ── Schemas ─────────────────────────────────────────────────────────

class LinkEmailRequest(BaseModel):
    email: EmailStr


class SetPasswordRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class SetPasswordByTokenRequest(BaseModel):
    token: str
    password: str


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    occupation: Optional[str] = None
    available_times: Optional[list[str]] = None
    daily_minutes: Optional[int] = None
    current_habits: Optional[list] = None
    physical_restrictions: Optional[str] = None
    timezone: Optional[str] = None
    morning_enabled: Optional[bool] = None
    evening_enabled: Optional[bool] = None
    current_focus: Optional[str] = None


class MergeConfirmRequest(BaseModel):
    source_user_id: int
    keep_project_from: Optional[int] = None


class ProfileResponse(BaseModel):
    id: int
    first_name: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[int] = None
    has_password: bool = False
    occupation: Optional[str] = None
    available_times: Optional[list[str]] = None
    daily_minutes: Optional[int] = None
    current_habits: Optional[list] = None
    physical_restrictions: Optional[str] = None
    timezone: str = "UTC"
    morning_enabled: bool = True
    evening_enabled: bool = True
    current_focus: Optional[str] = None
    link_prompt_dismissed: bool = False
    is_verified: bool = False


# ── Profile ─────────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user: UserDB = Depends(get_current_user),
):
    """Get current user profile with linking status."""
    return ProfileResponse(
        id=user.id,
        first_name=user.first_name,
        email=user.email,
        telegram_id=user.telegram_id,
        has_password=bool(
            user.hashed_password
            and user.hashed_password != "!telegram-no-password"
        ),
        occupation=user.occupation,
        available_times=user.available_times or [],
        daily_minutes=user.daily_minutes,
        current_habits=user.current_habits or [],
        physical_restrictions=user.physical_restrictions,
        timezone=user.timezone or "UTC",
        morning_enabled=bool(user.morning_enabled),
        evening_enabled=bool(user.evening_enabled),
        current_focus=user.current_focus,
        link_prompt_dismissed=bool(user.link_prompt_dismissed),
        is_verified=bool(user.is_verified),
    )


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update profile fields."""
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "Нечего обновлять")
    updated = await _link_svc.update_profile(db, user.id, **fields)
    if not updated:
        raise HTTPException(404, "Пользователь не найден")
    await db.commit()
    return {"success": True}


# ── Email Linking ───────────────────────────────────────────────────

@router.post("/link-email")
async def request_email_link(
    payload: LinkEmailRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Initiate email linking. Sends a verification email."""
    email = payload.email.lower().strip()

    # Check if this user already has this email
    if user.email and user.email.lower() == email:
        raise HTTPException(400, "Этот email уже привязан к твоему аккаунту")

    token = await _link_svc.create_email_verify_token(db, user.id, email)

    # Send verification email
    from app.email.service import send_verification_email
    sent = await send_verification_email(email, user.first_name or "друг", token)

    await db.commit()

    return {
        "success": True,
        "email_sent": sent,
        "message": "Мы отправили письмо — проверь почту 📬",
    }


@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify email token. Returns user info, merge status, and JWT for auto-login."""
    verified_user, email = await _link_svc.verify_email_token(db, payload.token)

    if not verified_user:
        raise HTTPException(400, "Ссылка недействительна или устарела")

    # Check if there's a conflicting user with same email (merge needed)
    existing = await _link_svc.get_user_by_email(db, email)  # type: ignore[arg-type]
    needs_merge = existing is not None and existing.id != verified_user.id

    has_password = bool(
        verified_user.hashed_password
        and verified_user.hashed_password != "!telegram-no-password"
    )

    await db.commit()

    # Generate JWT so the user is auto-logged-in after clicking email link
    access_token = _generate_jwt_for_user(verified_user.id)

    return {
        "success": True,
        "user_id": verified_user.id,
        "email": email,
        "needs_password": not has_password,
        "needs_merge": needs_merge,
        "merge_source_id": existing.id if needs_merge else None,
        "access_token": access_token,
    }


@router.post("/set-password-by-token")
async def set_password_by_token(
    payload: SetPasswordByTokenRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Set password using the email verification token (no auth required).

    Validates that the token was recently used (within 15 min) for email verification.
    """
    if len(payload.password) < 6:
        raise HTTPException(400, "Пароль должен быть не менее 6 символов")

    token_obj = await _link_svc.validate_recently_used_token(
        db, payload.token, "email_verify", max_age_minutes=15
    )
    if not token_obj:
        raise HTTPException(400, "Токен недействителен или устарел")

    hashed = _password_helper.hash(payload.password)
    ok = await _link_svc.set_password(db, token_obj.user_id, hashed)
    if not ok:
        raise HTTPException(404, "Пользователь не найден")
    await db.commit()

    access_token = _generate_jwt_for_user(token_obj.user_id)

    return {
        "success": True,
        "message": "Пароль установлен ✅",
        "access_token": access_token,
    }


@router.post("/set-password")
async def set_password(
    payload: SetPasswordRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Set password for user (after email verification)."""
    if len(payload.password) < 6:
        raise HTTPException(400, "Пароль должен быть не менее 6 символов")

    hashed = _password_helper.hash(payload.password)
    ok = await _link_svc.set_password(db, user.id, hashed)
    if not ok:
        raise HTTPException(404, "Пользователь не найден")
    await db.commit()
    return {"success": True, "message": "Пароль установлен ✅"}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Change password for user who already has one."""
    if not user.hashed_password or user.hashed_password == "!telegram-no-password":
        raise HTTPException(400, "Сначала установи пароль")

    verified, _ = _password_helper.verify_and_update(payload.current_password, user.hashed_password)
    if not verified:
        raise HTTPException(400, "Неверный текущий пароль")

    if len(payload.new_password) < 6:
        raise HTTPException(400, "Новый пароль должен быть не менее 6 символов")

    hashed = _password_helper.hash(payload.new_password)
    await _link_svc.set_password(db, user.id, hashed)
    await db.commit()
    return {"success": True, "message": "Пароль изменён ✅"}


# ── Telegram Linking ────────────────────────────────────────────────

@router.post("/link-telegram")
async def generate_telegram_link(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate a Telegram deep link token for account linking."""
    if user.telegram_id:
        raise HTTPException(400, "Telegram уже привязан к этому аккаунту")

    token, expires_at = await _link_svc.create_telegram_link_token(db, user.id)
    await db.commit()

    from app.api.bot import bot_username
    deep_link = f"https://t.me/{bot_username}?start=link_{token}" if bot_username else None

    return {
        "success": True,
        "token": token,
        "deep_link": deep_link,
        "bot_username": bot_username or None,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


# ── Merge ───────────────────────────────────────────────────────────

@router.get("/merge-preview")
async def merge_preview(
    source_user_id: int,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Preview what will happen when merging two accounts."""
    if source_user_id == user.id:
        raise HTTPException(400, "Нельзя объединить аккаунт сам с собой")

    preview = await _merge_svc.preview_merge(db, user.id, source_user_id)
    if "error" in preview:
        raise HTTPException(404, preview["error"])

    return preview


@router.post("/confirm-merge")
async def confirm_merge(
    payload: MergeConfirmRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Execute account merge after user confirmation."""
    if payload.source_user_id == user.id:
        raise HTTPException(400, "Нельзя объединить аккаунт сам с собой")

    ok = await _merge_svc.execute_merge(
        db,
        target_user_id=user.id,
        source_user_id=payload.source_user_id,
        keep_project_from=payload.keep_project_from,
    )
    if not ok:
        raise HTTPException(500, "Ошибка при объединении аккаунтов")

    await db.commit()
    return {"success": True, "message": "Аккаунты успешно объединены 🎉"}


# ── Miniapp prompt ──────────────────────────────────────────────────

@router.post("/dismiss-link-prompt")
async def dismiss_link_prompt(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Dismiss the miniapp account link prompt so it won't show again."""
    await _link_svc.dismiss_link_prompt(db, user.id)
    await db.commit()
    return {"success": True}
