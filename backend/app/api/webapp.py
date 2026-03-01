"""FastAPI endpoints for Mini App — aggregator router.

Individual endpoint modules live in app/api/endpoints/.
Shared schemas, helpers, and auth deps live in app/api/deps.py.
"""
from fastapi import APIRouter

from app.api.endpoints import me, daily, seeds, coffee, problems, projects, partners, practices, onboarding

router = APIRouter(prefix="/api", tags=["Mini App"])

# Include all sub-routers
router.include_router(me.router)
router.include_router(daily.router)
router.include_router(seeds.router)
router.include_router(coffee.router)
router.include_router(problems.router)
router.include_router(projects.router)
router.include_router(partners.router)
router.include_router(practices.router)
router.include_router(onboarding.router)


# Backward-compat re-exports used by other modules (bot.py, agents, etc.)
from app.api.deps import user_db_to_profile, get_current_user  # noqa: F401, E402
