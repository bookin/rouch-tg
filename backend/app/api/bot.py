"""Telegram Bot handlers"""
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (
    Message, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, 
    ErrorEvent, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
import logging
from app.config import get_settings
from app.workflows.onboarding import (
    OnboardingSteps, 
    get_step_data,
    save_onboarding_progress
)
from app.api.middleware.typing_middleware import TypingMiddleware
from sqlalchemy import select
from app.models.db.practice import PracticeDB

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
from app.mock_bot import MockBot

MENU_OPEN_APP = "📱 Открыть приложение"
MENU_SOLVER = "💭 Проблемы"
MENU_TODAY = "📋 План"
MENU_SEED = "🌱 Записать семя"
MENU_COFFEE = "☕️ Кофе-медитация"
MENU_DONE = "✅ Отметить выполнение"
MENU_SETTINGS = "⚙️ Настройки"
MENU_PARTNERS = "🤝 Партнёры"
MENU_PROJECTS = "🎯 Проекты"
MENU_PRACTICES = "🧘 Практики"
MENU_RESET = "🔄 Сброс прогресса"

if settings.TELEGRAM_ENABLED:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
else:
    bot = MockBot()
dp = Dispatcher()
router = Router()

# Register middleware
router.message.middleware(TypingMiddleware())
router.callback_query.middleware(TypingMiddleware())


@dp.error()
async def error_handler(event: ErrorEvent):
    """Global error handler for bot"""
    logger.error(f"Bot error: {event.exception}", exc_info=True)
    
    if event.update.message:
        try:
            await event.update.message.answer(
                "Произошла ошибка. Попробуй еще раз или напиши /start"
            )
        except TelegramAPIError as e:
            logger.error(f"Failed to send error message to user: {e}")
            pass


class SeedState(StatesGroup):
    """States for seed recording"""
    waiting_for_description = State()


class ActionState(StatesGroup):
    """States for action completion"""
    waiting_for_action_id = State()


class OnboardingState(StatesGroup):
    """States for onboarding flow"""
    occupation = State()
    schedule = State()
    duration = State()
    habits = State()
    restrictions = State()
    partners = State()


class ProblemState(StatesGroup):
    """States for problem solving"""
    waiting_for_description = State()
    diagnostic_in_progress = State()
    waiting_for_diagnostic_answer = State()


class ProjectSetupState(StatesGroup):
    """States for setting up a new project (partners)"""
    waiting_for_source = State()
    waiting_for_ally = State()
    waiting_for_protege = State()
    waiting_for_world = State()


class CoffeeState(StatesGroup):
    """States for interactive coffee meditation in bot"""
    step_1 = State()
    step_2 = State()
    step_3 = State()
    step_4_notes = State()


class SettingsState(StatesGroup):
    """States for /settings edits"""
    waiting_for_name = State()
    waiting_for_occupation = State()
    waiting_for_email = State()
    waiting_for_timezone = State()


# Map generic steps to FSM states
STEP_STATE_MAP = {
    OnboardingSteps.OCCUPATION: OnboardingState.occupation,
    OnboardingSteps.SCHEDULE: OnboardingState.schedule,
    OnboardingSteps.DURATION: OnboardingState.duration,
    OnboardingSteps.HABITS: OnboardingState.habits,
    OnboardingSteps.RESTRICTIONS: OnboardingState.restrictions,
    OnboardingSteps.PARTNERS: OnboardingState.partners,
}


def get_main_menu() -> ReplyKeyboardMarkup:
    """Build the main reply keyboard menu.

    Returns:
        ReplyKeyboardMarkup: The main menu layout.
    """
    keyboard = [
        [
            KeyboardButton(
                text=MENU_OPEN_APP,
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )
        ],
        [KeyboardButton(text=MENU_SOLVER), KeyboardButton(text=MENU_TODAY)],
        [KeyboardButton(text=MENU_SEED), KeyboardButton(text=MENU_COFFEE)],
        [KeyboardButton(text=MENU_DONE), KeyboardButton(text=MENU_SETTINGS)],
        [KeyboardButton(text=MENU_PARTNERS), KeyboardButton(text=MENU_PROJECTS)],
        [KeyboardButton(text=MENU_PRACTICES)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def _build_webapp_url(path: str) -> str:
    base = settings.WEBAPP_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}" if clean_path else base


async def show_main_menu(message: Message) -> None:
    """Show the main menu to the user."""
    await message.answer(
        "Я рядом. Выбирай, куда хочешь двигаться дальше.",
        reply_markup=get_main_menu(),
    )


async def _send_menu_hint(message: Message, hint: str) -> None:
    """Send a hint message, then show the main menu.

    Args:
        message: Incoming Telegram message.
        hint: Short supportive hint for the user.
    """
    await message.answer(hint)
    await show_main_menu(message)


def _build_today_view(
    tasks: list[dict],
    preface: str | None = None,
) -> tuple[str, InlineKeyboardMarkup | None]:
    lines: list[str] = []
    buttons: list[list[InlineKeyboardButton]] = []

    completed = sum(1 for task in tasks if task.get("completed"))
    total = len(tasks)
    remaining = max(total - completed, 0)
    percent = int((completed / total) * 100) if total else 0

    for idx, task in enumerate(tasks[:10], start=1):
        mark = "✅" if task.get("completed") else "⬜️"
        desc = task.get("desc", "")
        lines.append(f"Шаг {idx}\n{mark} {desc}")

        if not task.get("completed") and task.get("id"):
            label = f"✅ {idx}"
            buttons.append(
                [InlineKeyboardButton(text=label, callback_data=f"task_done_{task['id']}")]
            )

    text = "📋 Твой план на сегодня\n"
    text += "Ниже шаги, которые приближают тебя к цели.\n\n"
    text += f"💛 Пульс дня: {completed}/{total} • {percent}% • осталось {remaining}\n\n"
    text += "\n\n".join(lines)

    if buttons:
        text += "\n\nМожно отметить шаг прямо здесь — нажми кнопку нужного номера."
    else:
        text += "\n\nВсе шаги уже отмечены. Ты большой молодец!"

    if preface:
        text = f"{preface}\n\n{text}"

    buttons.append([InlineKeyboardButton(text="Поделиться прогрессом ✨", callback_data="share_progress")])
    buttons.append(
        [
            InlineKeyboardButton(
                text="Открыть план в приложении 📲",
                web_app=WebAppInfo(url=_build_webapp_url("/")),
            )
        ]
    )

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_share_progress_text(tasks: list[dict]) -> str:
    completed_tasks = [t for t in tasks if t.get("completed")]
    total = len(tasks)
    completed = len(completed_tasks)
    remaining = max(total - completed, 0)

    lines = ["✨ Мой кармический прогресс сегодня", f"✅ Выполнено: {completed}/{total}"]
    if remaining:
        lines.append(f"⏳ Осталось: {remaining}")

    if completed_tasks:
        lines.append("\nСделал(а):")
        for task in completed_tasks[:8]:
            desc = task.get("desc", "")
            lines.append(f"• {desc}")
    else:
        lines.append("\nСегодня только начинаю, но путь уже выбран 🌱")

    lines.append("\nПродолжаю путь к цели. Пусть будет мягко и честно.")
    return "\n".join(lines)


def _format_practice_steps(steps: list[str] | None) -> str:
    items = [s.strip() for s in (steps or []) if s and s.strip()]
    if not items:
        return "1. Сделай практику мягко и осознанно, без спешки."
    return "\n".join([f"{idx + 1}. {step}" for idx, step in enumerate(items)])


async def _load_practice_by_id(db: Any, practice_id: str) -> PracticeDB | None:
    result = await db.execute(
        select(PracticeDB).where(PracticeDB.id == practice_id).limit(1)
    )
    return result.scalar_one_or_none()


async def _load_user_by_telegram(db: Any, telegram_id: int):
    from app.repositories.user import UserRepository

    return await UserRepository().get_by_telegram_id(db, telegram_id)


async def _load_active_practices(db: Any, user_id: int):
    from app.services.practice_service import PracticeService

    progress_list = await PracticeService().get_user_progress(db, user_id)
    return [p for p in progress_list if p.is_active and not p.is_hidden]


def _build_practice_need(strategy: dict | None) -> str:
    if strategy:
        need = (
            f"{strategy.get('problem_text', '')} {strategy.get('stop_action', '')} "
            f"{strategy.get('start_action', '')} {strategy.get('grow_action', '')}"
        ).strip()
        if need:
            return need
    return "общее развитие, осознанность, кармические практики"


async def _load_practice_recommendations(
    db: Any,
    user_db: Any,
    offset: int = 0,
    limit: int = 5,
):
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.repositories.karma_plan import KarmaPlanRepository
    from app.services.practice_service import PracticeService

    practice_svc = PracticeService()
    existing_progress = await practice_svc.get_user_progress(db, user_db.id)
    existing_ids = {str(p.practice_id) for p in existing_progress}

    plan = await KarmaPlanRepository().get_active(db, user_db.id)
    strategy = plan.strategy_snapshot if plan else None
    need = _build_practice_need(strategy)

    qdrant = QdrantKnowledgeBase(get_settings().QDRANT_URL)
    fetched = await qdrant.search_practice(
        need=need,
        restrictions=user_db.physical_restrictions.split(",") if user_db.physical_restrictions else None,
        limit=offset + limit,
    )
    filtered = [r for r in fetched if str(r.get("id", "")) not in existing_ids]
    chunk = filtered[offset:offset + limit]
    has_more = len(filtered) > offset + limit
    return chunk, has_more


def _build_practice_list_keyboard(practices: list[PracticeDB]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for practice in practices:
        title = practice.name
        buttons.append([
            InlineKeyboardButton(
                text=f"▶️ Начать {title}",
                callback_data=f"practice_do_{practice.id}",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text=f"ℹ️ Подробнее {title}",
                callback_data=f"practice_view_{practice.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="✨ Найти новые практики", callback_data="practices_rec_0")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_practice_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Найти новые практики", callback_data="practices_rec_0")]
        ]
    )


def _build_practice_rec_keyboard(recommendations: list[dict], offset: int, has_more: bool) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for rec in recommendations:
        title = rec.get("name") or "Практика"
        pid = str(rec.get("id"))
        buttons.append([
            InlineKeyboardButton(
                text=f"🌟 Активировать {title}",
                callback_data=f"practice_activate_{pid}",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text=f"ℹ️ Подробнее {title}",
                callback_data=f"practice_view_{pid}",
            )
        ])
    if has_more:
        buttons.append([
            InlineKeyboardButton(
                text="Ещё практики",
                callback_data=f"practices_rec_{offset + len(recommendations)}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад к активным", callback_data="practices_active")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_practice_execute_keyboard(practice_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"practice_done_{practice_id}")],
            [InlineKeyboardButton(text="Отложить", callback_data="practice_defer")],
            [InlineKeyboardButton(text="⬅️ Назад к практикам", callback_data="practices_active")],
        ]
    )


def _build_practice_detail_keyboard(
    practice_id: str,
    can_activate: bool,
    next_offset: int | None = None,
) -> InlineKeyboardMarkup:
    buttons = []
    if can_activate:
        buttons.append([
            InlineKeyboardButton(text="🌟 Активировать", callback_data=f"practice_activate_{practice_id}")
        ])
    buttons.append([
        InlineKeyboardButton(text="▶️ Начать", callback_data=f"practice_do_{practice_id}")
    ])
    if next_offset is not None:
        buttons.append([
            InlineKeyboardButton(text="✨ Ещё практики", callback_data=f"practices_rec_{next_offset}")
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад к практикам", callback_data="practices_active")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_practice_detail_text(practice: PracticeDB) -> str:
    duration = f"{practice.duration_minutes} мин" if practice.duration_minutes else "—"
    benefits = practice.benefits or "Пусть эта практика мягко поддержит тебя."
    contraindications = (
        ", ".join(practice.contraindications or []) if practice.contraindications else "нет"
    )
    steps_text = _format_practice_steps(practice.steps or [])
    return (
        f"🧘 {practice.name}\n"
        f"Категория: {practice.category}\n"
        f"Длительность: {duration}\n\n"
        f"Польза: {benefits}\n\n"
        f"Что делать:\n{steps_text}\n\n"
        f"Если есть ограничения: {contraindications}"
    )


async def _send_practices_active(target: Message | CallbackQuery) -> None:
    from app.database import AsyncSessionLocal

    telegram_id = target.from_user.id if isinstance(target, (Message, CallbackQuery)) else None
    if telegram_id is None:
        return

    async with AsyncSessionLocal() as db:
        user_db = await _load_user_by_telegram(db, telegram_id)
        if not user_db:
            if isinstance(target, Message):
                await target.answer("Я пока не вижу тебя в системе. Нажми /start — и начнём мягко заново.")
            else:
                await target.message.edit_text("Я пока не вижу тебя в системе. Нажми /start — и начнём мягко заново.")
            return

        active_practices = await _load_active_practices(db, user_db.id)
        if not active_practices:
            text = (
                "🧘 Пока нет активных практик.\n\n"
                "Хочешь, подберём новые? Я покажу несколько вариантов и шаги выполнения."
            )
            markup = _build_practice_empty_keyboard()
        else:
            lines = ["🧘 Твои активные практики", "Выбирай — и я покажу шаги."]
            for idx, progress in enumerate(active_practices[:5], start=1):
                practice = progress.practice
                title = practice.name if practice else "Практика"
                duration = f"{practice.duration_minutes} мин" if practice and practice.duration_minutes else "—"
                lines.append(f"{idx}. {title} · {duration}")
            text = "\n".join(lines)
            markup = _build_practice_list_keyboard(
                [p.practice for p in active_practices if p.practice][:5]
            )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)
        await show_main_menu(target)


async def _send_practices_recommendations(
    target: CallbackQuery,
    offset: int,
    state: FSMContext | None = None,
) -> None:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user_db = await _load_user_by_telegram(db, target.from_user.id)
        if not user_db:
            await target.message.edit_text("Я пока не вижу тебя в системе. Нажми /start — и начнём мягко заново.")
            await target.answer()
            return

        recommendations, has_more = await _load_practice_recommendations(db, user_db, offset=offset)
        if not recommendations:
            await target.message.edit_text(
                "Пока не нашёл новых практик. Давай попробуем позже или вернёмся к активным.",
                reply_markup=_build_practice_rec_keyboard([], offset, has_more=False),
            )
            await target.answer()
            return

        lines = ["✨ Вот практики, которые могут подойти", "Выбирай любую — покажу шаги."]
        for idx, rec in enumerate(recommendations, start=1):
            title = rec.get("name") or "Практика"
            duration = rec.get("duration") or "—"
            lines.append(f"{idx}. {title} · {duration} мин")

        await target.message.edit_text(
            "\n".join(lines),
            reply_markup=_build_practice_rec_keyboard(recommendations, offset, has_more),
        )
        if state:
            await state.update_data(practices_rec_offset=offset)
        await target.answer()


async def _activate_practice(db: Any, user_db: Any, practice_id: str) -> bool:
    from app.services.practice_service import PracticeService
    from app.repositories.karma_plan import KarmaPlanRepository

    practice = await _load_practice_by_id(db, practice_id)
    if not practice:
        return False

    active_plan = await KarmaPlanRepository().get_active(db, user_db.id)
    await PracticeService().practice_repo.get_or_create(
        db, user_db.id, practice_id, karma_plan_id=(active_plan.id if active_plan else None)
    )
    return True


async def _send_coffee_intro(message: Message) -> None:
    """Send the coffee meditation intro with a start button."""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать ☕️", callback_data="cf_start")]]
    )
    await message.answer(
        "Готов(а) к короткой тёплой практике? Нажми «Начать».",
        reply_markup=kb,
    )


async def _start_onboarding(message: Message, state: FSMContext) -> None:
    await _send_onboarding_step(message, state, OnboardingSteps.OCCUPATION)


async def _send_onboarding_step(message: Message, state: FSMContext, step: str) -> None:
    step_data = get_step_data(step)
    input_type = step_data.get("input_type")
    options = step_data.get("options") or []

    fsm_state = STEP_STATE_MAP.get(step)
    if fsm_state:
        await state.set_state(fsm_state)
    await state.update_data(onb_step=step)

    if input_type in {"single_choice", "confirm"}:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=opt["label"])] for opt in options],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(step_data["message"], reply_markup=kb)
        return

    if input_type == "multi_choice":
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=opt["label"])] for opt in options]
            + [[KeyboardButton(text="Готово")]],
            resize_keyboard=True,
            one_time_keyboard=False,
        )
        await state.update_data(onb_multi_selected=[])
        await message.answer(
            step_data["message"] + "\n\nВыбирай пункты и потом нажми «Готово».",
            reply_markup=kb,
        )
        return

    if input_type == "text_optional":
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="➡️ Пропустить")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(step_data["message"], reply_markup=kb)
        return

    await message.answer(step_data["message"], reply_markup=ReplyKeyboardRemove())


def _option_id_by_label(step: str, label: str) -> str | None:
    step_data = get_step_data(step)
    for opt in step_data.get("options") or []:
        if opt.get("label") == label:
            return str(opt.get("id"))
    return None


def _selected_labels(step: str, ids_or_custom: list[str]) -> str:
    step_data = get_step_data(step)
    label_by_id = {str(opt.get("id")): str(opt.get("label")) for opt in (step_data.get("options") or [])}
    parts: list[str] = []
    for v in ids_or_custom:
        parts.append(label_by_id.get(v, v))
    return ", ".join(parts)


@router.message(F.text == "🚀 Начать знакомство")
async def start_onboarding(message: Message, state: FSMContext) -> None:
    await _start_onboarding(message, state)


async def _handle_open_app(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_menu_hint(
        message,
        "Я рядом. Нажми «Открыть приложение» — и продолжим там.",
    )


async def _handle_solver(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_menu_hint(
        message,
        "Чтобы решить проблему глубоко и спокойно, лучше открыть приложение.",
    )


async def _handle_today(message: Message, state: FSMContext) -> None:
    await state.clear()
    data = await _cf_load_data(message.from_user.id)
    if not data:
        await _send_menu_hint(
            message,
            "Сейчас нет активного проекта. Давай сначала соберём его в приложении.",
        )
        return

    tasks = data.get("tasks", [])
    if not tasks:
        await _send_menu_hint(
            message,
            "Сегодня шагов пока нет. Это нормально. Если хочешь — открой приложение и выберем путь.",
        )
        return
    text, reply_markup = _build_today_view(tasks)
    await message.answer(text, reply_markup=reply_markup)
    await show_main_menu(message)


async def _handle_coffee(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_coffee_intro(message)


async def _start_seed_flow(message: Message, state: FSMContext) -> None:
    await state.set_state(SeedState.waiting_for_description)
    await message.answer(
        "Опиши доброе действие одним коротким предложением.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _start_done_flow(message: Message, state: FSMContext) -> None:
    data = await _cf_load_data(message.from_user.id)
    if not data:
        await _send_menu_hint(
            message,
            "Сейчас нет активного проекта. Давай сначала соберём его в приложении.",
        )
        return

    tasks = [t for t in data.get("tasks", []) if not t.get("completed")]
    if not tasks:
        await _send_menu_hint(
            message,
            "Все шаги на сегодня уже отмечены. Ты молодец!",
        )
        return

    lines = []
    action_tasks = []
    for idx, task in enumerate(tasks[:10], start=1):
        lines.append(f"{idx}. ⬜️ {task.get('desc', '')}")
        action_tasks.append({"id": task.get("id"), "desc": task.get("desc", "")})

    await state.set_state(ActionState.waiting_for_action_id)
    await state.update_data(action_tasks=action_tasks)
    await message.answer(
        "Напиши номер шага, который хочешь отметить.\n\n"
        + "\n".join(lines)
        + "\n\nЕсли передумал(а), напиши «Отмена».",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _handle_reset(message: Message, state: FSMContext) -> None:
    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да, сбросить", callback_data="reset_confirm")],
            [InlineKeyboardButton(text="Нет, оставить", callback_data="reset_cancel")],
        ]
    )
    await message.answer(
        "Сброс удалит твои текущие шаги, семена и прогресс.\n"
        "Если ты уверен(а) — нажми «Да, сбросить».",
        reply_markup=kb,
    )


async def _handle_partners(message: Message, state: FSMContext) -> None:
    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть партнёров 🤝",
                    web_app=WebAppInfo(url=_build_webapp_url("/partners")),
                )
            ]
        ]
    )
    await message.answer(
        "Хочешь увидеть своих партнёров и их роли? Открой раздел — там всё аккуратно разложено.",
        reply_markup=kb,
    )
    await show_main_menu(message)


async def _handle_projects(message: Message, state: FSMContext) -> None:
    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть проекты 🎯",
                    web_app=WebAppInfo(url=_build_webapp_url("/problem")),
                )
            ]
        ]
    )
    await message.answer(
        "Готов(а) посмотреть или запустить проект? Открой раздел — там мягко проведём дальше.",
        reply_markup=kb,
    )
    await show_main_menu(message)


async def _handle_practices(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_practices_active(message)


async def _show_settings_menu(message: Message, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository

    await state.clear()

    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, message.from_user.id)
            email = user_db.email if user_db else None

        buttons = []
        if email:
            buttons.append([InlineKeyboardButton(text=f"📧 Email: {email}", callback_data="noop")])
        else:
            buttons.append([InlineKeyboardButton(text="📧 Привязать email", callback_data="settings_email")])
        buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="settings_close")])

        await message.answer(
            "⚙️ Настройки\n\nЧто хочешь сделать?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
    except Exception as e:
        logger.error(f"cmd_settings error: {e}", exc_info=True)
        await message.answer("Не получилось открыть настройки. Попробуй чуть позже.")


@router.message(StateFilter(None), F.text == MENU_OPEN_APP)
async def menu_open_app(message: Message, state: FSMContext) -> None:
    await _handle_open_app(message, state)


@router.message(StateFilter(None), F.text == MENU_SOLVER)
async def menu_solver(message: Message, state: FSMContext) -> None:
    await _handle_solver(message, state)


@router.message(StateFilter(None), F.text == MENU_TODAY)
async def menu_today(message: Message, state: FSMContext) -> None:
    await _handle_today(message, state)


@router.message(StateFilter(None), F.text == MENU_COFFEE)
async def menu_coffee(message: Message, state: FSMContext) -> None:
    await _handle_coffee(message, state)


@router.message(StateFilter(None), F.text == MENU_SEED)
async def menu_seed(message: Message, state: FSMContext) -> None:
    await _start_seed_flow(message, state)


@router.message(StateFilter(None), F.text == MENU_DONE)
async def menu_done(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _start_done_flow(message, state)


@router.message(StateFilter(None), F.text == MENU_SETTINGS)
async def menu_settings(message: Message, state: FSMContext) -> None:
    await _show_settings_menu(message, state)


@router.message(StateFilter(None), F.text == MENU_PARTNERS)
async def menu_partners(message: Message, state: FSMContext) -> None:
    await _handle_partners(message, state)


@router.message(StateFilter(None), F.text == MENU_PROJECTS)
async def menu_projects(message: Message, state: FSMContext) -> None:
    await _handle_projects(message, state)


@router.message(StateFilter(None), F.text == MENU_PRACTICES)
async def menu_practices(message: Message, state: FSMContext) -> None:
    await _handle_practices(message, state)


@router.message(StateFilter(None), F.text == MENU_RESET)
async def menu_reset(message: Message, state: FSMContext) -> None:
    await _handle_reset(message, state)


@router.message(Command("app"))
async def cmd_app(message: Message, state: FSMContext) -> None:
    await _handle_open_app(message, state)


@router.message(Command("solver"))
async def cmd_solver(message: Message, state: FSMContext) -> None:
    await _handle_solver(message, state)


@router.message(Command("today"))
async def cmd_today(message: Message, state: FSMContext) -> None:
    await _handle_today(message, state)


@router.message(Command("coffee"))
async def cmd_coffee(message: Message, state: FSMContext) -> None:
    await _handle_coffee(message, state)


@router.message(Command("seed"))
async def cmd_seed(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _start_seed_flow(message, state)


@router.message(Command("done"))
async def cmd_done(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _start_done_flow(message, state)


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    await _handle_reset(message, state)


@router.message(Command("practices"))
async def cmd_practices(message: Message, state: FSMContext) -> None:
    await _handle_practices(message, state)


@router.callback_query(F.data == "practices_active")
async def cb_practices_active(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(practices_rec_offset=0)
    await _send_practices_active(callback)


@router.callback_query(F.data.startswith("practices_rec_"))
async def cb_practices_rec(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    raw_offset = callback.data.replace("practices_rec_", "") if callback.data else "0"
    offset = int(raw_offset) if raw_offset.isdigit() else 0
    await _send_practices_recommendations(callback, offset, state)


@router.callback_query(F.data.startswith("practice_view_"))
async def cb_practice_view(callback: CallbackQuery, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal
    from app.services.practice_service import PracticeService

    practice_id = callback.data.replace("practice_view_", "") if callback.data else ""
    if not practice_id:
        await callback.answer("Не вижу практику. Попробуй ещё раз.")
        return

    async with AsyncSessionLocal() as db:
        user_db = await _load_user_by_telegram(db, callback.from_user.id)
        if not user_db:
            await callback.message.edit_text("Я пока не вижу тебя в системе. Нажми /start — и начнём мягко заново.")
            await callback.answer()
            return

        practice = await _load_practice_by_id(db, practice_id)
        if not practice:
            await callback.message.edit_text("Эту практику пока не удалось найти. Попробуй другую.")
            await callback.answer()
            return

        progress = await PracticeService().practice_repo.get_by_user_and_practice(
            db, user_db.id, practice_id
        )
        can_activate = not bool(progress and progress.is_active)
        rec_data = await state.get_data()
        offset = rec_data.get("practices_rec_offset")
        next_offset = offset + 5 if isinstance(offset, int) else None
        text = _build_practice_detail_text(practice)
        await callback.message.edit_text(
            text,
            reply_markup=_build_practice_detail_keyboard(practice_id, can_activate, next_offset),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("practice_activate_"))
async def cb_practice_activate(callback: CallbackQuery, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal

    practice_id = callback.data.replace("practice_activate_", "") if callback.data else ""
    if not practice_id:
        await callback.answer("Не вижу практику. Попробуй ещё раз.")
        return

    async with AsyncSessionLocal() as db:
        user_db = await _load_user_by_telegram(db, callback.from_user.id)
        if not user_db:
            await callback.message.edit_text("Я пока не вижу тебя в системе. Нажми /start — и начнём мягко заново.")
            await callback.answer()
            return

        ok = await _activate_practice(db, user_db, practice_id)
        await db.commit()

    if ok:
        await callback.message.answer("🌱 Практика добавлена. Хочешь начать прямо сейчас?")
        await _send_practices_active(callback)
    else:
        await callback.message.edit_text("Не получилось активировать практику. Попробуй позже.")
        await callback.answer()


@router.callback_query(F.data.startswith("practice_do_"))
async def cb_practice_do(callback: CallbackQuery, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal

    practice_id = callback.data.replace("practice_do_", "") if callback.data else ""
    if not practice_id:
        await callback.answer("Не вижу практику. Попробуй ещё раз.")
        return

    async with AsyncSessionLocal() as db:
        user_db = await _load_user_by_telegram(db, callback.from_user.id)
        if not user_db:
            await callback.message.edit_text("Я пока не вижу тебя в системе. Нажми /start — и начнём мягко заново.")
            await callback.answer()
            return

        ok = await _activate_practice(db, user_db, practice_id)
        practice = await _load_practice_by_id(db, practice_id)
        await db.commit()

        if not ok or not practice:
            await callback.message.edit_text("Не удалось начать практику. Попробуй ещё раз.")
            await callback.answer()
            return

        text = (
            f"🧘 {practice.name}\n\n"
            f"Что делать:\n{_format_practice_steps(practice.steps or [])}"
        )
        await callback.message.edit_text(
            text,
            reply_markup=_build_practice_execute_keyboard(practice_id),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("practice_done_"))
async def cb_practice_done(callback: CallbackQuery, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal
    from app.services.practice_service import PracticeService
    from app.repositories.karma_plan import KarmaPlanRepository

    practice_id = callback.data.replace("practice_done_", "") if callback.data else ""
    if not practice_id:
        await callback.answer("Не вижу практику. Попробуй ещё раз.")
        return

    async with AsyncSessionLocal() as db:
        user_db = await _load_user_by_telegram(db, callback.from_user.id)
        if not user_db:
            await callback.message.edit_text("Я пока не вижу тебя в системе. Нажми /start — и начнём мягко заново.")
            await callback.answer()
            return

        plan = await KarmaPlanRepository().get_active(db, user_db.id)
        await PracticeService().complete_and_create_seed(
            db,
            user_id=user_db.id,
            practice_id=practice_id,
            karma_plan_id=(plan.id if plan else None),
            emotion_score=5,
        )
        await db.commit()

    await callback.message.edit_text(
        "✅ Практика отмечена. Спасибо за тёплое усилие!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к практикам", callback_data="practices_active")]]
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "practice_defer")
async def cb_practice_defer(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_practices_active(callback)


@router.message(SeedState.waiting_for_description)
async def seed_receive_description(message: Message, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal
    from app.models.seed import Seed
    from app.repositories.karma_plan import KarmaPlanRepository
    from app.repositories.user import UserRepository
    from app.services.seed_service import SeedService

    text = (message.text or "").strip()
    if not text:
        await message.answer("Напиши пару слов — я бережно запишу их как семя.")
        return

    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, message.from_user.id)
            if not user_db:
                await message.answer("Я тебя не вижу в системе. Нажми /start, и начнём мягко заново.")
                await state.clear()
                return

            plan = await KarmaPlanRepository().get_active(db, user_db.id)
            if not plan:
                await message.answer(
                    "Сейчас нет активного проекта. Давай сначала соберём его в приложении."
                )
                await state.clear()
                await show_main_menu(message)
                return

            seed = Seed(
                user_id=user_db.id,
                action_type="kindness",
                description=text,
                partner_group="world",
                intention_score=5,
                emotion_level=5,
                understanding=True,
                estimated_maturation_days=21,
                strength_multiplier=1.0,
                karma_plan_id=plan.id,
            )
            seed_svc = SeedService()
            await seed_svc.create_seed(db, seed)
            await seed_svc.user_repo.increment_seeds_count(db, user_db.id)
            await db.commit()

        await state.clear()
        await message.answer("✨ Семя сохранено. Спасибо за доброе действие.")
        await show_main_menu(message)
    except Exception as e:
        logger.error(f"seed_receive_description error: {e}", exc_info=True)
        await message.answer("Не получилось сохранить семя. Давай попробуем ещё раз чуть позже.")
        await state.clear()
        await show_main_menu(message)


@router.message(ActionState.waiting_for_action_id)
async def action_receive_number(message: Message, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository
    from app.services.daily_service import DailyService

    text = (message.text or "").strip()
    if text.lower() == "отмена":
        await state.clear()
        await message.answer("Хорошо, вернул тебя в меню.")
        await show_main_menu(message)
        return

    if not text.isdigit():
        await message.answer("Напиши номер шага из списка или «Отмена».")
        return

    idx = int(text)
    data = await state.get_data()
    tasks = list(data.get("action_tasks", []))
    if idx < 1 or idx > len(tasks):
        await message.answer("Такого номера нет. Выбери номер из списка или напиши «Отмена».")
        return

    task_id = tasks[idx - 1].get("id")
    if not task_id:
        await message.answer("Не смог найти этот шаг. Попробуй ещё раз.")
        return

    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, message.from_user.id)
            if not user_db:
                await message.answer("Я тебя не вижу в системе. Нажми /start, и начнём мягко заново.")
                await state.clear()
                return

            ok = await DailyService().toggle_task_completion(
                db, user_id=user_db.id, task_id=int(task_id), completed=True
            )
            await db.commit()

        if not ok:
            await message.answer("Не получилось отметить шаг. Попробуй выбрать другой номер.")
            return

        await state.clear()
        await message.answer("✅ Готово. Шаг отмечен, ты молодец!")
        await show_main_menu(message)
    except Exception as e:
        logger.error(f"action_receive_number error: {e}", exc_info=True)
        await message.answer("Что-то помешало отметить шаг. Давай попробуем позже.")
        await state.clear()
        await show_main_menu(message)


@router.message(OnboardingState.occupation)
async def onb_occupation(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    if data.get("onb_expect_custom"):
        await state.update_data(onb_expect_custom=False)
        await save_onboarding_progress(message.from_user.id, OnboardingSteps.OCCUPATION, text, by_telegram_id=True)
        await _send_onboarding_step(message, state, OnboardingSteps.SCHEDULE)
        return

    opt_id = _option_id_by_label(OnboardingSteps.OCCUPATION, text)
    if not opt_id:
        await message.answer("Выбери вариант кнопкой — так будет проще.")
        return

    if opt_id == "other":
        await state.update_data(onb_expect_custom=True)
        await message.answer("Напиши, пожалуйста, одним коротким словом: ", reply_markup=ReplyKeyboardRemove())
        return

    await save_onboarding_progress(message.from_user.id, OnboardingSteps.OCCUPATION, opt_id, by_telegram_id=True)
    await _send_onboarding_step(message, state, OnboardingSteps.SCHEDULE)


@router.message(OnboardingState.schedule)
async def onb_schedule(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    selected: list[str] = list(data.get("onb_multi_selected") or [])

    if data.get("onb_expect_custom"):
        await state.update_data(onb_expect_custom=False)
        if text:
            selected.append(text)
            await state.update_data(onb_multi_selected=selected)
        await message.answer(f"Сейчас выбрано: { _selected_labels(OnboardingSteps.SCHEDULE, selected) or '—' }\nНажми «Готово», когда будешь готов(а).")
        return

    if text == "Готово":
        if not selected:
            await message.answer("Выбери хотя бы один вариант — и нажми «Готово».")
            return
        await save_onboarding_progress(message.from_user.id, OnboardingSteps.SCHEDULE, selected, by_telegram_id=True)
        await _send_onboarding_step(message, state, OnboardingSteps.DURATION)
        return

    opt_id = _option_id_by_label(OnboardingSteps.SCHEDULE, text)
    if not opt_id:
        await message.answer("Выбирай пункты кнопками и потом нажми «Готово».")
        return

    if opt_id == "other":
        await state.update_data(onb_expect_custom=True)
        await message.answer("Напиши свой вариант одним текстом:", reply_markup=ReplyKeyboardRemove())
        return

    if opt_id == "none":
        selected = ["none"]
        await save_onboarding_progress(message.from_user.id, OnboardingSteps.SCHEDULE, selected, by_telegram_id=True)
        await _send_onboarding_step(message, state, OnboardingSteps.DURATION)
        return

    if opt_id in selected:
        selected = [v for v in selected if v != opt_id]
    else:
        selected.append(opt_id)
        selected = [v for v in selected if v != "none"]

    await state.update_data(onb_multi_selected=selected)
    await message.answer(f"Сейчас выбрано: { _selected_labels(OnboardingSteps.SCHEDULE, selected) or '—' }\nНажми «Готово», когда будешь готов(а).")


@router.message(OnboardingState.duration)
async def onb_duration(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    opt_id = _option_id_by_label(OnboardingSteps.DURATION, text)
    if not opt_id:
        await message.answer("Выбери вариант кнопкой — так будет проще.")
        return

    await save_onboarding_progress(message.from_user.id, OnboardingSteps.DURATION, opt_id, by_telegram_id=True)
    await _send_onboarding_step(message, state, OnboardingSteps.HABITS)


@router.message(OnboardingState.habits)
async def onb_habits(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    selected: list[str] = list(data.get("onb_multi_selected") or [])

    if data.get("onb_expect_custom"):
        await state.update_data(onb_expect_custom=False)
        if text:
            selected.append(text)
            await state.update_data(onb_multi_selected=selected)
        await message.answer(f"Сейчас выбрано: { _selected_labels(OnboardingSteps.HABITS, selected) or '—' }\nНажми «Готово», когда будешь готов(а).")
        return

    if text == "Готово":
        if not selected:
            await message.answer("Выбери хотя бы один вариант — и нажми «Готово».")
            return
        await save_onboarding_progress(message.from_user.id, OnboardingSteps.HABITS, selected, by_telegram_id=True)
        await _send_onboarding_step(message, state, OnboardingSteps.RESTRICTIONS)
        return

    opt_id = _option_id_by_label(OnboardingSteps.HABITS, text)
    if not opt_id:
        await message.answer("Выбирай пункты кнопками и потом нажми «Готово».")
        return

    if opt_id == "other":
        await state.update_data(onb_expect_custom=True)
        await message.answer("Напиши свой вариант одним текстом:", reply_markup=ReplyKeyboardRemove())
        return

    if opt_id == "none":
        selected = ["none"]
        await save_onboarding_progress(message.from_user.id, OnboardingSteps.HABITS, selected, by_telegram_id=True)
        await _send_onboarding_step(message, state, OnboardingSteps.RESTRICTIONS)
        return

    if opt_id in selected:
        selected = [v for v in selected if v != opt_id]
    else:
        selected.append(opt_id)
        selected = [v for v in selected if v != "none"]

    await state.update_data(onb_multi_selected=selected)
    await message.answer(f"Сейчас выбрано: { _selected_labels(OnboardingSteps.HABITS, selected) or '—' }\nНажми «Готово», когда будешь готов(а).")


@router.message(OnboardingState.restrictions)
async def onb_restrictions(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    answer = "skip" if text == "➡️ Пропустить" else text
    await save_onboarding_progress(message.from_user.id, OnboardingSteps.RESTRICTIONS, answer, by_telegram_id=True)
    await _send_onboarding_step(message, state, OnboardingSteps.PARTNERS)


@router.message(OnboardingState.partners)
async def onb_partners(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    opt_id = _option_id_by_label(OnboardingSteps.PARTNERS, text)
    if not opt_id:
        await message.answer("Нажми кнопку, чтобы продолжить.")
        return

    await save_onboarding_progress(message.from_user.id, OnboardingSteps.PARTNERS, opt_id, by_telegram_id=True)
    complete = get_step_data(OnboardingSteps.COMPLETE)
    await message.answer(complete["message"], reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await show_main_menu(message)


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext) -> None:
    await _show_settings_menu(message, state)


@router.callback_query(F.data == "settings_close")
async def cb_settings_close(callback: CallbackQuery):
    await callback.message.edit_text("Настройки закрыты ✅")
    await callback.answer()
    await show_main_menu(callback.message)


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "skip_email_prompt")
async def cb_skip_email_prompt(callback: CallbackQuery, state: FSMContext):
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository
    from app.services.account_link import AccountLinkService

    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, callback.from_user.id)
            if user_db:
                await AccountLinkService().dismiss_link_prompt(db, user_db.id)
                await db.commit()
    except Exception as e:
        logger.error(f"cb_skip_email_prompt error: {e}", exc_info=True)

    await callback.answer()
    await callback.message.answer("Хорошо. Я отложил это на позже.", reply_markup=ReplyKeyboardRemove())

    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, callback.from_user.id)
            needs_onboarding = bool(user_db and not user_db.last_onboarding_update)
    except Exception:
        needs_onboarding = False

    if needs_onboarding:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🚀 Начать знакомство")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await callback.message.answer(
            "Давай познакомимся, чтобы я мог собрать тебе персональный план.",
            reply_markup=keyboard,
        )
        return

    await show_main_menu(callback.message)


@router.callback_query(F.data == "settings_email")
async def cb_settings_email(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_email)
    await callback.answer()
    await callback.message.answer(
        "📧 Напиши свой email. Я отправлю письмо с подтверждением.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(SettingsState.waiting_for_email)
async def process_settings_email(message: Message, state: FSMContext):
    import re
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository
    from app.services.account_link import AccountLinkService
    from app.email.service import send_link_account_email

    email = (message.text or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        await message.answer("Это не похоже на email. Попробуй ещё раз:")
        return

    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, message.from_user.id)
            if not user_db:
                await message.answer("Пользователь не найден. Нажми /start")
                await state.clear()
                return

            needs_onboarding = not user_db.last_onboarding_update

            link_svc = AccountLinkService()
            token = await link_svc.create_email_verify_token(db, user_db.id, email)
            sent = await send_link_account_email(email, user_db.first_name or "друг", token)
            await link_svc.dismiss_link_prompt(db, user_db.id)
            await db.commit()

        await state.clear()

        if sent:
            await message.answer(
                f"📬 Письмо отправлено на {email}\n\nОткрой почту и нажми на ссылку.",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await message.answer(
                f"Я сохранил email {email}, но письмо сейчас не отправилось. Попробуй позже через /settings.",
                reply_markup=ReplyKeyboardRemove(),
            )

        if needs_onboarding:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🚀 Начать знакомство")]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            await message.answer(
                "Если хочешь — можем продолжить знакомство и собрать персональный план.",
                reply_markup=keyboard,
            )
            return

        await show_main_menu(message)
    except Exception as e:
        logger.error(f"process_settings_email error: {e}", exc_info=True)
        await message.answer("Не получилось отправить письмо. Попробуй чуть позже.")
        await state.clear()
        await show_main_menu(message)


@router.callback_query(F.data == "reset_confirm")
async def cb_reset_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository
    from app.services.user_service import UserService

    await state.clear()
    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, callback.from_user.id)
            if not user_db:
                await callback.message.edit_text("Не вижу тебя в системе. Нажми /start.")
                await callback.answer()
                await show_main_menu(callback.message)
                return

            await UserService().reset_progress(db, user_db.id)
            await db.commit()

        await callback.message.edit_text(
            "✅ Готово. Я бережно сбросил прогресс. Если хочешь, начнём заново."
        )
        await callback.answer()
        await show_main_menu(callback.message)
    except Exception as e:
        logger.error(f"cb_reset_confirm error: {e}", exc_info=True)
        await callback.message.edit_text("Не получилось сделать сброс. Попробуй чуть позже.")
        await callback.answer()
        await show_main_menu(callback.message)


@router.callback_query(F.data == "reset_cancel")
async def cb_reset_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Сброс отменён. Всё осталось на месте.")
    await callback.answer()
    await show_main_menu(callback.message)


@router.callback_query(F.data.startswith("task_done_"))
async def cb_task_done(callback: CallbackQuery, state: FSMContext) -> None:
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository
    from app.services.daily_service import DailyService

    task_id = callback.data.replace("task_done_", "").strip() if callback.data else ""
    if not task_id.isdigit():
        await callback.answer("Не вижу номер шага. Попробуй ещё раз.")
        return

    try:
        async with AsyncSessionLocal() as db:
            user_db = await UserRepository().get_by_telegram_id(db, callback.from_user.id)
            if not user_db:
                await callback.answer("Не вижу тебя в системе. Нажми /start.")
                await show_main_menu(callback.message)
                return

            ok = await DailyService().toggle_task_completion(
                db, user_id=user_db.id, task_id=int(task_id), completed=True
            )
            await db.commit()

        if not ok:
            await callback.answer("Не получилось отметить шаг. Попробуй ещё раз.")
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Показать обновлённый план",
                        callback_data="task_done_show_plan",
                    )
                ],
                [InlineKeyboardButton(text="Поделиться прогрессом ✨", callback_data="share_progress")],
                [
                    InlineKeyboardButton(
                        text="Открыть план в приложении 📲",
                        web_app=WebAppInfo(url=_build_webapp_url("/")),
                    )
                ],
            ]
        )

        await callback.message.edit_text(
            "✅ Шаг отмечен\n"
            "Ты сделал(а) важный шаг сегодня. Пусть это будет тёплой опорой.\n\n"
            "Хочешь увидеть обновлённый план?",
            reply_markup=kb,
        )
        await callback.answer("✅ Готово!")
        await show_main_menu(callback.message)
    except Exception as e:
        logger.error(f"cb_task_done error: {e}", exc_info=True)
        await callback.answer("Не получилось отметить шаг. Попробуй позже.")
        await show_main_menu(callback.message)


@router.callback_query(F.data == "task_done_show_plan")
async def cb_task_done_show_plan(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await _cf_load_data(callback.from_user.id)
    if not data:
        await callback.message.edit_text(
            "Сейчас нет активного проекта. Давай сначала соберём его в приложении."
        )
        await show_main_menu(callback.message)
        return

    tasks = data.get("tasks", [])
    if not tasks:
        await callback.message.edit_text(
            "Сегодня шагов пока нет. Это нормально. Если хочешь — открой приложение и выберем путь."
        )
        await show_main_menu(callback.message)
        return

    text, reply_markup = _build_today_view(tasks, preface="Вот обновлённый план ✨")
    await callback.message.edit_text(text, reply_markup=reply_markup)
    await show_main_menu(callback.message)


@router.callback_query(F.data == "share_progress")
async def cb_share_progress(callback: CallbackQuery) -> None:
    await callback.answer()
    data = await _cf_load_data(callback.from_user.id)
    if not data:
        await callback.message.answer(
            "Сейчас нет активного проекта. Давай сначала соберём его в приложении."
        )
        await show_main_menu(callback.message)
        return

    tasks = data.get("tasks", [])
    if not tasks:
        await callback.message.answer(
            "Сегодня шагов пока нет. Это нормально. Если хочешь — открой приложение и выберем путь."
        )
        await show_main_menu(callback.message)
        return

    share_text = _build_share_progress_text(tasks)
    await callback.message.answer(
        "Вот текст, который можно переслать:\n\n" + share_text
    )
    await show_main_menu(callback.message)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command, including deep link payloads for account linking."""
    from app.database import AsyncSessionLocal
    from app.services.user_service import UserService
    from app.services.account_link import AccountLinkService
    
    user = message.from_user
    logger.info(f"User {user.id} ({user.first_name}) started bot")
    
    await state.clear()

    # Extract deep link payload: /start link_XXXXX
    deep_link_payload = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else None

    try:
        async with AsyncSessionLocal() as db:
            user_svc = UserService()
            user_db = await user_svc.get_or_create_telegram_user(
                db,
                telegram_id=user.id,
                first_name=user.first_name,
                username=user.username,
            )
            await db.commit()

            # ── Deep link: account linking ──
            if deep_link_payload and deep_link_payload.startswith("link_"):
                link_token = deep_link_payload[5:]  # strip "link_" prefix
                link_svc = AccountLinkService()
                web_user, tg_conflict = await link_svc.verify_telegram_link_token(
                    db, link_token, user.id
                )
                if not web_user:
                    await message.answer(
                        "Ссылка для привязки устарела или уже использована.\n"
                        "Попробуй создать новую в настройках приложения."
                    )
                elif tg_conflict:
                    from app.services.account_merge import AccountMergeService

                    # Merge needed — store in state for confirmation
                    await state.update_data(
                        merge_target_id=web_user.id,
                        merge_source_id=tg_conflict.id,
                    )

                    preview = await AccountMergeService().preview_merge(
                        db, target_user_id=web_user.id, source_user_id=tg_conflict.id
                    )
                    has_conflict = bool(preview.get("has_project_conflict"))

                    if has_conflict:
                        await state.update_data(merge_has_project_conflict=True)
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="Оставить активный проект из приложения",
                                    callback_data="merge_keep_target",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="Оставить активный проект из Telegram",
                                    callback_data="merge_keep_source",
                                )
                            ],
                            [InlineKeyboardButton(text="❌ Отмена", callback_data="merge_cancel")],
                        ])

                        target_problem = preview.get("target", {}).get("active_project_problem")
                        source_problem = preview.get("source", {}).get("active_project_problem")
                        text = (
                            "🔗 Обнаружены два аккаунта\n\n"
                            "И у каждого сейчас есть активный проект.\n"
                            "Давай выберем, какой проект оставить активным после объединения.\n\n"
                            f"В приложении: {target_problem or '—'}\n"
                            f"В Telegram: {source_problem or '—'}"
                        )
                        await message.answer(text, reply_markup=kb)
                    else:
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ Объединить аккаунты", callback_data="merge_confirm")],
                            [InlineKeyboardButton(text="❌ Отмена", callback_data="merge_cancel")],
                        ])
                        await message.answer(
                            "🔗 Обнаружены два аккаунта\n\n"
                            "У тебя уже есть аккаунт в Telegram и отдельный аккаунт в приложении. "
                            "Хочешь объединить их? Все данные сольются в один аккаунт.",
                            reply_markup=kb,
                        )
                    await db.commit()
                    return
                else:
                    await db.commit()

                    if web_user.telegram_id and web_user.telegram_id != user.id:
                        await message.answer(
                            "Похоже, этот аккаунт в приложении уже привязан к другому Telegram.\n\n"
                            "Если хочешь — мы можем аккуратно объединить аккаунты: "
                            "открой приложение → Настройки → «Привязать Telegram» и создай новый код, "
                            "а потом снова перейди по новой ссылке."
                        )
                        await show_main_menu(message)
                        return

                    if not web_user.telegram_id:
                        await message.answer(
                            "Я попробовал привязать Telegram, но сейчас что-то мешает.\n\n"
                            "Открой приложение → Настройки → «Привязать Telegram» и создай новый код, "
                            "а потом снова перейди по новой ссылке."
                        )
                        await show_main_menu(message)
                        return

                    await message.answer(
                        "✅ Telegram успешно привязан к твоему аккаунту!\n\n"
                        "Теперь ты можешь пользоваться и ботом, и приложением — всё синхронизировано."
                    )
                    await show_main_menu(message)
                    return

            # ── Onboarding check ──
            needs_onboarding = not user_db.last_onboarding_update
            if user_db.link_prompt_dismissed and not user_db.link_prompt_snoozed_until:
                try:
                    await AccountLinkService().snooze_link_prompt(db, user_db.id, days=7)
                    await db.commit()
                    user_db.link_prompt_dismissed = False
                    user_db.link_prompt_snoozed_until = datetime.now(UTC) + timedelta(days=7)
                except Exception as e:
                    logger.error(f"Failed to convert legacy link_prompt_dismissed: {e}", exc_info=True)

            snoozed = bool(
                user_db.link_prompt_snoozed_until
                and user_db.link_prompt_snoozed_until > datetime.now(UTC)
            )

            # ── Email prompt (before onboarding) ──
            if not user_db.email and not snoozed:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📧 Указать email", callback_data="settings_email")],
                    [InlineKeyboardButton(text="Позже (7 дней)", callback_data="skip_email_prompt")],
                ])
                await message.answer(
                    "Чтобы твой путь не потерялся — можно привязать email.\n\n"
                    "Это поможет входить через браузер и переносить практики между устройствами.",
                    reply_markup=kb,
                )
                return

            if needs_onboarding:
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🚀 Начать знакомство")]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                )

                welcome_text = (
                    f"Привет, {user.first_name}! 👋\n\n"
                    "Я твой кармический менеджер. Чтобы составить персональный план, "
                    "мне нужно узнать о тебе чуть больше.\n\n"
                    "Это займет всего минуту!"
                )
                await message.answer(welcome_text, reply_markup=keyboard)
                return

    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)

    # Standard welcome for existing users
    await show_main_menu(message)


@router.callback_query(F.data.in_({"merge_keep_target", "merge_keep_source"}))
async def cb_merge_keep_project(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("merge_target_id")
    source_id = data.get("merge_source_id")

    if not target_id or not source_id:
        await callback.message.edit_text("Данные для объединения устарели. Попробуй привязать аккаунт заново.")
        await callback.answer()
        await state.clear()
        return

    keep_from = target_id if callback.data == "merge_keep_target" else source_id
    await state.update_data(keep_project_from=keep_from)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Объединить аккаунты", callback_data="merge_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="merge_cancel")],
    ])

    await callback.message.edit_text(
        "Отлично. Я запомнил выбор активного проекта.\n\n"
        "Теперь подтверди объединение аккаунтов — и я аккуратно всё сведу в одно место.",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data == "merge_confirm")
async def cb_merge_confirm(callback: CallbackQuery, state: FSMContext):
    from app.database import AsyncSessionLocal
    from app.services.account_merge import AccountMergeService

    data = await state.get_data()
    target_id = data.get("merge_target_id")
    source_id = data.get("merge_source_id")
    keep_project_from = data.get("keep_project_from")

    if not target_id or not source_id:
        await callback.message.edit_text("Данные для объединения устарели. Попробуй привязать аккаунт заново.")
        await callback.answer()
        await state.clear()
        return

    try:
        async with AsyncSessionLocal() as db:
            merge_svc = AccountMergeService()
            ok = await merge_svc.execute_merge(
                db,
                target_user_id=target_id,
                source_user_id=source_id,
                keep_project_from=keep_project_from,
            )
            await db.commit()

        await state.clear()
        if ok:
            await callback.message.edit_text(
                "✅ Аккаунты объединены!\n\n"
                "Все данные слиты вместе. Теперь всё в одном месте."
            )
        else:
            await callback.message.edit_text("Не удалось объединить. Попробуй позже.")
    except Exception as e:
        logger.error(f"Merge error: {e}", exc_info=True)
        await callback.message.edit_text("Ошибка при объединении. Попробуй позже.")
    await callback.answer()


@router.callback_query(F.data == "merge_cancel")
async def cb_merge_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Объединение отменено.\n"
        "Ты можешь привязать аккаунт позже через /settings"
    )
    await callback.answer()


# =============================================================================
# Interactive Coffee Meditation (bot flow)
# =============================================================================

async def _cf_load_data(telegram_id: int):
    """Load all data needed for coffee meditation session."""
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository
    from app.repositories.karma_plan import KarmaPlanRepository
    from app.coffee_meditation import (
        get_user_zoneinfo,
        get_local_day_bounds,
        get_or_create_session,
        get_today_seeds,
        get_today_daily_plan,
        get_rejoiced_seed_ids,
    )
    from datetime import datetime, UTC

    async with AsyncSessionLocal() as db:
        user_db = await UserRepository().get_by_telegram_id(db, telegram_id)
        if not user_db:
            return None

        plan = await KarmaPlanRepository().get_active(db, user_db.id)
        if not plan:
            return None

        tz = get_user_zoneinfo(user_db.timezone)
        now = datetime.now(UTC)
        bounds = get_local_day_bounds(now, tz)

        daily_plan = await get_today_daily_plan(
            db, karma_plan_id=plan.id, utc_start=bounds.utc_start, utc_end=bounds.utc_end
        )
        seeds = await get_today_seeds(
            db, user_id=user_db.id, utc_start=bounds.utc_start, utc_end=bounds.utc_end
        )
        session = await get_or_create_session(
            db,
            user_id=user_db.id,
            local_date=bounds.local_date,
            karma_plan_id=plan.id,
            daily_plan_id=daily_plan.id if daily_plan else None,
        )
        rejoiced = await get_rejoiced_seed_ids(db, session_id=session.id)
        await db.commit()

        tasks_list = []
        if daily_plan and daily_plan.tasks:
            tasks_list = [
                {"id": str(t.id), "desc": t.description, "completed": t.completed}
                for t in daily_plan.tasks
            ]

        seeds_list = [
            {"id": s.id, "desc": s.description, "rc": s.rejoice_count or 0}
            for s in seeds
        ]

        return {
            "user_id": user_db.id,
            "session_id": session.id,
            "seeds": seeds_list,
            "tasks": tasks_list,
            "rejoiced": rejoiced,
        }


def _cf_seeds_keyboard(seeds: list, rejoiced: list[str]) -> InlineKeyboardMarkup:
    """Build inline keyboard for seed rejoice toggles."""
    buttons = []
    for i, s in enumerate(seeds[:10]):
        is_on = s["id"] in rejoiced
        icon = "✨" if is_on else "🌱"
        label = f"{icon} {s['desc'][:38]}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"cf_rj_{i}")])
    buttons.append([InlineKeyboardButton(text="Далее ☕️", callback_data="cf_next_4")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "cf_start")
async def cf_start(callback: CallbackQuery, state: FSMContext):
    """Start coffee meditation — Step 1: Breathing."""
    await callback.answer()

    data = await _cf_load_data(callback.from_user.id)
    if not data:
        await callback.message.edit_text(
            "Сейчас у тебя нет активного проекта. Давай сначала спокойно соберём его."
        )
        await show_main_menu(callback.message)
        return

    await state.update_data(
        cf_session_id=data["session_id"],
        cf_user_id=data["user_id"],
        cf_seeds=data["seeds"],
        cf_tasks=data["tasks"],
        cf_rejoiced=data["rejoiced"],
    )
    await state.set_state(CoffeeState.step_1)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Далее ☕️", callback_data="cf_next_2")]]
    )

    await callback.message.edit_text(
        "🧘 *Шаг 1 · Подготовка*\n\n"
        "Сделай пару спокойных вдохов.\n"
        "Давай мягко вспомним всё хорошее,\n"
        "что уже случилось сегодня.\n\n"
        "_Не торопись. Просто побудь здесь секунду._",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@router.callback_query(F.data == "cf_next_2")
async def cf_step_2(callback: CallbackQuery, state: FSMContext):
    """Step 2: Review day — tasks & seeds."""
    await callback.answer()
    fsm = await state.get_data()
    if not fsm.get("cf_session_id"):
        await callback.message.edit_text("Сессия не найдена. Попробуй /coffee заново.")
        await state.clear()
        return

    await state.set_state(CoffeeState.step_2)

    tasks = fsm.get("cf_tasks", [])
    seeds = fsm.get("cf_seeds", [])

    text = "📋 *Шаг 2 · Обзор дня*\n\n"

    if tasks:
        text += "*Твои шаги на сегодня:*\n"
        for t in tasks[:8]:
            mark = "✅" if t["completed"] else "⬜️"
            text += f"{mark} {t['desc']}\n"
        text += "\n"
    else:
        text += "_Шагов на сегодня пока нет — и это нормально._\n\n"

    if seeds:
        text += f"*Семена за сегодня:* {len(seeds)}\n"
        for s in seeds[:5]:
            text += f"🌱 {s['desc'][:50]}\n"
        if len(seeds) > 5:
            text += f"_...и ещё {len(seeds) - 5}_\n"
    else:
        text += "_Семян пока нет. Даже маленькое доброе дело уже считается._\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Далее ☕️", callback_data="cf_next_3")]]
    )

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data == "cf_next_3")
async def cf_step_3(callback: CallbackQuery, state: FSMContext):
    """Step 3: Rejoice — pick seeds to amplify."""
    await callback.answer()
    fsm = await state.get_data()
    if not fsm.get("cf_session_id"):
        await callback.message.edit_text("Сессия не найдена. Попробуй /coffee заново.")
        await state.clear()
        return

    await state.set_state(CoffeeState.step_3)

    seeds = fsm.get("cf_seeds", [])
    rejoiced = fsm.get("cf_rejoiced", [])

    if not seeds:
        text = (
            "✨ *Шаг 3 · Радость*\n\n"
            "_Сегодня семян ещё нет. Просто вспомни любое доброе дело — "
            "даже самое маленькое — и порадуйся ему в сердце._"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Далее ☕️", callback_data="cf_next_4")]]
        )
    else:
        text = (
            "✨ *Шаг 3 · Радость*\n\n"
            "Выбери семена, которым хочешь порадоваться.\n"
            "Каждое нажатие усиливает семя.\n"
        )
        kb = _cf_seeds_keyboard(seeds, rejoiced)

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data.startswith("cf_rj_"))
async def cf_toggle_rejoice(callback: CallbackQuery, state: FSMContext):
    """Toggle rejoice on a seed."""
    fsm = await state.get_data()
    seeds = fsm.get("cf_seeds", [])
    rejoiced = list(fsm.get("cf_rejoiced", []))

    try:
        idx = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if idx < 0 or idx >= len(seeds):
        await callback.answer("Ошибка")
        return

    seed_id = seeds[idx]["id"]
    if seed_id in rejoiced:
        rejoiced.remove(seed_id)
        await callback.answer("Убрано")
    else:
        rejoiced.append(seed_id)
        await callback.answer("Радость! ✨")

    await state.update_data(cf_rejoiced=rejoiced)

    # Save progress to backend
    try:
        from app.database import AsyncSessionLocal
        from app.coffee_meditation import save_progress
        from app.models.db.coffee import CoffeeMeditationSessionDB
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(CoffeeMeditationSessionDB).where(
                    CoffeeMeditationSessionDB.id == fsm["cf_session_id"]
                )
            )
            session = result.scalar_one_or_none()
            if session:
                await save_progress(
                    db,
                    session=session,
                    user_id=fsm["cf_user_id"],
                    current_step=2,
                    notes_draft=None,
                    rejoiced_seed_ids=rejoiced,
                )
                await db.commit()
    except Exception as e:
        logger.error(f"cf_toggle_rejoice save error: {e}", exc_info=True)

    # Rebuild keyboard
    kb = _cf_seeds_keyboard(seeds, rejoiced)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass


@router.callback_query(F.data == "cf_next_4")
async def cf_step_4(callback: CallbackQuery, state: FSMContext):
    """Step 4: Notes + dedication."""
    await callback.answer()
    fsm = await state.get_data()
    if not fsm.get("cf_session_id"):
        await callback.message.edit_text("Сессия не найдена. Попробуй /coffee заново.")
        await state.clear()
        return

    await state.set_state(CoffeeState.step_4_notes)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="cf_skip_notes")],
        ]
    )

    await callback.message.edit_text(
        "🙏 *Шаг 4 · Посвящение*\n\n"
        "Если хочешь — напиши пару тёплых слов для себя.\n"
        "Или просто нажми «Пропустить».\n\n"
        "_Например: «Сегодня я молодец, потому что...»_",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@router.message(CoffeeState.step_4_notes)
async def cf_receive_notes(message: Message, state: FSMContext):
    """Receive notes text from user and complete."""
    fsm = await state.get_data()
    notes = message.text.strip() if message.text else None

    await _cf_complete(message, state, fsm, notes)


@router.callback_query(F.data == "cf_skip_notes")
async def cf_skip_notes(callback: CallbackQuery, state: FSMContext):
    """Skip notes and complete."""
    await callback.answer()
    fsm = await state.get_data()

    await _cf_complete(callback.message, state, fsm, notes=None, edit=True)


async def _cf_complete(message: Message, state: FSMContext, fsm: dict, notes: str | None, edit: bool = False):
    """Finalize the coffee meditation session."""
    from app.database import AsyncSessionLocal
    from app.coffee_meditation import complete_session, save_progress
    from app.models.db.coffee import CoffeeMeditationSessionDB
    from sqlalchemy import select

    session_id = fsm.get("cf_session_id")
    user_id = fsm.get("cf_user_id")
    rejoiced = fsm.get("cf_rejoiced", [])

    if not session_id:
        text = "Сессия не найдена. Попробуй /coffee заново."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        await state.clear()
        return

    try:
        async with AsyncSessionLocal() as db:
            result = await complete_session(
                db,
                session_id=session_id,
                user_id=user_id,
                notes=notes,
                rejoice_seed_ids=rejoiced,
            )
            await db.commit()
    except Exception as e:
        logger.error(f"cf_complete error: {e}", exc_info=True)

    await state.clear()

    seeds_count = len(fsm.get("cf_seeds", []))
    rejoiced_count = len(rejoiced)

    text = "✅ *Кофе‑медитация завершена!*\n\n"
    if rejoiced_count:
        text += f"✨ Усилено семян: {rejoiced_count}\n"
    if notes:
        text += f"📝 Записано: _{notes[:80]}{'...' if len(notes) > 80 else ''}_\n"
    text += "\nКаждое мгновение осознанности — это семя. Хорошего дня! ☀️"

    if edit:
        await message.edit_text(text, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")
    await show_main_menu(message)


# Register router
dp.include_router(router)


shutdown_event = asyncio.Event()
bot_username: str = ""

async def start_bot():
    """Start the bot"""
    global bot_username
    logger.info("Starting Telegram bot...")
    retry_delay = 5
    shutdown_event.clear()
    try:
        while not shutdown_event.is_set():
            try:
                # Get bot info
                bot_info = await bot.get_me()
                bot_username = bot_info.username or ""
                logger.info(f"Bot @{bot_username} started successfully")

                # Set bot commands menu
                commands = [
                    BotCommand(command="start", description="🏠 Начать работу с ботом"),
                    BotCommand(command="app", description="📱 Открыть приложение"),
                    BotCommand(command="solver", description="💭 Решить проблему"),
                    BotCommand(command="today", description="📋 Действия на сегодня"),
                    BotCommand(command="coffee", description="☕️ Кофе-медитация"),
                    BotCommand(command="seed", description="🌱 Записать семя"),
                    BotCommand(command="done", description="✅ Отметить выполнение"),
                    BotCommand(command="practices", description="🧘 Практики"),
                    BotCommand(command="settings", description="⚙️ Настройки профиля"),
                    BotCommand(command="reset", description="🔄 Сброс прогресса"),
                ]
                await bot.set_my_commands(commands)
                logger.info("Bot commands menu set successfully")

                await dp.start_polling(
                    bot, 
                    allowed_updates=dp.resolve_used_update_types(),
                    handle_signals=False
                )

                # ✅ если это штатный shutdown — не рестартим
                if shutdown_event.is_set():
                    logger.info("Polling stopped due to shutdown")
                    break

                logger.warning(
                    "Bot polling stopped without explicit cancellation, restarting in %s seconds",
                    retry_delay,
                )
            except asyncio.CancelledError:
                # Прекращаем цикл при остановке сервера/приложения
                raise
            except Exception as e:
                logger.error(
                    f"Bot polling failed with error: {e}. Restarting in {retry_delay} seconds...",
                    exc_info=True,
                )

            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=retry_delay)
            except asyncio.TimeoutError:
                pass
    except asyncio.CancelledError:
        logger.info("Bot polling task cancelled, stopping bot loop")
        raise


async def stop_bot():
    """Stop the bot"""
    logger.info("Stopping Telegram bot...")
    try:
        shutdown_event.set()
        await bot.session.close()
        logger.info("Bot stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping bot: {e}", exc_info=True)
