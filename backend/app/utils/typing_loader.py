"""
Utility for managing Telegram 'typing' status and loader messages.
Supports ContextVar for access from deep within the service layer.
"""
import asyncio
import logging
from contextvars import ContextVar
from typing import Optional, Set
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError

logger = logging.getLogger(__name__)

# ContextVar to hold the current loader instance for the current asyncio task
_typing_loader_ctx = ContextVar("typing_loader", default=None)


class TypingLoader:
    """
    Manages 'typing' status display and progress messages.
    
    Features:
    - Delayed Start: message is sent only if operation is long (> delay_before_message)
    - Typing Loop: continuously sends 'typing' action
    - Throttling: protects against Telegram rate limits when updating status
    - Graceful Shutdown: correctly terminates all background tasks
    """

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        delay_before_message: float = 1.0,  # Wait 1 sec before sending "Thinking..."
        typing_interval: float = 4.0,       # Status update interval (standard ~5 sec life)
        edit_interval: float = 1.5          # Update text max once per 1.5 sec (TG limit ~1 sec)
    ):
        self.bot = bot
        self.chat_id = chat_id
        self.delay_before_message = delay_before_message
        self.typing_interval = typing_interval
        self.edit_interval = edit_interval

        self._running = False
        self._tasks: Set[asyncio.Task] = set()

        # State
        self._message_id: Optional[int] = None
        self._current_status: str = "⏳ Думаю..."
        self._last_sent_status: Optional[str] = None
        
        # Synchronization events
        self._status_changed_event = asyncio.Event()

    async def start(self):
        """Start background processes"""
        if self._running:
            return

        self._running = True

        # 1. Start typing loop (immediate)
        typing_task = asyncio.create_task(self._typing_loop())
        self._tasks.add(typing_task)
        typing_task.add_done_callback(self._tasks.discard)

        # 2. Start message management loop (delayed)
        msg_task = asyncio.create_task(self._message_lifecycle_loop())
        self._tasks.add(msg_task)
        msg_task.add_done_callback(self._tasks.discard)

    async def stop(self):
        """Stop and cleanup resources"""
        self._running = False
        self._status_changed_event.set()  # Wake up loop if sleeping

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        if self._tasks:
            # Wait for cancellation (ignoring CancelledError)
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Cleanup loader message (optional, delete to not clutter chat before final response)
        if self._message_id:
            try:
                await self.bot.delete_message(self.chat_id, self._message_id)
            except Exception:
                pass

    def set_status(self, text: str):
        """
        Update status text.
        Safe to call frequently (debounce implemented in loop).
        """
        if not self._running:
            return

        if text == self._current_status:
            return

        self._current_status = text
        self._status_changed_event.set()

    async def _typing_loop(self):
        """Loop sending send_chat_action"""
        while self._running:
            try:
                await self.bot.send_chat_action(self.chat_id, "typing")
            except Exception as e:
                logger.debug(f"Typing action failed: {e}")
            
            try:
                await asyncio.sleep(self.typing_interval)
            except asyncio.CancelledError:
                break

    async def _message_lifecycle_loop(self):
        """Loop managing message (creation -> update)"""
        
        # 1. Delayed Start
        try:
            await asyncio.sleep(self.delay_before_message)
        except asyncio.CancelledError:
            return

        if not self._running:
            return

        # 2. Send initial message
        try:
            msg = await self.bot.send_message(self.chat_id, self._current_status)
            self._message_id = msg.message_id
            self._last_sent_status = self._current_status
        except Exception as e:
            logger.error(f"Failed to send loader message: {e}")
            return

        # 3. Update Loop (Debounce + Throttling)
        while self._running:
            try:
                # Wait for change signal
                await self._status_changed_event.wait()
                self._status_changed_event.clear()

                if not self._running:
                    break

                if self._current_status == self._last_sent_status:
                    continue

                # Attempt edit
                if self._message_id:
                    try:
                        await self.bot.edit_message_text(
                            text=self._current_status,
                            chat_id=self.chat_id,
                            message_id=self._message_id
                        )
                        self._last_sent_status = self._current_status
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)
                    except TelegramAPIError as e:
                        if "message is not modified" in str(e):
                            pass
                        else:
                            logger.warning(f"Loader edit error: {e}")

                # Throttling before next update
                await asyncio.sleep(self.edit_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in loader loop: {e}")
                await asyncio.sleep(1)


# --- Public API for use in code ---

def set_typing_loader(loader: TypingLoader):
    """Set loader for current context"""
    _typing_loader_ctx.set(loader)


def get_typing_loader() -> Optional[TypingLoader]:
    """Get loader from current context"""
    return _typing_loader_ctx.get()


async def broadcast_status(text: str):
    """
    Send status to user.
    Safe to call from any part of the application (agents, services).
    If no loader exists (e.g. non-telegram call), does nothing.
    """
    loader = get_typing_loader()
    if loader:
        loader.set_status(text)
