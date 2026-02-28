"""Daily message scheduler"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.agents.daily_manager import DailyManagerAgent
from app.config import get_settings
from datetime import datetime, timezone


class MessageScheduler:
    """Schedules automatic messages to users"""
    
    def __init__(self, manager: DailyManagerAgent, bot):
        self.manager = manager
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.settings = get_settings()
    
    def start(self):
        """
        Start scheduler.

        We run the timezone check at the configured minutes (morning/evening),
        every hour. This allows users in any timezone to receive messages at their
        local time without scheduling per-timezone jobs.
        """

        minutes: list[int] = []
        if self.settings.MORNING_ENABLED:
            minutes.append(self.settings.MORNING_MINUTE)
        if self.settings.EVENING_ENABLED:
            minutes.append(self.settings.EVENING_MINUTE)

        minutes = sorted(set(minutes))
        if not minutes:
            return

        minute_expr = ",".join(str(m) for m in minutes)

        self.scheduler.add_job(
            self._check_and_send_messages,
            "cron",
            minute=minute_expr,
            id="timezone_message_check",
            replace_existing=True,
        )
        
        self.scheduler.start()
    
    @staticmethod
    def _as_utc_aware(dt: datetime) -> datetime:
        """Treat naive datetimes as UTC and return aware UTC datetime."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    async def _check_and_send_messages(self):
        """Check current time for all users and send appropriate messages"""
        from app.telegram_utils import safe_send_message
        from app.crud import get_active_users
        from app.database import AsyncSessionLocal
        import logging
        import asyncio
        from zoneinfo import ZoneInfo
        
        logger = logging.getLogger(__name__)
        logger.info("Checking timezones for scheduled messages")
        
        async with AsyncSessionLocal() as db:
            try:
                morning_users = []
                evening_users = []
                if self.settings.MORNING_ENABLED:
                    morning_users = await get_active_users(db, morning_enabled=True)
                if self.settings.EVENING_ENABLED:
                    evening_users = await get_active_users(db, evening_enabled=True)
                
                morning_sent = 0
                evening_sent = 0
                failed = 0
                
                # Check morning messages
                for user in morning_users:
                    try:
                        user_tz = ZoneInfo(user.timezone)
                        user_time = datetime.now(user_tz)
                        user_date = user_time.date()
                        
                        # Check if already sent today
                        if user.last_morning_message:
                            last_sent_date = self._as_utc_aware(user.last_morning_message).astimezone(user_tz).date()
                            if last_sent_date >= user_date:
                                continue  # Already sent today
                        
                        # Check if it's exactly the configured morning time for this user
                        if (
                            user_time.hour == self.settings.MORNING_HOUR
                            and user_time.minute == self.settings.MORNING_MINUTE
                        ):
                            
                            msg = await self.manager.morning_message(
                                user_id=user.id,
                                first_name=user.first_name,
                                streak_days=user.streak_days,
                                total_seeds=user.total_seeds,
                                channel="telegram",
                            )
                            if msg.get("skip"):
                                continue

                            send_kwargs = {}
                            if msg.get("reply_markup") is not None:
                                send_kwargs["reply_markup"] = msg["reply_markup"]
                            success = await safe_send_message(
                                self.bot,
                                user.telegram_id,
                                msg["message"],
                                **send_kwargs,
                            )
                            if success:
                                # Update last sent time (store in UTC)
                                user.last_morning_message = datetime.now(timezone.utc)
                                await db.flush()
                                morning_sent += 1
                            else:
                                failed += 1

                            # Simple rate limiting between users
                            await asyncio.sleep(self.settings.TELEGRAM_MESSAGE_DELAY)
                            
                    except Exception as e:
                        logger.error(f"Error sending morning message to {user.telegram_id}: {e}")
                        failed += 1
                
                # Check evening messages
                for user in evening_users:
                    try:
                        user_tz = ZoneInfo(user.timezone)
                        user_time = datetime.now(user_tz)
                        user_date = user_time.date()
                        
                        # Check if already sent today
                        if user.last_evening_message:
                            last_sent_date = self._as_utc_aware(user.last_evening_message).astimezone(user_tz).date()
                            if last_sent_date >= user_date:
                                continue  # Already sent today
                        
                        # Check if it's exactly the configured evening time for this user
                        if (
                            user_time.hour == self.settings.EVENING_HOUR
                            and user_time.minute == self.settings.EVENING_MINUTE
                        ):
                            
                            msg = await self.manager.evening_message(
                                user,
                                channel="telegram",
                            )
                            if msg.get("skip"):
                                continue

                            send_kwargs = {}
                            if msg.get("reply_markup") is not None:
                                send_kwargs["reply_markup"] = msg["reply_markup"]
                            success = await safe_send_message(
                                self.bot,
                                user.telegram_id,
                                msg["message"],
                                **send_kwargs,
                            )
                            if success:
                                # Update last sent time (store in UTC)
                                user.last_evening_message = datetime.now(timezone.utc)
                                await db.flush()
                                evening_sent += 1
                            else:
                                failed += 1

                            # Simple rate limiting between users
                            await asyncio.sleep(self.settings.TELEGRAM_MESSAGE_DELAY)
                            
                    except Exception as e:
                        logger.error(f"Error sending evening message to {user.telegram_id}: {e}")
                        failed += 1
                
                if morning_sent > 0 or evening_sent > 0:
                    logger.info(f"Messages sent: morning={morning_sent}, evening={evening_sent}, failed={failed}")
                
                # Commit all updates
                await db.commit()
                    
            except Exception as e:
                logger.error(f"Error in scheduled message check: {e}")
    
    def stop(self):
        """Stop the scheduler"""
        from apscheduler.schedulers import SchedulerNotRunningError
        import logging
        
        try:
            self.scheduler.shutdown()
        except SchedulerNotRunningError as e:
            if self.settings.MORNING_ENABLED or self.settings.EVENING_ENABLED:
                raise e
            # If both are disabled, it's expected that the scheduler isn't running, so we silently pass.

