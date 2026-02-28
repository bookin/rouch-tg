"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from app.config import get_settings
from app.api.webapp import router as webapp_router
from app.api.calendar import router as calendar_router
from app.api.bot import start_bot, stop_bot, bot
from app.database import check_db_connection
from app.cache import init_cache, close_cache
from app.scheduler.daily_messages import MessageScheduler
from app.agents.daily_manager import DailyManagerAgent
from app.knowledge.qdrant import QdrantKnowledgeBase


settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    bot_task = None
    scheduler = None
    
    try:
        # Verify database connectivity (schema is managed by Alembic migrations)
        await check_db_connection()
        print("✅ Database connection OK")
        
        # Initialize Redis cache
        await init_cache()
        print("✅ Redis cache initialized")
        
        # Start Telegram bot in background
        if settings.TELEGRAM_ENABLED:
            bot_task = asyncio.create_task(start_bot())
            print("✅ Telegram bot started")
        else:
            print("⚠️  Running in No-Telegram Mode (Mock Bot active)")
        
        # Start scheduler for daily messages
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        daily_manager = DailyManagerAgent(qdrant)
        scheduler = MessageScheduler(daily_manager, bot)
        scheduler.start()
        print("✅ Message scheduler started")
        
        yield
        
    finally:
        # Shutdown
        if scheduler:
            try:
                scheduler.stop()
                print("✅ Scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}", exc_info=True)
        
        try:
            await stop_bot()
        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)
        
        if bot_task:
            try:
                bot_task.cancel()
                await bot_task
            except asyncio.CancelledError:
                logger.info("Bot task cancelled")
                pass
            except Exception as e:
                logger.error(f"Error cancelling bot task: {e}", exc_info=True)
        
        try:
            await close_cache()
            print("✅ Cache closed")
        except Exception as e:
            logger.error(f"Error closing cache: {e}", exc_info=True)


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Rouch Karma Manager Bot with AI-powered insights",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=settings.DOCS_URL if settings.ENVIRONMENT != "production" else None,
    redoc_url=settings.REDOC_URL if settings.ENVIRONMENT != "production" else None,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Auth routers (fastapi-users)
from app.auth import fastapi_users, telegram_backend, jwt_backend
from app.models.schemas.user import UserRead, UserCreate, UserUpdate

app.include_router(
    fastapi_users.get_auth_router(jwt_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Include routers
app.include_router(webapp_router)
app.include_router(calendar_router)


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with application info"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": f"{settings.DOCS_URL}" if settings.ENVIRONMENT != "production" else None
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }
