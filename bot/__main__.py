import asyncio
import logging
from pyrogram import Client, idle
from bot.config import Config

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Main bot function"""
    # Validate config
    Config.validate_config()
    
    # Create necessary directories
    Config.ensure_dirs()
    
    # Create bot client
    bot = Client(
        "ZxZone-MLB",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        plugins=dict(root="bot/plugins"),
        workers=200
    )
    
    try:
        # Start bot
        await bot.start()
        logger.info("✅ Bot started successfully!")
        logger.info(f"🤖 Bot: @{Config.BOT_USERNAME}")
        logger.info(f"👑 Owner: {Config.OWNER_ID}")
        
        # Keep bot running
        await idle()
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        
    finally:
        await bot.stop()
        logger.info("❌ Bot stopped!")

if __name__ == "__main__":
    asyncio.run(main())
