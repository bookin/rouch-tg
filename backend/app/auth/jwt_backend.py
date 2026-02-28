"""JWT authentication backend for fastapi-users (web login)"""
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from app.config import get_settings

settings = get_settings()

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.JWT_SECRET_KEY,
        lifetime_seconds=3600 * 24,  # 24 hours
    )


jwt_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
