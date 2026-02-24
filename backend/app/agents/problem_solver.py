"""Problem Solver Agent"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from app.models.user import UserProfile
from app.knowledge.qdrant import QdrantKnowledgeBase
from app.ai.diagnostic_agent import (
    start_karmic_diagnostic,
    continue_karmic_diagnostic,
    DiagnosticResult,
)
from app.ai.problem_agent import (
    solve_problem as ai_solve_problem,
)
from app.config import get_settings
from app.utils.typing_loader import broadcast_status


class ProblemSolverAgent:
    """Agent that helps solve user problems using karmic correlations"""
    
    def __init__(self, qdrant: QdrantKnowledgeBase):
        self.qdrant = qdrant
        self.logger = logging.getLogger(__name__)
    
    async def analyze_problem(
        self, 
        user: UserProfile, 
        problem: str,
        session_id: Optional[str] = None,
        diagnostic_answer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze problem and provide solution using AI **only** via diagnostic flow.

        Всегда запускает или продолжает сессию диагностического агента,
        а затем, после завершения диагностики, использует resolver (problem_agent).
        Прямого "одношагового" режима без диагностики больше нет.
        """

        # Гарантируем, что у каждого анализа есть session_id для диагностики
        if session_id is None:
            session_id = f"auto_{user.id}_{uuid.uuid4().hex[:8]}"

        return await self._handle_diagnostic_mode(
            user=user,
            problem=problem,
            session_id=session_id,
            diagnostic_answer=diagnostic_answer,
        )
    
    async def _handle_diagnostic_mode(
        self, 
        user: UserProfile, 
        problem: str,
        session_id: str,
        diagnostic_answer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle intelligent diagnostic mode"""
        
        try:
            # Start or continue diagnostic session
            if diagnostic_answer is None:
                # First message - start diagnostic
                diagnostic_result = await start_karmic_diagnostic(
                    user_name=user.first_name,
                    problem=problem,
                    session_id=session_id,
                    qdrant_knowledge_base=self.qdrant,
                )
            else:
                # Follow-up message - continue diagnostic with explicit answer
                diagnostic_result = await continue_karmic_diagnostic(
                    user_name=user.first_name,
                    answer=diagnostic_answer,
                    session_id=session_id,
                    qdrant_knowledge_base=self.qdrant,
                )
            
            # If diagnostic agent reported a technical error, return karmic error response
            if getattr(diagnostic_result, "has_error", False):
                return self._error_solution(
                    problem=problem,
                    technical_message=diagnostic_result.diagnostic_summary,
                )
            
            # If diagnostic is complete, proceed to full solution
            if diagnostic_result.is_complete:
                return await self._generate_solution_from_diagnostic(
                    user, diagnostic_result
                )
            
            # Otherwise, return diagnostic question
            return {
                "problem": diagnostic_result.normalized_problem,
                "root_cause": "",
                "imprint_logic": "",
                "stop_action": "",
                "start_action": "",
                "grow_action": "",
                "practice_steps": [],
                "expected_outcome": "",
                "timeline_days": 30,
                "success_tip": "",
                "clarity_level": "diagnostic",
                "karmic_pattern": "",
                "seed_strategy_summary": "",
                "coffee_meditation_script": "",
                "partner_actions": [],
                "needs_clarification": True,
                "clarifying_questions": [diagnostic_result.next_question.question] if diagnostic_result.next_question else [],
                "correlations": [],
                "concepts": [],
                "rules": [],
                "practices": [],
                "diagnostic_summary": diagnostic_result.diagnostic_summary,
                "confidence_score": diagnostic_result.confidence_score,
            }
            
        except Exception as e:
            self.logger.error(f"Diagnostic mode failed: {str(e)}", exc_info=True)
            # Structured karmic error instead of legacy fallback
            return self._error_solution(problem=problem, technical_message=str(e))
    
    async def _generate_solution_from_diagnostic(
        self,
        user: UserProfile,
        diagnostic_result: DiagnosticResult
    ) -> Dict[str, Any]:
        """Generate full solution based on completed diagnostic"""
        
        await broadcast_status("🔍 Подбираю примеры из базы знаний...")
        
        # Search for correlations based on diagnostic insights
        correlations = await self.qdrant.search_correlation(
            diagnostic_result.normalized_problem,
            limit=get_settings().PROBLEM_SOLVER_CORRELATIONS_LIMIT * 2,
        )
        
        concepts = await self.qdrant.search_concepts(
            diagnostic_result.normalized_problem,
            limit=get_settings().PROBLEM_SOLVER_CONCEPTS_LIMIT,
        )
        
        rules = await self.qdrant.search_rules(
            diagnostic_result.normalized_problem,
            limit=get_settings().PROBLEM_SOLVER_RULES_LIMIT,
        )
        
        practices = await self.qdrant.search_practice(
            need=diagnostic_result.normalized_problem,
            restrictions=(
                user.physical_restrictions.split(",")
                if user.physical_restrictions
                else None
            ),
            limit=get_settings().PROBLEM_SOLVER_PRACTICES_LIMIT,
        )
        
        # Generate solution using diagnostic insights
        solution = await ai_solve_problem(
            user_name=user.first_name,
            problem_description=diagnostic_result.normalized_problem,
            correlations=correlations,
            concepts=concepts,
            rules=rules,
            practices=practices,
            sphere=diagnostic_result.sphere,
            desired_outcome=diagnostic_result.desired_outcome,
            hypothesized_imprints=[diagnostic_result.final_hypothesis.imprint] if diagnostic_result.final_hypothesis else [],
        )
        
        return {
            "problem": solution.problem_summary,
            "root_cause": solution.root_cause,
            "imprint_logic": solution.imprint_logic,
            "stop_action": solution.stop_action,
            "start_action": solution.start_action,
            "grow_action": solution.grow_action,
            # "practice_steps": solution.practice_steps,
            "expected_outcome": solution.expected_outcome,
            # "timeline_days": solution.timeline_days,
            "success_tip": solution.success_tip,
            "clarity_level": solution.clarity_level,
            "karmic_pattern": solution.karmic_pattern,
            "seed_strategy_summary": solution.seed_strategy_summary,
            # "coffee_meditation_script": solution.coffee_meditation_script,
            # "partner_actions": solution.partner_actions,
            "partner_selection_guide": [
                g.model_dump() for g in (solution.partner_selection_guide or [])
            ],
            "needs_clarification": False,
            "clarifying_questions": [],
            "correlations": correlations,
            "concepts": concepts,
            "rules": rules,
            "practices": practices,
            "diagnostic": diagnostic_result.model_dump(),
            "diagnostic_summary": diagnostic_result.diagnostic_summary,
            "confidence_score": diagnostic_result.confidence_score,
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

    def _error_solution(self, problem: str, technical_message: Optional[str] = None) -> Dict[str, Any]:
        """Return a structured karmic-style error response without using legacy fallbacks."""

        message = (
            "Кармический диагност сейчас не может корректно продолжить работу — "
            "это похоже на небольшой сбой в системе. Попробуйте повторить запрос чуть позже."
        )
        # if technical_message:
        #     message = f"{message}\n\nТехническая деталь: {technical_message}"

        return {
            "problem": problem,
            "root_cause": message,
            "imprint_logic": "Система временно не может построить полный кармический разбор, "
            "но сам сбой можно использовать как тренажёр терпения и доброжелательности.",
            "stop_action": "Не ругайте себя и технику за сбой — это лишь временная помеха.",
            "start_action": (
                "Сделайте одно небольшое доброе действие для другого человека, "
                "пока система восстанавливается."
            ),
            "grow_action": (
                "Отметьте это действие как семя для ясности и решения вашей задачи, "
                "сделайте короткую кофе-медитацию о том, что помогаете другим, даже когда техника не идеальна."
            ),
            "practice_steps": [
                "Сделать паузу и мягко отложить повторный запрос на чуть более позднее время.",
                "Выбрать одного человека и сделать для него маленький, но осознанный акт заботы.",
                "Вечером вспомнить это действие и порадоваться ему, связывая его с решением вашей проблемы.",
            ],
            "expected_outcome": (
                "Когда система восстановится, вы получите более точный кармический план, "
                "а заодно укрепите терпение и доброжелательность."
            ),
            "timeline_days": 30,
            "success_tip": (
                "Относитесь к техническим сбоям как к напоминанию о том, что мир тоже зависит от наших отпечатков. "
                "Чем мягче вы реагируете, тем легче менять ситуацию."
            ),
            "clarity_level": "error",
            "karmic_pattern": "Временный сбой системы как шанс натренировать терпение.",
            "seed_strategy_summary": "Сеем терпение и поддержку в ситуации, когда что-то идёт не по плану.",
            "coffee_meditation_script": (
                "Закройте глаза на минуту и вспомните маленькое доброе действие, которое вы сделали, пока система не работала. "
                "Побудьте в ощущении, что такие моменты создают будущее, где решения приходят быстрее и мягче."
            ),
            "partner_actions": [],
            "needs_clarification": False,
            "clarifying_questions": [],
            "correlations": [],
            "concepts": [],
            "rules": [],
            "practices": [],
            "diagnostic_summary": message,
            "confidence_score": 0.0
        }
