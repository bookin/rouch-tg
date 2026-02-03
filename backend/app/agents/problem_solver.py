"""Problem Solver Agent"""
from typing import Dict, Any
from app.models.user import UserProfile
from app.knowledge.qdrant_client import QdrantKnowledgeBase
from app.workflows.problem_flow import ProblemSolverWorkflow
from app.ai.problem_agent import solve_problem as ai_solve_problem


class ProblemSolverAgent:
    """Agent that helps solve user problems using karmic correlations"""
    
    def __init__(self, qdrant: QdrantKnowledgeBase):
        self.qdrant = qdrant
        self.workflow = ProblemSolverWorkflow(qdrant)
    
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
                "opposite_action": solution.opposite_action,
                "practice_steps": solution.practice_steps,
                "expected_outcome": solution.expected_outcome,
                "timeline_days": solution.timeline_days,
                "related_concepts": [c.get("title", "") for c in concepts]
            }
            
        except Exception as e:
            # Fallback to workflow
            result = await self.workflow.solve_problem(user, problem)
            return {
                "problem": problem,
                "solution": result["solution_plan"],
                "related_concepts": result["concepts"]
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
