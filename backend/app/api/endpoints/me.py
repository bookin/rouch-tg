"""User profile endpoint."""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, user_db_to_profile
from app.models.db.user import UserDB

router = APIRouter()


@router.get("/me")
async def get_me(user: UserDB = Depends(get_current_user)):
    """Get current user profile"""
    return user_db_to_profile(user)
