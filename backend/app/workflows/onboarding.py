"""Onboarding workflow using LangGraph - refactored for step-by-step execution"""
from typing import TypedDict, List, Optional, Any
from langgraph.graph import StateGraph, START, END
from app.models.user import UserProfile, OnboardingState as UserOnboardingState


class OnboardingSteps:
    """Constants for onboarding steps"""
    OCCUPATION = "occupation"
    SCHEDULE = "schedule"
    DURATION = "duration"
    HABITS = "habits"
    RESTRICTIONS = "restrictions"
    FOCUS = "focus"
    PARTNERS = "partners"
    COMPLETE = "complete"


class OnboardingWorkflowState(TypedDict):
    """State for onboarding flow"""
    user_id: int
    telegram_id: int
    step: str
    data: dict
    completed: bool
    messages: List[str]


# Step definitions - single source of truth for both Telegram and Web
ONBOARDING_STEPS = {
    OnboardingSteps.OCCUPATION: {
        "number": 1,
        "total": 5,
        "message": "Привет! Давай познакомимся. 👋\n\nЧем ты занимаешься?",
        "field": "occupation",
        "input_type": "single_choice",
        "options": [
            {"id": "entrepreneur", "label": "💼 Предприниматель"},
            {"id": "employee", "label": "👔 Сотрудник компании"},
            {"id": "freelancer", "label": "💻 Фрилансер"},
            {"id": "other", "label": "🌟 Другое"},
        ],
        "next_step": OnboardingSteps.SCHEDULE,
    },
    OnboardingSteps.SCHEDULE: {
        "number": 2,
        "total": 5,
        "message": "Отлично! Когда у тебя есть время для практик?",
        "field": "available_times",
        "input_type": "multi_choice",
        "options": [
            {"id": "morning", "label": "🌅 Утро (6:00-9:00)"},
            {"id": "afternoon", "label": "☀️ День (12:00-14:00)"},
            {"id": "evening", "label": "🌙 Вечер (19:00-22:00)"},
        ],
        "next_step": OnboardingSteps.DURATION,
    },
    OnboardingSteps.DURATION: {
        "number": 2,
        "total": 5,
        "message": "Сколько минут готов уделять практикам?",
        "field": "daily_minutes",
        "input_type": "single_choice",
        "options": [
            {"id": "15", "label": "⏱ 10-15 минут"},
            {"id": "30", "label": "⏱ 30 минут"},
            {"id": "60", "label": "⏱ 1 час+"},
        ],
        "next_step": OnboardingSteps.HABITS,
    },
    OnboardingSteps.HABITS: {
        "number": 3,
        "total": 5,
        "message": "Что уже практикуешь?",
        "field": "current_habits",
        "input_type": "multi_choice",
        "options": [
            {"id": "meditation", "label": "🧘 Медитация"},
            {"id": "yoga", "label": "🧘‍♀️ Йога"},
            {"id": "sport", "label": "💪 Спорт"},
            {"id": "journaling", "label": "📝 Дневник"},
            {"id": "none", "label": "❌ Ничего из этого"},
        ],
        "next_step": OnboardingSteps.RESTRICTIONS,
    },
    OnboardingSteps.RESTRICTIONS: {
        "number": 3,
        "total": 5,
        "message": "Есть ли физические ограничения?\n\nНапиши текстом или пропусти.",
        "field": "physical_restrictions",
        "input_type": "text_optional",
        "options": [
            {"id": "skip", "label": "➡️ Пропустить"},
        ],
        "next_step": OnboardingSteps.FOCUS,
    },
    OnboardingSteps.FOCUS: {
        "number": 4,
        "total": 5,
        "message": "Что хочешь улучшить в первую очередь?",
        "field": "current_focus",
        "input_type": "single_choice",
        "options": [
            {"id": "finances", "label": "💰 Финансы"},
            {"id": "relationships", "label": "💑 Отношения"},
            {"id": "health", "label": "❤️ Здоровье"},
            {"id": "focus", "label": "🎯 Концентрация"},
            {"id": "other", "label": "🌟 Другое"},
        ],
        "next_step": OnboardingSteps.PARTNERS,
    },
    OnboardingSteps.PARTNERS: {
        "number": 5,
        "total": 5,
        "message": "Последний шаг!\n\nТвои ключевые партнёры:\n\n👥 Коллеги — кто рядом с тобой?\n🤝 Клиенты — кого ты обслуживаешь?\n📦 Поставщики — кто тебе помогает?\n🌍 Мир — кому ещё можешь помочь?\n\nДобавишь конкретных людей позже в приложении.",
        "field": None,
        "input_type": "confirm",
        "options": [
            {"id": "continue", "label": "✅ Понятно, продолжаем!"},
        ],
        "next_step": OnboardingSteps.COMPLETE,
    },
    OnboardingSteps.COMPLETE: {
        "number": 5,
        "total": 5,
        "message": "🎉 Отлично! Знакомство завершено.\n\nЯ составил для тебя персональный план.\n\nКаждое утро буду присылать:\n• Цитату для размышления\n• 4 действия на день\n• Напоминания о практиках\n\nПоехали! 🚀",
        "field": None,
        "input_type": "complete",
        "options": [],
        "next_step": None,
    },
}


def get_step_data(step: str) -> dict:
    """Get data for a specific step"""
    if step not in ONBOARDING_STEPS:
        step = OnboardingSteps.OCCUPATION
    
    step_info = ONBOARDING_STEPS[step]
    return {
        "step": step,
        "step_number": step_info["number"],
        "total_steps": step_info["total"],
        "message": step_info["message"],
        "input_type": step_info["input_type"],
        "options": step_info["options"],
        "field": step_info["field"],
        "completed": step == OnboardingSteps.COMPLETE,
    }


def get_next_step(current_step: str) -> Optional[str]:
    """Get the next step after current"""
    if current_step not in ONBOARDING_STEPS:
        return OnboardingSteps.OCCUPATION
    return ONBOARDING_STEPS[current_step].get("next_step")


async def save_onboarding_progress(telegram_id: int, step: str, answer: Any):
    """
    Save onboarding progress to DB.
    
    Args:
        telegram_id: User's Telegram ID
        step: Current step name (from OnboardingSteps)
        answer: The answer to save (string, list, or int)
    """
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from datetime import datetime
    
    step_info = ONBOARDING_STEPS.get(step)
    if not step_info:
        return

    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, telegram_id)
        if not user_db:
            return
        
        field = step_info.get("field")
        if field:
            if field == "daily_minutes":
                # Ensure integer for daily_minutes
                try:
                    val = int(answer) if answer else 30
                except (ValueError, TypeError):
                    val = 30
                setattr(user_db, field, val)
            else:
                setattr(user_db, field, answer)
        
        # If this is the last step or partners step, update timestamp
        # 'partners' is the last interaction before 'complete'
        next_step_name = get_next_step(step)
        if next_step_name == OnboardingSteps.COMPLETE or step == OnboardingSteps.PARTNERS:
            user_db.last_onboarding_update = datetime.utcnow()
            
        await db.commit()


def process_step_answer(step: str, answer: Any) -> dict:
    """Process answer for a step and return next step data"""
    next_step = get_next_step(step)
    if next_step:
        return get_step_data(next_step)
    return get_step_data(OnboardingSteps.COMPLETE)


class OnboardingWorkflow:
    """Onboarding state machine"""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the onboarding graph"""
        
        workflow = StateGraph(OnboardingWorkflowState)
        
        # Add nodes
        workflow.add_node("intro", self._ask_occupation)
        workflow.add_node("schedule", self._ask_schedule)
        workflow.add_node("habits", self._ask_habits)
        workflow.add_node("problems", self._identify_problems)
        workflow.add_node("partners", self._setup_partners)
        workflow.add_node("summary", self._generate_summary)
        
        # Add edges - modern API uses START constant
        workflow.add_edge(START, "intro")
        workflow.add_edge("intro", "schedule")
        workflow.add_edge("schedule", "habits")
        workflow.add_edge("habits", "problems")
        workflow.add_edge("problems", "partners")
        workflow.add_edge("partners", "summary")
        workflow.add_edge("summary", END)
        
        return workflow.compile()
    
    async def _ask_occupation(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Ask about occupation"""
        if "messages" not in state:
            state["messages"] = []
        step_data = ONBOARDING_STEPS[OnboardingSteps.OCCUPATION]
        state["messages"].append(f"📍 Шаг {step_data['number']}/{step_data['total']}: {step_data['message']}")
        state["step"] = OnboardingSteps.SCHEDULE
        return state
    
    async def _ask_schedule(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Ask about available time"""
        step_data = ONBOARDING_STEPS[OnboardingSteps.SCHEDULE]
        state["messages"].append(f"📍 Шаг {step_data['number']}/{step_data['total']}: {step_data['message']}")
        state["step"] = OnboardingSteps.HABITS
        return state
    
    async def _ask_habits(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Ask about current habits"""
        step_data = ONBOARDING_STEPS[OnboardingSteps.HABITS]
        state["messages"].append(f"📍 Шаг {step_data['number']}/{step_data['total']}: {step_data['message']}")
        state["step"] = OnboardingSteps.FOCUS
        return state
    
    async def _identify_problems(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Identify current problems"""
        step_data = ONBOARDING_STEPS[OnboardingSteps.FOCUS]
        state["messages"].append(f"📍 Шаг {step_data['number']}/{step_data['total']}: {step_data['message']}")
        state["step"] = OnboardingSteps.PARTNERS
        return state
    
    async def _setup_partners(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Setup partner groups"""
        step_data = ONBOARDING_STEPS[OnboardingSteps.PARTNERS]
        state["messages"].append(f"📍 Шаг {step_data['number']}/{step_data['total']}: {step_data['message']}")
        state["step"] = "summary"
        return state
    
    async def _generate_summary(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Generate personalized summary"""
        step_data = ONBOARDING_STEPS[OnboardingSteps.COMPLETE]
        state["messages"].append(step_data["message"])
        state["completed"] = True
        return state
    
    async def run(self, initial_state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Run the onboarding workflow"""
        result = await self.graph.ainvoke(initial_state)
        return result
