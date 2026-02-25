"""Daily Manager Agent - communicates with users twice a day"""
from datetime import datetime, UTC
from typing import Dict, Any
import logging
import asyncio
from pydantic import BaseModel
from app.models.user import UserProfile
from app.models.db_models import DailyTaskDB
from app.knowledge.qdrant import QdrantKnowledgeBase
from app.workflows.daily_flow import DailyFlowWorkflow
from app.ai import generate_morning_message, generate_evening_message


logger = logging.getLogger(__name__)


class ManagerPersonality(BaseModel):
    """Personality settings for the manager"""
    tone: str = "wise_supportive"  # мудрый, поддерживающий
    formality: str = "friendly"     # дружелюбный, на "ты"
    humor_level: float = 0.3        # немного юмора
    strictness: float = 0.5         # средняя строгость


class DailyManagerAgent:
    """
    Karmic manager that communicates twice a day:
    - Morning (7:00-9:00): motivation + daily plan
    - Evening (21:00-22:00): reflection + gratitude
    """
    
    def __init__(
        self, 
        qdrant: QdrantKnowledgeBase,
        personality: ManagerPersonality = None
    ):
        self.qdrant = qdrant
        self.personality = personality or ManagerPersonality()
        self.daily_flow = DailyFlowWorkflow(qdrant)

    @staticmethod
    def _action_templates() -> list[dict[str, str]]:
        return [
            {
                "id": "source",
                "group": "source",
                "partner_name": "Источник",
                "why": "Сеешь благодарность → получишь ресурсы",
            },
            {
                "id": "ally",
                "group": "ally",
                "partner_name": "Соратник",
                "why": "Сеешь поддержку → получишь помощь",
            },
            {
                "id": "protege",
                "group": "protege",
                "partner_name": "Подопечный",
                "why": "Сеешь заботу → получишь рост",
            },
            {
                "id": "world",
                "group": "world",
                "partner_name": "Внешний мир",
                "why": "Сеешь сострадание → получишь гармонию",
            },
        ]

    @staticmethod
    def _infer_task_group(description: str, project_partners_map: dict[str, list[str]] | None) -> str:
        """Infer project task group (source/ally/protege/world/project) from description and partners map."""
        if not project_partners_map:
            return "project"

        text = description.lower()
        for category, names in project_partners_map.items():
            for name in names:
                if name.lower() in text:
                    return category
        return "project"

    @staticmethod
    def _build_project_tasks_data(
        actions: list[str],
        project_partners_map: dict[str, list[str]] | None,
    ) -> list[dict[str, str]]:
        """Convert raw AI actions to structured project tasks with group/why filled."""
        tasks: list[dict[str, str]] = []
        for text in actions:
            group = DailyManagerAgent._infer_task_group(text, project_partners_map)
            tasks.append(
                {
                    "description": text,
                    "group": group,
                    "why": "Кармический проект",
                }
            )
        return tasks

    async def get_daily_actions(
        self,
        user_id: int,
        first_name: str,
        focus: str | None,
        streak_days: int,
        total_seeds: int,
        regenerate: bool = False,
    ) -> list[dict[str, Any]]:
        """Return daily actions only, without generating a full message.

        Используется там, где фронту или боту нужны только задачи без текста сообщения
        (webapp /daily/actions, команда /today и т.п.).
        """
        from app.database import AsyncSessionLocal
        from app.crud import get_daily_suggestions, save_daily_suggestions
        from app.crud_extended import get_active_karma_plan, get_daily_plan, create_daily_plan

        try:
            async with AsyncSessionLocal() as db:
                now = datetime.now(UTC)
                actions: list[dict[str, Any]] = []

                # 0. Check for active Karma Plan
                active_plan = await get_active_karma_plan(db, user_id)

                if active_plan:
                    # --- PROJECT MODE ---
                    plan_strategy = active_plan.strategy_snapshot

                    # Resolve project partners names if they exist
                    project_partners_map = None
                    partner_contact_types_map = None

                    if active_plan.partners_association:
                        project_partners_map = {}
                        partner_contact_types_map = {}

                        for assoc in active_plan.partners_association:
                            cat = assoc.category
                            if cat not in project_partners_map:
                                project_partners_map[cat] = []
                            if assoc.partner:
                                project_partners_map[cat].append(assoc.partner.name)
                                partner_contact_types_map[assoc.partner.name] = getattr(
                                    assoc.partner,
                                    "contact_type",
                                    "physical",
                                ) or "physical"

                    # Try to get today's daily plan
                    daily_plan = await get_daily_plan(db, active_plan.id, now)

                    if daily_plan and daily_plan.tasks and not regenerate:
                        # Tasks already exist for today – utilize DailyTaskDB objects
                        # Convert DB objects to simple strings for local processing if needed, 
                        # but for actions construction we use IDs
                        tasks_db = daily_plan.tasks # List[DailyTaskDB]
                        
                        actions = [
                            {
                                "id": str(t.id), # Return ID as string for consistency
                                "group": t.group or "project",
                                "partner_name": "Проект",
                                "description": t.description,
                                "why": t.why or "Шаг к цели",
                                "completed": t.completed,
                            }
                            for t in tasks_db
                        ]
                        # Sort by order if available
                        actions.sort(key=lambda x: x.get("order", 0))
                        
                        return actions

                    else:
                        # Need to generate AI message once for this day to get tasks
                        ai_message = await generate_morning_message(
                            user_name=first_name,
                            focus=focus,
                            streak_days=streak_days,
                            total_seeds=total_seeds,
                            plan_strategy=plan_strategy,
                            project_partners=project_partners_map,
                            isolation_settings=active_plan.isolation_settings if active_plan else None,
                            partner_contact_types=partner_contact_types_map,
                        )
                        # Prefer structured project_actions from AI; fallback to legacy string actions
                        project_actions = getattr(ai_message, "project_actions", None) or []
                        if project_actions:
                            tasks_data = [
                                {
                                    "description": a.description,
                                    "group": a.group,
                                    "why": a.why,
                                }
                                for a in project_actions
                            ]
                        else:
                            raw_tasks = ai_message.actions  # Expecting 3 tasks for project
                            tasks_data = [
                                {
                                    "description": text,
                                    "group": "project",
                                    "why": "Кармический проект",
                                }
                                for text in raw_tasks
                            ]

                        # Determine day number & quality
                        day_number = (now - active_plan.start_date).days + 1
                        day_of_week = now.strftime("%A").lower()
                        quality_map = {
                            "monday": "Giving",
                            "tuesday": "Ethics",
                            "wednesday": "Patience",
                            "thursday": "Effort",
                            "friday": "Concentration",
                            "saturday": "Wisdom",
                            "sunday": "Compassion",
                        }
                        quality = quality_map.get(day_of_week, "General")

                        if daily_plan:
                            # Plan exists but has no tasks yet (e.g. after migration) – create tasks for it
                            for i, task_data in enumerate(tasks_data):
                                description = (
                                    task_data
                                    if isinstance(task_data, str)
                                    else task_data.get("description", "")
                                )
                                why = None
                                group = "project"
                                if isinstance(task_data, dict):
                                    why = task_data.get("why")
                                    group = task_data.get("group", "project")

                                task = DailyTaskDB(
                                    daily_plan_id=daily_plan.id,
                                    description=description,
                                    why=why,
                                    group=group,
                                    order=i,
                                )
                                db.add(task)
                        else:
                            # Create new plan with tasks
                            daily_plan = await create_daily_plan(
                                db,
                                active_plan.id,
                                day_number,
                                now,
                                quality,
                                tasks_data,
                            )

                            # Also save to DailySuggestionDB for backward compatibility / fallback UI
                            to_save = [
                                {
                                    "group": (t.get("group") or "project"),
                                    "description": t.get("description", ""),
                                    "why": t.get("why") or "Кармический проект",
                                }
                                for t in tasks_data
                            ]
                            await save_daily_suggestions(db, user_id, to_save)

                        await db.commit()
                        # Refresh to get tasks with IDs
                        await db.refresh(daily_plan)
                        
                        tasks_db = daily_plan.tasks

                    actions = [
                        {
                            "id": str(t.id),
                            "group": t.group or "project",
                            "partner_name": "Проект",
                            "description": t.description,
                            "why": t.why or "Шаг к цели",
                            "completed": t.completed,
                        }
                        for t in tasks_db
                    ]

                    return actions

                # --- CLASSIC MODE (no active project) ---
                existing_suggestions = await get_daily_suggestions(db, user_id, now)

                if existing_suggestions:
                    actions = [
                        {
                            "id": s.id,
                            "group": s.group,
                            "partner_name": self._get_partner_name(s.group),
                            "description": s.description,
                            "why": s.why,
                            "completed": s.completed,
                        }
                        for s in existing_suggestions
                    ]
                else:
                    # Static suggestions without LLM/Qdrant, но сохраняем в БД
                    templates = self._action_templates()
                    descriptions = [
                        "Позвони родителям и узнай как дела",
                        "Предложи помощь коллеге",
                        "Научи кого-то чему-то новому",
                        "Пожертвуй 100₽ в благотворительность",
                    ]
                    to_save = []
                    # Take up to 4 actions
                    for template, desc in zip(templates, descriptions):
                        to_save.append(
                            {
                                "group": template["group"],
                                "description": desc,
                                "why": template["why"],
                            }
                        )

                    saved_objs = await save_daily_suggestions(db, user_id, to_save)
                    await db.commit()

                    actions = [
                        {
                            "id": s.id,
                            "group": s.group,
                            "partner_name": self._get_partner_name(s.group),
                            "description": s.description,
                            "why": s.why,
                            "completed": s.completed,
                        }
                        for s in saved_objs
                    ]

                return actions

        except Exception as e:
            logger.error(f"Error getting daily actions for user {user_id}: {e}", exc_info=True)

            # Very simple fully static fallback (no DB, no external calls)
            templates = self._action_templates()
            descriptions = [
                "Позвони родителям и узнай как дела",
                "Предложи помощь коллеге",
                "Научи кого-то чему-то новому",
                "Пожертвуй 100₽ в благотворительность",
            ]
            actions = [
                {
                    "id": template["id"],
                    "group": template["group"],
                    "partner_name": template["partner_name"],
                    "description": desc,
                    "why": template["why"],
                    "completed": False,
                }
                for template, desc in zip(templates, descriptions)
            ]
            return actions

    async def morning_message(
        self,
        user_id: int,
        first_name: str,
        focus: str | None,
        streak_days: int,
        total_seeds: int,
        regenerate: bool = False,
        channel: str = "system",
    ) -> Dict[str, Any]:
        """Generate morning message with quote and daily actions.

        Project mode (есть активный Karma Plan):
        - Задачи дня берутся из DailyPlanDB.tasks (создаются/обновляются отдельно).
        - Полный текст сообщения (greeting/motivation/closing + quote + actions) кешируется
          в таблице MessageLogDB (message_type="morning", channel).
        - При повторных вызовах за тот же день по умолчанию читаем из MessageLogDB
          (если regenerate=False), без повторного вызова LLM и Qdrant.

        Classic mode (нет активного Karma Plan):
        - Не вызываем LLM и внешние сервисы, генерим простой статический текст + базовые действия.
        - Результат также логируется в MessageLogDB и может переиспользоваться в течение дня.
        """
        from app.database import AsyncSessionLocal
        from app.crud import (
            get_daily_suggestions,
            save_daily_suggestions,
            get_latest_message_log,
            create_message_log,
        )
        from app.crud_extended import get_active_karma_plan, get_daily_plan, create_daily_plan
        
        try:
            async with AsyncSessionLocal() as db:
                now = datetime.now(UTC)
                actions: list[dict[str, Any]] = []

                # 0. Check for active Karma Plan
                active_plan = await get_active_karma_plan(db, user_id)

                if active_plan:
                    # --- PROJECT MODE ---
                    plan_strategy = active_plan.strategy_snapshot

                    # Resolve project partners names if they exist
                    project_partners_map = None
                    partner_contact_types_map = None
                    
                    if active_plan.partners_association:
                        project_partners_map = {}
                        partner_contact_types_map = {}
                        
                        for assoc in active_plan.partners_association:
                            cat = assoc.category
                            if cat not in project_partners_map:
                                project_partners_map[cat] = []
                            # assoc.partner is lazy="joined" in model so it should be there
                            if assoc.partner:
                                project_partners_map[cat].append(assoc.partner.name)
                                # Collect contact type (default to physical if missing)
                                partner_contact_types_map[assoc.partner.name] = getattr(
                                    assoc.partner,
                                    "contact_type",
                                    "physical",
                                ) or "physical"

                    # First, try to reuse cached message from MessageLogDB
                    if not regenerate:
                        cached = await get_latest_message_log(
                            db,
                            user_id=user_id,
                            message_type="morning",
                            channel=channel,
                            date=now,
                            karma_plan_id=active_plan.id,
                        )
                        if cached and cached.payload:
                            return cached.payload

                    # Prepare tasks: reuse existing daily plan tasks or generate new ones
                    daily_plan = await get_daily_plan(db, active_plan.id, now)

                    if daily_plan and daily_plan.tasks:
                        # Tasks already exist for today – just reuse them and generate text/quote
                        tasks_db = daily_plan.tasks  # List[DailyTaskDB]

                        ai_task = generate_morning_message(
                            user_name=first_name,
                            focus=focus,
                            streak_days=streak_days,
                            total_seeds=total_seeds,
                            plan_strategy=plan_strategy,
                            project_partners=project_partners_map,
                            isolation_settings=active_plan.isolation_settings if active_plan else None,
                            partner_contact_types=partner_contact_types_map,
                        )
                        quote_task = self.qdrant.get_daily_quote(focus)
                        ai_message, quote = await asyncio.gather(ai_task, quote_task)
                    else:
                        # Need to generate AI message once for this day (и задачи, и текст) + quote в параллели
                        ai_task = generate_morning_message(
                            user_name=first_name,
                            focus=focus,
                            streak_days=streak_days,
                            total_seeds=total_seeds,
                            plan_strategy=plan_strategy,
                            project_partners=project_partners_map,
                            isolation_settings=active_plan.isolation_settings if active_plan else None,
                            partner_contact_types=partner_contact_types_map,
                        )
                        quote_task = self.qdrant.get_daily_quote(focus)
                        ai_message, quote = await asyncio.gather(ai_task, quote_task)

                        # Use structured project_actions from AI if available; otherwise fallback to plain strings
                        project_actions = getattr(ai_message, "project_actions", None) or []
                        if project_actions:
                            tasks_data = [
                                {
                                    "description": a.description,
                                    "group": a.group,
                                    "why": a.why,
                                }
                                for a in project_actions
                            ]
                        else:
                            raw_tasks = ai_message.actions
                            tasks_data = [
                                {
                                    "description": text,
                                    "group": "project",
                                    "why": "Кармический проект",
                                }
                                for text in raw_tasks
                            ]

                        # Determine day number & quality
                        day_number = (now - active_plan.start_date).days + 1
                        day_of_week = now.strftime("%A").lower()
                        quality_map = {
                            "monday": "Giving",
                            "tuesday": "Ethics",
                            "wednesday": "Patience",
                            "thursday": "Effort",
                            "friday": "Concentration",
                            "saturday": "Wisdom",
                            "sunday": "Compassion",
                        }
                        quality = quality_map.get(day_of_week, "General")

                        if daily_plan:
                            # Plan exists but has no tasks yet (e.g. after migration) – create tasks for it
                            for i, task_data in enumerate(tasks_data):
                                description = task_data.get("description", "")
                                group = task_data.get("group", "project")
                                why = task_data.get("why")

                                task = DailyTaskDB(
                                    daily_plan_id=daily_plan.id,
                                    description=description,
                                    why=why,
                                    group=group,
                                    order=i,
                                )
                                db.add(task)
                        else:
                            daily_plan = await create_daily_plan(
                                db,
                                active_plan.id,
                                day_number,
                                now,
                                quality,
                                tasks_data,
                            )

                            # Also save to DailySuggestionDB for backward compatibility / fallback UI
                            to_save = [
                                {
                                    "group": (t.get("group") or "project"),
                                    "description": t.get("description", ""),
                                    "why": t.get("why") or "Кармический проект",
                                }
                                for t in tasks_data
                            ]
                            await save_daily_suggestions(db, user_id, to_save)

                        await db.commit()
                        await db.refresh(daily_plan)
                        tasks_db = daily_plan.tasks

                    actions = [
                        {
                            "id": str(t.id),
                            "group": t.group or "project",
                            "partner_name": "Проект",
                            "description": t.description,
                            "why": t.why or "Шаг к цели",
                            "completed": t.completed,
                        }
                        for t in tasks_db
                    ]
                    # Sort by order
                    actions.sort(key=lambda x: x.get("order", 0))

                    greeting = ai_message.greeting
                    motivation = ai_message.motivation
                    closing = ai_message.closing

                    # Format message for project mode
                    message = (
                        f"{greeting}\n\n"
                        f"💭 {quote.get('text', '')}\n\n"
                        f"{motivation}\n\n"
                        f"🌱 Твои действия на сегодня:\n"
                    )
                    
                    for i, action in enumerate(actions, 1):
                        message += f"{i}. {action['partner_name']}: {action['description']}\n"
                    
                    message += f"\n{closing}"

                    payload = {
                        "message": message,
                        "quote": quote,
                        "actions": actions,
                        "time": "morning",
                    }

                    # Log message for caching/analytics
                    await create_message_log(
                        db,
                        user_id=user_id,
                        message_type="morning",
                        channel=channel,
                        payload=payload,
                        karma_plan_id=active_plan.id,
                        daily_plan_id=daily_plan.id if daily_plan else None,
                        sent_at=now,
                    )
                    await db.commit()

                    return payload

                # --- CLASSIC MODE (no active project) ---
                # Try cache first (per-day per-channel)
                if not regenerate:
                    cached = await get_latest_message_log(
                        db,
                        user_id=user_id,
                        message_type="morning",
                        channel=channel,
                        date=now,
                        karma_plan_id=None,
                    )
                    if cached and cached.payload:
                        return cached.payload

                existing_suggestions = await get_daily_suggestions(db, user_id, now)

                if existing_suggestions:
                    actions = [
                        {
                            "id": s.id,
                            "group": s.group,
                            "partner_name": self._get_partner_name(s.group),
                            "description": s.description,
                            "why": s.why,
                            "completed": s.completed,
                        }
                        for s in existing_suggestions
                    ]
                else:
                    # Generate static suggestions without LLM, but persist for completion tracking
                    templates = self._action_templates()
                    descriptions = [
                        "Позвони родителям и узнай как дела",
                        "Предложи помощь коллеге",
                        "Научи кого-то чему-то новому",
                        "Пожертвуй 100₽ в благотворительность",
                    ]
                    to_save = []
                    # Take up to 4 actions
                    for template, desc in zip(templates, descriptions):
                        to_save.append(
                            {
                                "group": template["group"],
                                "description": desc,
                                "why": template["why"],
                            }
                        )
                    
                    saved_objs = await save_daily_suggestions(db, user_id, to_save)
                    await db.commit()
                    
                    actions = [
                        {
                            "id": s.id,
                            "group": s.group,
                            "partner_name": self._get_partner_name(s.group),
                            "description": s.description,
                            "why": s.why,
                            "completed": s.completed,
                        }
                        for s in saved_objs
                    ]

                # Simple stub message for users without active project (no LLM, no external services)
                message = (
                    f"☀️ Доброе утро, {first_name}!\n\n"
                    "Сейчас у тебя нет активного Кармического Проекта.\n"
                    "Зайди в приложение, реши главную задачу и активируй проект — тогда я буду присылать точный план на день.\n\n"
                    "А пока вот базовые добрые действия на сегодня:\n"
                )
                for i, action in enumerate(actions, 1):
                    message += f"{i}. {action['partner_name']}: {action['description']}\n"
                message += "\nХорошего дня! 🌱"

                payload = {
                    "message": message,
                    "quote": None,
                    "actions": actions,
                    "time": "morning",
                }

                # Log classic stub as well (для единой аналитики/кеша)
                await create_message_log(
                    db,
                    user_id=user_id,
                    message_type="morning",
                    channel=channel,
                    payload=payload,
                    karma_plan_id=None,
                    daily_plan_id=None,
                    sent_at=now,
                )
                await db.commit()

                return payload
            
        except Exception as e:
            logger.error(f"Error generating morning message for user {user_id}: {e}", exc_info=True)
            # Fallback to workflow if AI fails
            user = UserProfile(
                id=user_id,
                telegram_id=0,
                first_name=first_name,
                current_focus=focus,
                streak_days=streak_days,
                total_seeds=total_seeds,
            )
            result = await self.daily_flow.morning_workflow(user)
            return {
                "message": result["message"],
                "quote": result["quote"],
                "actions": result["actions"],
                "time": "morning",
            }
    
    async def evening_message(
        self,
        user: UserProfile,
        regenerate: bool = False,
        channel: str = "system",
    ) -> Dict[str, Any]:
        """Generate evening message using AI"""
        
        from app.database import AsyncSessionLocal
        from app.crud import get_latest_message_log, create_message_log

        try:
            now = datetime.now(UTC)

            # Try cache first
            async with AsyncSessionLocal() as db:
                if not regenerate:
                    cached = await get_latest_message_log(
                        db,
                        user_id=user.id,
                        message_type="evening",
                        channel=channel,
                        date=now,
                        karma_plan_id=None,
                    )
                    if cached and cached.payload:
                        return cached.payload

            # Get today's activity
            seeds_today = await self._get_today_seeds(user.id)
            actions_completed = await self._get_completed_actions(user.id)
            
            # Generate AI message and quote in parallel
            ai_task = generate_evening_message(
                user_name=user.first_name,
                seeds_today=seeds_today,
                actions_completed=len(actions_completed),
            )
            quote_task = self.qdrant.get_daily_quote("reflection")

            ai_message, quote = await asyncio.gather(ai_task, quote_task)
            
            # Format message
            message = (
                f"{ai_message.greeting}\n\n"
                f"💭 {quote.get('text', '')}\n\n"
                f"{ai_message.motivation}\n\n"
                f"{ai_message.closing}"
            )

            payload = {
                "message": message,
                "quote": quote,
                "summary": {"seeds": seeds_today, "actions": len(actions_completed)},
                "time": "evening",
            }

            # Log message for caching/analytics
            async with AsyncSessionLocal() as db:
                await create_message_log(
                    db,
                    user_id=user.id,
                    message_type="evening",
                    channel=channel,
                    payload=payload,
                    karma_plan_id=None,
                    daily_plan_id=None,
                    sent_at=now,
                )
                await db.commit()

            return payload
            
        except Exception as e:
            logger.error(f"Error generating evening message for user {user.id}: {e}", exc_info=True)
            # Fallback
            result = await self.daily_flow.evening_workflow(user)
            return {
                "message": result["message"],
                "quote": result["quote"],
                "summary": result["summary"],
                "time": "evening"
            }
    
    async def _get_today_seeds(self, user_id: int) -> int:
        """Get count of seeds planted today (UTC-based day)."""
        from app.database import AsyncSessionLocal
        from app.models.db_models import SeedDB
        from sqlalchemy import select, func

        try:
            async with AsyncSessionLocal() as db:
                today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                result = await db.execute(
                    select(func.count(SeedDB.id)).where(
                        SeedDB.user_id == user_id,
                        SeedDB.timestamp >= today_start,
                    )
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting today's seeds for user {user_id}: {e}", exc_info=True)
            return 0
    
    async def _get_completed_actions(self, user_id: int) -> list:
        """Get completed actions for today (UTC-based day)."""
        from app.database import AsyncSessionLocal
        from app.models.db_models import PartnerActionDB
        from sqlalchemy import select

        try:
            async with AsyncSessionLocal() as db:
                today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                result = await db.execute(
                    select(PartnerActionDB).where(
                        PartnerActionDB.user_id == user_id,
                        PartnerActionDB.timestamp >= today_start,
                        PartnerActionDB.completed == True,
                    )
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting completed actions for user {user_id}: {e}", exc_info=True)
            return []
    
    async def _analyze_recent_progress(self, user: UserProfile) -> Dict[str, Any]:
        """Analyze user's recent progress"""
        
        analysis = {
            "streak": user.streak_days,
            "total_seeds": user.total_seeds,
            "completed_practices": user.completed_practices
        }
        
        # Determine recent win
        if user.streak_days >= 7:
            analysis["win"] = f"Неделя подряд - ты молодец!"
        elif user.total_seeds > 10:
            analysis["win"] = f"Уже {user.total_seeds} семян посеяно!"
        
        return analysis
    
    async def _analyze_day(self, user: UserProfile) -> Dict[str, Any]:
        """Analyze the user's day"""
        seeds_today = await self._get_today_seeds(user.id)
        actions_completed = await self._get_completed_actions(user.id)
        
        # Determine mood based on activity
        if seeds_today >= 3 and len(actions_completed) >= 3:
            mood = "productive"
        elif seeds_today >= 1 or len(actions_completed) >= 1:
            mood = "neutral"
        else:
            mood = "struggling"
        
        return {
            "mood": mood,
            "seeds_count": seeds_today,
            "actions_completed": len(actions_completed),
            "message": self._get_encouragement(mood, seeds_today)
        }
    
    def _get_partner_name(self, group: str) -> str:
        """Helper to get display name for group"""
        names = {
            # New Universal Categories
            "source": "Источник",
            "ally": "Соратник",
            "protege": "Подопечный",
            "world": "Внешний мир",
            # Legacy support
            "colleagues": "Коллега",
            "clients": "Клиент",
            "suppliers": "Поставщик",
        }
        return names.get(group, "Партнер")

    def _get_encouragement(self, mood: str, seeds_count: int) -> str:
        """Get appropriate encouragement based on mood"""
        
        if mood == "productive":
            return "Отличный день! Продолжай в том же духе."
        elif mood == "neutral":
            return "Хороший прогресс. Завтра можем сделать ещё больше?"
        else:
            return "Не всегда всё получается идеально. Завтра новый день - новые возможности!"
