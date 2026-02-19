"""Daily Manager Agent - communicates with users twice a day"""
from datetime import datetime, UTC
from typing import Dict, Any
import logging
from pydantic import BaseModel
from app.models.user import UserProfile
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
    
    async def morning_message(
        self,
        user_id: int,
        first_name: str,
        focus: str | None,
        streak_days: int,
        total_seeds: int,
    ) -> Dict[str, Any]:
        """Generate morning message with quote and daily actions using AI"""
        from app.database import AsyncSessionLocal
        from app.crud import get_daily_suggestions, save_daily_suggestions, get_user_partners
        from app.crud_extended import get_active_karma_plan, get_daily_plan, create_daily_plan
        
        try:
            async with AsyncSessionLocal() as db:
                # 0. Check for active Karma Plan
                active_plan = await get_active_karma_plan(db, user_id)
                plan_strategy = active_plan.strategy_snapshot if active_plan else None
                
                # Resolve project partners names if they exist
                project_partners_map = None
                if active_plan and active_plan.partners_association:
                    # No need to fetch all users partners, we can get them from association if eager loaded
                    # or just fetch what we need. Since lazy="selectin", they are loaded.
                    # We need partner names.
                    
                    project_partners_map = {}
                    for assoc in active_plan.partners_association:
                        cat = assoc.category
                        if cat not in project_partners_map:
                            project_partners_map[cat] = []
                        # assoc.partner is lazy="joined" in model so it should be there
                        if assoc.partner:
                            project_partners_map[cat].append(assoc.partner.name)

                # 1. Generate AI message
                ai_message = await generate_morning_message(
                    user_name=first_name,
                    focus=focus,
                    streak_days=streak_days,
                    total_seeds=total_seeds,
                    plan_strategy=plan_strategy,
                    project_partners=project_partners_map
                )

                now = datetime.now(UTC)
                actions = []

                if active_plan:
                    # --- PROJECT MODE ---
                    # Check if daily plan exists
                    daily_plan = await get_daily_plan(db, active_plan.id, now)
                    
                    if daily_plan:
                        print(f"📊 Found existing DAILY PLAN for project {active_plan.id}")
                        # Use existing tasks
                        actions = [
                            {
                                "id": f"task_{i}", 
                                "group": "project",
                                "partner_name": "Проект", 
                                "description": task, 
                                "why": "Шаг к цели", 
                                "completed": False
                            }
                            for i, task in enumerate(daily_plan.tasks)
                        ]
                    else:
                        print(f"🪄 Generating NEW DAILY PLAN for project {active_plan.id}")
                        # Use AI generated actions as tasks
                        tasks = ai_message.actions[:3] # Expecting 3 tasks for project
                        
                        # Create DailyPlanDB
                        # Determine day number
                        day_number = (now - active_plan.start_date).days + 1
                        # Determine quality (simple rotation for now, Mon=Giving etc)
                        day_of_week = now.strftime('%A').lower()
                        quality_map = {
                            'monday': 'Giving', 'tuesday': 'Ethics', 'wednesday': 'Patience',
                            'thursday': 'Effort', 'friday': 'Concentration', 'saturday': 'Wisdom',
                            'sunday': 'Compassion'
                        }
                        quality = quality_map.get(day_of_week, 'General')
                        
                        await create_daily_plan(
                            db, active_plan.id, day_number, now, quality, tasks
                        )
                        
                        actions = [
                            {
                                "id": f"task_{i}", 
                                "group": "project",
                                "partner_name": "Проект", 
                                "description": task, 
                                "why": "Шаг к цели", 
                                "completed": False
                            }
                            for i, task in enumerate(tasks)
                        ]
                        
                        # Also save to DailySuggestionDB for backward compatibility / fallback UI
                        to_save = [
                            {"group": "project", "description": t, "why": "Кармический проект"}
                            for t in tasks
                        ]
                        await save_daily_suggestions(db, user_id, to_save)
                        await db.commit()

                else:
                    # --- CLASSIC MODE ---
                    # 1. Try to get from database
                    existing_suggestions = await get_daily_suggestions(db, user_id, now)
                    
                    if existing_suggestions:
                        print(f"📊 Found {len(existing_suggestions)} existing suggestions for user {user_id}")
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
                        # 2. Generate new if not found
                        print(f"🪄 Generating NEW suggestions for user {user_id}")
                        
                        templates = self._action_templates()
                        to_save = []
                        # Take up to 4 actions
                        for template, action_text in zip(templates, ai_message.actions[:4]):
                            to_save.append(
                                {
                                    "group": template["group"],
                                    "description": action_text,
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

            # Get quote from Qdrant
            quote = await self.qdrant.get_daily_quote(focus)

            # Format message
            message = (
                f"{ai_message.greeting}\n\n"
                f"💭 {quote.get('text', '')}\n\n"
                f"{ai_message.motivation}\n\n"
                f"🌱 Твои действия на сегодня:\n"
            )
            
            for i, action in enumerate(actions, 1):
                message += f"{i}. {action['partner_name']}: {action['description']}\n"
            
            message += f"\n{ai_message.closing}"
            
            return {
                "message": message,
                "quote": quote,
                "actions": actions,
                "time": "morning",
            }
            
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
    
    async def evening_message(self, user: UserProfile) -> Dict[str, Any]:
        """Generate evening message using AI"""
        
        try:
            # Get today's activity
            seeds_today = await self._get_today_seeds(user.id)
            actions_completed = await self._get_completed_actions(user.id)
            
            # Generate AI message
            ai_message = await generate_evening_message(
                user_name=user.first_name,
                seeds_today=seeds_today,
                actions_completed=len(actions_completed)
            )
            
            # Get quote
            quote = await self.qdrant.get_daily_quote("reflection")
            
            # Format message
            message = (
                f"{ai_message.greeting}\n\n"
                f"💭 {quote.get('text', '')}\n\n"
                f"{ai_message.motivation}\n\n"
                f"{ai_message.closing}"
            )
            
            return {
                "message": message,
                "quote": quote,
                "summary": {"seeds": seeds_today, "actions": len(actions_completed)},
                "time": "evening"
            }
            
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
