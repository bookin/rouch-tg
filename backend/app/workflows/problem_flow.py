"""Problem solver workflow"""
from typing import Dict, Any, List
from app.knowledge.qdrant_client import QdrantKnowledgeBase
from app.models.user import UserProfile


class ProblemSolverWorkflow:
    """Solves user problems using correlations from knowledge base"""
    
    def __init__(self, qdrant: QdrantKnowledgeBase):
        self.qdrant = qdrant
    
    async def solve_problem(
        self, 
        user: UserProfile, 
        problem_description: str
    ) -> Dict[str, Any]:
        """Analyze problem and provide solution"""
        
        # 1. Search for correlations
        correlations = await self.qdrant.search_correlation(problem_description, limit=3)
        
        # 2. Get relevant concepts
        concepts = await self.qdrant.search_concepts(problem_description, limit=2)
        
        # 3. Create solution plan
        solution = self._create_solution_plan(correlations, concepts)
        
        return {
            "problem": problem_description,
            "correlations": correlations,
            "concepts": concepts,
            "solution_plan": solution
        }
    
    def _create_solution_plan(
        self, 
        correlations: List[Dict], 
        concepts: List[Dict]
    ) -> Dict[str, Any]:
        """Create actionable solution plan"""
        
        if not correlations:
            return {
                "message": "Не нашёл точного совпадения в базе знаний. Опиши проблему подробнее.",
                "actions": []
            }
        
        main_correlation = correlations[0]
        
        plan = {
            "message": f"Нашёл решение!\n\n"
                      f"📌 Проблема: {main_correlation['problem']}\n\n"
                      f"🔍 Кармическая причина:\n{main_correlation['cause']}\n\n"
                      f"✅ Решение:\n{main_correlation['solution']}",
            "actions": [
                {
                    "type": "stop",
                    "description": f"Прекрати: {main_correlation['cause']}"
                },
                {
                    "type": "start",
                    "description": f"Начни: {main_correlation['solution']}"
                },
                {
                    "type": "track",
                    "description": "Отслеживай прогресс в течение 30 дней"
                }
            ],
            "concepts": [c["title"] for c in concepts] if concepts else []
        }
        
        return plan
