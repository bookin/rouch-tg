"""Problem Solver Agent"""
import logging
from typing import Dict, Any
from app.models.user import UserProfile
from app.knowledge.qdrant import QdrantKnowledgeBase
from app.workflows.problem_flow import ProblemSolverWorkflow
from app.ai.problem_agent import solve_problem as ai_solve_problem
from app.config import get_settings


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
            settings = get_settings()
            # Get correlations and concepts from Qdrant
            correlations = await self.qdrant.search_correlation(
                problem,
                limit=settings.PROBLEM_SOLVER_CORRELATIONS_LIMIT,
            )
            concepts = await self.qdrant.search_concepts(
                problem,
                limit=settings.PROBLEM_SOLVER_CONCEPTS_LIMIT,
            )
            # Дополнительный слой знаний: правила и практики
            rules = await self.qdrant.search_rules(
                problem,
                limit=settings.PROBLEM_SOLVER_RULES_LIMIT,
            )
            practices = await self.qdrant.search_practice(
                need=problem,
                restrictions=user.physical_restrictions.split(',') if user.physical_restrictions else None,
                limit=settings.PROBLEM_SOLVER_PRACTICES_LIMIT,
            )
            
            # Use AI to generate solution
            solution = await ai_solve_problem(
                user_name=user.first_name,
                problem_description=problem,
                correlations=correlations,
                concepts=concepts,
                rules=rules,
                practices=practices,
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
                # Дополнительные поля для более глубокой логики
                "clarity_level": solution.clarity_level,
                "karmic_pattern": solution.karmic_pattern,
                "seed_strategy_summary": solution.seed_strategy_summary,
                "coffee_meditation_script": solution.coffee_meditation_script,
                "partner_actions": solution.partner_actions,
                "needs_clarification": solution.needs_clarification,
                "clarifying_questions": solution.clarifying_questions,
                "correlations": correlations,
                "concepts": concepts,
                "rules": rules,
                "practices": practices,
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
                # Консервативные значения для дополнительных полей
                "clarity_level": "fallback",
                "karmic_pattern": "",
                "seed_strategy_summary": "",
                "coffee_meditation_script": "Используйте любую знакомую вам медитацию кофе, вспоминая добро, которое вы делаете.",
                "partner_actions": [],
                "needs_clarification": False,
                "clarifying_questions": [],
                "correlations": result.get("correlations", []),
                "concepts": result.get("concepts", []),
                "rules": [],
                "practices": [],
            }
    
    async def get_practice_recommendation(
        self,
        user: UserProfile,
        goal: str
    ) -> Dict[str, Any]:
        """Recommend practices based on user's goal"""
        
        settings = get_settings()
        practices = await self.qdrant.search_practice(
            need=goal,
            restrictions=user.physical_restrictions.split(',') if user.physical_restrictions else None,
            limit=settings.PROBLEM_SOLVER_PRACTICES_LIMIT,
        )
        
        return {
            "goal": goal,
            "practices": practices
        }
