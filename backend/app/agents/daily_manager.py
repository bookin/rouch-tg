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

    async def get_daily_actions(
        self,
        user_id: int,
        first_name: str,
        streak_days: int,
        total_seeds: int,
        regenerate: bool = False,
    ) -> list[dict[str, Any]]:
        """Return daily actions only, without generating a full message.

        Используется там, где фронту или боту нужны только задачи без текста сообщения
        (webapp /daily/actions, команда /today и т.п.).
        """
        from app.database import AsyncSessionLocal
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

                    # Resolve project partners ids/names if they exist
                    project_partners_map = None
                    partner_contact_types_map = None
                    partner_name_by_id = {}

                    if active_plan.partners_association:
                        project_partners_map = {}
                        partner_contact_types_map = {}

                        for assoc in active_plan.partners_association:
                            cat = assoc.category
                            if cat not in project_partners_map:
                                project_partners_map[cat] = {}
                            if assoc.partner:
                                pid = assoc.partner.id
                                pname = assoc.partner.name
                                project_partners_map[cat][pid] = pname
                                partner_name_by_id[pid] = pname
                                partner_contact_types_map[pid] = getattr(
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
                            tasks_data = []
                            for a in project_actions:
                                partner_id = getattr(a, "partner_id", None)

                                # Мягкая валидация: используем только те id, которые реально присутствуют в плане
                                if partner_id and project_partners_map and a.group in project_partners_map:
                                    if partner_id not in project_partners_map[a.group]:
                                        partner_id = None

                                tasks_data.append(
                                    {
                                        "description": a.description,
                                        "group": a.group,
                                        "why": a.why,
                                        "partner_id": partner_id,
                                        "action_type": getattr(a, "action_type", None),
                                    }
                                )
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
                                partner_id = None
                                action_type = None
                                if isinstance(task_data, dict):
                                    why = task_data.get("why")
                                    group = task_data.get("group", "project")
                                    partner_id = task_data.get("partner_id")
                                    action_type = task_data.get("action_type")

                                task = DailyTaskDB(
                                    daily_plan_id=daily_plan.id,
                                    description=description,
                                    why=why,
                                    group=group,
                                    partner_id=partner_id,
                                    action_type=action_type,
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

                        await db.commit()
                        # Refresh to get tasks with IDs
                        await db.refresh(daily_plan)
                        
                        tasks_db = daily_plan.tasks

                    actions = [
                        {
                            "id": str(t.id),
                            "group": t.group or "project",
                            "partner_name": (
                                partner_name_by_id.get(t.partner_id)
                                if getattr(t, "partner_id", None) and partner_name_by_id
                                else self._get_partner_name(t.group or "project")
                            ),
                            "description": t.description,
                            "why": t.why or "Шаг к цели",
                            "completed": t.completed,
                        }
                        for t in tasks_db
                    ]

                    return actions

                # No active Karma Plan → нет задач на день
                return []

        except Exception as e:
            logger.error(f"Error getting daily actions for user {user_id}: {e}", exc_info=True)
            # On error we просто не возвращаем задач, чтобы не плодить "висящие" действия без плана
            return []

    async def morning_message(
        self,
        user_id: int,
        first_name: str,
        streak_days: int,
        total_seeds: int,
        regenerate: bool = False,
        channel: str = "system",
    ) -> Dict[str, Any]:
        """Generate morning message with quote and daily actions.

        Если есть активный Karma Plan (проектный режим):
        - Задачи дня берутся из DailyPlanDB.tasks (создаются/обновляются отдельно).
        - Полный текст сообщения (greeting/motivation/closing + quote + actions) кешируется
          в таблице MessageLogDB (message_type="morning", channel).
        - При повторных вызовах за тот же день по умолчанию читаем из MessageLogDB
          (если regenerate=False), без повторного вызова LLM и Qdrant.

        Если активного плана нет:
        - Не генерируем задачи дня.
        - Отправляем короткое сообщение с подсказкой активировать Кармический Проект
          через раздел «Проблема» в веб‑приложении.
        """
        from app.database import AsyncSessionLocal
        from app.crud import (
            get_latest_message_log,
            create_message_log,
            get_user_practice_progress,
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

                    # Resolve project partners ids/names if they exist
                    project_partners_map = None
                    partner_contact_types_map = None
                    partner_name_by_id = {}

                    if active_plan.partners_association:
                        project_partners_map = {}
                        partner_contact_types_map = {}

                        for assoc in active_plan.partners_association:
                            cat = assoc.category
                            if cat not in project_partners_map:
                                project_partners_map[cat] = {}
                            # assoc.partner is lazy="joined" in model so it should be there
                            if assoc.partner:
                                pid = assoc.partner.id
                                pname = assoc.partner.name
                                project_partners_map[cat][pid] = pname
                                partner_name_by_id[pid] = pname
                                # Collect contact type (default to physical if missing)
                                partner_contact_types_map[pid] = getattr(
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
                            streak_days=streak_days,
                            total_seeds=total_seeds,
                            plan_strategy=plan_strategy,
                            project_partners=project_partners_map,
                            isolation_settings=active_plan.isolation_settings if active_plan else None,
                            partner_contact_types=partner_contact_types_map,
                        )
                        quote_task = self.qdrant.get_daily_quote(None)
                        ai_message, quote = await asyncio.gather(ai_task, quote_task)
                    else:
                        # Need to generate AI message once for this day (и задачи, и текст) + quote в параллели
                        ai_task = generate_morning_message(
                            user_name=first_name,
                            streak_days=streak_days,
                            total_seeds=total_seeds,
                            plan_strategy=plan_strategy,
                            project_partners=project_partners_map,
                            isolation_settings=active_plan.isolation_settings if active_plan else None,
                            partner_contact_types=partner_contact_types_map,
                        )
                        quote_task = self.qdrant.get_daily_quote(None)
                        ai_message, quote = await asyncio.gather(ai_task, quote_task)

                        # Use structured project_actions from AI if available; otherwise fallback to plain strings
                        project_actions = getattr(ai_message, "project_actions", None) or []
                        if project_actions:
                            tasks_data = []
                            for a in project_actions:
                                partner_id = getattr(a, "partner_id", None)

                                # Мягкая валидация: используем только те id, которые реально присутствуют в плане
                                if partner_id and project_partners_map and a.group in project_partners_map:
                                    if partner_id not in project_partners_map[a.group]:
                                        partner_id = None

                                tasks_data.append(
                                    {
                                        "description": a.description,
                                        "group": a.group,
                                        "why": a.why,
                                        "partner_id": partner_id,
                                        "action_type": getattr(a, "action_type", None),
                                    }
                                )
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
                                partner_id = task_data.get("partner_id")
                                action_type = task_data.get("action_type")

                                task = DailyTaskDB(
                                    daily_plan_id=daily_plan.id,
                                    description=description,
                                    why=why,
                                    group=group,
                                    partner_id=partner_id,
                                    action_type=action_type,
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

                        await db.commit()
                        await db.refresh(daily_plan)
                        tasks_db = daily_plan.tasks

                    actions = [
                        {
                            "id": str(t.id),
                            "group": t.group or "project",
                            "partner_name": (
                                partner_name_by_id.get(t.partner_id)
                                if getattr(t, "partner_id", None) and partner_name_by_id
                                else self._get_partner_name(t.group or "project")
                            ),
                            "description": t.description,
                            "why": t.why or "Шаг к цели",
                            "completed": t.completed,
                        }
                        for t in tasks_db
                    ]
                    # Sort by order
                    actions.sort(key=lambda x: x.get("order", 0))

                    # Add practice tracking actions
                    practice_progress_list = await get_user_practice_progress(db, user_id)
                    active_practices = [p for p in practice_progress_list if not p.is_habit]
                    
                    for practice in active_practices[:3]:  # Limit to 3 practices
                        actions.append({
                            "id": f"practice_{practice.practice_id}",
                            "group": "practice",
                            "partner_name": None,
                            "description": f"Практика: {practice.practice.name if practice.practice else 'Unknown'}",
                            "why": f"Прогресс: {practice.habit_score}% • Серия: {practice.streak_days} дней",
                            "completed": False,
                            "order": 100 + len(actions),
                        })

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

                # --- NO ACTIVE PROJECT (classic mode отключён) ---
                # Простой месседж без задач, мягко направляющий пользователя к разбору проблемы в приложении
                message = (
                    f"☀️ Доброе утро, {first_name}!\n\n"
                    "Сейчас у тебя нет активного Кармического Проекта.\n"
                    "Открой приложение, зайди в раздел «Проблема» и спокойно разберись с главной задачей — "
                    "после этого я смогу готовить для тебя конкретный план на день.\n\n"
                    "Пока просто будь внимателен к людям вокруг и посей сегодня несколько добрых семян."
                )

                payload = {
                    "message": message,
                    "quote": None,
                    "actions": [],
                    "time": "morning",
                }

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
            # В случае ошибки не генерируем отдельные задачи, только мягкое текстовое сообщение
            message = (
                f"☀️ Доброе утро, {first_name}!\n\n"
                "Сейчас мне не удалось сформировать подробный утренний план. "
                "Сделай сегодня несколько простых добрых действий и при первой возможности "
                "активируй или пересоздай Кармический Проект в веб‑приложении."
            )
            return {
                "message": message,
                "quote": None,
                "actions": [],
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
