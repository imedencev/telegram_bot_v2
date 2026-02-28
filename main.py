"""
Main bot file - entry point.
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.database import init_db, get_session
from app.handlers import order_handlers, business_messages
from app.services.schedule_service import ScheduleService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main bot function"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN not found in environment")
    
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    
    # Sync staff data from pythonbotk13 database
    try:
        staff_count = ScheduleService.sync_staff_from_database()
        logger.info(f"Synced {staff_count} staff members from pythonbotk13 database")
    except Exception as e:
        logger.warning(f"Could not sync staff data: {e}")
    
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(business_messages.router)  # Owner commands first
    dp.include_router(order_handlers.router)
    logger.info("Handlers registered")
    
    async def db_session_middleware(handler, event, data):
        async for session in get_session():
            data["session"] = session
            data["bot"] = bot
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                raise
    
    dp.message.middleware()(db_session_middleware)
    dp.callback_query.middleware()(db_session_middleware)
    
    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
