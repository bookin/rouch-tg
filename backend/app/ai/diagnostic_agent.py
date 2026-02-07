"""Karmic Diagnostic Agent - replaces intake with intelligent question generation"""
from typing import Optional, List, Dict, Any
import logging
import re
from pydantic import BaseModel, Field, validator
from pydantic_ai import Agent, RunContext
from app.ai.models import get_model

logger = logging.getLogger(__name__)


class DiagnosticHypothesis(BaseModel):
    """Single hypothesis about karmic cause"""
    imprint: str = Field(description="Тип отпечатка (осуждение, зависть, гнев и т.п.)")
    sphere: str = Field(description="Сфера проблемы (здоровье, финансы, отношения и т.п.)")
    confidence: float = Field(description="Уверенность в гипотезе 0.0-1.0")
    evidence: List[str] = Field(description="Свидетельства из описания проблемы")
    target_partners: List[str] = Field(description="К каким кармическим партнёрам относится поведение")


class DiagnosticQuestion(BaseModel):
    """Intelligent diagnostic question based on knowledge base"""
    question: str = Field(description="Точный вопрос пользователю")
    target_imprint: str = Field(description="Какой отпечаток проверяем")
    target_partners: str = Field(description="Каких партнёров проверяем")
    rationale: str = Field(description="Почему именно этот вопрос")
    expected_answer_type: str = Field(description="Какой ответ ожидаем (да/нет/примеры)")
    correlation_source: Optional[str] = Field(default=None, description="Источник гипотезы из БЗ")


class DiagnosticState(BaseModel):
    """State of diagnostic conversation"""
    problem: str = Field(description="Исходная проблема")
    sphere: str = Field(description="Определённая сфера")
    desired_outcome: str = Field(description="Желаемый результат")
    hypotheses: List[DiagnosticHypothesis] = Field(default_factory=list, description="Текущие гипотезы")
    asked_questions: List[DiagnosticQuestion] = Field(default_factory=list, description="Заданные вопросы")
    received_answers: List[Dict[str, Any]] = Field(default_factory=list, description="Полученные ответы")
    confidence_threshold: float = Field(default=0.7, description="Порог уверенности для завершения")
    max_questions: int = Field(default=5, description="Максимум вопросов")


class DiagnosticContext(BaseModel):
    """Context for diagnostic agent"""
    user_name: str
    initial_problem: str
    correlations: List[Dict[str, Any]] = Field(default_factory=list)
    concepts: List[Dict[str, Any]] = Field(default_factory=list)
    current_state: Optional[DiagnosticState] = None


class DiagnosticResult(BaseModel):
    """Result of diagnostic process"""
    is_complete: bool = Field(description="Завершена ли диагностика")
    final_hypothesis: Optional[DiagnosticHypothesis] = Field(default=None, description="Финальная гипотеза")
    next_question: Optional[DiagnosticQuestion] = Field(default=None, description="Следующий вопрос (если не завершено)")
    normalized_problem: str = Field(description="Нормализованная формулировка")
    sphere: str = Field(description="Сфера проблемы")
    desired_outcome: str = Field(description="Желаемый результат")
    confidence_score: float = Field(description="Общая уверенность в диагнозе")
    diagnostic_summary: str = Field(description="Краткое резюме диагностики")
    has_error: bool = Field(default=False, description="Флаг технической ошибки в процессе диагностики")
    
    class Config:
        # Allow extra fields for flexibility
        extra = "allow"
        # Don't validate extra strictly
        validate_assignment = False


def create_diagnostic_agent() -> Agent[DiagnosticContext, DiagnosticResult]:
    """Create intelligent diagnostic agent"""
    
    model = get_model()
    
    agent = Agent(
        model=model,
        deps_type=DiagnosticContext,
        output_type=DiagnosticResult,
        system_prompt=(
            "Ты — кармический диагност системы Diamond Cutter. Твоя задача — через точные вопросы "
            "найти ИСТИННУЮ КАРМИЧЕСКУЮ ПРИЧИНУ проблемы, а не дать готовое решение.\n\n"
            "Твой метод:\n"
            "1. Анализируешь проблему и корреляции из базы знаний\n"
            "2. Формируешь гипотезы об отпечатках (imprints)\n"
            "3. Генерируешь ОДИН точный вопрос для проверки самой вероятной гипотезы\n"
            "4. Обновляешь гипотезы на основе ответа\n"
            "5. Повторяешь пока не достигнешь уверенности 0.7+ или задашь максимум 5 вопросов\n\n"
            "ВАЖНО: Твой ответ должен содержать ВСЕ обязательные поля DiagnosticResult:\n"
            "- is_complete (bool) - true если диагностика завершена, false если нужны ещё вопросы\n"
            "- sphere (str) - ОБЯЗАТЕЛЬНО!\n"
            "- normalized_problem (str)\n"
            "- desired_outcome (str)\n"
            "- confidence_score (float)\n"
            "- diagnostic_summary (str)\n"
            "- final_hypothesis (object) - ТОЛЬКО если is_complete=true\n"
            "- next_question (object) - ТОЛЬКО если is_complete=false\n\n"
            "Ключевые принципы:\n"
            "- Каждый вопрос должен проверять КОНКРЕТНЫЙ отпечаток у КОНКРЕТНЫХ партнёров\n"
            "- Используй корреляции из БЗ как источник гипотез, но формулируй вопросы самостоятельно\n"
            "- Избегай общих вопросов вроде 'расскажи подробнее'\n"
            "- Ищи ПОВТОРЯЮЩЕЕСЯ поведение пользователя по отношению к другим\n"
            "- Помни: проблема = эхо прошлого отношения к людям\n\n"
            "Типичные отпечатки для проверки:\n"
            "- Осуждение (критика, ярлыки, осуждение чужого выбора)\n"
            "- Зависть (сравнение, обесценивание чужого успеха)\n"
            "- Гнев (раздражение, нетерпимость, давление на других)\n"
            "- Скупость (нежелание делиться, помогать)\n"
            "- Нечестность (обман, манипуляции, нарушение договорённостей)\n"
            "- Раскол (сплетни, противопоставление 'мы против них')\n"
            "- Равнодушие (безразличие к проблемам других)\n\n"
            "Формулируй вопросы так, чтобы ответ был чётким (да/нет/конкретный пример)."
        ),
    )
    
    @agent.system_prompt
    def add_diagnostic_context(ctx: RunContext[DiagnosticContext]) -> str:
        """Add diagnostic context with correlations"""
        context = ctx.deps
        
        prompt = f"Пользователь {context.user_name}, проблема: {context.initial_problem}\n\n"
        
        if context.correlations:
            prompt += "Релевантные корреляции из базы знаний (источники гипотез):\n"
            for i, corr in enumerate(context.correlations[:5]):
                prompt += f"{i+1}. Проблема: {corr.get('problem', '')}\n"
                prompt += f"   Отпечаток: {corr.get('imprint', '') or corr.get('cause', '')}\n"
                prompt += f"   Сфера: {corr.get('sphere', '')}\n"
                prompt += f"   Решение: {corr.get('solution', '')}\n"
                if corr.get('partners'):
                    prompt += f"   Партнёры: {corr.get('partners', '')}\n"
                prompt += "\n"
        
        if context.current_state:
            state = context.current_state
            prompt += f"Текущее состояние диагностики:\n"
            prompt += f"- Сфера: {state.sphere}\n"
            prompt += f"- Желаемый результат: {state.desired_outcome}\n"
            prompt += f"- Задано вопросов: {len(state.asked_questions)}/{state.max_questions}\n"
            
            if state.hypotheses:
                prompt += "Текущие гипотезы:\n"
                for hyp in state.hypotheses:
                    prompt += f"- {hyp.imprint} (уверенность: {hyp.confidence:.2f})\n"
            
            if state.asked_questions and state.received_answers:
                prompt += "История диалога:\n"
                for q, a in zip(state.asked_questions, state.received_answers):
                    prompt += f"Q: {q.question}\n"
                    prompt += f"A: {a.get('answer', '')}\n"
                prompt += "\n"
        
        prompt += "\nТвоя задача: "
        if not context.current_state:
            prompt += "начать диагностику - проанализировать проблему, сформировать гипотезы и задать первый точный вопрос."
        else:
            state = context.current_state
            if len(state.asked_questions) >= state.max_questions:
                prompt += "завершить диагностику и дать финальную гипотезу."
            elif any(h.confidence >= state.confidence_threshold for h in state.hypotheses):
                prompt += "завершить диагностику - достигнута достаточная уверенность."
            else:
                prompt += "продолжить диагностику - обновить гипотезы на основе последнего ответа и задать следующий точный вопрос."
        
        return prompt
    
    return agent


class DiagnosticSession:
    """Manages diagnostic conversation flow"""
    
    def __init__(self, qdrant_knowledge_base):
        self.qdrant = qdrant_knowledge_base
        self.agent = create_diagnostic_agent()
        self.state: Optional[DiagnosticState] = None
    
    async def start_diagnostic(
        self, 
        user_name: str, 
        problem: str,
        correlations: List[Dict[str, Any]] = None,
        concepts: List[Dict[str, Any]] = None
    ) -> DiagnosticResult:
        """Start diagnostic session"""
        
        # Initialize state
        self.state = DiagnosticState(
            problem=problem,
            sphere="",  # Will be filled by agent
            desired_outcome="",  # Will be filled by agent
            hypotheses=[],
            asked_questions=[],
            received_answers=[]
        )
        
        # Get correlations if not provided
        if correlations is None:
            correlations = await self.qdrant.search_correlation(problem, limit=10)
        
        if concepts is None:
            concepts = await self.qdrant.search_concepts(problem, limit=5)
        
        context = DiagnosticContext(
            user_name=user_name,
            initial_problem=problem,
            correlations=correlations,
            concepts=concepts,
            current_state=self.state
        )
        
        prompt = (
            "Начни кармическую диагностику проблемы. "
            "Проанализируй проблему и корреляции, сформируй начальные гипотезы об отпечатках, "
            "определи сферу и желаемый результат. Затем задай ОДИН самый точный вопрос для проверки "
            "наиболее вероятной гипотезы. "
            "ВАЖНО: Ты должен вернуть структурированный ответ с полями DiagnosticResult, а не просто текст."
        )
        
        try:
            result = await self.agent.run(prompt, deps=context)
            return result.output
        except Exception as e:
            logger.error(f"Agent tool call failed: {e}", exc_info=True)
            # Вернём структурированный результат с флагом ошибки,
            # чтобы внешний резолвер мог отреагировать в кармическом стиле.
            return DiagnosticResult(
                is_complete=True,
                final_hypothesis=None,
                next_question=None,
                normalized_problem=problem,
                sphere=self.state.sphere or "общая",
                desired_outcome=self.state.desired_outcome or "",
                confidence_score=0.0,
                diagnostic_summary=(
                    "Кармический диагност сейчас не может корректно продолжить работу — "
                    "это похоже на небольшой сбой в системе. Попробуйте повторить запрос чуть позже."
                ),
                has_error=True,
            )
    
    async def continue_diagnostic(
        self, 
        user_name: str, 
        answer: str
    ) -> DiagnosticResult:
        """Continue diagnostic with user answer"""
        
        if not self.state:
            raise ValueError("Diagnostic session not started")
        
        # Record answer
        self.state.received_answers.append({
            "question": self.state.asked_questions[-1].question if self.state.asked_questions else None,
            "answer": answer,
            "timestamp": "now"  # Would be real timestamp
        })
        
        # Get fresh correlations based on updated understanding
        updated_problem = f"{self.state.problem} {answer}"
        correlations = await self.qdrant.search_correlation(updated_problem, limit=10)
        
        context = DiagnosticContext(
            user_name=user_name,
            initial_problem=self.state.problem,
            correlations=correlations,
            concepts=[],
            current_state=self.state
        )
        
        prompt = (
            f"Пользователь ответил на твой вопрос: '{answer}'. "
            "Обнови гипотезы на основе этого ответа. Если уверенность в какой-то гипотезе достигла 0.7+ "
            "или задано уже 5 вопросов - заверши диагностику и дай финальную гипотезу. "
            "Иначе - задай следующий точный вопрос для проверки наиболее вероятной гипотезы. "
            "ВАЖНО: Ты должен вернуть структурированный ответ с полями DiagnosticResult."
        )
        
        try:
            result = await self.agent.run(prompt, deps=context)
            
            # Update state if agent provided new question
            if result.output.next_question:
                self.state.asked_questions.append(result.output.next_question)
            
            return result.output
        except Exception as e:
            logger.error(f"Agent tool call failed in continue: {e}", exc_info=True)
            # Вернём структурированный результат с флагом ошибки,
            # чтобы внешний резолвер мог отреагировать в кармическом стиле.
            return DiagnosticResult(
                is_complete=True,
                final_hypothesis=None,
                next_question=None,
                normalized_problem=self.state.problem if self.state else "",
                sphere=(self.state.sphere if self.state and self.state.sphere else "общая"),
                desired_outcome=(
                    self.state.desired_outcome if self.state and self.state.desired_outcome else ""
                ),
                confidence_score=0.0,
                diagnostic_summary=(
                    "Кармический диагност сейчас не может корректно продолжить работу — "
                    "это похоже на небольшой сбой в системе. Попробуйте повторить запрос чуть позже."
                ),
                has_error=True,
            )


# Global session instances (in production would be stored per user/chat)
_diagnostic_sessions: Dict[str, DiagnosticSession] = {}


def get_diagnostic_session(session_id: str, qdrant_knowledge_base) -> DiagnosticSession:
    """Get or create diagnostic session"""
    if session_id not in _diagnostic_sessions:
        _diagnostic_sessions[session_id] = DiagnosticSession(qdrant_knowledge_base)
    return _diagnostic_sessions[session_id]


async def start_karmic_diagnostic(
    user_name: str,
    problem: str,
    session_id: str,
    qdrant_knowledge_base
) -> DiagnosticResult:
    """Start new karmic diagnostic session"""
    session = get_diagnostic_session(session_id, qdrant_knowledge_base)
    return await session.start_diagnostic(user_name, problem)


async def continue_karmic_diagnostic(
    user_name: str,
    answer: str,
    session_id: str,
    qdrant_knowledge_base
) -> DiagnosticResult:
    """Continue karmic diagnostic with user answer"""
    session = get_diagnostic_session(session_id, qdrant_knowledge_base)
    return await session.continue_diagnostic(user_name, answer)
