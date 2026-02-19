"""FastAPI endpoints for Mini App"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import List, Optional
from datetime import datetime, UTC
from pydantic import BaseModel
from app.models.user import UserProfile
from app.models.seed import Seed
from uuid import uuid4
import logging
from app.crud_extended import create_karma_plan, get_active_karma_plan, get_daily_plan, create_daily_plan
from app.crud import get_user_by_telegram_id, update_user_focus
from app.models.db_models import ProblemHistoryDB
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
    notes: Optional[str] = None


class PartnersResponse(BaseModel):
    groups: list[PartnerGroupOut]
    partners: list[PartnerOut]


class PartnerCreateRequest(BaseModel):
    name: str
    group_id: str
    telegram_username: Optional[str] = None
    phone: Optional[str] = None
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




async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> UserProfile:
    """
    Get current user from Telegram WebApp initData
    
    Validates Telegram WebApp initData and returns user profile.
    For development without frontend, returns mock user.
    
    Args:
        authorization: Telegram initData from Authorization header
        
    Returns:
        UserProfile object
        
    Raises:
        HTTPException: If authentication fails
    """
    from app.telegram_auth import validate_telegram_webapp_data, extract_user_from_init_data
    from app.config import get_settings
    from app.database import AsyncSessionLocal
    from app.crud import get_or_create_user, ensure_default_partner_groups

    settings = get_settings()

    # Development mode: allow working without Telegram WebApp
    if not authorization:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(status_code=401, detail="Authentication required")

        async with AsyncSessionLocal() as session:
            user_db = await get_or_create_user(
                session,
                telegram_id=123456789,
                first_name="Dev User",
                username="dev",
            )
            await ensure_default_partner_groups(session, user_db.id)
            await session.commit()

        return UserProfile(
            id=user_db.id,
            telegram_id=user_db.telegram_id,
            first_name=user_db.first_name,
            username=user_db.username,
            occupation=user_db.occupation or "employee",
            available_times=user_db.available_times or [],
            daily_minutes=user_db.daily_minutes or 30,
            current_habits=user_db.current_habits or [],
            physical_restrictions=user_db.physical_restrictions,
            streak_days=user_db.streak_days,
            total_seeds=user_db.total_seeds,
            completed_practices=user_db.completed_practices,
            timezone=user_db.timezone or "UTC",
            morning_enabled=bool(user_db.morning_enabled),
            evening_enabled=bool(user_db.evening_enabled),
            current_focus=user_db.current_focus,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            last_onboarding_update=user_db.last_onboarding_update,
        )

    parsed_data = validate_telegram_webapp_data(authorization)
    if not parsed_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication")

    user_info = extract_user_from_init_data(parsed_data)
    if not user_info:
        raise HTTPException(status_code=401, detail="Could not extract user data")

    async with AsyncSessionLocal() as session:
        user_db = await get_or_create_user(
            session,
            telegram_id=user_info["telegram_id"],
            first_name=user_info["first_name"],
            username=user_info.get("username"),
        )
        await ensure_default_partner_groups(session, user_db.id)
        await session.commit()

    return UserProfile(
        id=user_db.id,
        telegram_id=user_db.telegram_id,
        first_name=user_db.first_name,
        username=user_db.username,
        occupation=user_db.occupation or "employee",
        available_times=user_db.available_times or [],
        daily_minutes=user_db.daily_minutes or 30,
        current_habits=user_db.current_habits or [],
        physical_restrictions=user_db.physical_restrictions,
        streak_days=user_db.streak_days,
        total_seeds=user_db.total_seeds,
        completed_practices=user_db.completed_practices,
        timezone=user_db.timezone or "UTC",
        morning_enabled=bool(user_db.morning_enabled),
        evening_enabled=bool(user_db.evening_enabled),
        current_focus=user_db.current_focus,
        created_at=user_db.created_at,
        updated_at=user_db.updated_at,
        last_onboarding_update=user_db.last_onboarding_update,
    )


@router.get("/me")
async def get_me(user: UserProfile = Depends(get_current_user)):
    """Get current user profile"""
    return user


class UpdateFocusRequest(BaseModel):
    focus: str


@router.patch("/me/focus")
async def update_focus(
    payload: UpdateFocusRequest,
    user: UserProfile = Depends(get_current_user)
):
    """Update user current focus"""
    from app.database import AsyncSessionLocal
    from app.crud import update_user_focus, get_user_by_telegram_id
    
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            raise HTTPException(status_code=404, detail="User not found")
            
        success = await update_user_focus(db, user_db.id, payload.focus)
        
        # Clear today's suggestions so they re-generate with new focus
        from app.crud import clear_today_suggestions
        await clear_today_suggestions(db, user_db.id)
        
        await db.commit()
        
        return {"success": success}


@router.get(
    "/daily/actions",
    summary="Get daily actions",
    description="Retrieve personalized daily actions based on user profile and current focus"
)
async def get_daily_actions(user: UserProfile = Depends(get_current_user)):
    """Get 4 daily actions"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.agents.daily_manager import DailyManagerAgent
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        agent = DailyManagerAgent(qdrant)
        
        # Now passing all needed fields for persistence check
        result = await agent.morning_message(
            user_id=user.id,
            first_name=user.first_name,
            focus=user.current_focus,
            streak_days=user.streak_days,
            total_seeds=user.total_seeds
        )
        actions = result.get("actions", [])
        
        return {"actions": actions}
    except Exception as e:
        logger.error(f"Error getting daily actions: {e}", exc_info=True)
        # Fallback to default actions
        actions = [
            {
                "id": "1",
                "group": "source",
                "partner_name": "Источник",
                "description": "Позвони родителям",
                "why": "Сеешь благодарность → получишь ресурсы",
                "completed": False
            },
            {
                "id": "2",
                "group": "ally",
                "partner_name": "Соратник",
                "description": "Помоги коллеге",
                "why": "Сеешь поддержку → получишь помощь",
                "completed": False
            },
            {
                "id": "3",
                "group": "protege",
                "partner_name": "Подопечный",
                "description": "Научи чему-то",
                "why": "Сеешь знания → получишь авторитет",
                "completed": False
            },
            {
                "id": "4",
                "group": "world",
                "partner_name": "Внешний мир",
                "description": "Пожертвуй 100₽",
                "why": "Сеешь сострадание → получишь гармонию",
                "completed": False
            }
        ]
        return {"actions": actions}


class UpdateActionCompletionRequest(BaseModel):
    completed: bool


@router.patch("/daily/actions/{action_id}")
async def update_action_completion(
    action_id: str,
    payload: UpdateActionCompletionRequest,
    user: UserProfile = Depends(get_current_user)
):
    """Toggle daily action completion"""
    from app.database import AsyncSessionLocal
    from app.crud import update_daily_suggestion_completion
    
    async with AsyncSessionLocal() as db:
        await update_daily_suggestion_completion(db, action_id, payload.completed)
        await db.commit()
        return {"success": True}


@router.get(
    "/quote/daily",
    summary="Get daily quote",
    description="Retrieve a daily quote from the knowledge base relevant to user's current focus"
)
async def get_daily_quote(user: UserProfile = Depends(get_current_user)):
    """Get quote for the day"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        
        # Get quote based on user focus area
        quote = await qdrant.get_daily_quote(user.current_focus)
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
    user: UserProfile = Depends(get_current_user)
):
    """Get user's seeds"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_seeds, get_user_by_telegram_id
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, user.telegram_id)
            
            if not user_db:
                return {"seeds": []}
            
            seeds_db = await get_user_seeds(db, user_db.id, limit)
            
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
    user: UserProfile = Depends(get_current_user)
):
    """Create new seed"""
    from app.database import AsyncSessionLocal
    from app.crud import create_seed, get_user_by_telegram_id, increment_user_seeds_count
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, user.telegram_id)
            if not user_db:
                raise HTTPException(status_code=404, detail="User not found")
            
            seed = Seed(
                user_id=user_db.id,
                action_type=payload.action_type,
                description=payload.description,
                partner_group=payload.partner_group,
                intention_score=payload.intention_score,
                emotion_level=payload.emotion_level,
                understanding=payload.understanding,
                estimated_maturation_days=payload.estimated_maturation_days,
                strength_multiplier=payload.strength_multiplier,
            )
            seed_db = await create_seed(db, seed)
            await increment_user_seeds_count(db, user_db.id)
            await db.commit()
            return SeedCreateResponse(success=True, seed_id=seed_db.id).model_dump()
    except Exception as e:
        logger.error(f"Error creating seed via API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/problems/history")
async def get_problems_history(user: UserProfile = Depends(get_current_user)):
    """Get problem history"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, get_problem_history
    
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            return {"history": []}
        
        history = await get_problem_history(db, user_db.id)
        return {
            "history": [
                {
                    "id": h.id,
                    "problem_text": h.problem_text,
                    "solution": h.solution_json,
                    "is_active": h.is_active,
                    "created_at": h.created_at
                } for h in history
            ]
        }


@router.post("/problems/{history_id}/activate")
async def activate_problem(
    history_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """Make a historical problem active"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, set_active_problem, update_user_focus
    
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            raise HTTPException(status_code=404, detail="User not found")
            
        from app.models.db_models import ProblemHistoryDB
        from sqlalchemy import select
        res = await db.execute(select(ProblemHistoryDB).where(ProblemHistoryDB.id == history_id))
        hist = res.scalar_one_or_none()
        
        if hist:
            await set_active_problem(db, user_db.id, history_id)
            await update_user_focus(db, user_db.id, hist.problem_text)
            await db.commit()
            return {"success": True}
            
        raise HTTPException(status_code=404, detail="History entry not found")


class AddToCalendarRequest(BaseModel):
    steps: list[str]
    start_date: Optional[datetime] = None


@router.post("/problem/add-to-calendar")
async def add_problem_to_calendar(
    payload: AddToCalendarRequest,
    user: UserProfile = Depends(get_current_user)
):
    """Add 30-day plan steps to calendar"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from app.models.db_models import PartnerActionDB
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    import uuid
    
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            raise HTTPException(status_code=404, detail="User not found")

        # Normalize start date to UTC-aware datetime
        if payload.start_date is not None:
            start = payload.start_date
            user_tz = ZoneInfo(user.timezone or "UTC")
            if start.tzinfo is None:
                start = start.replace(tzinfo=user_tz)
            start = start.astimezone(UTC)
        else:
            start = datetime.now(UTC)
        
        actions = []
        for i in range(30):
            step_idx = i % len(payload.steps)
            step_text = payload.steps[step_idx]
            
            action = PartnerActionDB(
                id=str(uuid.uuid4()),
                user_id=user_db.id,
                timestamp=start + timedelta(days=i),
                action=step_text,
                completed=False
            )
            actions.append(action)
            
        db.add_all(actions)
        await db.commit()
        
        return {"success": True, "count": len(actions)}

@router.post("/problem/solve", response_model=ProblemSolveResponse)
async def solve_problem_endpoint(
        payload: ProblemSolveRequest,
        user: UserProfile = Depends(get_current_user)
):
    """Solve problem using AI agent and knowledge base"""
    from app.agents.problem_solver import ProblemSolverAgent
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, save_problem_history

    settings = get_settings()
    qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
    agent = ProblemSolverAgent(qdrant)

    # Determine or create diagnostic session id for web flow
    from uuid import uuid4
    session_id = payload.session_id or f"web_{user.id}_{uuid4().hex[:8]}"

    # Always use diagnostic mode for web problem solving flow
    solution = await agent.analyze_problem(
        user,
        payload.problem,
        session_id=session_id,
        diagnostic_answer=payload.diagnostic_answer,
    )

    # Attach session id so client can continue diagnostic if needed
    solution["session_id"] = session_id

    # Save to history только для финальных решений (без запроса уточнений)
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if user_db and not solution.get("needs_clarification"):
            history_item = await save_problem_history(db, user_db.id, payload.problem, solution)
            solution["history_id"] = history_item.id
            await db.commit()

    return solution


class ProjectActivateRequest(BaseModel):
    history_id: str
    duration_days: int = 30
    project_partners: Optional[dict[str, List[str]]] = None # {category: [partner_ids]}


class ProjectSetupResponse(BaseModel):
    problem: str
    partner_selection_guide: Optional[list[dict]] = None # From AI
    user_partners: dict[str, list[PartnerOut]] = {} # Grouped by universal_category


@router.get("/projects/setup/{history_id}", response_model=ProjectSetupResponse)
async def get_project_setup(
    history_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """Get setup data for a new project (guide + existing partners)"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, get_user_partners, get_partner_groups
    from app.models.db_models import ProblemHistoryDB
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            raise HTTPException(status_code=404, detail="User not found")
            
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
        partners_db = await get_user_partners(db, user_db.id)
        groups_db = await get_partner_groups(db, user_db.id)
        
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
    user: UserProfile = Depends(get_current_user)
):
    """Activate a new Karmic Project (Karma Plan)"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, update_user_focus
    from app.models.db_models import ProblemHistoryDB
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            raise HTTPException(status_code=404, detail="User not found")

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
            user_db.id, 
            payload.history_id, 
            strategy_snapshot, 
            payload.duration_days,
            project_partners=payload.project_partners
        )
        
        # Update user focus
        await update_user_focus(db, user_db.id, hist.problem_text)
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
                "partners": partners_dict
            }
        }


@router.get("/projects/active", response_model=ProjectStatusResponse)
async def get_active_project(user: UserProfile = Depends(get_current_user)):
    """Get current active Karmic Project status"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from datetime import datetime, UTC

    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
             return {"has_active_project": False}
             
        plan = await get_active_karma_plan(db, user_db.id)
        if not plan:
            return {"has_active_project": False}
            
        # Calculate day number
        days_passed = (datetime.now(UTC) - plan.start_date).days + 1
        
        # Get today's daily plan
        daily = await get_daily_plan(db, plan.id, datetime.now(UTC))
        
        daily_data = None
        if daily:
            daily_data = {
                "id": daily.id,
                "day_number": daily.day_number,
                "focus_quality": daily.focus_quality,
                "tasks": daily.tasks,
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
                "partners": partners_dict
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
    user: UserProfile = Depends(get_current_user)
):
    """Complete daily tasks for the project (Coffee Meditation)"""
    from app.database import AsyncSessionLocal
    from app.models.db_models import DailyPlanDB
    from sqlalchemy import select, update
    from datetime import datetime, UTC
    
    async with AsyncSessionLocal() as db:
        active_plan = await get_active_karma_plan(db, user.id) 
        
        if not active_plan or active_plan.id != payload.plan_id:
             raise HTTPException(status_code=404, detail="Active project not found or mismatch")

        daily = await get_daily_plan(db, active_plan.id, datetime.now(UTC))
        
        if not daily:
             raise HTTPException(status_code=404, detail="Daily plan for today not found")
             
        # Update completion
        await db.execute(
            update(DailyPlanDB)
            .where(DailyPlanDB.id == daily.id)
            .values(
                is_completed=True,
                completion_notes=payload.notes,
                updated_at=datetime.now(UTC)
            )
        )
        
        # Also increment seeds/streak for the user
        from app.crud import increment_user_seeds_count
        
        for _ in payload.completed_tasks:
            await increment_user_seeds_count(db, active_plan.user_id)
            
        await db.commit()
        return {"success": True}


@router.get("/partners", response_model=PartnersResponse)
async def get_partners(user: UserProfile = Depends(get_current_user)):
    """Get user's partner groups and partners"""
    from app.database import AsyncSessionLocal
    from app.crud import (
        get_user_by_telegram_id,
        ensure_default_partner_groups,
        get_user_partners,
        get_partner_groups,
    )

    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            return PartnersResponse(groups=[], partners=[]).model_dump()

        await ensure_default_partner_groups(db, user_db.id)
        await db.commit()

        groups_db = await get_partner_groups(db, user_db.id)
        partners_db = await get_user_partners(db, user_db.id)

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
    user: UserProfile = Depends(get_current_user),
):
    """Create new partner"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, ensure_default_partner_groups
    from app.models.db_models import PartnerDB, PartnerGroupDB
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        if not user_db:
            raise HTTPException(status_code=404, detail="User not found")

        await ensure_default_partner_groups(db, user_db.id)

        group_result = await db.execute(
            select(PartnerGroupDB).where(
                PartnerGroupDB.id == payload.group_id,
                PartnerGroupDB.user_id == user_db.id,
            )
        )
        group_db = group_result.scalar_one_or_none()
        if not group_db:
            raise HTTPException(status_code=400, detail="Invalid partner group")

        partner_db = PartnerDB(
            id=str(uuid4()),
            user_id=user_db.id,
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
async def get_practices(user: UserProfile = Depends(get_current_user)):
    """Get available practices"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        practices = await qdrant.search_practice(need="общее развитие", restrictions=None, limit=10)
        return {"practices": practices}
    except Exception as e:
        logger.error(f"Error getting practices: {e}", exc_info=True)
        return {"practices": []}


@router.get("/habits")
async def get_habits(user: UserProfile = Depends(get_current_user)):
    """Get user's habits"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from sqlalchemy import select
    from app.models.db_models import HabitDB
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, user.telegram_id)
            if not user_db:
                return {"habits": []}
            
            result = await db.execute(select(HabitDB).where(HabitDB.user_id == user_db.id))
            habits_db = result.scalars().all()
            habits = [
                {
                    "id": h.id,
                    "practice_id": h.practice_id,
                    "frequency": h.frequency,
                    "preferred_time": h.preferred_time,
                    "duration": h.duration,
                    "is_active": h.is_active,
                }
                for h in habits_db
            ]
            return {"habits": habits}
    except Exception as e:
        logger.error(f"Error getting habits: {e}", exc_info=True)
        return {"habits": []}


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
async def start_onboarding(user: UserProfile = Depends(get_current_user)):
    """Start or resume onboarding flow"""
    from app.workflows.onboarding import get_step_data, ONBOARDING_STEPS, OnboardingSteps
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, user.telegram_id)
        
        # Check if user already completed onboarding
        if user_db and user_db.last_onboarding_update:
            return get_step_data(OnboardingSteps.COMPLETE)
        
        # Check current progress based on filled fields
        # Use sequential checks - stop at first unfinished step
        current_step = OnboardingSteps.OCCUPATION
        if user_db:
            # occupation is "employee" by default, so check if user explicitly set something
            if not user_db.occupation or user_db.occupation == "employee":
                current_step = OnboardingSteps.OCCUPATION
            elif not user_db.available_times or len(user_db.available_times) == 0:
                current_step = OnboardingSteps.SCHEDULE
            elif user_db.daily_minutes == 30:  # default value, not explicitly set
                current_step = OnboardingSteps.DURATION
            elif not user_db.current_habits or len(user_db.current_habits) == 0:
                current_step = OnboardingSteps.HABITS
            elif not user_db.current_focus:
                current_step = OnboardingSteps.FOCUS
            else:
                current_step = OnboardingSteps.PARTNERS
        
        return get_step_data(current_step)


@router.post("/onboarding/answer", response_model=OnboardingStepResponse)
async def answer_onboarding(
    payload: OnboardingAnswerRequest,
    user: UserProfile = Depends(get_current_user)
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
    await save_onboarding_progress(user.telegram_id, payload.step, val)
    
    next_step = get_next_step(payload.step)
    return get_step_data(next_step or OnboardingSteps.COMPLETE)

