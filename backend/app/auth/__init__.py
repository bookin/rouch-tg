"""FastAPIUsers setup with Telegram + JWT backends"""
from fastapi_users import FastAPIUsers
from app.models.db_models import UserDB
from app.auth.user_manager import get_user_manager
from app.auth.telegram_backend import telegram_backend
from app.auth.jwt_backend import jwt_backend

# FastAPIUsers with BOTH backends
fastapi_users = FastAPIUsers[UserDB, int](  # type: ignore[type-var]
    get_user_manager=get_user_manager,
    auth_backends=[telegram_backend, jwt_backend],
)

# Dependencies for endpoints
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
