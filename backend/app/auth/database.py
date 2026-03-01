"""Database adapter for fastapi-users"""
from typing import AsyncGenerator
from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.db.user import UserDB


async def get_user_db(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """Database adapter for fastapi-users"""
    yield SQLAlchemyUserDatabase(session, UserDB)
