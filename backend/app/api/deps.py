"""Shared API dependencies, schemas, and helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_db
from app.models.db.user import UserDB
from app.models.user import UserProfile
from app.services.seed_service import SeedService
from app.services.partner_service import PartnerService
from app.services.daily_service import DailyService
from app.services.practice_service import PracticeService
from app.services.user_service import UserService


# ---- Auth dependency ----

async def get_current_user(
    user: UserDB = Depends(current_active_user),
) -> UserDB:
    """Hybrid auth dependency (Telegram + JWT).

    Uses fastapi-users under the hood, which tries each backend
    (Telegram initData, then JWT Bearer) and returns the authenticated UserDB.
    """
    return user


# ---- DB Session dependency ----

async def get_db_session() -> AsyncSession:  # type: ignore[misc]
    """Yield an async DB session via FastAPI Depends."""
    async for session in get_db():
        yield session  # type: ignore[misc]


# ---- Service factories (for Depends) ----

def get_seed_service() -> SeedService:
    return SeedService()

def get_partner_service() -> PartnerService:
    return PartnerService()

def get_daily_service() -> DailyService:
    return DailyService()

def get_practice_service() -> PracticeService:
    return PracticeService()

def get_user_service() -> UserService:
    return UserService()


# ---- Helpers ----

def user_db_to_profile(u: UserDB) -> UserProfile:
    """Convert UserDB to UserProfile (for agents that expect Pydantic model)"""
    return UserProfile(
        id=u.id,
        telegram_id=u.telegram_id or 0,
        first_name=u.first_name,
        username=u.username,
        occupation=u.occupation or "employee",
        available_times=u.available_times or [],
        daily_minutes=u.daily_minutes or 30,
        current_habits=u.current_habits or [],
        physical_restrictions=u.physical_restrictions,
        streak_days=u.streak_days or 0,
        total_seeds=u.total_seeds or 0,
        completed_practices=u.completed_practices or 0,
        timezone=u.timezone or "UTC",
        morning_enabled=bool(u.morning_enabled),
        evening_enabled=bool(u.evening_enabled),
        created_at=u.created_at or datetime.min,
        updated_at=u.updated_at or datetime.min,
        last_onboarding_update=u.last_onboarding_update,
    )


# ---- Shared Schemas ----

class PartnerGroupOut(BaseModel):
    id: str
    name: str
    icon: str
    description: str
    universal_category: Optional[str] = "world"
    is_default: bool = False


class PartnerOut(BaseModel):
    id: str
    name: str
    group_id: str
    telegram_username: Optional[str] = None
    phone: Optional[str] = None
    contact_type: str = "physical"
    notes: Optional[str] = None


class PartnersResponse(BaseModel):
    groups: list[PartnerGroupOut]
    partners: list[PartnerOut]


class PartnerCreateRequest(BaseModel):
    name: str
    group_id: str
    telegram_username: Optional[str] = None
    phone: Optional[str] = None
    contact_type: str = "physical"
    notes: Optional[str] = None


class PartnerCreateResponse(BaseModel):
    success: bool
    partner_id: str


class SeedCreateRequest(BaseModel):
    action_type: str = "kindness"
    description: str
    partner_group: str = "world"
    intention_score: int = 5
    emotion_level: int = 5
    understanding: bool = False
    estimated_maturation_days: int = 21
    strength_multiplier: float = 1.0


class SeedCreateResponse(BaseModel):
    success: bool
    seed_id: str


class CoffeeProgressRequest(BaseModel):
    current_step: Optional[int] = None
    notes_draft: Optional[str] = None
    rejoiced_seed_ids: Optional[list[str]] = None


class CoffeeCompleteRequest(BaseModel):
    rejoiced_seed_ids: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    complete_project_day: bool = False
    completed_task_ids: list[str] = Field(default_factory=list)


class ProblemSolveRequest(BaseModel):
    problem: str
    session_id: Optional[str] = None
    diagnostic_answer: Optional[str] = None


class ProblemSolveResponse(BaseModel):
    problem: str
    root_cause: Optional[str] = None
    imprint_logic: Optional[str] = None
    stop_action: Optional[str] = None
    start_action: Optional[str] = None
    grow_action: Optional[str] = None
    practice_steps: list[str] = []
    expected_outcome: Optional[str] = None
    timeline_days: Optional[int] = None
    success_tip: Optional[str] = None
    correlations: list[dict] = []
    concepts: list[dict] = []
    clarity_level: Optional[str] = None
    karmic_pattern: Optional[str] = None
    seed_strategy_summary: Optional[str] = None
    coffee_meditation_script: Optional[str] = None
    partner_actions: list[str] = []
    needs_clarification: Optional[bool] = None
    clarifying_questions: list[str] = []
    rules: list[dict] = []
    practices: list[dict] = []
    session_id: Optional[str] = None
    history_id: Optional[str] = None


class UpdateActionCompletionRequest(BaseModel):
    completed: bool


class ProjectActivateRequest(BaseModel):
    history_id: str
    duration_days: int = 30
    project_partners: Optional[dict[str, list[str]]] = None
    isolation_settings: Optional[dict[str, dict]] = None


class ProjectStatusResponse(BaseModel):
    has_active_project: bool
    project: Optional[dict] = None
    daily_plan: Optional[dict] = None


class ProjectSetupResponse(BaseModel):
    problem: str
    partner_selection_guide: Optional[list[dict]] = None
    user_partners: dict[str, list[PartnerOut]] = {}


class DailyCompleteRequest(BaseModel):
    plan_id: str
    completed_tasks: list[str]
    notes: Optional[str] = None


class AddToCalendarRequest(BaseModel):
    steps: list[str]
    start_date: Optional[datetime] = None


class PracticeProgressResponse(BaseModel):
    practice_id: str
    habit_score: int
    streak_days: int
    total_completions: int
    last_completed: Optional[str]
    is_habit: bool


class PracticeCompleteRequest(BaseModel):
    emotion_score: int = 5


class OnboardingStepResponse(BaseModel):
    step: str
    step_number: int
    total_steps: int
    message: str
    input_type: str
    options: list
    field: Optional[str] = None
    completed: bool = False
    prev_step: Optional[str] = None
    current_value: Optional[Any] = None


class OnboardingAnswerRequest(BaseModel):
    step: str
    answer: Optional[str] = None
    answers: Optional[list] = None

