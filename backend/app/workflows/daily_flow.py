"""Daily morning and evening workflows"""
from typing import Dict, Any, List
from app.models.user import UserProfile
from app.knowledge.qdrant import QdrantKnowledgeBase
from app.ai import generate_morning_message, generate_evening_message
from app.database import AsyncSessionLocal
from app.models.db_models import SeedDB, PartnerActionDB
from sqlalchemy import select, func
from datetime import datetime, UTC


class DailyFlowWorkflow:
    """Handles morning and evening workflows"""
    
    def __init__(self, qdrant: QdrantKnowledgeBase):
        self.qdrant = qdrant

    @staticmethod
    def _default_action_templates() -> list[dict[str, str]]:
        """Default 4 groups used across the app."""
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
    
    async def morning_workflow(self, user: UserProfile) -> Dict[str, Any]:
        """Morning workflow: motivation + daily actions"""
        
        # 1. Get quote for the day
        quote = await self.qdrant.get_daily_quote(None)
        
        # 2. Analyze recent progress
        analysis = await self._analyze_progress(user)
        
        # 3. Generate 4 daily actions (simplified fallback or AI)
        actions = await self._generate_daily_actions(user)
        
        # 4. Create message
        message = self._format_morning_message(user, quote, analysis, actions)
        
        return {
            "message": message,
            "quote": quote,
            "actions": actions,
            "time": "morning"
        }
    
    async def evening_workflow(self, user: UserProfile) -> Dict[str, Any]:
        """Evening workflow: reflection + gratitude"""
        
        # 1. Get evening quote
        quote = await self.qdrant.get_daily_quote("reflection")
        
        # 2. Analyze day
        day_summary = await self._analyze_day(user)
        
        # 3. Create message
        message = self._format_evening_message(user, quote, day_summary)
        
        return {
            "message": message,
            "quote": quote,
            "summary": day_summary,
            "time": "evening"
        }
    
    async def _analyze_progress(self, user: UserProfile) -> Dict[str, Any]:
        """Analyze recent progress"""
        return {
            "streak": user.streak_days,
            "seeds_planted": user.total_seeds,
            "win": "Регулярность практик" if user.streak_days > 5 else None
        }
    
    async def _generate_daily_actions(self, user: UserProfile) -> List[Dict[str, str]]:
        """Generate 4 daily actions for partner groups"""
        
        try:
            # Try to use AI first
            ai_message = await generate_morning_message(
                user_name=user.first_name,
                streak_days=user.streak_days,
                total_seeds=user.total_seeds
            )
            
            templates = self._default_action_templates()
            actions: list[dict[str, str]] = []
            for template, action_text in zip(templates, ai_message.actions[:4]):
                actions.append(
                    {
                        **template,
                        "description": action_text,
                        "completed": False,
                    }
                )
            return actions
        except Exception:
            # Fallback to static list if AI fails
            templates = self._default_action_templates()
            descriptions = [
                "Позвони родителям и узнай как дела",
                "Предложи помощь коллеге",
                "Научи кого-то чему-то новому",
                "Пожертвуй 100₽ в благотворительность",
            ]
            return [
                {**template, "description": desc, "completed": False}
                for template, desc in zip(templates, descriptions)
            ]
    
    async def _analyze_day(self, user: UserProfile) -> Dict[str, Any]:
        """Analyze the day from DB"""
        seeds_count = 0
        actions_completed = 0
        
        try:
            async with AsyncSessionLocal() as db:
                today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Count seeds
                seeds_result = await db.execute(
                    select(func.count(SeedDB.id)).where(
                        SeedDB.user_id == user.id,
                        SeedDB.timestamp >= today_start
                    )
                )
                seeds_count = seeds_result.scalar() or 0
                
                # Count completed actions
                actions_result = await db.execute(
                    select(func.count(PartnerActionDB.id)).where(
                        PartnerActionDB.user_id == user.id,
                        PartnerActionDB.timestamp >= today_start,
                        PartnerActionDB.completed == True
                    )
                )
                actions_completed = actions_result.scalar() or 0
                
        except Exception:
            pass
            
        return {
            "mood": "productive" if seeds_count > 0 else "neutral",
            "seeds_count": seeds_count,
            "practices_done": actions_completed
        }
    
    def _format_morning_message(
        self, 
        user: UserProfile, 
        quote: Dict, 
        analysis: Dict, 
        actions: List[Dict]
    ) -> str:
        """Format morning message"""
        
        msg = f"☀️ Доброе утро, {user.first_name}!\n\n"
        
        if analysis.get("streak", 0) > 0:
            msg += f"{analysis['streak']} дней подряд - отличная работа! 👏\n\n"
        
        if analysis.get("win"):
            msg += f"{analysis['win']}\n\n"
        
        msg += f"💭 Цитата на сегодня:\n\"{quote.get('text', '')}\"\n\n"
        
        msg += "🌱 4 действия на день:\n"
        for i, action in enumerate(actions, 1):
            msg += f"{i}. {action['partner_name']}: {action['description']}\n"
        
        msg += "\n[Открыть приложение]"
        
        return msg
    
    def _format_evening_message(
        self, 
        user: UserProfile, 
        quote: Dict, 
        summary: Dict
    ) -> str:
        """Format evening message"""
        
        msg = f"🌙 {user.first_name}, день подходит к концу\n\n"
        
        seeds = summary.get("seeds_count", 0)
        if seeds > 0:
            msg += f"Сегодня ты посеял {seeds} семян - молодец!\n\n"
        
        msg += f"💭 На размышление перед сном:\n\"{quote['text']}\"\n\n"
        
        msg += "Спокойной ночи! 🙏"
        
        return msg
