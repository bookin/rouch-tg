from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from app.utils.typing_loader import TypingLoader, set_typing_loader

class TypingMiddleware(BaseMiddleware):
    """
    Middleware for automatic management of TypingLoader.
    - Initializes loader at start of processing
    - Passes it to ContextVar
    - Guarantees stop at completion
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        bot = data.get("bot")
        if not bot:
            return await handler(event, data)
            
        # Determine chat_id for Message and CallbackQuery
        chat_id = None
        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = event.message.chat.id
            
        # If chat not determined, just run handler
        if not chat_id:
            return await handler(event, data)
            
        # Initialization
        loader = TypingLoader(bot, chat_id)
        
        # Registration in ContextVar (makes broadcast_status available)
        set_typing_loader(loader)
        
        # Start (background process)
        await loader.start()
        
        try:
            return await handler(event, data)
        finally:
            # Guaranteed stop and cleanup
            await loader.stop()
