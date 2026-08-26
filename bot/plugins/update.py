import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config

@Client.on_message(filters.command("update") & filters.private)
async def update_command(client: Client, message: Message):
    """Update bot from upstream (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if not Config.UPSTREAM_REPO:
        await message.reply_text("❌ **Upstream repo not configured!**")
        return
    
    status_msg = await message.reply_text("🔄 **Checking for updates...**")
    
    try:
        # Fetch updates
        result = subprocess.run(
            ["git", "fetch", "upstream"],
            capture_output=True,
            text=True,
            cwd=Config.BASE_DIR
        )
        
        if result.returncode != 0:
            # Add upstream if not exists
            subprocess.run(
                ["git", "remote", "add", "upstream", Config.UPSTREAM_REPO],
                capture_output=True,
                cwd=Config.BASE_DIR
            )
            subprocess.run(
                ["git", "fetch", "upstream"],
                capture_output=True,
                cwd=Config.BASE_DIR
            )
            
        # Check for updates
        result = subprocess.run(
            ["git", "diff", "HEAD", f"upstream/{Config.UPSTREAM_BRANCH}", "--stat"],
            capture_output=True,
            text=True,
            cwd=Config.BASE_DIR
        )
        
        if result.stdout.strip():
            # Updates available
            update_text = "📦 **Updates Available!**\n\n"
            update_text += "```\n" + result.stdout + "\n```"
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Update Now", callback_data="update_now"),
                    InlineKeyboardButton("❌ Cancel", callback_data="update_cancel")
                ]
            ])
            
            await status_msg.edit_text(
                update_text,
                reply_markup=keyboard,
                parse_mode="markdown"
            )
        else:
            await status_msg.edit_text("✅ **Already up to date!**")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Update check failed:** {str(e)}")

@Client.on_callback_query(filters.regex("^update_now$"))
async def update_now_callback(client: Client, callback_query):
    """Execute update"""
    user_id = callback_query.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    await callback_query.message.edit_text("🔄 **Updating...**")
    
    try:
        # Pull updates
        result = subprocess.run(
            ["git", "pull", "upstream", Config.UPSTREAM_BRANCH],
            capture_output=True,
            text=True,
            cwd=Config.BASE_DIR
        )
        
        if result.returncode == 0:
            await callback_query.message.edit_text(
                "✅ **Update successful!**\n\n"
                "🔄 Restarting bot...",
                parse_mode="markdown"
            )
            
            # Restart bot
            os.execv(sys.executable, [sys.executable, "-m", "bot"])
        else:
            await callback_query.message.edit_text(
                f"❌ **Update failed:**\n\n"
                f"```\n{result.stderr}\n```",
                parse_mode="markdown"
            )
            
    except Exception as e:
        await callback_query.message.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_callback_query(filters.regex("^update_cancel$"))
async def update_cancel_callback(client: Client, callback_query):
    """Cancel update"""
    await callback_query.message.edit_text("❌ **Update cancelled!**")
    await callback_query.answer()

@Client.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    """Restart bot (admin only)"""
    import sys
    
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    await message.reply_text("🔄 **Restarting bot...**")
    
    # Restart
    os.execv(sys.executable, [sys.executable, "-m", "bot"])

@Client.on_message(filters.command("logs") & filters.private)
async def logs_command(client: Client, message: Message):
    """View logs (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    try:
        with open("bot.log", "r") as f:
            lines = f.readlines()[-100:]  # Last 100 lines
            
        log_text = "📝 **Recent Logs:**\n\n```\n"
        log_text += "".join(lines[-30:])  # Last 30 lines for readability
        log_text += "\n```"
        
        await message.reply_text(log_text, parse_mode="markdown")
        
    except FileNotFoundError:
        await message.reply_text("📝 **No logs found!**")
