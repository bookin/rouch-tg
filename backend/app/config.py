"""Application configuration"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = Field(default="Rouch Karma Manager", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="production", description="Environment: development/production")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://rouch_user:password@localhost:5432/rouch",
        description="PostgreSQL connection URL"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow connections")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries (debug)")
    
    # Qdrant Vector Database
    QDRANT_URL: str = Field(default="http://localhost:6333", description="Qdrant URL")
    QDRANT_API_KEY: Optional[str] = Field(default=None, description="Qdrant API Key")
    QDRANT_COLLECTION_SIZE: int = Field(default=384, description="Vector embedding size")
    
    # Redis Cache
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis URL")
    REDIS_CACHE_TTL: int = Field(default=3600, description="Default cache TTL in seconds")
    REDIS_QUOTE_CACHE_TTL: int = Field(default=86400, description="Quote cache TTL (24h)")
    REDIS_CORRELATION_CACHE_TTL: int = Field(default=7200, description="Correlation cache TTL (2h)")
    
    # Telegram Bot
    TELEGRAM_ENABLED: bool = Field(default=True, description="Enable Telegram integration (disable for local dev)")
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot API token")
    TELEGRAM_RATE_LIMIT: int = Field(default=30, description="Max messages per second")
    TELEGRAM_MESSAGE_DELAY: float = Field(default=0.05, description="Delay between messages (seconds)")
    WEBAPP_URL: str = Field(default="http://localhost:5180", description="Telegram Mini App URL")
    
    # AI / LLM
    AI_PROVIDER: str = Field(default="groq", description="AI provider: groq, openai, gemini, ollama")
    AI_API_KEY: str = Field(default="", description="AI provider API key")
    AI_MODEL: str = Field(default="llama-3.1-70b-versatile", description="AI model name")
    AI_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    AI_MAX_TOKENS: int = Field(default=2048, description="Max tokens in response")
    AI_BASE_URL: Optional[str] = Field(default=None, description="Custom base URL for AI provider (e.g., Ollama)")
    
    # Knowledge Base
    KNOWLEDGE_BASE_PATH: str = Field(default="data/knowledge_base", description="Path to knowledge base files")
    # Problem Solver Agent tuning
    PROBLEM_SOLVER_CORRELATIONS_LIMIT: int = Field(default=3, description="How many correlations to fetch from Qdrant for problem analysis")
    PROBLEM_SOLVER_CONCEPTS_LIMIT: int = Field(default=2, description="How many concepts to fetch from Qdrant for problem analysis")
    PROBLEM_SOLVER_RULES_LIMIT: int = Field(default=3, description="How many karmic rules to fetch from Qdrant for problem analysis")
    PROBLEM_SOLVER_PRACTICES_LIMIT: int = Field(default=3, description="How many practices to fetch from Qdrant for problem analysis and recommendations")
    
    # Scheduler Settings
    SCHEDULER_ENABLED: bool = Field(default=True, description="Enable daily message scheduler")
    SCHEDULER_CHECK_INTERVAL: int = Field(default=60, description="Scheduler check interval (minutes)")
    
    # Morning Messages
    MORNING_ENABLED: bool = Field(default=True, description="Enable morning messages")
    MORNING_HOUR: int = Field(default=7, ge=0, le=23, description="Morning message hour (0-23)")
    MORNING_MINUTE: int = Field(default=30, ge=0, le=59, description="Morning message minute (0-59)")
    
    # Evening Messages
    EVENING_ENABLED: bool = Field(default=True, description="Enable evening messages")
    EVENING_HOUR: int = Field(default=21, ge=0, le=23, description="Evening message hour (0-23)")
    EVENING_MINUTE: int = Field(default=0, ge=0, le=59, description="Evening message minute (0-59)")
    
    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5180", "http://localhost:3000"],
        description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials in CORS")
    
    # API Settings
    API_PREFIX: str = Field(default="/api", description="API route prefix")
    DOCS_URL: str = Field(default="/docs", description="Swagger docs URL")
    REDOC_URL: str = Field(default="/redoc", description="ReDoc URL")
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="Secret key for signatures")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
