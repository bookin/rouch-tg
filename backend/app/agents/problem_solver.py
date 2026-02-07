"""Problem Solver Agent"""
import logging
from typing import Dict, Any, List, Optional
from app.models.user import UserProfile
from app.knowledge.qdrant import QdrantKnowledgeBase
from app.workflows.problem_flow import ProblemSolverWorkflow
from app.ai.diagnostic_agent import (
    start_karmic_diagnostic,
    continue_karmic_diagnostic,
    DiagnosticResult,
    DiagnosticSession,
    get_diagnostic_session
)
from app.ai.problem_agent import (
    solve_problem as ai_solve_problem,
    ProblemIntakeResult,
)
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
        problem: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze problem and provide solution using AI with explicit intake step"""

        # Check if this is diagnostic mode (session_id provided)
        if session_id:
            return await self._handle_diagnostic_mode(user, problem, session_id)
        
        # Legacy mode: use simple intake for backward compatibility
        return await self._handle_legacy_mode(user, problem)
    
    async def _handle_diagnostic_mode(
        self, 
        user: UserProfile, 
        problem: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Handle intelligent diagnostic mode"""
        
        try:
            # Start or continue diagnostic session
            if "уточнения пользователя" not in problem.lower():
                # First message - start diagnostic
                diagnostic_result = await start_karmic_diagnostic(
                    user_name=user.first_name,
                    problem=problem,
                    session_id=session_id,
                    qdrant_knowledge_base=self.qdrant
                )
            else:
                # Follow-up message - continue diagnostic
                # Extract user's answer from the message
                user_answer = problem.replace("уточнения пользователя", "").strip()
                diagnostic_result = await continue_karmic_diagnostic(
                    user_name=user.first_name,
                    answer=user_answer,
                    session_id=session_id,
                    qdrant_knowledge_base=self.qdrant
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
            # Fallback to legacy mode
            return await self._handle_legacy_mode(user, problem)
    
    async def _handle_legacy_mode(
        self, 
        user: UserProfile, 
        problem: str
    ) -> Dict[str, Any]:
        """Handle legacy intake mode for backward compatibility"""
        
        try:
            # Use simple intake for backward compatibility
            from app.ai.problem_agent import solve_problem_intake
            
            intake: ProblemIntakeResult = await solve_problem_intake(
                user_name=user.first_name,
                problem_description=problem,
            )
            
            # Check if clarification needed
            if intake.needs_clarification and intake.clarifying_questions:
                return {
                    "problem": intake.normalized_problem or problem,
                    "root_cause": "",
                    "imprint_logic": "",
                    "stop_action": "",
                    "start_action": "",
                    "grow_action": "",
                    "practice_steps": [],
                    "expected_outcome": "",
                    "timeline_days": 30,
                    "success_tip": "",
                    "clarity_level": intake.clarity_level,
                    "karmic_pattern": "",
                    "seed_strategy_summary": "",
                    "coffee_meditation_script": "",
                    "partner_actions": [],
                    "needs_clarification": True,
                    "clarifying_questions": intake.clarifying_questions,
                    "correlations": [],
                    "concepts": [],
                    "rules": [],
                    "practices": [],
                }
            
            # Continue with full analysis
            effective_problem = intake.normalized_problem or problem
            
        except Exception as e:
            self.logger.error(f"Legacy intake failed: {str(e)}", exc_info=True)
            effective_problem = problem
            intake = None
        
        # Continue with existing logic
        return await self._full_analysis(user, effective_problem, intake)
    
    async def _generate_solution_from_diagnostic(
        self,
        user: UserProfile,
        diagnostic_result: DiagnosticResult
    ) -> Dict[str, Any]:
        """Generate full solution based on completed diagnostic"""
        
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
            "practice_steps": solution.practice_steps,
            "expected_outcome": solution.expected_outcome,
            "timeline_days": solution.timeline_days,
            "success_tip": solution.success_tip,
            "clarity_level": solution.clarity_level,
            "karmic_pattern": solution.karmic_pattern,
            "seed_strategy_summary": solution.seed_strategy_summary,
            "coffee_meditation_script": solution.coffee_meditation_script,
            "partner_actions": solution.partner_actions,
            "needs_clarification": False,
            "clarifying_questions": [],
            "correlations": correlations,
            "concepts": concepts,
            "rules": rules,
            "practices": practices,
            "diagnostic_summary": diagnostic_result.diagnostic_summary,
            "confidence_score": diagnostic_result.confidence_score,
        }
    
    async def _full_analysis(
        self,
        user: UserProfile,
        problem: str,
        intake: Optional[ProblemIntakeResult]
    ) -> Dict[str, Any]:
        """Full analysis logic extracted from original method"""
        
        try:
            settings = get_settings()

            # Search correlations
            raw_correlations = await self.qdrant.search_correlation(
                problem,
                limit=settings.PROBLEM_SOLVER_CORRELATIONS_LIMIT * 2,
            )
            correlations = self._select_top_correlations(
                raw_correlations,
                intake,
                limit=settings.PROBLEM_SOLVER_CORRELATIONS_LIMIT,
            )

            # Search concepts, rules, practices
            concepts = await self.qdrant.search_concepts(
                problem,
                limit=settings.PROBLEM_SOLVER_CONCEPTS_LIMIT,
            )
            rules = await self.qdrant.search_rules(
                problem,
                limit=settings.PROBLEM_SOLVER_RULES_LIMIT,
            )
            practices = await self.qdrant.search_practice(
                need=problem,
                restrictions=(
                    user.physical_restrictions.split(",")
                    if user.physical_restrictions
                    else None
                ),
                limit=settings.PROBLEM_SOLVER_PRACTICES_LIMIT,
            )

            # Generate solution
            solution = await ai_solve_problem(
                user_name=user.first_name,
                problem_description=problem,
                correlations=correlations,
                concepts=concepts,
                rules=rules,
                practices=practices,
                sphere=intake.sphere if intake else None,
                desired_outcome=intake.desired_outcome if intake else None,
                hypothesized_imprints=intake.hypothesized_imprints if intake else [],
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
            self.logger.error(f"Full analysis failed: {str(e)}", exc_info=True)
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

    def _select_top_correlations(
        self,
        correlations: List[Dict[str, Any]],
        intake: ProblemIntakeResult,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Re-rank correlations using intake sphere/imprints to pick the most karmically relevant ones."""

        if not correlations:
            return []
        
        if intake is None:
            # Если intake отсутствует, просто возвращаем первые limit корреляций
            return correlations[:limit]

        sphere = (intake.sphere or "").lower()
        imprints = [imp.lower() for imp in intake.hypothesized_imprints or []]

        def score(corr: Dict[str, Any]) -> float:
            base = float(corr.get("score") or 0.0)

            # Сфера: поощряем совпадения по человеку‑читаемой сфере
            corr_sphere = (corr.get("sphere") or "").lower()
            if sphere and corr_sphere:
                if sphere in corr_sphere or corr_sphere in sphere:
                    base += 0.3

            # Импринты/тип проблемы: ищем совпадения по словам
            corr_imprint_text = " ".join(
                [str(corr.get("imprint") or ""), str(corr.get("problem_type") or "")]
            ).lower()
            if imprints and corr_imprint_text:
                for imp in imprints:
                    if imp and imp in corr_imprint_text:
                        base += 0.4
                        break

            # Лёгкий бонус за расширенную таблицу (более структурированные кейсы)
            if (corr.get("source_type") or "") == "extended":
                base += 0.05

            return base

        ranked = sorted(correlations, key=score, reverse=True)
        return ranked[:limit]
