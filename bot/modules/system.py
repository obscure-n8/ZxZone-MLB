import os
import sys
import time
import psutil
import platform
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.permissions import permission_system

@Client.on_message(filters.command("sysinfo") & filters.private)
async def sysinfo_command(client: Client, message: Message):
    """System information command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    # Get system info
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    uptime = time.time() - psutil.boot_time()
    
    info_text = f"""
🖥 **System Information**

💻 **OS:** {platform.system()} {platform.release()}
🐍 **Python:** {sys.version.split()[0]}

⚡ **CPU:**
• Usage: {cpu_percent}%
• Cores: {psutil.cpu_count()}

💾 **Memory:**
• Total: {memory.total / (1024**3):.1f} GB
• Used: {memory.used / (1024**3):.1f} GB
• Percent: {memory.percent}%

💿 **Disk:**
• Total: {disk.total / (1024**3):.1f} GB
• Free: {disk.free / (1024**3):.1f} GB

⏰ **Uptime:** {int(uptime // 3600)}h {int((uptime % 3600) // 60)}m

📱 **Bot:** @{Config.BOT_USERNAME}
"""
    
    await message.reply_text(info_text, parse_mode="markdown")

@Client.on_message(filters.command("ping") & filters.private)
async def ping_command(client: Client, message: Message):
    """Ping command"""
    start_time = time.time()
    
    msg = await message.reply_text("🏓 **Pinging...**")
    
    end_time = time.time()
    ping_time = (end_time - start_time) * 1000
    
    await msg.edit_text(
        f"🏓 **Pong!**\n\n"
        f"⚡ Response Time: {ping_time:.2f}ms\n"
        f"📱 Bot: @{Config.BOT_USERNAME}\n"
        f"✅ Status: Online",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("uptime") & filters.private)
async def uptime_command(client: Client, message: Message):
    """Bot uptime command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    uptime = time.time() - psutil.boot_time()
    
    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    
    await message.reply_text(
        f"⏰ **Bot Uptime:**\n\n"
        f"📅 {days} days\n"
        f"⏰ {hours} hours\n"
        f"⏱ {minutes} minutes",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("clearcache") & filters.private)
async def clearcache_command(client: Client, message: Message):
    """Clear cache command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    status_msg = await message.reply_text("🧹 **Clearing cache...**")
    
    try:
        # Clear temp files
        temp_dir = os.path.join(Config.DOWNLOAD_DIR, "temp")
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
        
        # Clear Python cache
        for root, dirs, files in os.walk(Config.BASE_DIR):
            for dir_name in dirs:
                if dir_name == '__pycache__':
                    shutil.rmtree(os.path.join(root, dir_name))
        
        await status_msg.edit_text("✅ **Cache cleared successfully!**")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
