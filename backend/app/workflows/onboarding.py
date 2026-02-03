"""Onboarding workflow using LangGraph"""
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, START, END
from app.models.user import UserProfile, OnboardingState


class OnboardingWorkflowState(TypedDict):
    """State for onboarding flow"""
    user_id: int
    telegram_id: int
    step: str
    data: dict
    completed: bool
    messages: List[str]


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
        state["messages"].append(
            "📍 Шаг 1/5: Чем ты занимаешься?\n\n"
            "• Предприниматель\n"
            "• Сотрудник компании\n"
            "• Фрилансер\n"
            "• Другое"
        )
        state["step"] = "schedule"
        return state
    
    async def _ask_schedule(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Ask about available time"""
        state["messages"].append(
            "📍 Шаг 2/5: Когда у тебя есть время?\n\n"
            "Выбери удобные слоты:\n"
            "☐ Утро (6:00-9:00)\n"
            "☐ День (12:00-14:00)\n"
            "☐ Вечер (19:00-22:00)\n\n"
            "Сколько минут готов уделять практикам?\n"
            "• 10-15 мин\n"
            "• 30 мин\n"
            "• 1 час+"
        )
        state["step"] = "habits"
        return state
    
    async def _ask_habits(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Ask about current habits"""
        state["messages"].append(
            "📍 Шаг 3/5: Что уже делаешь?\n\n"
            "☐ Медитация\n"
            "☐ Йога\n"
            "☐ Спорт\n"
            "☐ Веду дневник\n"
            "☐ Ничего из этого\n\n"
            "Есть ли физические ограничения?"
        )
        state["step"] = "problems"
        return state
    
    async def _identify_problems(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Identify current problems"""
        state["messages"].append(
            "📍 Шаг 4/5: Что хочешь улучшить?\n\n"
            "☐ Финансы (нестабильные доходы, нехватка денег)\n"
            "☐ Отношения (конфликты с командой, партнёрами)\n"
            "☐ Здоровье (стресс, усталость)\n"
            "☐ Концентрация (сложно сосредоточиться)\n"
            "☐ Другое"
        )
        state["step"] = "partners"
        return state
    
    async def _setup_partners(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Setup partner groups"""
        state["messages"].append(
            "📍 Шаг 5/5: Твои ключевые партнёры\n\n"
            "Подумай о 4 группах:\n"
            "1. 👥 Коллеги - кто рядом с тобой?\n"
            "2. 🤝 Клиенты - кого ты обслуживаешь?\n"
            "3. 📦 Поставщики - кто тебе помогает?\n"
            "4. 🌍 Мир - кому ещё можешь помочь?\n\n"
            "Добавишь конкретных людей после завершения."
        )
        state["step"] = "summary"
        return state
    
    async def _generate_summary(self, state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Generate personalized summary"""
        state["messages"].append(
            "🎉 Отлично! Знакомство завершено.\n\n"
            "Я составил для тебя персональный план. "
            "Открой приложение, чтобы увидеть его.\n\n"
            "Каждое утро буду присылать тебе:\n"
            "• Цитату для размышления\n"
            "• 4 действия на день\n"
            "• Напоминания о практиках\n\n"
            "Поехали! 🚀"
        )
        state["completed"] = True
        return state
    
    async def run(self, initial_state: OnboardingWorkflowState) -> OnboardingWorkflowState:
        """Run the onboarding workflow"""
        result = await self.graph.ainvoke(initial_state)
        return result
