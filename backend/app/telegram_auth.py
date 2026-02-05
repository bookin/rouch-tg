"""Telegram WebApp authentication utilities"""
import hmac
import hashlib
from urllib.parse import parse_qsl
from typing import Optional, Dict
import logging
from app.config import get_settings


logger = logging.getLogger(__name__)


def validate_telegram_webapp_data(init_data: str) -> Optional[Dict[str, str]]:
    """
    Validate Telegram WebApp initData
    
    According to Telegram documentation:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    
    Args:
        init_data: Raw initData string from Telegram WebApp
        
    Returns:
        Dict with parsed data if valid, None if invalid
    """
    settings = get_settings()
    
    if not init_data or not settings.TELEGRAM_BOT_TOKEN:
        return None
    
    try:
        # Parse query string
        parsed_data = dict(parse_qsl(init_data))
        
        # Extract hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return None
        
        # Sort keys and create data-check-string
        data_check_arr = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
        data_check_string = '\n'.join(data_check_arr)
        
        # Calculate secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.TELEGRAM_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Compare hashes
        if calculated_hash != received_hash:
            return None
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}", exc_info=True)
        return None


def extract_user_from_init_data(parsed_data: Dict[str, str]) -> Optional[Dict]:
    """
    Extract user info from validated initData
    
    Args:
        parsed_data: Validated and parsed initData
        
    Returns:
        Dict with user info or None
    """
    import json
    
    try:
        if 'user' not in parsed_data:
            return None
        
        user_data = json.loads(parsed_data['user'])
        
        return {
            'telegram_id': user_data.get('id'),
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'username': user_data.get('username'),
            'language_code': user_data.get('language_code', 'ru')
        }
        
    except Exception as e:
        logger.error(f"Error extracting Telegram user data: {e}", exc_info=True)
        return None
