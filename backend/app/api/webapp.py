"""FastAPI endpoints for Mini App"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from app.models.user import UserProfile
from app.models.seed import Seed
from app.models.db_models import UserDB, ProblemHistoryDB
from app.auth import current_active_user
from uuid import uuid4
import logging
from app.crud_extended import create_karma_plan, get_active_karma_plan, get_daily_plan, create_daily_plan
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Mini App"])


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
    # Дополнительные поля для более глубокой логики (обратносуместимо)
    clarity_level: Optional[str] = None
    karmic_pattern: Optional[str] = None
    seed_strategy_summary: Optional[str] = None
    coffee_meditation_script: Optional[str] = None
    partner_actions: list[str] = []
    needs_clarification: Optional[bool] = None
    clarifying_questions: list[str] = []
    # Отладочные/объяснительные слои знаний
    rules: list[dict] = []
    practices: list[dict] = []
    # Идентификатор сессии диагностики (для многошагового режима)
    session_id: Optional[str] = None
    # ID истории для активации проекта
    history_id: Optional[str] = None




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
        created_at=u.created_at,
        updated_at=u.updated_at,
        last_onboarding_update=u.last_onboarding_update,
    )


async def get_current_user(
    user: UserDB = Depends(current_active_user),
) -> UserDB:
    """Hybrid auth dependency (Telegram + JWT).
    
    Uses fastapi-users under the hood, which tries each backend
    (Telegram initData, then JWT Bearer) and returns the authenticated UserDB.
    """
    return user


@router.get("/me")
async def get_me(user: UserDB = Depends(get_current_user)):
    """Get current user profile"""
    return user_db_to_profile(user)


@router.get(
    "/daily/actions",
    summary="Get daily actions",
    description="Retrieve personalized daily actions based on user profile and current focus"
)
async def get_daily_actions(user: UserDB = Depends(get_current_user)):
    """Get 4 daily actions"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.agents.daily_manager import DailyManagerAgent
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        agent = DailyManagerAgent(qdrant)

        # Now passing all needed fields for persistence check
        actions = await agent.get_daily_actions(
            user_id=user.id,
            first_name=user.first_name,
            streak_days=user.streak_days,
            total_seeds=user.total_seeds
        )

        return {"actions": actions}
    except Exception as e:
        logger.error(f"Error getting daily actions: {e}", exc_info=True)
        # In case of error не возвращаем статические действия, чтобы не плодить задачи без плана
        return {"actions": []}


class UpdateActionCompletionRequest(BaseModel):
    completed: bool


@router.patch("/daily/actions/{action_id}")
async def update_action_completion(
    action_id: str,
    payload: UpdateActionCompletionRequest,
    user: UserDB = Depends(get_current_user)
):
    """Toggle daily action completion for project tasks (DailyTaskDB only)."""
    from app.database import AsyncSessionLocal
    from app.crud import toggle_daily_task_completion
    from app.crud_extended import get_active_karma_plan, get_daily_plan
    from app.models.db_models import DailyTaskDB
    from sqlalchemy import select
    from datetime import datetime, UTC

    async with AsyncSessionLocal() as db:
        if not action_id.isdigit():
            raise HTTPException(status_code=400, detail="Invalid action id for project task")

        active_plan = await get_active_karma_plan(db, user.id)
        if not active_plan:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Сейчас у тебя нет активного проекта. Давай сначала мягко соберём его — и после этого можно будет отмечать шаги дня.",
                    "cta_path": "/problem",
                },
            )

        daily_plan = await get_daily_plan(db, active_plan.id, datetime.now(UTC))
        if not daily_plan:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Я не вижу план на сегодня. Открой кофе‑медитацию — и я подхвачу всё аккуратно.",
                    "cta_path": "/coffee",
                },
            )

        task_id = int(action_id)
        task_plan_res = await db.execute(
            select(DailyTaskDB.daily_plan_id)
            .where(DailyTaskDB.id == task_id)
            .limit(1)
        )
        task_daily_plan_id = task_plan_res.scalar_one_or_none()
        if not task_daily_plan_id or task_daily_plan_id != daily_plan.id:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Этот шаг не относится к сегодняшнему дню проекта. Давай отметим всё прямо в кофе‑медитации — там будет проще.",
                    "cta_path": "/coffee",
                },
            )

        # Project mode: toggle completion on DailyTaskDB and manage SeedDB links
        await toggle_daily_task_completion(
            db,
            user_id=user.id,
            task_id=int(action_id),
            completed=payload.completed,
        )
        await db.commit()
        return {"success": True}


@router.get(
    "/quote/daily",
    summary="Get daily quote",
    description="Retrieve a daily quote from the knowledge base relevant to user's current focus"
)
async def get_daily_quote(user: UserDB = Depends(get_current_user)):
    """Get quote for the day"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        
        # Get quote (no focus dependency)
        quote = await qdrant.get_daily_quote(None)
        return quote
    except Exception as e:
        logger.error(f"Error getting daily quote: {e}", exc_info=True)
        # Fallback quote
        return {
            "text": "Даяние приносит богатство, но не размер суммы важен, а щедрое состояние ума",
            "author": "Геше Майкл Роуч",
            "context": "О богатстве",
            "source": "diamond-concepts.md"
        }


@router.get("/seeds")
async def get_seeds(
    limit: int = 50,
    user: UserDB = Depends(get_current_user)
):
    """Get user's seeds"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_seeds
    
    try:
        async with AsyncSessionLocal() as db:
            seeds_db = await get_user_seeds(db, user.id, limit)
            
            seeds = [
                {
                    "id": seed.id,
                    "timestamp": seed.timestamp.isoformat(),
                    "action_type": seed.action_type,
                    "description": seed.description,
                    "partner_group": seed.partner_group,
                    "intention_score": seed.intention_score,
                    "emotion_level": seed.emotion_level,
                    "strength_multiplier": seed.strength_multiplier,
                    "estimated_maturation_days": seed.estimated_maturation_days
                }
                for seed in seeds_db
            ]
            
            return {"seeds": seeds}
    except Exception as e:
        logger.error(f"Error getting seeds for user {user.id}: {e}", exc_info=True)
        return {"seeds": []}


@router.post("/seeds", response_model=SeedCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_seed_endpoint(
    payload: SeedCreateRequest,
    user: UserDB = Depends(get_current_user)
):
    """Create new seed"""
    from app.database import AsyncSessionLocal
    from app.crud import create_seed, increment_user_seeds_count
    from app.crud_extended import get_active_karma_plan
    
    try:
        async with AsyncSessionLocal() as db:
            active_plan = await get_active_karma_plan(db, user.id)
            if not active_plan:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": "Сейчас у тебя нет активного проекта. Давай сначала мягко соберём его в разделе «Проблема», и после этого семена будут работать стабильно.",
                        "cta_path": "/problem",
                    },
                )
            
            seed = Seed(
                user_id=user.id,
                action_type=payload.action_type,
                description=payload.description,
                partner_group=payload.partner_group,
                intention_score=payload.intention_score,
                emotion_level=payload.emotion_level,
                understanding=payload.understanding,
                estimated_maturation_days=payload.estimated_maturation_days,
                strength_multiplier=payload.strength_multiplier,
                karma_plan_id=active_plan.id,
            )
            seed_db = await create_seed(db, seed)
            await increment_user_seeds_count(db, user.id)
            await db.commit()
            return SeedCreateResponse(success=True, seed_id=seed_db.id).model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating seed via API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coffee/today")
async def get_coffee_today(user: UserDB = Depends(get_current_user)):
    from app.coffee_meditation import get_local_day_bounds, get_rejoiced_seed_ids, get_today_daily_plan, get_today_seeds, get_user_zoneinfo
    from app.crud_extended import get_active_karma_plan
    from app.database import AsyncSessionLocal
    from app.models.db_models import CoffeeMeditationSessionDB
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        active_plan = await get_active_karma_plan(db, user.id)
        if not active_plan:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Кофе‑медитация работает, когда есть активный проект. Давай сначала соберём его — это займёт несколько спокойных шагов.",
                    "cta_path": "/problem",
                },
            )

        user_tz = get_user_zoneinfo(user.timezone)
        bounds = get_local_day_bounds(datetime.now(UTC), user_tz)

        daily_plan = await get_today_daily_plan(
            db,
            karma_plan_id=active_plan.id,
            utc_start=bounds.utc_start,
            utc_end=bounds.utc_end,
        )

        session_result = await db.execute(
            select(CoffeeMeditationSessionDB).where(
                CoffeeMeditationSessionDB.user_id == user.id,
                CoffeeMeditationSessionDB.local_date == bounds.local_date,
            )
        )
        session = session_result.scalar_one_or_none()
        rejoiced_seed_ids: list[str] = []
        if session:
            rejoiced_seed_ids = await get_rejoiced_seed_ids(db, session_id=session.id)

        seeds_db = await get_today_seeds(
            db,
            user_id=user.id,
            utc_start=bounds.utc_start,
            utc_end=bounds.utc_end,
        )

        seeds = [
            {
                "id": seed.id,
                "timestamp": seed.timestamp.isoformat(),
                "action_type": seed.action_type,
                "description": seed.description,
                "partner_group": seed.partner_group,
                "intention_score": seed.intention_score,
                "emotion_level": seed.emotion_level,
                "strength_multiplier": seed.strength_multiplier,
                "estimated_maturation_days": seed.estimated_maturation_days,
                "rejoice_count": seed.rejoice_count,
                "last_rejoiced_at": seed.last_rejoiced_at.isoformat() if seed.last_rejoiced_at else None,
            }
            for seed in seeds_db
        ]

        daily_data = None
        if daily_plan:
            tasks_data = []
            if daily_plan.tasks:
                sorted_tasks = sorted(
                    daily_plan.tasks,
                    key=lambda t: t.order if t.order is not None else 0,
                )
                tasks_data = [
                    {
                        "id": str(t.id),
                        "description": t.description,
                        "why": t.why,
                        "group": t.group,
                        "completed": t.completed,
                    }
                    for t in sorted_tasks
                ]

            daily_data = {
                "id": daily_plan.id,
                "day_number": daily_plan.day_number,
                "focus_quality": daily_plan.focus_quality,
                "tasks": tasks_data,
                "is_completed": daily_plan.is_completed,
            }

        session_data = None
        if session:
            session_data = {
                "id": session.id,
                "current_step": session.current_step,
                "notes_draft": session.notes_draft,
                "notes": session.notes,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "rejoiced_seed_ids": rejoiced_seed_ids,
            }

        return {
            "has_active_project": True,
            "local_date": bounds.local_date.isoformat(),
            "utc_start": bounds.utc_start.isoformat(),
            "utc_end": bounds.utc_end.isoformat(),
            "session": session_data,
            "seeds": seeds,
            "daily_plan": daily_data,
        }


@router.post("/coffee/progress")
async def save_coffee_progress(
    payload: CoffeeProgressRequest,
    user: UserDB = Depends(get_current_user),
):
    from app.coffee_meditation import get_local_day_bounds, get_rejoiced_seed_ids, get_today_daily_plan, get_user_zoneinfo, get_or_create_session, save_progress
    from app.crud_extended import get_active_karma_plan
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        active_plan = await get_active_karma_plan(db, user.id)
        if not active_plan:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Сейчас у тебя нет активного проекта. Давай сначала спокойно соберём его — и кофемедитация сразу оживёт.",
                    "cta_path": "/problem",
                },
            )

        user_tz = get_user_zoneinfo(user.timezone)
        bounds = get_local_day_bounds(datetime.now(UTC), user_tz)

        daily_plan = await get_today_daily_plan(
            db,
            karma_plan_id=active_plan.id,
            utc_start=bounds.utc_start,
            utc_end=bounds.utc_end,
        )

        session = await get_or_create_session(
            db,
            user_id=user.id,
            local_date=bounds.local_date,
            karma_plan_id=active_plan.id,
            daily_plan_id=daily_plan.id if daily_plan else None,
        )

        await save_progress(
            db,
            session=session,
            user_id=user.id,
            current_step=payload.current_step,
            notes_draft=payload.notes_draft,
            rejoiced_seed_ids=payload.rejoiced_seed_ids,
        )

        await db.commit()

        rejoiced_seed_ids = await get_rejoiced_seed_ids(db, session_id=session.id)
        return {
            "success": True,
            "session": {
                "id": session.id,
                "current_step": session.current_step,
                "notes_draft": session.notes_draft,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "rejoiced_seed_ids": rejoiced_seed_ids,
            },
        }


@router.post("/coffee/complete")
async def complete_coffee(
    payload: CoffeeCompleteRequest,
    user: UserDB = Depends(get_current_user),
):
    from app.coffee_meditation import complete_session, get_local_day_bounds, get_today_daily_plan, get_user_zoneinfo, get_or_create_session
    from app.crud import toggle_daily_task_completion
    from app.crud_extended import get_active_karma_plan
    from app.database import AsyncSessionLocal
    from app.models.db_models import DailyPlanDB
    from sqlalchemy import update

    async with AsyncSessionLocal() as db:
        active_plan = await get_active_karma_plan(db, user.id)
        if not active_plan:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Кофе‑медитация работает, когда есть активный проект. Давай сначала соберём его в разделе «Проблема».",
                    "cta_path": "/problem",
                },
            )

        user_tz = get_user_zoneinfo(user.timezone)
        bounds = get_local_day_bounds(datetime.now(UTC), user_tz)

        daily_plan = await get_today_daily_plan(
            db,
            karma_plan_id=active_plan.id,
            utc_start=bounds.utc_start,
            utc_end=bounds.utc_end,
        )

        session = await get_or_create_session(
            db,
            user_id=user.id,
            local_date=bounds.local_date,
            karma_plan_id=active_plan.id,
            daily_plan_id=daily_plan.id if daily_plan else None,
        )

        result = await complete_session(
            db,
            session_id=session.id,
            user_id=user.id,
            notes=payload.notes,
            rejoice_seed_ids=payload.rejoiced_seed_ids,
        )

        if payload.complete_project_day and daily_plan:
            await db.execute(
                update(DailyPlanDB)
                .where(DailyPlanDB.id == daily_plan.id)
                .values(
                    is_completed=True,
                    completion_notes=payload.notes,
                    updated_at=datetime.now(UTC),
                )
            )

            allowed_task_ids = {
                int(t.id) for t in (daily_plan.tasks or []) if getattr(t, "id", None) is not None
            }

            for task_id_str in payload.completed_task_ids:
                if not task_id_str.isdigit():
                    continue
                task_id = int(task_id_str)
                if task_id not in allowed_task_ids:
                    continue

                await toggle_daily_task_completion(
                    db,
                    user_id=user.id,
                    task_id=task_id,
                    completed=True,
                )

        await db.commit()
        return {"success": True, "result": result}


@router.get("/problems/history")
async def get_problems_history(user: UserDB = Depends(get_current_user)):
    """Get problem history"""
    from app.database import AsyncSessionLocal
    from app.crud import get_problem_history
    from app.crud_extended import get_active_karma_plan
    
    async with AsyncSessionLocal() as db:
        active_plan = await get_active_karma_plan(db, user.id)
        active_history_id = active_plan.problem_history_id if active_plan else None

        history = await get_problem_history(db, user.id)
        return {
            "history": [
                {
                    "id": h.id,
                    "problem_text": h.problem_text,
                    "solution": h.solution_json,
                    # History "activity" is now derived from the active karma plan
                    "is_active": bool(active_history_id and h.id == active_history_id),
                    "created_at": h.created_at
                } for h in history
            ]
        }


class AddToCalendarRequest(BaseModel):
    steps: list[str]
    start_date: Optional[datetime] = None


@router.post("/problem/add-to-calendar")
async def add_problem_to_calendar(
    _payload: AddToCalendarRequest,
    user: UserDB = Depends(get_current_user)
):
    """Add 30-day plan steps to calendar"""
    from app.database import AsyncSessionLocal
    from app.crud_extended import get_active_karma_plan
    
    async with AsyncSessionLocal() as db:
        active_plan = await get_active_karma_plan(db, user.id)
        if not active_plan:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Чтобы сохранить план на 30 дней, нужен активный проект. Давай запустим его — и план станет твоими задачами дня.",
                    "cta_path": "/problem",
                },
            )

        return {
            "success": True,
            "count": 0,
            "message": "У тебя уже есть активный проект — план на 30 дней уже хранится там. Открой проект, и он будет вести тебя шаг за шагом.",
        }

@router.post("/problem/solve", response_model=ProblemSolveResponse)
async def solve_problem_endpoint(
        payload: ProblemSolveRequest,
        user: UserDB = Depends(get_current_user)
):
    """Solve problem using AI agent and knowledge base"""
    from app.agents.problem_solver import ProblemSolverAgent
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings
    from app.database import AsyncSessionLocal
    from app.crud import save_problem_history

    settings = get_settings()
    qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
    agent = ProblemSolverAgent(qdrant)

    # Determine or create diagnostic session id for web flow
    from uuid import uuid4
    session_id = payload.session_id or f"web_{user.id}_{uuid4().hex[:8]}"

    # Convert UserDB to UserProfile for agent compatibility
    user_profile = user_db_to_profile(user)

    # Always use diagnostic mode for web problem solving flow
    solution = await agent.analyze_problem(
        user_profile,
        payload.problem,
        session_id=session_id,
        diagnostic_answer=payload.diagnostic_answer,
    )

    # Attach session id so client can continue diagnostic if needed
    solution["session_id"] = session_id

    # Save to history только для финальных решений (без запроса уточнений)
    async with AsyncSessionLocal() as db:
        if not solution.get("needs_clarification"):
            history_item = await save_problem_history(db, user.id, payload.problem, solution)
            solution["history_id"] = history_item.id
            await db.commit()

    return solution


class ProjectActivateRequest(BaseModel):
    history_id: str
    duration_days: int = 30
    project_partners: Optional[dict[str, List[str]]] = None # {category: [partner_ids]}
    isolation_settings: Optional[dict[str, dict]] = None # {category: {is_isolated: bool}}


class ProjectSetupResponse(BaseModel):
    problem: str
    partner_selection_guide: Optional[list[dict]] = None # From AI
    user_partners: dict[str, list[PartnerOut]] = {} # Grouped by universal_category


@router.get("/projects/setup/{history_id}", response_model=ProjectSetupResponse)
async def get_project_setup(
    history_id: str,
    user: UserDB = Depends(get_current_user)
):
    """Get setup data for a new project (guide + existing partners)"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_partners, get_partner_groups
    from app.models.db_models import ProblemHistoryDB
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        # 1. Get history for guide
        res = await db.execute(select(ProblemHistoryDB).where(ProblemHistoryDB.id == history_id))
        hist = res.scalar_one_or_none()
        if not hist:
            raise HTTPException(status_code=404, detail="History entry not found")
            
        solution = hist.solution_json
        guide = solution.get("partner_selection_guide")
        
        # Fallback if AI didn't generate guide
        if not guide:
            guide = [
                {
                    "category": "source",
                    "title": "Ваш Источник (Source)",
                    "description": "Выберите того, кто дает вам ресурсы, основу и поддержку. Это ваш фундамент.",
                    "examples": ["Родители", "Учителя", "Врачи", "Авторы книг"]
                },
                {
                    "category": "ally",
                    "title": "Ваш Соратник (Ally)",
                    "description": "Выберите того, кто находится с вами на одном уровне и идет к общей цели.",
                    "examples": ["Супруг(а)", "Близкий друг", "Партнер по бизнесу", "Коллега"]
                },
                {
                    "category": "protege",
                    "title": "Ваш Подопечный (Protege)",
                    "description": "Выберите того, кто зависит от вас и нуждается в вашей помощи.",
                    "examples": ["Дети", "Ученики", "Клиенты", "Подчиненные"]
                },
                {
                    "category": "world",
                    "title": "Внешний мир (World)",
                    "description": "Выберите кого-то далекого от вашего круга или даже конкурента.",
                    "examples": ["Случайный прохожий", "Конкурент", "Незнакомец", "Общество"]
                }
            ]
        
        # 2. Get user partners and groups
        partners_db = await get_user_partners(db, user.id)
        groups_db = await get_partner_groups(db, user.id)
        
        # Map group_id to universal_category
        group_map = {g.id: g.universal_category or "world" for g in groups_db}
        
        # Group partners by category
        user_partners = {
            "source": [],
            "ally": [],
            "protege": [],
            "world": []
        }
        
        for p in partners_db:
            cat = group_map.get(p.group_id, "world")
            if cat not in user_partners:
                user_partners[cat] = []
                
            user_partners[cat].append(PartnerOut(
                id=p.id,
                name=p.name,
                group_id=p.group_id,
                telegram_username=p.telegram_username,
                phone=p.phone,
                notes=p.notes
            ))
            
        return {
            "problem": hist.problem_text,
            "partner_selection_guide": guide,
            "user_partners": user_partners
        }


class ProjectStatusResponse(BaseModel):
    has_active_project: bool
    project: Optional[dict] = None
    daily_plan: Optional[dict] = None


@router.post("/projects/activate", response_model=ProjectStatusResponse)
async def activate_project(
    payload: ProjectActivateRequest,
    user: UserDB = Depends(get_current_user)
):
    """Activate a new Karmic Project (Karma Plan)"""
    from app.database import AsyncSessionLocal
    from app.models.db_models import ProblemHistoryDB
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Get the history item to extract strategy
        res = await db.execute(select(ProblemHistoryDB).where(ProblemHistoryDB.id == payload.history_id))
        hist = res.scalar_one_or_none()
        
        if not hist:
            raise HTTPException(status_code=404, detail="History entry not found")
            
        solution = hist.solution_json
        
        # Extract strategy snapshot
        strategy_snapshot = {
            "root_cause": solution.get("root_cause"),
            "stop_action": solution.get("stop_action"),
            "start_action": solution.get("start_action"),
            "grow_action": solution.get("grow_action"),
            "success_tip": solution.get("success_tip"),
            "practice_steps": solution.get("practice_steps", []),
            "problem_text": hist.problem_text
        }
        
        # Create plan
        plan = await create_karma_plan(
            db, 
            user.id, 
            payload.history_id, 
            strategy_snapshot, 
            payload.duration_days,
            project_partners=payload.project_partners,
            isolation_settings=payload.isolation_settings
        )
        
        await db.commit()
        
        # Serialize partners from association
        partners_dict = {}
        if plan.partners_association:
            for assoc in plan.partners_association:
                if assoc.category not in partners_dict:
                    partners_dict[assoc.category] = []
                partners_dict[assoc.category].append(assoc.partner_id)

        return {
            "has_active_project": True,
            "project": {
                "id": plan.id,
                "problem": hist.problem_text,
                "day_number": 1,
                "duration_days": plan.duration_days,
                "strategy": plan.strategy_snapshot,
                "partners": partners_dict,
                "history_id": payload.history_id,
                "isolation_settings": plan.isolation_settings or {},
            }
        }


@router.get("/projects/active", response_model=ProjectStatusResponse)
async def get_active_project(user: UserDB = Depends(get_current_user)):
    """Get current active Karmic Project status"""
    from app.database import AsyncSessionLocal
    from datetime import datetime, UTC

    async with AsyncSessionLocal() as db:
        plan = await get_active_karma_plan(db, user.id)
        if not plan:
            return {"has_active_project": False}
            
        # Calculate day number
        days_passed = (datetime.now(UTC) - plan.start_date).days + 1
        
        # Get today's daily plan
        daily = await get_daily_plan(db, plan.id, datetime.now(UTC))
        
        daily_data = None
        if daily:
            # Serialize tasks from DB objects to dicts
            tasks_data = []
            if daily.tasks:
                # Sort by order if available (DailyTaskDB has 'order' column)
                sorted_tasks = sorted(daily.tasks, key=lambda t: t.order if t.order is not None else 0)
                
                tasks_data = [
                    {
                        "id": str(t.id),
                        "description": t.description,
                        "why": t.why,
                        "group": t.group,
                        "completed": t.completed
                    }
                    for t in sorted_tasks
                ]

            daily_data = {
                "id": daily.id,
                "day_number": daily.day_number,
                "focus_quality": daily.focus_quality,
                "tasks": tasks_data,
                "is_completed": daily.is_completed
            }
            
        # Serialize partners from association
        partners_dict = {}
        if plan.partners_association:
            for assoc in plan.partners_association:
                if assoc.category not in partners_dict:
                    partners_dict[assoc.category] = []
                partners_dict[assoc.category].append(assoc.partner_id)
            
        return {
            "has_active_project": True,
            "project": {
                "id": plan.id,
                "problem": plan.strategy_snapshot.get("problem_text", "Unknown Problem"),
                "day_number": days_passed,
                "duration_days": plan.duration_days,
                "strategy": plan.strategy_snapshot,
                "partners": partners_dict,
                "history_id": plan.problem_history_id,
                "isolation_settings": plan.isolation_settings or {},
            },
            "daily_plan": daily_data
        }


class DailyCompleteRequest(BaseModel):
    plan_id: str
    completed_tasks: list[str]
    notes: Optional[str] = None


@router.post("/projects/daily/complete")
async def complete_daily_plan(
    payload: DailyCompleteRequest,
    user: UserDB = Depends(get_current_user)
):
    """Complete daily tasks for the project (Coffee Meditation)"""
    from app.database import AsyncSessionLocal
    from app.models.db_models import DailyPlanDB
    from sqlalchemy import select, update
    from datetime import datetime, UTC
    from app.crud import toggle_daily_task_completion
    
    async with AsyncSessionLocal() as db:
        active_plan = await get_active_karma_plan(db, user.id) 
        
        if not active_plan or active_plan.id != payload.plan_id:
             raise HTTPException(status_code=404, detail="Active project not found or mismatch")

        daily = await get_daily_plan(db, active_plan.id, datetime.now(UTC))
        
        if not daily:
             raise HTTPException(status_code=404, detail="Daily plan for today not found")
             
        # Update completion status of the plan itself
        await db.execute(
            update(DailyPlanDB)
            .where(DailyPlanDB.id == daily.id)
            .values(
                is_completed=True,
                completion_notes=payload.notes,
                updated_at=datetime.now(UTC)
            )
        )
        
        # Process individual tasks to ensure seeds are created/linked
        for task_id_str in payload.completed_tasks:
            if task_id_str.isdigit():
                # For each task marked as completed in the Coffee Meditation, ensure it's toggled to True
                # This will create the seed if it doesn't exist, and update user stats
                await toggle_daily_task_completion(
                    db,
                    user_id=user.id,
                    task_id=int(task_id_str),
                    completed=True
                )
            
        await db.commit()
        return {"success": True}


@router.get("/partners", response_model=PartnersResponse)
async def get_partners(user: UserDB = Depends(get_current_user)):
    """Get user's partner groups and partners"""
    from app.database import AsyncSessionLocal
    from app.crud import (
        ensure_default_partner_groups,
        get_user_partners,
        get_partner_groups,
    )

    async with AsyncSessionLocal() as db:
        await ensure_default_partner_groups(db, user.id)
        await db.commit()

        groups_db = await get_partner_groups(db, user.id)
        partners_db = await get_user_partners(db, user.id)

        groups = [
            PartnerGroupOut(
                id=g.id,
                name=g.name,
                icon=g.icon,
                description=g.description,
                universal_category=g.universal_category,
                is_default=bool(g.is_default),
            )
            for g in groups_db
        ]
        partners = [
            PartnerOut(
                id=p.id,
                name=p.name,
                group_id=p.group_id,
                telegram_username=p.telegram_username,
                phone=p.phone,
                notes=p.notes,
            )
            for p in partners_db
        ]

        return PartnersResponse(groups=groups, partners=partners).model_dump()


@router.post("/partners", response_model=PartnerCreateResponse)
async def create_partner_endpoint(
    payload: PartnerCreateRequest,
    user: UserDB = Depends(get_current_user),
):
    """Create new partner"""
    from app.database import AsyncSessionLocal
    from app.crud import ensure_default_partner_groups
    from app.models.db_models import PartnerDB, PartnerGroupDB
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        await ensure_default_partner_groups(db, user.id)

        group_result = await db.execute(
            select(PartnerGroupDB).where(
                PartnerGroupDB.id == payload.group_id,
                PartnerGroupDB.user_id == user.id,
            )
        )
        group_db = group_result.scalar_one_or_none()
        if not group_db:
            raise HTTPException(status_code=400, detail="Invalid partner group")

        partner_db = PartnerDB(
            id=str(uuid4()),
            user_id=user.id,
            group_id=group_db.id,
            name=payload.name,
            telegram_username=payload.telegram_username,
            phone=payload.phone,
            notes=payload.notes,
        )

        db.add(partner_db)
        await db.commit()

        return PartnerCreateResponse(success=True, partner_id=partner_db.id).model_dump()


@router.get("/practices")
async def get_practices(
    user: UserDB = Depends(get_current_user),
    limit: int = Query(default=0, description="Limit results, 0 = all"),
):
    """Get all practices from PracticeDB (canonical source)"""
    from app.database import AsyncSessionLocal
    from app.models.db_models import PracticeDB
    from sqlalchemy import select
    
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(PracticeDB).order_by(PracticeDB.category, PracticeDB.name)
            if limit > 0:
                stmt = stmt.limit(limit)
            result = await db.execute(stmt)
            practices_db = result.scalars().all()
            practices = [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "description": p.description,
                    "duration": p.duration_minutes,
                    "difficulty": p.difficulty,
                    "physical_intensity": p.physical_intensity,
                    "requires_morning": p.requires_morning,
                    "requires_silence": p.requires_silence,
                    "max_completions_per_day": p.max_completions_per_day,
                    "steps": p.steps or [],
                    "contraindications": p.contraindications or [],
                    "benefits": p.benefits,
                    "tags": p.tags or [],
                }
                for p in practices_db
            ]
            return {"practices": practices}
    except Exception as e:
        logger.error(f"Error getting practices: {e}", exc_info=True)
        return {"practices": []}




# =============================================================================
# Practice Progress Endpoints
# =============================================================================

class PracticeProgressResponse(BaseModel):
    practice_id: str
    habit_score: int
    streak_days: int
    total_completions: int
    last_completed: Optional[str]
    is_habit: bool


class PracticeCompleteRequest(BaseModel):
    emotion_score: int = 5


@router.post("/practices/{practice_id}/start")
async def start_practice_tracking(practice_id: str, user: UserDB = Depends(get_current_user)):
    """Начать отслеживание практики (PracticeDB must exist)"""
    from app.database import AsyncSessionLocal
    from app.crud import get_or_create_practice_progress
    from app.crud_extended import get_active_karma_plan
    from app.models.db_models import PracticeDB
    from sqlalchemy import select
    
    try:
        async with AsyncSessionLocal() as db:
            # PracticeDB is canonical — must exist
            practice_result = await db.execute(
                select(PracticeDB).where(PracticeDB.id == practice_id).limit(1)
            )
            practice = practice_result.scalar_one_or_none()
            if not practice:
                return {"error": "Practice not found in catalog"}
            
            # Get active project for karma_plan_id
            active_plan = await get_active_karma_plan(db, user.id)
            plan_id = active_plan.id if active_plan else None
            
            progress = await get_or_create_practice_progress(
                db, user.id, practice_id, karma_plan_id=plan_id
            )
            await db.commit()
            
            return {
                "practice_id": practice_id,
                "tracking_started": True,
                "habit_score": progress.habit_score,
                "streak_days": progress.streak_days
            }
    except Exception as e:
        logger.error(f"Error starting practice tracking: {e}", exc_info=True)
        return {"error": "Failed to start tracking"}


@router.post("/practices/{practice_id}/complete")
async def complete_practice(
    practice_id: str, 
    request: PracticeCompleteRequest = None,
    user: UserDB = Depends(get_current_user)
):
    """Отметить выполнение практики"""
    from app.database import AsyncSessionLocal
    from app.crud import complete_practice_and_create_seed
    from app.crud_extended import get_active_karma_plan
    
    if request is None:
        request = PracticeCompleteRequest()
    
    try:
        async with AsyncSessionLocal() as db:
            active_plan = await get_active_karma_plan(db, user.id)
            
            result = await complete_practice_and_create_seed(
                db,
                user_id=user.id,
                practice_id=practice_id,
                karma_plan_id=(active_plan.id if active_plan else None),
                emotion_score=request.emotion_score,
            )
            await db.commit()
            
            return {
                "practice_id": practice_id,
                "completed": result["actually_updated"],
                "habit_score": result["progress"].habit_score,
                "streak_days": result["progress"].streak_days,
                "is_habit": result["progress"].is_habit,
                "seed_created": result["seed"].id if result["seed"] else None,
                "is_new_habit": result["is_new_habit"]
            }
    except Exception as e:
        logger.error(f"Error completing practice: {e}", exc_info=True)
        return {"error": "Failed to complete practice"}


@router.get("/practices/progress")
async def get_practices_progress(user: UserDB = Depends(get_current_user)):
    """Получить прогресс всех практик (включая привычки)"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_practice_progress
    
    try:
        async with AsyncSessionLocal() as db:
            progress_list = await get_user_practice_progress(db, user.id)
            
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            
            result = []
            for progress in progress_list:
                practice = progress.practice
                max_per_day = (practice.max_completions_per_day if practice else 1) or 1
                
                can_complete_today = (
                    progress.is_active and
                    not progress.is_hidden and
                    (not progress.last_completed or progress.last_completed.date() != today or max_per_day > 1)
                )
                
                result.append({
                    "practice_id": progress.practice_id,
                    "practice_name": practice.name if practice else "Unknown",
                    "practice_category": practice.category if practice else "",
                    "practice_duration": practice.duration_minutes if practice else 0,
                    "habit_score": progress.habit_score,
                    "streak_days": progress.streak_days,
                    "total_completions": progress.total_completions,
                    "last_completed": progress.last_completed.isoformat() if progress.last_completed else None,
                    "is_habit": progress.is_habit,
                    "is_active": progress.is_active,
                    "is_hidden": progress.is_hidden,
                    "can_complete_today": can_complete_today,
                    "habit_min_streak_days": practice.habit_min_streak_days if practice else 14,
                    "habit_min_score": practice.habit_min_score if practice else 70,
                })
            
            return {"progress": result}
    except Exception as e:
        logger.error(f"Error getting practice progress: {e}", exc_info=True)
        return {"progress": []}


@router.post("/practices/{practice_id}/pause")
async def pause_practice_endpoint(practice_id: str, user: UserDB = Depends(get_current_user)):
    """Приостановить практику"""
    from app.database import AsyncSessionLocal
    from app.crud import pause_practice
    
    try:
        async with AsyncSessionLocal() as db:
            ok = await pause_practice(db, user.id, practice_id)
            await db.commit()
            return {"success": ok}
    except Exception as e:
        logger.error(f"Error pausing practice: {e}", exc_info=True)
        return {"error": "Failed to pause practice"}


@router.post("/practices/{practice_id}/resume")
async def resume_practice_endpoint(practice_id: str, user: UserDB = Depends(get_current_user)):
    """Возобновить практику"""
    from app.database import AsyncSessionLocal
    from app.crud import resume_practice
    
    try:
        async with AsyncSessionLocal() as db:
            ok = await resume_practice(db, user.id, practice_id)
            await db.commit()
            return {"success": ok}
    except Exception as e:
        logger.error(f"Error resuming practice: {e}", exc_info=True)
        return {"error": "Failed to resume practice"}


@router.post("/practices/{practice_id}/hide")
async def hide_practice_endpoint(practice_id: str, user: UserDB = Depends(get_current_user)):
    """Скрыть практику из списков"""
    from app.database import AsyncSessionLocal
    from app.crud import hide_practice
    
    try:
        async with AsyncSessionLocal() as db:
            ok = await hide_practice(db, user.id, practice_id)
            await db.commit()
            return {"success": ok}
    except Exception as e:
        logger.error(f"Error hiding practice: {e}", exc_info=True)
        return {"error": "Failed to hide practice"}


@router.post("/practices/{practice_id}/reset")
async def reset_practice_endpoint(practice_id: str, user: UserDB = Depends(get_current_user)):
    """Сбросить прогресс практики"""
    from app.database import AsyncSessionLocal
    from app.crud import reset_practice
    
    try:
        async with AsyncSessionLocal() as db:
            ok = await reset_practice(db, user.id, practice_id)
            await db.commit()
            return {"success": ok}
    except Exception as e:
        logger.error(f"Error resetting practice: {e}", exc_info=True)
        return {"error": "Failed to reset practice"}


@router.delete("/practices/{practice_id}")
async def delete_practice_endpoint(practice_id: str, user: UserDB = Depends(get_current_user)):
    """Удалить практику и все связанные семена"""
    from app.database import AsyncSessionLocal
    from app.crud import delete_practice_all
    
    try:
        async with AsyncSessionLocal() as db:
            deleted_seeds = await delete_practice_all(db, user.id, practice_id)
            await db.commit()
            return {"success": True, "deleted_seeds": deleted_seeds}
    except Exception as e:
        logger.error(f"Error deleting practice: {e}", exc_info=True)
        return {"error": "Failed to delete practice"}


def _build_recommend_query(strategy: dict | None) -> str:
    """Build Qdrant search query from active plan strategy or default"""
    if strategy:
        need = f"{strategy.get('problem_text', '')} {strategy.get('stop_action', '')} {strategy.get('start_action', '')} {strategy.get('grow_action', '')}".strip()
        if need:
            return need
    return "общее развитие, осознанность, кармические практики"


@router.get("/practices/recommend")
async def get_practice_recommendations(user: UserDB = Depends(get_current_user)):
    """AI рекомендации практик (M6: единый источник для dashboard и бота)"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_practice_progress
    from app.crud_extended import get_active_karma_plan
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings
    
    try:
        async with AsyncSessionLocal() as db:
            existing_progress = await get_user_practice_progress(db, user.id)
            existing_ids = {str(p.practice_id) for p in existing_progress}
            
            # M6: Context from active project strategy or general development
            active_plan = await get_active_karma_plan(db, user.id)
            strategy = active_plan.strategy_snapshot if active_plan else None
            need = _build_recommend_query(strategy)
            
            settings = get_settings()
            qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
            
            recommendations = await qdrant.search_practice(
                need=need,
                restrictions=user.physical_restrictions.split(',') if user.physical_restrictions else None,
                limit=8
            )
            
            # Filter out already tracked practices (string comparison)
            filtered = [
                r for r in recommendations 
                if str(r.get('id', '')) not in existing_ids
            ]

            return {"recommendations": filtered[:6]}
            
    except Exception as e:
        logger.error(f"Error getting practice recommendations: {e}", exc_info=True)
        return {"recommendations": []}


# =============================================================================
# Onboarding Endpoints
# =============================================================================

class OnboardingStepResponse(BaseModel):
    step: str
    step_number: int
    total_steps: int
    message: str
    input_type: str
    options: list
    field: Optional[str] = None
    completed: bool = False


class OnboardingAnswerRequest(BaseModel):
    step: str
    answer: Optional[str] = None
    answers: Optional[list] = None  # For multi-choice


@router.get("/onboarding/start", response_model=OnboardingStepResponse)
async def start_onboarding(user: UserDB = Depends(get_current_user)):
    """Start or resume onboarding flow"""
    from app.workflows.onboarding import get_step_data, ONBOARDING_STEPS, OnboardingSteps
    
    # Check if user already completed onboarding
    if user.last_onboarding_update:
        return get_step_data(OnboardingSteps.COMPLETE)
    
    # Check current progress based on filled fields
    current_step = OnboardingSteps.OCCUPATION
    if not user.occupation or user.occupation == "employee":
        current_step = OnboardingSteps.OCCUPATION
    elif not user.available_times or len(user.available_times) == 0:
        current_step = OnboardingSteps.SCHEDULE
    elif user.daily_minutes == 30:  # default value, not explicitly set
        current_step = OnboardingSteps.DURATION
    elif not user.current_habits or len(user.current_habits) == 0:
        current_step = OnboardingSteps.HABITS
    else:
        current_step = OnboardingSteps.PARTNERS
    
    return get_step_data(current_step)


@router.post("/onboarding/answer", response_model=OnboardingStepResponse)
async def answer_onboarding(
    payload: OnboardingAnswerRequest,
    user: UserDB = Depends(get_current_user)
):
    """Process onboarding step answer and return next step"""
    from app.workflows.onboarding import get_step_data, get_next_step, ONBOARDING_STEPS, save_onboarding_progress, OnboardingSteps
    
    step_info = ONBOARDING_STEPS.get(payload.step)
    if not step_info:
        raise HTTPException(status_code=400, detail="Invalid step")
    
    # Prepare answer value
    val = payload.answer
    if step_info.get("input_type") == "multi_choice":
        val = payload.answers or []
    elif step_info.get("input_type") == "text_optional":
        if val == "skip":
            val = None
            
    # Save using shared logic
    await save_onboarding_progress(user.id, payload.step, val)
    
    next_step = get_next_step(payload.step)
    return get_step_data(next_step or OnboardingSteps.COMPLETE)

