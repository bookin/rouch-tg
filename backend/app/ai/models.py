"""AI Model factory for Pydantic AI"""
from pydantic_ai.models import Model
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google import GoogleProvider
try:
    from pydantic_ai.providers.ollama import OllamaProvider
except ImportError:
    OllamaProvider = None

import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

def get_model() -> Model:
    """
    Get configured AI model based on settings
    
    Returns:
        Configured Pydantic AI Model instance
    """
    settings = get_settings()
    provider = settings.AI_PROVIDER.lower()
    
    if provider == "groq":
        logger.info(f"Initializing Groq model: {settings.AI_MODEL}")
        return GroqModel(
            model_name=settings.AI_MODEL,
            provider=GroqProvider(api_key=settings.AI_API_KEY)
        )
    elif provider == "openai":
        logger.info(f"Initializing OpenAI model: {settings.AI_MODEL}")
        return OpenAIChatModel(
            model_name=settings.AI_MODEL,
            provider=OpenAIProvider(api_key=settings.AI_API_KEY, base_url=settings.AI_BASE_URL)
        )
    elif provider == "gemini":
        logger.info(f"Initializing Gemini model: {settings.AI_MODEL}")
        return GoogleModel(
            model_name=settings.AI_MODEL,
            provider=GoogleProvider(api_key=settings.AI_API_KEY)
        )
    elif provider == "ollama":
        if OllamaProvider is None:
            raise ValueError("OllamaProvider is not available. Please install pydantic-ai[ollama].")
        logger.info(f"Initializing Ollama model: {settings.AI_MODEL} at {settings.AI_BASE_URL}")
        return OpenAIChatModel(
            model_name=settings.AI_MODEL,
            provider=OllamaProvider(base_url=settings.AI_BASE_URL or "http://localhost:11434/v1")
        )
    else:
        # Fallback to Groq or raise error
        raise ValueError(f"Unsupported AI provider: {provider}")
