"""Pydantic schemas for fastapi-users"""
from typing import Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    """Schema for reading user data"""
    telegram_id: Optional[int] = None
    first_name: str = ""
    username: Optional[str] = None
    occupation: str = "employee"
    timezone: str = "UTC"
    streak_days: int = 0
    total_seeds: int = 0
    completed_practices: int = 0
    morning_enabled: bool = True
    evening_enabled: bool = True


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating user via web registration"""
    first_name: str
    occupation: str = "employee"


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user"""
    first_name: Optional[str] = None
    occupation: Optional[str] = None
    timezone: Optional[str] = None
