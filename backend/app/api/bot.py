"""Telegram Bot handlers"""
import asyncio
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
    ONBOARDING_STEPS, 
    OnboardingSteps, 
    get_next_step, 
    get_step_data,
    save_onboarding_progress
)
from app.api.middleware.typing_middleware import TypingMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
from app.mock_bot import MockBot

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
    focus = State()
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


# Map generic steps to FSM states
STEP_STATE_MAP = {
    OnboardingSteps.OCCUPATION: OnboardingState.occupation,
    OnboardingSteps.SCHEDULE: OnboardingState.schedule,
    OnboardingSteps.DURATION: OnboardingState.duration,
    OnboardingSteps.HABITS: OnboardingState.habits,
    OnboardingSteps.RESTRICTIONS: OnboardingState.restrictions,
    OnboardingSteps.FOCUS: OnboardingState.focus,
    OnboardingSteps.PARTNERS: OnboardingState.partners,
}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    from app.database import AsyncSessionLocal
    from app.crud import get_or_create_user
    
    user = message.from_user
    logger.info(f"User {user.id} ({user.first_name}) started bot")
    
    await state.clear()
    
    try:
        # Get or create user in database
        async with AsyncSessionLocal() as db:
            user_db = await get_or_create_user(
                db,
                telegram_id=user.id,
                first_name=user.first_name,
                username=user.username
            )
            await db.commit()
            
            # Check if onboarding is needed
            needs_onboarding = not user_db.last_onboarding_update
            
            if needs_onboarding:
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🚀 Начать знакомство")]],
                    resize_keyboard=True,
                    one_time_keyboard=True
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
        logger.error(f"Error creating user: {e}", exc_info=True)
    
    # Standard welcome for existing users
    await show_main_menu(message)


async def show_main_menu(message: Message):
    """Show main menu with app button"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=settings.WEBAPP_URL)
            )
        ]],
        resize_keyboard=True
    )
    
    text = (
        "С возвращением! 🧘\n\n"
        "Твой план и практики ждут тебя в приложении."
    )
    
    await message.answer(text, reply_markup=keyboard)


# =============================================================================
# Onboarding Handlers
# =============================================================================

@router.message(F.text == "🚀 Начать знакомство")
async def start_onboarding_flow(message: Message, state: FSMContext):
    """Start onboarding process"""
    current_step = OnboardingSteps.OCCUPATION
    await state.set_state(STEP_STATE_MAP[current_step])
    
    step_data = get_step_data(current_step)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt["label"])] for opt in step_data["options"]],
        resize_keyboard=True
    )
    
    await message.answer(step_data["message"], reply_markup=kb)


@router.message(OnboardingState.occupation)
async def process_occupation(message: Message, state: FSMContext):
    """Process occupation answer"""
    current_step = OnboardingSteps.OCCUPATION
    step_data = get_step_data(current_step)
    
    # Find selected option id
    selected_id = next((opt["id"] for opt in step_data["options"] if opt["label"] == message.text), "other")
    
    # Save using shared logic
    await save_onboarding_progress(message.from_user.id, current_step, selected_id)
    await state.update_data(occupation=selected_id)
    
    # Move to next step
    next_step_name = get_next_step(current_step)
    next_step_data = get_step_data(next_step_name)
    
    await state.set_state(STEP_STATE_MAP[next_step_name])
    
    # For multi-choice using inline keyboard to allow multiple selections
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt["label"], callback_data=f"sched_{opt['id']}")]
        for opt in next_step_data["options"]
    ] + [[InlineKeyboardButton(text="✅ Готово", callback_data="sched_done")]])
    
    await message.answer(next_step_data["message"], reply_markup=kb)


@router.callback_query(F.data.startswith("sched_"))
async def process_schedule_selection(callback: CallbackQuery, state: FSMContext):
    """Handle schedule selection (multi-choice)"""
    action = callback.data.split("_")[1]
    
    data = await state.get_data()
    current_selection = data.get("available_times", [])
    
    if action == "done":
        if not current_selection:
            await callback.answer("Выбери хотя бы один вариант", show_alert=True)
            return
        
        # Save using shared logic
        await save_onboarding_progress(callback.from_user.id, OnboardingSteps.SCHEDULE, current_selection)
        
        await callback.message.delete()
        
        next_step_name = get_next_step(OnboardingSteps.SCHEDULE)
        next_step_data = get_step_data(next_step_name)
        
        await state.set_state(STEP_STATE_MAP[next_step_name])
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=opt["label"])] for opt in next_step_data["options"]],
            resize_keyboard=True
        )
        await callback.message.answer(next_step_data["message"], reply_markup=kb)
        return

    # Toggle selection
    if action in current_selection:
        current_selection.remove(action)
    else:
        current_selection.append(action)
    
    await state.update_data(available_times=current_selection)
    
    # Update keyboard visualization
    step_data = get_step_data(OnboardingSteps.SCHEDULE)
    new_kb = []
    for opt in step_data["options"]:
        label = opt["label"]
        if opt["id"] in current_selection:
            label = "✅ " + label
        new_kb.append([InlineKeyboardButton(text=label, callback_data=f"sched_{opt['id']}")])
    
    new_kb.append([InlineKeyboardButton(text="✅ Готово", callback_data="sched_done")])
    
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb))
    await callback.answer()


@router.message(OnboardingState.duration)
async def process_duration(message: Message, state: FSMContext):
    """Process duration answer"""
    current_step = OnboardingSteps.DURATION
    step_data = get_step_data(current_step)
    
    selected_id = next((opt["id"] for opt in step_data["options"] if opt["label"] == message.text), "30")
    
    # Save using shared logic
    await save_onboarding_progress(message.from_user.id, current_step, int(selected_id))
    await state.update_data(daily_minutes=int(selected_id))
    
    next_step_name = get_next_step(current_step)
    next_step_data = get_step_data(next_step_name)
    
    await state.set_state(STEP_STATE_MAP[next_step_name])
    
    # Multi-choice for habits
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt["label"], callback_data=f"habit_{opt['id']}")]
        for opt in next_step_data["options"]
    ] + [[InlineKeyboardButton(text="✅ Готово", callback_data="habit_done")]])
    
    await message.answer(next_step_data["message"], reply_markup=kb)


@router.callback_query(F.data.startswith("habit_"))
async def process_habit_selection(callback: CallbackQuery, state: FSMContext):
    """Handle habits selection"""
    action = callback.data.split("_")[1]
    
    data = await state.get_data()
    current_selection = data.get("current_habits", [])
    
    if action == "done":
        # Save using shared logic
        await save_onboarding_progress(callback.from_user.id, OnboardingSteps.HABITS, current_selection)
        
        await callback.message.delete()
        
        next_step_name = get_next_step(OnboardingSteps.HABITS)
        next_step_data = get_step_data(next_step_name)
        
        await state.set_state(STEP_STATE_MAP[next_step_name])
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=opt["label"])] for opt in next_step_data["options"]],
            resize_keyboard=True
        )
        await callback.message.answer(next_step_data["message"], reply_markup=kb)
        return

    # Toggle selection
    if action in current_selection:
        current_selection.remove(action)
    else:
        # Handle "none" exclusive selection
        if action == "none":
            current_selection = ["none"]
        elif "none" in current_selection:
            current_selection.remove("none")
            current_selection.append(action)
        else:
            current_selection.append(action)
    
    await state.update_data(current_habits=current_selection)
    
    # Update keyboard
    step_data = get_step_data(OnboardingSteps.HABITS)
    new_kb = []
    for opt in step_data["options"]:
        label = opt["label"]
        if opt["id"] in current_selection:
            label = "✅ " + label
        new_kb.append([InlineKeyboardButton(text=label, callback_data=f"habit_{opt['id']}")])
    
    new_kb.append([InlineKeyboardButton(text="✅ Готово", callback_data="habit_done")])
    
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb))
    await callback.answer()


@router.message(OnboardingState.restrictions)
async def process_restrictions(message: Message, state: FSMContext):
    """Process restrictions answer"""
    current_step = OnboardingSteps.RESTRICTIONS
    
    text = message.text
    value = None if text == "➡️ Пропустить" else text
    
    # Save using shared logic
    await save_onboarding_progress(message.from_user.id, current_step, value)
    await state.update_data(physical_restrictions=value)
    
    next_step_name = get_next_step(current_step)
    next_step_data = get_step_data(next_step_name)
    
    await state.set_state(STEP_STATE_MAP[next_step_name])
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt["label"])] for opt in next_step_data["options"]],
        resize_keyboard=True
    )
    
    await message.answer(next_step_data["message"], reply_markup=kb)


@router.message(OnboardingState.focus)
async def process_focus(message: Message, state: FSMContext):
    """Process focus answer"""
    current_step = OnboardingSteps.FOCUS
    step_data = get_step_data(current_step)
    
    selected_id = next((opt["id"] for opt in step_data["options"] if opt["label"] == message.text), "other")
    
    # Save using shared logic
    await save_onboarding_progress(message.from_user.id, current_step, selected_id)
    await state.update_data(current_focus=selected_id)
    
    next_step_name = get_next_step(current_step)
    next_step_data = get_step_data(next_step_name)
    
    await state.set_state(STEP_STATE_MAP[next_step_name])
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt["label"])] for opt in next_step_data["options"]],
        resize_keyboard=True
    )
    
    await message.answer(next_step_data["message"], reply_markup=kb)


@router.message(OnboardingState.partners)
async def process_partners_confirm(message: Message, state: FSMContext):
    """Finalize onboarding"""
    # Save partner step (mark as complete)
    await save_onboarding_progress(message.from_user.id, OnboardingSteps.PARTNERS, "continue")
    
    await state.clear()
    
    # Show completion message
    step_data = get_step_data(OnboardingSteps.COMPLETE)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗣 Рассказать о проблеме", callback_data="start_problem_flow")],
        [InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
    ])
    
    await message.answer(step_data["message"], reply_markup=kb)


# =============================================================================
# Project Setup Helpers
# =============================================================================

async def _ask_partner_category(message: Message, state: FSMContext, category: str):
    """Ask user for a partner in a specific category"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, get_partners_by_universal_category
    from app.models.db_models import PartnerDB
    from sqlalchemy import select
    
    data = await state.get_data()
    solution = data.get("pending_solution", {})
    guide_list = solution.get("partner_selection_guide", [])
    project_partners = data.get("project_partners", {})
    selected_in_cat = project_partners.get(category, [])
    
    isolation_settings = data.get("isolation_settings", {})
    is_isolated = isolation_settings.get(category, {}).get("is_isolated", False)
    
    # Find guide item for this category
    guide_item = next((g for g in guide_list if g.get("category") == category), None)
    
    # Fallback texts
    fallbacks = {
        "source": ("🙌 Источник", "Кто дает тебе ресурсы и основу? (Родители, учителя)", "Если нет источника: Используй ментальные семена. Посвящай практики учителям прошлого."),
        "ally": ("🤝 Соратник", "Кто помогает тебе в делах? (Коллеги, партнеры)", "Если нет соратника: Стань соратником для других. Помогай бескорыстно."),
        "protege": ("🌱 Подопечный", "Кто зависит от тебя? (Клиенты, подчиненные)", "Если нет подопечного: Найди того, кому нужна помощь, даже в малом."),
        "world": ("🌍 Внешний мир", "Кто-то далекий или конкурент.", "Если изоляция от мира: Делай тайные добрые дела (уборка мусора, пожертвования).")
    }
    
    title = guide_item["title"] if guide_item else fallbacks[category][0]
    desc = guide_item["description"] if guide_item else fallbacks[category][1]
    fallback_advice = guide_item.get("fallback_advice") if guide_item else fallbacks[category][2]
    examples = guide_item.get("examples", []) if guide_item else []
    
    text = f"**{title}**\n\n{desc}\n"
    if examples:
        text += f"\n💡 Пример: {', '.join(examples)}"
    
    # Show isolation status or selected partners
    if is_isolated:
        text += f"\n\n🧘 **Выбрана изоляция / Никого нет**\n_{fallback_advice}_"
    elif selected_in_cat:
        async with AsyncSessionLocal() as db:
            # Fetch names for display
            res = await db.execute(select(PartnerDB.name).where(PartnerDB.id.in_(selected_in_cat)))
            names = res.scalars().all()
            if names:
                text += f"\n\n✅ **Выбрано:** {', '.join(names)}"

    # Check if user has existing partners in this category
    has_existing = False
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, message.from_user.id if isinstance(message, Message) else message.from_user.id)
        if user_db:
            existing = await get_partners_by_universal_category(db, user_db.id, category)
            if existing:
                has_existing = True
    
    # Build Keyboard
    kb_rows = []
    
    if is_isolated:
        kb_rows.append([InlineKeyboardButton(text="↩️ Отменить изоляцию", callback_data=f"no_iso_p_{category}")])
        kb_rows.append([InlineKeyboardButton(text="➡️ Дальше", callback_data=f"next_p_{category}")])
    else:
        # Main actions
        if has_existing:
            kb_rows.append([InlineKeyboardButton(text="📂 Выбрать из списка", callback_data=f"list_p_{category}")])
            
        kb_rows.append([InlineKeyboardButton(text="➕ Добавить нового", callback_data=f"add_p_{category}")])
        
        # Navigation
        if selected_in_cat:
            kb_rows.append([InlineKeyboardButton(text="➡️ Дальше", callback_data=f"next_p_{category}")])
        else:
            kb_rows.append([InlineKeyboardButton(text="🧘 Никого нет / Изоляция", callback_data=f"iso_p_{category}")])
            kb_rows.append([InlineKeyboardButton(text="🤷‍♂️ Пропустить", callback_data=f"skip_p_{category}")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    
    # Update state
    state_map = {
        "source": ProjectSetupState.waiting_for_source,
        "ally": ProjectSetupState.waiting_for_ally,
        "protege": ProjectSetupState.waiting_for_protege,
        "world": ProjectSetupState.waiting_for_world
    }
    await state.set_state(state_map[category])
    
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.answer(text, parse_mode="Markdown", reply_markup=markup)


@router.callback_query(F.data.startswith("iso_p_"))
async def set_isolation(callback: CallbackQuery, state: FSMContext):
    """Set isolation for category"""
    _, _, category = callback.data.split("_")
    
    data = await state.get_data()
    
    # Update isolation settings
    isolation_settings = data.get("isolation_settings", {})
    isolation_settings[category] = {"is_isolated": True}
    
    # Clear selected partners for this category
    project_partners = data.get("project_partners", {})
    project_partners[category] = []
    
    await state.update_data(isolation_settings=isolation_settings, project_partners=project_partners)
    
    await _ask_partner_category(callback, state, category)
    await callback.answer("Режим изоляции выбран")


@router.callback_query(F.data.startswith("no_iso_p_"))
async def unset_isolation(callback: CallbackQuery, state: FSMContext):
    """Unset isolation for category"""
    _, _, _, category = callback.data.split("_")
    
    data = await state.get_data()
    
    # Update isolation settings
    isolation_settings = data.get("isolation_settings", {})
    isolation_settings[category] = {"is_isolated": False}
    
    await state.update_data(isolation_settings=isolation_settings)
    
    await _ask_partner_category(callback, state, category)
    await callback.answer("Режим изоляции отключен")


@router.callback_query(F.data.startswith("list_p_"))
async def show_existing_partners(callback: CallbackQuery, state: FSMContext):
    """Show list of existing partners to select"""
    _, _, category = callback.data.split("_")
    
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, get_partners_by_universal_category
    
    data = await state.get_data()
    project_partners = data.get("project_partners", {})
    selected_in_cat = project_partners.get(category, [])
    
    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, callback.from_user.id)
        if not user_db:
            await callback.answer("Ошибка пользователя")
            return
        partners = await get_partners_by_universal_category(db, user_db.id, category)
        
    kb_rows = []
    for p in partners:
        label = f"✅ {p.name}" if p.id in selected_in_cat else p.name
        kb_rows.append([InlineKeyboardButton(text=label, callback_data=f"sel_p_{category}_{p.id}")])
        
    kb_rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_p_{category}")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await callback.message.edit_text(f"Выберите партнеров для категории **{category.upper()}**:", parse_mode="Markdown", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("back_p_"))
async def back_to_category_menu(callback: CallbackQuery, state: FSMContext):
    """Go back to category main menu"""
    _, _, category = callback.data.split("_")
    await _ask_partner_category(callback, state, category)


@router.callback_query(F.data.startswith("sel_p_"))
async def toggle_partner_selection(callback: CallbackQuery, state: FSMContext):
    """Toggle partner selection from list"""
    parts = callback.data.split("_")
    # format: sel_p_category_id - id might contain dashes/underscores, need to be careful
    # But UUID usually doesn't conflict if we split carefully. 
    # Actually split("_") with partner_id being uuid might be risky if uuid has underscores? UUIDs use hyphens.
    # So split("_") is fine for 4 parts: sel, p, category, id.
    
    category = parts[2]
    partner_id = "_".join(parts[3:]) # Rejoin in case id had underscores (unlikely for uuid but safe)
    
    data = await state.get_data()
    project_partners = data.get("project_partners", {})
    
    current_list = project_partners.get(category, [])
    if partner_id in current_list:
        current_list.remove(partner_id)
    else:
        current_list.append(partner_id)
        
    project_partners[category] = current_list
    await state.update_data(project_partners=project_partners)
    
    # Stay in list view
    await show_existing_partners(callback, state)


@router.callback_query(F.data.startswith("add_p_"))
async def start_add_partner(callback: CallbackQuery, state: FSMContext):
    """Ask for new partner name"""
    _, _, category = callback.data.split("_")
    await state.update_data(adding_category=category)
    
    # We keep the state as is (waiting_for_X), but send a prompt
    await callback.message.answer(
        "Напиши имя нового партнера (одним сообщением):", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"cancel_add_{category}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_add_"))
async def cancel_add_partner(callback: CallbackQuery, state: FSMContext):
    """Cancel adding new partner"""
    _, _, category = callback.data.split("_")
    await state.update_data(adding_category=None)
    await callback.message.delete()
    # No need to refresh main view, it's still there
    await callback.answer("Отменено")


@router.callback_query(F.data.startswith("next_p_"))
async def next_partner_step(callback: CallbackQuery, state: FSMContext):
    """Go to next category"""
    _, _, category = callback.data.split("_")
    
    next_map = {
        "source": "ally",
        "ally": "protege",
        "protege": "world",
        "world": "finish"
    }
    
    next_cat = next_map.get(category)
    if next_cat == "finish":
        await _finish_project_setup(callback.message, state)
    else:
        await _ask_partner_category(callback, state, next_cat)
    await callback.answer()


@router.callback_query(F.data.startswith("skip_p_"))
async def skip_partner_step(callback: CallbackQuery, state: FSMContext):
    """Skip category (empty list)"""
    # Just proceed to next
    await next_partner_step(callback, state)


@router.callback_query(F.data.startswith("ctype_"))
async def process_contact_type(callback: CallbackQuery, state: FSMContext):
    """Handle contact type selection and create partner"""
    ctype = callback.data.split("_")[1] # physical/online
    
    data = await state.get_data()
    name = data.get("temp_partner_name")
    category = data.get("adding_category")
    
    if not name or not category:
        await callback.answer("Данные устарели, попробуй снова")
        await callback.message.delete()
        return

    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, get_default_partner_group_by_category, create_partner
    from app.models.partner import Partner
    from uuid import uuid4

    async with AsyncSessionLocal() as db:
        user_db = await get_user_by_telegram_id(db, callback.from_user.id)
        if not user_db:
            await callback.answer("Пользователь не найден")
            return
            
        group = await get_default_partner_group_by_category(db, user_db.id, category)
        if not group:
            await callback.answer("Группа не найдена")
            return
            
        p = Partner(
            id=str(uuid4()),
            name=name,
            group_id=group.id,
            user_id=user_db.id,
            contact_type=ctype
        )
        created = await create_partner(db, p)
        await db.commit()
        
        # Add to selection
        project_partners = data.get("project_partners", {})
        current_list = project_partners.get(category, [])
        current_list.append(created.id)
        project_partners[category] = current_list
        
        await state.update_data(project_partners=project_partners, adding_category=None, temp_partner_name=None)
        
        await callback.message.edit_text(f"✅ Добавлен и выбран: {name} ({'🏠' if ctype=='physical' else '🌐'})")
        
        # Refresh wizard
        await _ask_partner_category(callback, state, category)


async def _process_partner_input(message: Message, state: FSMContext, current_cat: str, next_cat: str):
    """Process NEW partner name input"""
    
    data = await state.get_data()
    adding_cat = data.get("adding_category")
    
    # Only process text if we are adding a partner for this category
    if adding_cat != current_cat:
        # Ignore random text or show hint
        return

    name = message.text.strip()
    if not name:
        return

    # Save temp name
    await state.update_data(temp_partner_name=name)
    
    # Ask contact type
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Лично", callback_data="ctype_physical"),
            InlineKeyboardButton(text="🌐 Онлайн", callback_data="ctype_online")
        ],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"cancel_add_{current_cat}")]
    ])
    
    await message.answer(
        f"Как ты будешь контактировать с **{name}**?", 
        reply_markup=kb,
        parse_mode="Markdown"
    )


async def _finish_project_setup(message: Message, state: FSMContext):
    """Finish setup and activate project"""
    from app.database import AsyncSessionLocal
    from app.crud_extended import create_karma_plan
    from app.crud import update_user_focus, get_user_by_telegram_id, save_problem_history
    from app.knowledge.qdrant import QdrantKnowledgeBase
    
    data = await state.get_data()
    solution = data.get("pending_solution")
    problem_text = data.get("problem_text")
    history_id = data.get("history_id")
    project_partners = data.get("project_partners")
    isolation_settings = data.get("isolation_settings")
    
    if not solution or not problem_text:
        await message.answer("Данные устарели. Начни заново: /solver")
        return
        
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            if user_db:
                # 1. Ensure we have a history record for this solution
                if not history_id:
                    history = await save_problem_history(db, user_db.id, problem_text, solution)
                    history_id = history.id
                
                # Extract strategy
                strategy_snapshot = {
                    "root_cause": solution.get("root_cause"),
                    "stop_action": solution.get("stop_action"),
                    "start_action": solution.get("start_action"),
                    "grow_action": solution.get("grow_action"),
                    "success_tip": solution.get("success_tip"),
                    "practice_steps": solution.get("practice_steps", []),
                    "problem_text": problem_text
                }

                # 2. Create Plan with Partners
                await create_karma_plan(
                    db,
                    user_db.id,
                    history_id,
                    strategy_snapshot,
                    duration_days=30,
                    project_partners=project_partners,
                    isolation_settings=isolation_settings
                )
                
                # 3. Update Focus
                await update_user_focus(db, user_db.id, problem_text)
                
                await db.commit()
                
                # Format success message
                partners_text = ""
                # Could format this nicely
                
                await message.answer(
                    f"🎯 **Цель активирована:** {problem_text}\n\n"
                    "✅ Команда кармических партнеров собрана!\n"
                    "Теперь твой план на день будет настроен на решение этой задачи.",
                    parse_mode="Markdown"
                )
                
                # Get Daily Quote
                qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
                quote = await qdrant.get_daily_quote(problem_text)
                
                quote_text = (
                    f"📜 **Мудрость дня:**\n\n"
                    f"_{quote['text']}_\n\n"
                    f"Открой приложение, чтобы увидеть свои 4 действия на сегодня! 👇"
                )
                
                kb = ReplyKeyboardMarkup(
                    keyboard=[[
                        KeyboardButton(
                            text="📱 Открыть приложение",
                            web_app=WebAppInfo(url=settings.WEBAPP_URL)
                        )
                    ]],
                    resize_keyboard=True
                )
                
                await message.answer(quote_text, parse_mode="Markdown", reply_markup=kb)
                await state.clear()
                
    except Exception as e:
        logger.error(f"Error setting goal: {e}", exc_info=True)
        await message.answer("Ошибка при сохранении цели.")


# =============================================================================
# Problem Solving Flow
# =============================================================================

@router.message(Command("solver"))
async def cmd_solver(message: Message, state: FSMContext):
    """Start problem solving dialog"""
    try:
        await state.set_state(ProblemState.waiting_for_description)

        await message.answer(
            "Опиши свою текущую проблему или ситуацию, которую хочешь разрешить.\n\n"
            "Например: 'Мало денег, долги', 'Конфликты с партнером', 'Нет энергии'..."
        )
        logger.info(f"User {message.from_user.id} started resolving action")
    except Exception as e:
        logger.error(f"Error in cmd_done: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуй еще раз.")

@router.callback_query(F.data == "start_problem_flow")
async def start_problem_flow(callback: CallbackQuery, state: FSMContext):
    """Start problem solving dialog"""
    await state.set_state(ProblemState.waiting_for_description)
    
    await callback.message.answer(
        "Опиши свою текущую проблему или ситуацию, которую хочешь разрешить.\n\n"
        "Например: 'Мало денег, долги', 'Конфликты с партнером', 'Нет энергии'..."
    )
    await callback.answer()


@router.message(ProblemState.waiting_for_description)
async def process_problem_description(message: Message, state: FSMContext):
    """Start intelligent diagnostic dialog"""
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.agents.problem_solver import ProblemSolverAgent
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    
    problem_text = message.text
    
    # Show typing status
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Initialize Agent
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        agent = ProblemSolverAgent(qdrant)
        
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            if not user_db:
                await message.answer("Пользователь не найден.")
                return
                
            # Convert DB model to Pydantic for Agent
            from app.models.user import UserProfile
            user_profile = UserProfile.model_validate(user_db)
            
            # Generate unique session ID for this diagnostic
            import uuid
            session_id = f"tg_{message.from_user.id}_{uuid.uuid4().hex[:8]}"
            
            # Start intelligent diagnostic (multi-step mode)
            solution = await agent.analyze_problem(
                user_profile,
                problem_text,
                session_id=session_id,
            )
            
            # Check if diagnostic needs more questions
            if solution.get("needs_clarification") and solution.get("clarifying_questions"):
                # Save diagnostic state
                await state.update_data(
                    session_id=session_id,
                    original_problem=problem_text,
                    diagnostic_summary=solution.get("diagnostic_summary", ""),
                    confidence_score=solution.get("confidence_score", 0.0)
                )
                await state.set_state(ProblemState.waiting_for_diagnostic_answer)
                
                # Show the first diagnostic question
                question = solution["clarifying_questions"][0]
                
                text = (
                    f"🔍 **Карма-диагностика**\n\n"
                    f"{solution.get('diagnostic_summary', '')}\n\n"
                    f"❓ **Вопрос:**\n{question}\n\n"
                    f"Отвечай просто: 'да', 'нет' или приведи пример."
                )
                
                await message.answer(text, parse_mode="Markdown")
                return
            
            # If diagnostic is complete, show solution immediately
            await _show_complete_solution(message, state, problem_text, solution, user_db)
            
    except Exception as e:
        logger.error(f"Error in diagnostic: {e}", exc_info=True)
        await message.answer("Не удалось начать диагностику. Попробуй позже.")
        await state.clear()


@router.callback_query(F.data == "start_partner_setup")
async def start_partner_setup(callback: CallbackQuery, state: FSMContext):
    """Start partner selection wizard"""
    await callback.answer()
    await callback.message.answer(
        "🧘 **Кармические партнеры**\n\n"
        "Чтобы достичь цели со 100% вероятностью, нам нужно посадить семена. "
        "Семена сажаются в почву — это другие люди.\n\n"
        "Давай выберем 4 группы партнеров для этого проекта."
    )
    await _ask_partner_category(callback.message, state, "source")


@router.message(ProjectSetupState.waiting_for_source)
async def process_source_partner(message: Message, state: FSMContext):
    """Process source partner"""
    await _process_partner_input(message, state, "source", "ally")


@router.message(ProjectSetupState.waiting_for_ally)
async def process_ally_partner(message: Message, state: FSMContext):
    """Process ally partner"""
    await _process_partner_input(message, state, "ally", "protege")


@router.message(ProjectSetupState.waiting_for_protege)
async def process_protege_partner(message: Message, state: FSMContext):
    """Process protege partner"""
    await _process_partner_input(message, state, "protege", "world")


@router.message(ProjectSetupState.waiting_for_world)
async def process_world_partner(message: Message, state: FSMContext):
    """Process world partner"""
    await _process_partner_input(message, state, "world", "finish")
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.agents.problem_solver import ProblemSolverAgent
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, save_problem_history
    
    user_answer = message.text.strip()
    data = await state.get_data()
    
    session_id = data.get("session_id")
    original_problem = data.get("original_problem")
    
    if not session_id or not original_problem:
        await message.answer("Сессия диагностики утеряна. Начни заново: /solver")
        await state.clear()
        return
    
    # Show typing status
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
        agent = ProblemSolverAgent(qdrant)
        
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            if not user_db:
                await message.answer("Пользователь не найден.")
                await state.clear()
                return
            
            from app.models.user import UserProfile
            user_profile = UserProfile.model_validate(user_db)
            
            # Continue diagnostic with user's answer (structured, без текстовых маркеров)
            solution = await agent.analyze_problem(
                user_profile,
                original_problem,
                session_id=session_id,
                diagnostic_answer=user_answer,
            )
            
            # Check if diagnostic needs more questions
            if solution.get("needs_clarification") and solution.get("clarifying_questions"):
                # Continue with next question
                question = solution["clarifying_questions"][0]
                confidence = solution.get("confidence_score", 0.0)
                
                text = (
                    f"🔍 **Карма-диагностика** (уверенность: {confidence:.1%})\n\n"
                    f"❓ **Следующий вопрос:**\n{question}\n\n"
                    f"Отвечай просто: 'да', 'нет' или приведи пример."
                )
                
                await message.answer(text, parse_mode="Markdown")
                return
            
            # Diagnostic complete - show full solution
            await _show_complete_solution(message, state, original_problem, solution, user_db)
            
    except Exception as e:
        logger.error(f"Error in diagnostic continuation: {e}", exc_info=True)
        await message.answer("Ошибка в процессе диагностики. Попробуй позже.")
        await state.clear()


async def _show_complete_solution(message: Message, state: FSMContext, problem_text: str, solution: dict, user_db):
    """Show complete solution and save to database"""
    from app.database import AsyncSessionLocal
    from app.crud import save_problem_history
    
    try:
        async with AsyncSessionLocal() as db:
            # Save to database (no special active flag on history)
            history = await save_problem_history(
                db, 
                user_db.id, 
                problem_text, 
                solution,
            )
            await db.commit()
            
            # Update state
            await state.update_data(
                pending_solution=solution,
                problem_text=problem_text,
                history_id=history.id
            )
            
            # Format response
            confidence = solution.get("confidence_score", 0.0)
            diagnostic_summary = solution.get("diagnostic_summary", "")
            
            response_text = (
                f"🎯 **Карма-диагностика завершена**\n"
                f"Уверенность: {confidence:.1%}\n\n"
            )
            
            if diagnostic_summary:
                response_text += f"📋 **Анализ:** {diagnostic_summary}\n\n"
            
            response_text += (
                f"🧐 **Корень проблемы:** {solution.get('root_cause')}\n\n"
                f"🌱 **Как это работает:**\n{solution.get('imprint_logic')}\n\n"
                f"🛑 **Что прекратить:** {solution.get('stop_action')}\n"
                f"🚀 **Что начать:** {solution.get('start_action')}\n"
            )
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Выбрать целью", callback_data="confirm_goal")],
                [InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
            ])
            
            await message.answer(response_text, parse_mode="Markdown", reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error showing solution: {e}", exc_info=True)
        await message.answer("Ошибка при сохранении решения. Попробуй позже.")


@router.message(Command("today"))
async def cmd_today(message: Message):
    """Quick text list for today"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from app.agents.daily_manager import DailyManagerAgent
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from app.config import get_settings
    from datetime import datetime
    
    try:
        settings = get_settings()
        
        async with AsyncSessionLocal() as db:
            # Get or create user
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            
            if not user_db:
                await message.answer(
                    "Привет! Сначала нажми /start чтобы начать работу с ботом 🙏"
                )
                return
            
            # Generate daily actions using agent
            from app.models.user import UserProfile
            user_profile = UserProfile(
                id=user_db.id,
                telegram_id=user_db.telegram_id,
                first_name=user_db.first_name,
                username=user_db.username,
                occupation=user_db.occupation or "employee",
                available_times=user_db.available_times or [],
                daily_minutes=user_db.daily_minutes or 30,
                current_focus=user_db.current_focus,
                streak_days=user_db.streak_days,
            )
            
            # Use agent to generate actions only (без полного сообщения)
            qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
            agent = DailyManagerAgent(qdrant)
            
            actions = await agent.get_daily_actions(
                user_id=user_profile.id,
                first_name=user_profile.first_name,
                focus=user_profile.current_focus,
                streak_days=user_profile.streak_days,
                total_seeds=user_profile.total_seeds
            )

            if actions:
                text = " Твои действия на сегодня:\n\n"
                for i, action in enumerate(actions[:4], 1):
                    partner_name = action.get("partner_name", "Партнёр")
                    description = action.get("description", "")
                    why = action.get("why")
                    if why:
                        text += f"{i}. {partner_name}: {description} — {why}\n"
                    else:
                        text += f"{i}. {partner_name}: {description}\n"

                await message.answer(text)
            else:
                text = (
                    "🌱 На сегодня:\n\n"
                    "Пока у тебя ещё нет активного кармического проекта, поэтому я не могу честно предложить конкретные шаги.\n\n"
                    "Давай сначала аккуратно разберёмся с главной задачей, а потом я соберу для тебя точный план на день."
                )

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🧠 Разобрать задачу здесь", callback_data="start_problem_flow")],
                    [InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/problem"))],
                ])

                await message.answer(text, reply_markup=kb)
            logger.info(f"User {message.from_user.id} requested today's actions")
            
    except Exception as e:
        logger.error(f"Error in cmd_today: {e}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке действий. Попробуй позже.")


@router.message(Command("done"))
async def cmd_done(message: Message, state: FSMContext):
    """Quick mark action as done"""
    
    try:
        await state.set_state(ActionState.waiting_for_action_id)
        await message.answer(
            "Что сделал? Отправь номер действия (1-4) или описание:"
        )
        logger.info(f"User {message.from_user.id} started marking action as done")
    except Exception as e:
        logger.error(f"Error in cmd_done: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуй еще раз.")

async def process_action_done(message: Message, state: FSMContext):
    """Process completed action"""
    from app.database import AsyncSessionLocal
    from app.crud import (
		get_user_by_telegram_id, 
		increment_user_seeds_count,
		toggle_daily_task_completion,
		create_seed
	)
    from app.models.db_models import PartnerActionDB
    from app.models.seed import Seed
    from app.agents.daily_manager import DailyManagerAgent
    from app.knowledge.qdrant import QdrantKnowledgeBase
    from datetime import datetime, UTC
    import uuid
    
    text = message.text.strip()
    
    try:
        settings = get_settings()
        
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            
            if not user_db:
                await message.answer("Ошибка: пользователь не найден. Нажми /start")
                return

            # Check if user sent a number corresponding to a daily task
            if text.isdigit() and text in {"1", "2", "3", "4"}:
                idx = int(text) - 1 # 0-indexed
                
                # Fetch actions to get the ID
                # We need to reconstruct the agent to get the same actions
                # This is a bit heavy but ensures we get the right IDs
                qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
                agent = DailyManagerAgent(qdrant)
                
                actions = await agent.get_daily_actions(
                    user_id=user_db.id,
                    first_name=user_db.first_name,
                    focus=user_db.current_focus,
                    streak_days=user_db.streak_days,
                    total_seeds=user_db.total_seeds
                )
                
                if 0 <= idx < len(actions):
                    target_action = actions[idx]
                    action_id = target_action["id"]
                    description = target_action["description"]
                    
                    if action_id.isdigit():
                        # Project Mode: DailyTaskDB
                        await toggle_daily_task_completion(
                            db,
                            user_id=user_db.id,
                            task_id=int(action_id),
                            completed=True
                        )
                        # toggle_daily_task_completion handles seed creation internally
                    
                    await db.commit()

                    await message.answer(
                        f"✅ Выполнено: {description}\n\n"
                        f"🌱 Семя посажено!\n"
                        "Продолжай в том же духе!"
                    )
                    await state.clear()
                    return

            # Fallback: Custom text or number out of range (treat as custom text)
            partner_name = None
            action_text = text

            # Save partner action to database
            action = PartnerActionDB(
                id=str(uuid.uuid4()),
                user_id=user_db.id,
                partner_id=None,
                partner_name=partner_name,
                action=action_text,
                timestamp=datetime.now(UTC),
                completed=True,
            )
            db.add(action)
            
            # Create a Seed for this custom action too? 
            # The prompt implies "marking in UI... create seed". 
            # If user manually types "Done X", it's good to treat as seed too.
            seed = Seed(
                id=str(uuid.uuid4()),
                user_id=user_db.id,
                timestamp=datetime.now(UTC),
                action_type="custom_action",
                description=action_text,
                partner_group="world",
                intention_score=5,
                emotion_level=5,
                understanding=True,
                estimated_maturation_days=21,
                strength_multiplier=1.0
            )
            await create_seed(db, seed)
            
            # Increment seeds count
            await increment_user_seeds_count(db, user_db.id)
            
            await db.commit()
            
            logger.info(f"User {message.from_user.id} completed action: {action_text}")
            
            await message.answer(
                f"✅ Отлично! Записал: {action_text}\n\n"
                f"Всего семян посеяно: {user_db.total_seeds + 1} 🌱\n"
                "Продолжай в том же духе!"
            )
                
    except Exception as e:
        logger.error(f"Error saving action: {e}", exc_info=True)
        await message.answer(
            f"✅ Отлично! Записал: {text}\n\n"
            "Продолжай в том же духе! 🌱"
        )
    
    await state.clear()


@router.message(Command("seed"))
async def cmd_seed(message: Message, state: FSMContext):
    """Quick seed logging"""
    
    try:
        await state.set_state(SeedState.waiting_for_description)
        await message.answer(
            "Опиши что посеял (одна строка):\n\n"
            "Например: Помог коллеге с проектом"
        )
        logger.info(f"User {message.from_user.id} started seed recording")
    except Exception as e:
        logger.error(f"Error in cmd_seed: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуй еще раз.")


@router.message(SeedState.waiting_for_description)
async def process_seed(message: Message, state: FSMContext):
    """Process seed description"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, create_seed, increment_user_seeds_count
    from app.models.seed import Seed
    from datetime import datetime, UTC, timedelta
    from zoneinfo import ZoneInfo
    import uuid
    
    description = message.text.strip()
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            
            if user_db:
                # Create seed
                now_utc = datetime.now(UTC)
                seed = Seed(
                    id=str(uuid.uuid4()),
                    user_id=user_db.id,
                    timestamp=now_utc,
                    action_type="kindness",
                    description=description,
                    partner_group="world",
                    intention_score=7,
                    emotion_level=7,
                    understanding=True,
                    estimated_maturation_days=21,
                    strength_multiplier=1.5
                )
                
                await create_seed(db, seed)
                await increment_user_seeds_count(db, user_db.id)
                await db.commit()

                logger.info(f"User {message.from_user.id} planted seed: {description}")

                # Calculate maturation date in user's local timezone for display
                user_tz = ZoneInfo(user_db.timezone or "UTC")
                maturation_utc = now_utc + timedelta(days=21)
                maturation_date = maturation_utc.astimezone(user_tz)

                await message.answer(
                    f"🌱 Семя посеяно!\n\n"
                    f"📝 {description}\n\n"
                    f"📅 Ожидаемое созревание: {maturation_date.strftime('%d.%m.%Y')}\n"
                    f"💪 Сила: {seed.strength_multiplier}x\n\n"
                    f"Всего семян: {user_db.total_seeds}\n\n"
                    "Чем сильнее намерение и эмоция - тем быстрее созреет! 💎"
                )
            else:
                await message.answer("Ошибка: пользователь не найден. Нажми /start")
                
    except Exception as e:
        logger.error(f"Error saving seed: {e}", exc_info=True)
        await message.answer(
            f"🌱 Семя посеяно!\n\n"
            f"Описание: {description}\n\n"
            "Ожидай результата через 14-30 дней. "
            "Чем сильнее намерение и эмоция - тем быстрее созреет!"
        )
    
    await state.clear()


@router.message(Command("app"))
async def cmd_app(message: Message):
    """Open Mini App"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=settings.WEBAPP_URL)
            )
        ]],
        resize_keyboard=True
    )
    
    await message.answer("Открывай:", reply_markup=keyboard)


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Reset user progress with confirmation"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, стереть всё", callback_data="reset_confirm"),
            InlineKeyboardButton(text="❌ Нет, оставить", callback_data="reset_cancel")
        ]
    ])
    
    await message.answer(
        "🗑 **Сброс всех данных**\n\n"
        "Ты действительно хочешь удалить весь свой прогресс, историю посаженных семян и настройки? "
        "Это вернет тебя к самому началу пути, как чистый лист.\n\n"
        "Как в «Кармическом менеджменте»: иногда, чтобы создать что-то новое, нужно полностью очистить пространство от старого. "
        "Но помни, что все накопленные заслуги (семена) в системе тоже исчезнут (хотя в карме они останутся навсегда 😉).\n\n"
        "Уверен?",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "reset_cancel")
async def reset_cancel(callback: CallbackQuery):
    """Cancel reset"""
    await callback.message.edit_text("Фух! Всё осталось на своих местах. Продолжаем сеять разумное, доброе, вечное! 🌱")
    await callback.answer()


@router.callback_query(F.data == "reset_confirm")
async def reset_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm reset"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, reset_user_progress
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, callback.from_user.id)
            
            if user_db:
                await reset_user_progress(db, user_db.id)
                await db.commit()
                
                # Clear state
                await state.clear()
                
                await callback.message.edit_text(
                    "✨ **Полная перезагрузка**\n\n"
                    "Все данные очищены. Ты снова в начале пути, но теперь с опытом!\n"
                    "Чтобы начать заново, нажми /start",
                    parse_mode="Markdown"
                )
            else:
                await callback.message.edit_text("Пользователь не найден. Нажми /start")
                
    except Exception as e:
        logger.error(f"Error resetting user: {e}", exc_info=True)
        await callback.message.edit_text("Произошла ошибка при сбросе данных. Попробуй позже.")
        
    await callback.answer()


# Register router
dp.include_router(router)


shutdown_event = asyncio.Event()

async def start_bot():
    """Start the bot"""
    logger.info("Starting Telegram bot...")
    retry_delay = 5
    shutdown_event.clear()
    try:
        while not shutdown_event.is_set():
            try:
                # Get bot info
                bot_info = await bot.get_me()
                logger.info(f"Bot @{bot_info.username} started successfully")

                # Set bot commands menu
                commands = [
                    BotCommand(command="start", description="🏠 Начать работу с ботом"),
                    BotCommand(command="app", description="📱 Открыть приложение"),
                    BotCommand(command="solver", description="💭 Решить проблему"),
                    BotCommand(command="today", description="📋 Действия на сегодня"),
                    BotCommand(command="seed", description="🌱 Записать семя"),
                    BotCommand(command="done", description="✅ Отметить выполнение"),
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
