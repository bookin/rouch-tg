"""Problem Solver Agent"""
import logging
from typing import Dict, Any, List
from app.models.user import UserProfile
from app.knowledge.qdrant import QdrantKnowledgeBase
from app.workflows.problem_flow import ProblemSolverWorkflow
from app.ai.problem_agent import (
    solve_problem as ai_solve_problem,
    solve_problem_intake as ai_solve_problem_intake,
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
        problem: str
    ) -> Dict[str, Any]:
        """Analyze problem and provide solution using AI with explicit intake step"""

        try:
            settings = get_settings()

            # 0. Intake: понять сферу, желаемый результат, ясность и возможные отпечатки
            intake: ProblemIntakeResult = await ai_solve_problem_intake(
                user_name=user.first_name,
                problem_description=problem,
            )
            # Второй заход (после уточнений) помечается фразой в тексте — в этом случае мы обязаны дать финальный ответ
            is_clarification_pass = "уточнения пользователя" in problem.lower()

            # Если это первый заход и проблема размыта — возвращаем вопросы, не тратя ресурсы на полный анализ
            if (
                not is_clarification_pass
                and intake.needs_clarification
                and intake.clarifying_questions
            ):
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

            # 1. Нормализованный текст проблемы, который пойдёт в поиск и в основной агент
            effective_problem = intake.normalized_problem or problem

            # 2. Поиск корреляций с учётом сферы и гипотезы по отпечаткам
            raw_correlations = await self.qdrant.search_correlation(
                effective_problem,
                limit=settings.PROBLEM_SOLVER_CORRELATIONS_LIMIT * 2,
            )
            correlations = self._select_top_correlations(
                raw_correlations,
                intake,
                limit=settings.PROBLEM_SOLVER_CORRELATIONS_LIMIT,
            )

            # 3. Подбор концепций, правил и практик по нормализованной формулировке
            concepts = await self.qdrant.search_concepts(
                effective_problem,
                limit=settings.PROBLEM_SOLVER_CONCEPTS_LIMIT,
            )
            rules = await self.qdrant.search_rules(
                effective_problem,
                limit=settings.PROBLEM_SOLVER_RULES_LIMIT,
            )
            practices = await self.qdrant.search_practice(
                need=effective_problem,
                restrictions=(
                    user.physical_restrictions.split(",")
                    if user.physical_restrictions
                    else None
                ),
                limit=settings.PROBLEM_SOLVER_PRACTICES_LIMIT,
            )

            # 4. Основной кармический агент: собирает решение, опираясь на intake и отобранный контекст
            solution = await ai_solve_problem(
                user_name=user.first_name,
                problem_description=effective_problem,
                correlations=correlations,
                concepts=concepts,
                rules=rules,
                practices=practices,
                sphere=intake.sphere,
                desired_outcome=intake.desired_outcome,
                hypothesized_imprints=intake.hypothesized_imprints,
            )

            # Во втором проходе (после уточнений) больше не запрашиваем новые уточнения, даже если модель так решила
            needs_clarification = solution.needs_clarification
            clarifying_questions = solution.clarifying_questions
            if is_clarification_pass:
                needs_clarification = False
                clarifying_questions = []

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
                "needs_clarification": needs_clarification,
                "clarifying_questions": clarifying_questions,
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

    def _select_top_correlations(
        self,
        correlations: List[Dict[str, Any]],
        intake: ProblemIntakeResult,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Re-rank correlations using intake sphere/imprints to pick the most karmically relevant ones."""

        if not correlations:
            return []

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
