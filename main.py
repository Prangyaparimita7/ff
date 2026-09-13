import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

# Import all modular routers including the new channels module
from handlers import start, seller, marketplace_mongo, admin_panel, general, channels

async def main():
    # Setup logging to monitor bot events and errors
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    # Initialize Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register routers in logical execution order
    dp.include_router(start.router)
    dp.include_router(seller.router)
    dp.include_router(marketplace_mongo.router)
    dp.include_router(admin_panel.router)
    dp.include_router(channels.router)  # Added channels router for force-sub and admin panel linking
    dp.include_router(general.router)

    print("🤖 Free Fire Marketplace Bot is up and running...")
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🤖 Bot stopped successfully.")