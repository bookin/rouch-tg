"""Telegram Bot handlers"""
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, ErrorEvent, BotCommand
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
import logging
from app.config import get_settings


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
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


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    from app.database import AsyncSessionLocal
    from app.crud import get_or_create_user
    
    user = message.from_user
    logger.info(f"User {user.id} ({user.first_name}) started bot")
    
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
            
            is_new = user_db.created_at == user_db.updated_at
            logger.info(f"User {user.id}: {'created' if is_new else 'existing'}")
    
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=settings.WEBAPP_URL)
            )
        ]],
        resize_keyboard=True
    )
    
    welcome_text = (
        f"Привет, {user.first_name}! Я твой кармический менеджер 🧙‍♂️\n\n"
        "Я помогу тебе:\n"
        "🌱 Сажать и отслеживать кармические семена\n"
        "🧘 Практиковать медитацию и этику\n"
        "👥 Работать с 4 группами партнёров\n"
        "💎 Применять мудрость Diamond Cutter\n\n"
        "Открой приложение, чтобы начать:"
    )
    
    await message.answer(welcome_text, reply_markup=keyboard)


@router.message(Command("today"))
async def cmd_today(message: Message):
    """Quick text list for today"""
    from app.database import AsyncSessionLocal
    from app.crud import get_user_by_telegram_id
    from app.agents.daily_manager import DailyManagerAgent
    from app.knowledge.qdrant_client import QdrantKnowledgeBase
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
                occupation=user_db.occupation or "employee",
                available_times=user_db.available_times or [],
                daily_minutes=30
            )
            
            # Use agent to generate actions
            qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
            agent = DailyManagerAgent(qdrant)
            
            morning_msg = await agent.morning_message(user_profile)
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
