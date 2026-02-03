"""FastAPI endpoints for Mini App"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.user import UserProfile
from app.models.seed import Seed
from uuid import uuid4


router = APIRouter(prefix="/api", tags=["Mini App"])


class PartnerGroupOut(BaseModel):
    id: str
    name: str
    icon: str
    description: str
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


class ProblemSolveResponse(BaseModel):
    problem: str
    root_cause: Optional[str] = None
    opposite_action: Optional[str] = None
    practice_steps: list[str] = []
    expected_outcome: Optional[str] = None
    timeline_days: Optional[int] = None
    correlations: list[dict] = []
    concepts: list[dict] = []


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
    )


@router.get("/me")
async def get_me(user: UserProfile = Depends(get_current_user)):
    """Get current user profile"""
    return user


@router.get(
    "/daily/actions",
    summary="Get daily actions",
    description="Retrieve personalized daily actions based on user profile and current focus"
)
async def get_daily_actions(user: UserProfile = Depends(get_current_user)):
    """Get 4 daily actions"""
    from app.knowledge.qdrant_client import QdrantKnowledgeBase
    from app.agents.daily_manager import DailyManagerAgent
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        agent = DailyManagerAgent(qdrant)
        
        # Generate morning message with actions
        result = await agent.morning_message(user)
        actions = result.get("actions", [])
        
        return {"actions": actions}
        
    except Exception as e:
        # Fallback to default actions
        actions = [
            {
                "id": "1",
                "group": "colleagues",
                "partner_name": "Коллега",
                "description": "Принеси кофе",
                "why": "Сеешь поддержку → получишь помощь",
                "completed": False
            },
            {
                "id": "2",
                "group": "clients",
                "partner_name": "Клиент",
                "description": "Отправь статью",
                "why": "Сеешь знания → получишь лояльность",
                "completed": False
            },
            {
                "id": "3",
                "group": "suppliers",
                "partner_name": "Поставщик",
                "description": "Поблагодари",
                "why": "Сеешь признание → получишь приоритет",
                "completed": False
            },
            {
                "id": "4",
                "group": "world",
                "partner_name": "Мир",
                "description": "Пожертвуй 100₽",
                "why": "Сеешь сострадание → получишь гармонию",
                "completed": False
            }
        ]
        return {"actions": actions}


@router.get(
    "/quote/daily",
    summary="Get daily quote",
    description="Retrieve a daily quote from the knowledge base relevant to user's current focus"
)
async def get_daily_quote(user: UserProfile = Depends(get_current_user)):
    """Get quote for the day"""
    from app.knowledge.qdrant_client import QdrantKnowledgeBase
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        
        # Get quote based on user focus area
        quote = await qdrant.get_daily_quote(user.current_focus)
        return quote
        
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/problem/solve", response_model=ProblemSolveResponse)
async def solve_problem_endpoint(
    payload: ProblemSolveRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Solve user's problem using correlations + AI (fallback to workflow)."""
    from app.config import get_settings
    from app.knowledge.qdrant_client import QdrantKnowledgeBase
    from app.agents.problem_solver import ProblemSolverAgent

    settings = get_settings()
    qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
    agent = ProblemSolverAgent(qdrant)

    result = await agent.analyze_problem(user, payload.problem)

    # Normalize output for frontend
    return ProblemSolveResponse(
        problem=payload.problem,
        root_cause=result.get("root_cause"),
        opposite_action=result.get("opposite_action"),
        practice_steps=result.get("practice_steps") or [],
        expected_outcome=result.get("expected_outcome"),
        timeline_days=result.get("timeline_days"),
        correlations=result.get("correlations") or [],
        concepts=result.get("related_concepts") or result.get("concepts") or [],
    ).model_dump()

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
    from app.knowledge.qdrant_client import QdrantKnowledgeBase
    from app.config import get_settings
    
    try:
        settings = get_settings()
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        practices = await qdrant.search_practice(need="общее развитие", restrictions=None, limit=10)
        return {"practices": practices}
    except Exception:
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
    except Exception:
        return {"habits": []}
