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
# Problem Solving Flow
# =============================================================================

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
    """Analyze problem using Agent"""
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
            
            # Analyze
            solution = await agent.analyze_problem(user_profile, problem_text)
            
            # Save solution in state to use later if user confirms
            await state.update_data(
                pending_solution=solution,
                problem_text=problem_text
            )
            
            # Format response
            response_text = (
                f"🧐 **Анализ ситуации:**\n\n"
                f"**Корень проблемы:** {solution.get('root_cause')}\n\n"
                f"🌱 **Как это работает (семена):**\n{solution.get('imprint_logic')}\n\n"
                f"🛑 **Что прекратить (Stop):** {solution.get('stop_action')}\n"
                f"🚀 **Что начать (Start):** {solution.get('start_action')}\n"
            )
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Выбрать целью", callback_data="confirm_goal")],
                [InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
            ])
            
            await message.answer(response_text, parse_mode="Markdown", reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Error analyzing problem: {e}", exc_info=True)
        await message.answer("Не удалось проанализировать проблему. Попробуй позже.")
        await state.clear()


@router.callback_query(F.data == "confirm_goal")
async def confirm_goal_selection(callback: CallbackQuery, state: FSMContext):
    """Set problem as current focus and show daily plan"""
    from app.database import AsyncSessionLocal
    from app.crud import update_user_focus, save_problem_history, set_active_problem, clear_today_suggestions, get_user_by_telegram_id
    from app.knowledge.qdrant import QdrantKnowledgeBase
    
    data = await state.get_data()
    solution = data.get("pending_solution")
    problem_text = data.get("problem_text")
    
    if not solution or not problem_text:
        await callback.answer("Данные устарели. Начни заново.", show_alert=True)
        return
        
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, callback.from_user.id)
            if user_db:
                # 1. Save history
                history = await save_problem_history(db, user_db.id, problem_text, solution)
                
                # 2. Set Active
                await set_active_problem(db, user_db.id, history.id)
                
                # 3. Update Focus
                await update_user_focus(db, user_db.id, problem_text)
                
                # 4. Clear old suggestions so they regenerate
                await clear_today_suggestions(db, user_db.id)
                
                await db.commit()
                
                await callback.message.edit_text(
                    f"🎯 Цель активирована: **{problem_text}**\n\n"
                    "Теперь твой план на день будет настроен на решение этой задачи.",
                    parse_mode="Markdown"
                )
                
                # Get Daily Quote and encourage to open app
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
                
                await callback.message.answer(quote_text, parse_mode="Markdown", reply_markup=kb)
                await state.clear()
                
    except Exception as e:
        logger.error(f"Error setting goal: {e}", exc_info=True)
        await callback.answer("Ошибка при сохранении цели", show_alert=True)


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
                total_seeds=user_db.total_seeds
            )
            
            # Use agent to generate actions
            qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
            agent = DailyManagerAgent(qdrant)
            
            morning_msg = await agent.morning_message(
                user_id=user_profile.id,
                first_name=user_profile.first_name,
                focus=user_profile.current_focus,
                streak_days=user_profile.streak_days,
                total_seeds=user_profile.total_seeds
            )
            actions = morning_msg.get("actions", [])
            
            if actions:
                text = "🌱 Твои действия на сегодня:\n\n"
                for i, action in enumerate(actions[:4], 1):
                    partner_name = action.get("partner_name", "Партнёр")
                    description = action.get("description", "")
                    why = action.get("why")
                    if why:
                        text += f"{i}. {partner_name}: {description} — {why}\n"
                    else:
                        text += f"{i}. {partner_name}: {description}\n"
            else:
                text = "🌱 На сегодня:\n\n"
                text += "Открой приложение 📱 чтобы увидеть полный план дня!"
            
            await message.answer(text)
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


@router.message(ActionState.waiting_for_action_id)
async def process_action_done(message: Message, state: FSMContext):
    """Process completed action"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id, increment_user_seeds_count
    from app.models.db_models import PartnerActionDB
    from datetime import datetime
    import uuid
    
    text = message.text.strip()
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            
            if user_db:
                partner_name = None
                action_text = text

                # If user sends a number 1-4, store a meaningful label
                if text.isdigit() and text in {"1", "2", "3", "4"}:
                    idx = int(text)
                    partner_name_map = {
                        1: "Коллега",
                        2: "Клиент",
                        3: "Поставщик",
                        4: "Мир",
                    }
                    partner_name = partner_name_map.get(idx)
                    action_text = f"Daily action #{idx} completed"

                # Save partner action to database
                action = PartnerActionDB(
                    id=str(uuid.uuid4()),
                    user_id=user_db.id,
                    partner_id=None,
                    partner_name=partner_name,
                    action=action_text,
                    timestamp=datetime.utcnow(),
                    completed=True
                )
                db.add(action)
                
                # Increment seeds count
                await increment_user_seeds_count(db, user_db.id)
                
                await db.commit()
                
                logger.info(f"User {message.from_user.id} completed action: {action_text}")
                
                await message.answer(
                    f"✅ Отлично! Записал: {action_text}\n\n"
                    f"Всего семян посеяно: {user_db.total_seeds} 🌱\n"
                    "Продолжай в том же духе!"
                )
            else:
                await message.answer("Ошибка: пользователь не найден. Нажми /start")
                
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
    from datetime import datetime, timedelta
    import uuid
    
    description = message.text.strip()
    
    try:
        async with AsyncSessionLocal() as db:
            user_db = await get_user_by_telegram_id(db, message.from_user.id)
            
            if user_db:
                # Create seed
                seed = Seed(
                    id=str(uuid.uuid4()),
                    user_id=user_db.id,
                    timestamp=datetime.utcnow(),
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
                
                maturation_date = datetime.utcnow() + timedelta(days=21)
                
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


async def start_bot():
    """Start the bot"""
    logger.info("Starting Telegram bot...")
    try:
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"Bot @{bot_info.username} started successfully")
        
        # Set bot commands menu
        commands = [
            BotCommand(command="start", description="🏠 Начать работу с ботом"),
            BotCommand(command="app", description="📱 Открыть приложение"),
            BotCommand(command="today", description="📋 Действия на сегодня"),
            BotCommand(command="seed", description="🌱 Записать семя"),
            BotCommand(command="done", description="✅ Отметить выполнение"),
            BotCommand(command="reset", description="🔄 Сброс прогресса"),
        ]
        await bot.set_my_commands(commands)
        logger.info("Bot commands menu set successfully")
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        raise


async def stop_bot():
    """Stop the bot"""
    logger.info("Stopping Telegram bot...")
    try:
        await bot.session.close()
        logger.info("Bot stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping bot: {e}", exc_info=True)
