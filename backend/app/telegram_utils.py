"""Telegram bot utilities and helpers"""
import asyncio
from typing import List
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
import logging

logger = logging.getLogger(__name__)

# Telegram message limits
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split long message into chunks respecting Telegram limits
    
    Args:
        text: Message text to split
        max_length: Maximum length per chunk (default 4096 for messages)
        
    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by lines to keep formatting
    lines = text.split('\n')
    
    for line in lines:
        # If single line is too long, split it
        if len(line) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Split long line by words
            words = line.split(' ')
            for word in words:
                if len(current_chunk) + len(word) + 1 <= max_length:
                    current_chunk += (word + ' ')
                else:
                    chunks.append(current_chunk.strip())
                    current_chunk = word + ' '
        
        # Normal line handling
        elif len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + '\n'
        else:
            chunks.append(current_chunk.strip())
            current_chunk = line + '\n'
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


async def send_long_message(bot: Bot, chat_id: int, text: str, **kwargs):
    """
    Send long message, splitting if necessary
    
    Handles Telegram message length limits and rate limiting
    
    Args:
        bot: Bot instance
        chat_id: Chat ID to send to
        text: Message text
        **kwargs: Additional parameters for send_message
    """
    chunks = split_message(text)
    
    for i, chunk in enumerate(chunks):
        try:
            await bot.send_message(chat_id, chunk, **kwargs)
            
            # Add small delay between chunks to avoid rate limiting
            if i < len(chunks) - 1:
                await asyncio.sleep(0.5)
                
        except TelegramRetryAfter as e:
            # Rate limit hit - wait and retry
            logger.warning(f"Rate limit hit for chat {chat_id}, waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await bot.send_message(chat_id, chunk, **kwargs)
            
        except TelegramAPIError as e:
            logger.error(f"Telegram API error sending to {chat_id}: {e}")
            raise


async def safe_send_message(bot: Bot, chat_id: int, text: str, **kwargs) -> bool:
    """
    Safely send message with error handling
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        await send_long_message(bot, chat_id, text, **kwargs)
        return True
    except TelegramRetryAfter as e:
        logger.warning(f"Rate limit for chat {chat_id}: {e}")
        return False
    except TelegramAPIError as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending to {chat_id}: {e}", exc_info=True)
        return False


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
