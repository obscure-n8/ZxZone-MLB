import os
import sys
import time
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.permissions import permission_system
from bot.database.settings import settings_db

class RestartManager:
    def __init__(self):
        self.restarting = False
        
    async def restart_bot(self, client: Client, message: Message):
        """Restart bot gracefully"""
        user = message.from_user
        
        if not await permission_system.is_admin(user.id):
            await message.reply_text("❌ **You are not authorized!**")
            return
        
        if self.restarting:
            await message.reply_text("⚠️ **Restart already in progress!**")
            return
        
        self.restarting = True
        
        status_msg = await message.reply_text(
            "🔄 **Restarting bot...**\n\n"
            "⏳ Please wait..."
        )
        
        try:
            # Save state before restart
            await settings_db.update_setting('last_restart', time.time())
            await settings_db.update_setting('restart_by', user.id)
            
            # Update status
            await status_msg.edit_text(
                "🔄 **Restarting bot...**\n\n"
                "✅ State saved\n"
                "⏳ Shutting down..."
            )
            
            await asyncio.sleep(2)
            
            # Method 1: os.execv (Linux/VPS)
            if os.name == 'posix':
                await status_msg.edit_text(
                    "🔄 **Restarting bot...**\n\n"
                    "✅ State saved\n"
                    "🔄 Executing restart..."
                )
                
                # Restart with os.execv
                os.execv(sys.executable, [sys.executable, "-m", "bot"])
                
            # Method 2: subprocess (Windows)
            elif os.name == 'nt':
                await status_msg.edit_text(
                    "🔄 **Restarting bot...**\n\n"
                    "✅ State saved\n"
                    "🔄 Starting new process..."
                )
                
                # Start new process
                subprocess.Popen(
                    [sys.executable, "-m", "bot"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                
                # Exit current process
                os._exit(0)
                
            # Method 3: Heroku/Docker
            else:
                await status_msg.edit_text(
                    "🔄 **Restarting bot...**\n\n"
                    "✅ State saved\n"
                    "🔄 Sending SIGTERM..."
                )
                
                # Send SIGTERM to self
                os.kill(os.getpid(), 15)
                
        except Exception as e:
            self.restarting = False
            await status_msg.edit_text(f"❌ **Restart failed:** {str(e)}")
    
    async def shutdown_bot(self, client: Client, message: Message):
        """Shutdown bot gracefully"""
        user = message.from_user
        
        if not await permission_system.is_admin(user.id):
            await message.reply_text("❌ **You are not authorized!**")
            return
        
        status_msg = await message.reply_text("🛑 **Shutting down...**")
        
        try:
            # Save state
            await settings_db.update_setting('last_shutdown', time.time())
            await settings_db.update_setting('shutdown_by', user.id)
            
            await status_msg.edit_text(
                "🛑 **Shutting down...**\n\n"
                "✅ State saved\n"
                "🔄 Cleaning up..."
            )
            
            await asyncio.sleep(2)
            
            # Stop bot
            await client.stop()
            
            # Exit
            os._exit(0)
            
        except Exception as e:
            await status_msg.edit_text(f"❌ **Shutdown failed:** {str(e)}")

# Create instance
restart_manager = RestartManager()

@Client.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    """Restart bot command"""
    await restart_manager.restart_bot(client, message)

@Client.on_message(filters.command("shutdown") & filters.private)
async def shutdown_command(client: Client, message: Message):
    """Shutdown bot command"""
    await restart_manager.shutdown_bot(client, message)

@Client.on_message(filters.command("reboot") & filters.private)
async def reboot_command(client: Client, message: Message):
    """Reboot bot command (same as restart)"""
    await restart_manager.restart_bot(client, message)
