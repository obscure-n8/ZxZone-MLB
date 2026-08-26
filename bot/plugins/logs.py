import logging
import os
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Logger:
    def __init__(self):
        self.log_file = "bot.log"
        self.max_log_size = 10 * 1024 * 1024  # 10MB
        
    def log(self, level: str, message: str):
        """Log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Check log file size
        if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_log_size:
            # Rotate log
            os.rename(self.log_file, f"{self.log_file}.old")
            
        # Write to file
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
            
        # Print to console
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
            
    def info(self, message: str):
        self.log("INFO", message)
        
    def error(self, message: str):
        self.log("ERROR", message)
        
    def warning(self, message: str):
        self.log("WARNING", message)
        
    def debug(self, message: str):
        self.log("DEBUG", message)

# Create logger instance
bot_logger = Logger()

@Client.on_message(filters.command("logs") & filters.private)
async def logs_command(client: Client, message: Message):
    """Handle /logs command for admin"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    # Read last 50 lines of log
    try:
        with open("bot.log", 'r') as f:
            lines = f.readlines()[-50:]
            
        log_text = "📝 **Recent Logs:**\n\n"
        log_text += "".join(lines)
        
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
            
        await message.reply_text(f"```\n{log_text}\n```", parse_mode="markdown")
        
    except FileNotFoundError:
        await message.reply_text("📝 **No logs found!**")

@Client.on_message(filters.command("clearlogs") & filters.private)
async def clearlogs_command(client: Client, message: Message):
    """Clear logs"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    try:
        if os.path.exists("bot.log"):
            os.remove("bot.log")
        await message.reply_text("✅ **Logs cleared!**")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** {str(e)}")

def log_user_activity(user_id: int, action: str):
    """Log user activity"""
    bot_logger.info(f"User {user_id} - {action}")

def log_task_start(task_id: str, task_type: str, user_id: int):
    """Log task start"""
    bot_logger.info(f"Task {task_id} started - Type: {task_type} - User: {user_id}")

def log_task_complete(task_id: str, status: str):
    """Log task completion"""
    bot_logger.info(f"Task {task_id} {status}")

def log_error(error: str, context: str = ""):
    """Log error"""
    bot_logger.error(f"{context} - {error}" if context else error)
