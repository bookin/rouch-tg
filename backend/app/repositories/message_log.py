"""Message log repository."""
from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.message_log import MessageLogDB
from app.repositories.base import BaseRepository


class MessageLogRepository(BaseRepository[MessageLogDB]):
    def __init__(self) -> None:
        super().__init__(MessageLogDB)

    async def get_latest(
        self,
        db: AsyncSession,
        user_id: int,
        message_type: str,
        channel: str,
        date: datetime,
        karma_plan_id: str | None = None,
    ) -> MessageLogDB | None:
        """Get latest message log for user/type/channel/day."""
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        query = (
            select(MessageLogDB)
            .where(
                MessageLogDB.user_id == user_id,
                MessageLogDB.message_type == message_type,
                MessageLogDB.channel == channel,
                MessageLogDB.sent_at >= day_start,
                MessageLogDB.sent_at <= day_end,
            )
            .order_by(MessageLogDB.sent_at.desc())
            .limit(1)
        )

        if karma_plan_id is not None:
            query = query.where(MessageLogDB.karma_plan_id == karma_plan_id)
        else:
            query = query.where(MessageLogDB.karma_plan_id.is_(None))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_log(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        message_type: str,
        channel: str,
        payload: dict,
        karma_plan_id: str | None = None,
        daily_plan_id: str | None = None,
        sent_at: datetime | None = None,
    ) -> MessageLogDB:
        log = MessageLogDB(
            id=str(uuid4()),
            user_id=user_id,
            karma_plan_id=karma_plan_id,
            daily_plan_id=daily_plan_id,
            message_type=message_type,
            channel=channel,
            payload=payload,
            sent_at=sent_at or datetime.now(UTC),
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log
