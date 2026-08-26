import asyncio
import logging
from pyrogram import Client, idle
from bot.config import Config
from bot.core.smart_env import smart_env
from bot.core.auto_optimizer import auto_optimizer
from bot.core.lazy_imports import lazy_imports
from bot.core.db_cache import db_cache

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
    logger.info(f"RAM Limit: {env_info['ram_limit_mb']} MB")
    logger.info(f"Optimization: {env_info['optimization_level']}")
    logger.info("=" * 50)
    
    # Apply optimizations
    await auto_optimizer.apply_optimizations()
    
    # Set optimization mode for lazy imports and cache
    is_optimized = auto_optimizer.is_active
    lazy_imports.set_optimized(is_optimized)
    db_cache.set_optimized(is_optimized)
    
    if is_optimized:
        logger.info(f"Applied {env_info['optimization_level']} optimization for {env_info['environment']}")
    else:
        logger.info("Full power mode - No optimization needed")
    
    # Get worker count
    workers = auto_optimizer.get_workers()
    logger.info(f"Worker count: {workers}")
    
    # Create bot client
    bot = Client(
        "ZxZone-MLB",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        plugins=dict(root="bot/plugins"),
        workers=workers
    )
    
    try:
        # Start bot
        await bot.start()
        logger.info("Bot started successfully!")
        logger.info(f"Bot: @{Config.BOT_USERNAME}")
        logger.info(f"Owner: {Config.OWNER_ID}")
        
        # Start background optimization
        await auto_optimizer.start_background_optimization()
        
        # Keep bot running
        await idle()
        
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        
    finally:
        await bot.stop()
        logger.info("Bot stopped!")

if __name__ == "__main__":
    asyncio.run(main())
