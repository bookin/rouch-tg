"""Karmic Project endpoints."""
import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_session,
    get_partner_service,
    get_daily_service,
    PartnerOut,
    ProjectActivateRequest,
    ProjectSetupResponse,
    ProjectStatusResponse,
    DailyCompleteRequest,
)
from app.models.db.user import UserDB
from app.models.db.daily import DailyPlanDB
from app.repositories.karma_plan import KarmaPlanRepository
from app.repositories.problem import ProblemHistoryRepository
from app.services.partner_service import PartnerService
from app.services.daily_service import DailyService

logger = logging.getLogger(__name__)
router = APIRouter()

_karma_plan_repo = KarmaPlanRepository()
_problem_repo = ProblemHistoryRepository()


@router.get("/projects/setup/{history_id}", response_model=ProjectSetupResponse)
async def get_project_setup(
    history_id: str,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    partner_svc: PartnerService = Depends(get_partner_service),
):
    """Get setup data for a new project (guide + existing partners)"""
    hist = await _problem_repo.get(db, history_id)
    if not hist:
        raise HTTPException(status_code=404, detail="History entry not found")

    solution = hist.solution_json
    guide = solution.get("partner_selection_guide")

    if not guide:
        guide = [
            {
                "category": "source",
                "title": "Ваш Источник (Source)",
                "description": "Выберите того, кто дает вам ресурсы, основу и поддержку. Это ваш фундамент.",
                "examples": ["Родители", "Учителя", "Врачи", "Авторы книг"],
            },
            {
                "category": "ally",
                "title": "Ваш Соратник (Ally)",
                "description": "Выберите того, кто находится с вами на одном уровне и идет к общей цели.",
                "examples": ["Супруг(а)", "Близкий друг", "Партнер по бизнесу", "Коллега"],
            },
            {
                "category": "protege",
                "title": "Ваш Подопечный (Protege)",
                "description": "Выберите того, кто зависит от вас и нуждается в вашей помощи.",
                "examples": ["Дети", "Ученики", "Клиенты", "Подчиненные"],
            },
            {
                "category": "world",
                "title": "Внешний мир (World)",
                "description": "Выберите кого-то далекого от вашего круга или даже конкурента.",
                "examples": ["Случайный прохожий", "Конкурент", "Незнакомец", "Общество"],
            },
        ]

    partners_db = await partner_svc.get_partners(db, user.id)
    groups_db = await partner_svc.get_groups(db, user.id)

    group_map = {g.id: g.universal_category or "world" for g in groups_db}

    user_partners: dict[str, list] = {"source": [], "ally": [], "protege": [], "world": []}

    for p in partners_db:
        cat = group_map.get(p.group_id, "world")
        if cat not in user_partners:
            user_partners[cat] = []
        user_partners[cat].append(
            PartnerOut(
                id=p.id,
                name=p.name,
                group_id=p.group_id,
                telegram_username=p.telegram_username,
                phone=p.phone,
                notes=p.notes,
            )
        )

    return {
        "problem": hist.problem_text,
        "partner_selection_guide": guide,
        "user_partners": user_partners,
    }


@router.post("/projects/activate", response_model=ProjectStatusResponse)
async def activate_project(
    payload: ProjectActivateRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Activate a new Karmic Project (Karma Plan)"""
    hist = await _problem_repo.get(db, payload.history_id)
    if not hist:
        raise HTTPException(status_code=404, detail="History entry not found")

    solution = hist.solution_json

    strategy_snapshot = {
        "root_cause": solution.get("root_cause"),
        "stop_action": solution.get("stop_action"),
        "start_action": solution.get("start_action"),
        "grow_action": solution.get("grow_action"),
        "success_tip": solution.get("success_tip"),
        "practice_steps": solution.get("practice_steps", []),
        "problem_text": hist.problem_text,
    }

    plan = await _karma_plan_repo.create_plan(
        db,
        user.id,
        payload.history_id,
        strategy_snapshot,
        payload.duration_days,
        project_partners=payload.project_partners,
        isolation_settings=payload.isolation_settings,
    )

    partners_dict: dict[str, list] = {}
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
        },
    }


@router.get("/projects/active", response_model=ProjectStatusResponse)
async def get_active_project(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    daily_svc: DailyService = Depends(get_daily_service),
):
    """Get current active Karmic Project status"""
    plan = await _karma_plan_repo.get_active(db, user.id)
    if not plan:
        return {"has_active_project": False}

    start = plan.start_date or datetime.now(UTC)
    days_passed = (datetime.now(UTC) - start).days + 1

    daily = await daily_svc.daily_plan_repo.get_by_karma_plan_and_date(
        db, plan.id, datetime.now(UTC)
    )

    daily_data = None
    if daily:
        tasks_data = []
        if daily.tasks:
            sorted_tasks = sorted(daily.tasks, key=lambda t: t.order if t.order is not None else 0)
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
            "id": daily.id,
            "day_number": daily.day_number,
            "focus_quality": daily.focus_quality,
            "tasks": tasks_data,
            "is_completed": daily.is_completed,
        }

    partners_dict: dict[str, list] = {}
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
        "daily_plan": daily_data,
    }


@router.post("/projects/daily/complete")
async def complete_daily_plan(
    payload: DailyCompleteRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    daily_svc: DailyService = Depends(get_daily_service),
):
    """Complete daily tasks for the project (Coffee Meditation)"""
    active_plan = await _karma_plan_repo.get_active(db, user.id)

    if not active_plan or active_plan.id != payload.plan_id:
        raise HTTPException(status_code=404, detail="Active project not found or mismatch")

    daily = await daily_svc.daily_plan_repo.get_by_karma_plan_and_date(
        db, active_plan.id, datetime.now(UTC)
    )

    if not daily:
        raise HTTPException(status_code=404, detail="Daily plan for today not found")

    await db.execute(
        update(DailyPlanDB)
        .where(DailyPlanDB.id == daily.id)
        .values(
            is_completed=True,
            completion_notes=payload.notes,
            updated_at=datetime.now(UTC),
        )
    )

    for task_id_str in payload.completed_tasks:
        if task_id_str.isdigit():
            await daily_svc.toggle_task_completion(
                db,
                user_id=user.id,
                task_id=int(task_id_str),
                completed=True,
            )

    return {"success": True}
