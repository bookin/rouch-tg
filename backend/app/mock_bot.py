"""Mock Bot for No-Telegram mode"""
import logging
from types import SimpleNamespace

logger = logging.getLogger(__name__)

class MockBot:
    """Mock Bot that logs actions instead of sending to Telegram"""
    
    def __init__(self, token: str = "mock-token"):
        self.token = token
        self.session = SimpleNamespace(close=self.close)
        logger.info("🤖 Mock Bot initialized")

    async def get_me(self):
        """Mock get_me"""
        logger.info("🤖 Mock Bot: get_me called")
        return SimpleNamespace(username="MockBot", id=12345, first_name="Mock Bot")

    async def set_my_commands(self, commands, scope=None, language_code=None):
        """Mock set_my_commands"""
        logger.info(f"🤖 Mock Bot: Commands set: {[c.command for c in commands]}")
        return True

    async def send_message(self, chat_id, text, **kwargs):
        """Mock send_message"""
        logger.info(f"🤖 Mock Bot: Sending to {chat_id}:\n{text}")
        return SimpleNamespace(message_id=1)

    async def close(self):
        """Mock close"""
        logger.info("🤖 Mock Bot: Closed")
