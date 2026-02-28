"""Custom Telegram WebApp authentication backend for fastapi-users"""
import logging
from typing import Optional

from fastapi import Response, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from fastapi_users.authentication import AuthenticationBackend, Strategy
from fastapi_users import BaseUserManager

from app.models.db_models import UserDB
from app.telegram_auth import validate_telegram_webapp_data, extract_user_from_init_data

logger = logging.getLogger(__name__)


class TelegramTransport:
    """Transport that reads Telegram WebApp initData from Authorization header"""

    scheme = APIKeyHeader(name="Authorization", auto_error=False)

    async def get_login_response(self, token: str) -> Response:
        return JSONResponse({"status": "authenticated", "method": "telegram"})

    async def get_logout_response(self) -> Response:
        return JSONResponse({"status": "logged_out"})

    @staticmethod
    def get_openapi_login_responses_success():
        return {
            status.HTTP_200_OK: {
                "description": "Telegram auth successful",
                "content": {
                    "application/json": {
                        "example": {"status": "authenticated", "method": "telegram"}
                    }
                },
            }
        }

    @staticmethod
    def get_openapi_logout_responses_success():
        return {}


class TelegramStrategy(Strategy[UserDB, int]):  # type: ignore[type-var]
    """Strategy that validates Telegram WebApp initData and returns/creates user"""

    async def read_token(
        self,
        token: str | None,
        user_manager: BaseUserManager[UserDB, int],  # type: ignore[type-var]
    ) -> Optional[UserDB]:
        if not token:
            return None

        # Skip if it looks like a Bearer JWT token
        if token.startswith("Bearer "):
            return None

        # Reuse existing Telegram validation
        parsed_data = validate_telegram_webapp_data(token)
        if not parsed_data:
            return None

        user_info = extract_user_from_init_data(parsed_data)
        if not user_info:
            return None

        # get_or_create via custom UserManager method
        user = await user_manager.get_or_create_telegram_user(user_info)  # type: ignore[attr-defined]
        return user  # type: ignore[no-any-return]

    async def write_token(self, user: UserDB) -> str:
        return str(user.telegram_id or user.id)

    async def destroy_token(self, token: str, user: UserDB) -> None:
        pass


def get_telegram_strategy() -> TelegramStrategy:
    return TelegramStrategy()


telegram_backend = AuthenticationBackend(  # type: ignore[type-var]
    name="telegram",
    transport=TelegramTransport(),  # type: ignore[arg-type]
    get_strategy=get_telegram_strategy,
)
