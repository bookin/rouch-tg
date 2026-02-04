"""Problem Solver Agent"""
import logging
from typing import Dict, Any
from app.models.user import UserProfile
from app.knowledge.qdrant import QdrantKnowledgeBase
from app.workflows.problem_flow import ProblemSolverWorkflow
from app.ai.problem_agent import solve_problem as ai_solve_problem


class ProblemSolverAgent:
    """Agent that helps solve user problems using karmic correlations"""
    
    def __init__(self, qdrant: QdrantKnowledgeBase):
        self.qdrant = qdrant
        self.workflow = ProblemSolverWorkflow(qdrant)
        self.logger = logging.getLogger(__name__)
    
    async def analyze_problem(
        self, 
        user: UserProfile, 
        problem: str
    ) -> Dict[str, Any]:
        """Analyze problem and provide solution using AI"""
        
        try:
            # Get correlations and concepts from Qdrant
            correlations = await self.qdrant.search_correlation(problem, limit=3)
            concepts = await self.qdrant.search_concepts(problem, limit=2)
            
            # Use AI to generate solution
            solution = await ai_solve_problem(
                user_name=user.first_name,
                problem_description=problem,
                correlations=correlations,
                concepts=concepts
            )
            
            return {
                "problem": solution.problem_summary,
                "root_cause": solution.root_cause,
                "imprint_logic": solution.imprint_logic,
                "stop_action": solution.stop_action,
                "start_action": solution.start_action,
                "grow_action": solution.grow_action,
                "practice_steps": solution.practice_steps,
                "expected_outcome": solution.expected_outcome,
                "timeline_days": solution.timeline_days,
                "success_tip": solution.success_tip,
                "correlations": correlations,
                "concepts": concepts
            }
            
        except Exception as e:
            self.logger.error(f"AI Problem Solver failed: {str(e)}", exc_info=True)
            # Fallback to workflow
            result = await self.workflow.solve_problem(user, problem)
            plan = result.get("solution_plan", {})
            return {
                "problem": problem,
                "root_cause": plan.get("message", "Система временно недоступна. Попробуйте позже."),
                "imprint_logic": "Используется резервный алгоритм анализа.",
                "stop_action": next((a["description"] for a in plan.get("actions", []) if a["type"] == "stop"), "Прекратите негативные действия"),
                "start_action": next((a["description"] for a in plan.get("actions", []) if a["type"] == "start"), "Начните позитивные действия"),
                "grow_action": next((a["description"] for a in plan.get("actions", []) if a["type"] == "track"), "Следите за отпечатками"),
                "practice_steps": [plan.get("message", "")] if not plan.get("actions") else [a["description"] for a in plan.get("actions", [])],
                "expected_outcome": "Перемены начнутся с изменением вашего восприятия.",
                "timeline_days": 30,
                "success_tip": "Используйте медитацию кофе для усиления результатов.",
                "correlations": result.get("correlations", []),
                "concepts": result.get("concepts", [])
            }
    
    async def get_practice_recommendation(
        self,
        user: UserProfile,
        goal: str
    ) -> Dict[str, Any]:
        """Recommend practices based on user's goal"""
        
        practices = await self.qdrant.search_practice(
            need=goal,
            restrictions=user.physical_restrictions.split(',') if user.physical_restrictions else None,
            limit=3
        )
        
        return {
            "goal": goal,
            "practices": practices
        }
