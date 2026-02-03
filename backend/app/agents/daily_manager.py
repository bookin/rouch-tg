"""Daily Manager Agent - communicates with users twice a day"""
from typing import Dict, Any
from pydantic import BaseModel
from app.models.user import UserProfile
from app.knowledge.qdrant_client import QdrantKnowledgeBase
from app.workflows.daily_flow import DailyFlowWorkflow
from app.ai.groq_agent import generate_morning_message, generate_evening_message


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
                "id": "colleagues",
                "group": "colleagues",
                "partner_name": "Коллега",
                "why": "Сеешь поддержку → получишь помощь",
            },
            {
                "id": "clients",
                "group": "clients",
                "partner_name": "Клиент",
                "why": "Сеешь знания → получишь лояльность",
            },
            {
                "id": "suppliers",
                "group": "suppliers",
                "partner_name": "Поставщик",
                "why": "Сеешь признание → получишь приоритет",
            },
            {
                "id": "world",
                "group": "world",
                "partner_name": "Мир",
                "why": "Сеешь сострадание → получишь гармонию",
            },
        ]
    
    async def morning_message(self, user: UserProfile) -> Dict[str, Any]:
        """Generate morning message with quote and daily actions using AI"""
        
        try:
            # Generate AI message
            ai_message = await generate_morning_message(
                user_name=user.first_name,
                focus=user.current_focus,
                streak_days=user.streak_days,
                total_seeds=user.total_seeds
            )
            
            # Get quote from Qdrant
            quote = await self.qdrant.get_daily_quote(user.current_focus)

            templates = self._action_templates()
            actions: list[dict[str, Any]] = []
            for template, action_text in zip(templates, ai_message.actions[:4]):
                actions.append(
                    {
                        **template,
                        "description": action_text,
                        "completed": False,
                    }
                )
            
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
                "time": "morning"
            }
            
        except Exception as e:
            # Fallback to workflow if AI fails
            result = await self.daily_flow.morning_workflow(user)
            return {
                "message": result["message"],
                "quote": result["quote"],
                "actions": result["actions"],
                "time": "morning"
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
            # Fallback
            result = await self.daily_flow.evening_workflow(user)
            return {
                "message": result["message"],
                "quote": result["quote"],
                "summary": result["summary"],
                "time": "evening"
            }
    
    async def _get_today_seeds(self, user_id: int) -> int:
        """Get count of seeds planted today"""
        from app.database import AsyncSessionLocal
        from app.models.db_models import SeedDB
        from sqlalchemy import select, func
        from datetime import datetime
        
        try:
            async with AsyncSessionLocal() as db:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                result = await db.execute(
                    select(func.count(SeedDB.id)).where(
                        SeedDB.user_id == user_id,
                        SeedDB.timestamp >= today_start
                    )
                )
                return result.scalar() or 0
        except Exception:
            return 0
    
    async def _get_completed_actions(self, user_id: int) -> list:
        """Get completed actions for today"""
        from app.database import AsyncSessionLocal
        from app.models.db_models import PartnerActionDB
        from sqlalchemy import select
        from datetime import datetime
        
        try:
            async with AsyncSessionLocal() as db:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                result = await db.execute(
                    select(PartnerActionDB).where(
                        PartnerActionDB.user_id == user_id,
                        PartnerActionDB.timestamp >= today_start,
                        PartnerActionDB.completed == True
                    )
                )
                return result.scalars().all()
        except Exception:
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
    
    def _get_encouragement(self, mood: str, seeds_count: int) -> str:
        """Get appropriate encouragement based on mood"""
        
        if mood == "productive":
            return "Отличный день! Продолжай в том же духе."
        elif mood == "neutral":
            return "Хороший прогресс. Завтра можем сделать ещё больше?"
        else:
            return "Не всегда всё получается идеально. Завтра новый день - новые возможности!"
