"""Quote Provider Agent"""
from typing import Dict, Any, Optional
from app.knowledge.qdrant import QdrantKnowledgeBase


class QuoteProvider:
    """Provides relevant quotes for different situations"""
    
    def __init__(self, qdrant: QdrantKnowledgeBase):
        self.qdrant = qdrant
    
    async def get_quote(
        self, 
        context: Optional[str] = None,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """Get relevant quote"""
        
        quote = await self.qdrant.get_daily_quote(context)
        
        return quote
    
    async def get_motivational_quote(self) -> Dict[str, Any]:
        """Get motivational quote for the day"""
        return await self.get_quote(context="motivation success")
    
    async def get_reflection_quote(self) -> Dict[str, Any]:
        """Get quote for evening reflection"""
        return await self.get_quote(context="reflection wisdom life")
    
    async def get_problem_quote(self, problem_area: str) -> Dict[str, Any]:
        """Get quote related to specific problem area"""
        return await self.get_quote(context=problem_area)
