import asyncio
import logging
import threading
from pyrogram import Client, idle
from bot.config import Config
from bot.core.smart_env import smart_env
from bot.core.auto_optimizer import auto_optimizer
from bot.core.keep_alive import keep_alive
from bot.core.heroku_keeper import heroku_keeper

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
    
    # Get environment info
    env_info = smart_env.get_info()
    logger.info("=" * 50)
    logger.info("ZxZone-MLB Bot Starting...")
    logger.info(f"Environment: {env_info['environment']}")
    logger.info("=" * 50)
    
    # Apply optimizations
    await auto_optimizer.apply_optimizations()
    
    # Start keep alive (Heroku only)
    await keep_alive.start()
    await heroku_keeper.start()
    
    # Start web server (for keep alive)
    if smart_env.env_type == 'heroku':
        from web_server import start_web_server
        web_thread = threading.Thread(target=start_web_server, daemon=True)
        web_thread.start()
        logger.info("Web server started for keep alive")
    
    # Create bot client
    bot = Client(
        "ZxZone-MLB",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        plugins=dict(root="bot/plugins"),
        workers=auto_optimizer.get_workers()
    )
    
    try:
        # Start bot
        await bot.start()
        logger.info("Bot started successfully!")
        logger.info(f"Bot: @{Config.BOT_USERNAME}")
        logger.info(f"Owner: {Config.OWNER_ID}")
        
        # Keep bot running
        await idle()
        
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        
    finally:
        await bot.stop()
        logger.info("Bot stopped!")

if __name__ == "__main__":
    asyncio.run(main())
