import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.database.settings import settings_db

@Client.on_message(filters.command("aria2") & filters.private)
async def aria2_settings_command(client: Client, message: Message):
    """Aria2 settings panel"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    settings = await settings_db.get_settings()
    
    aria2_config = f"""
🔧 **Aria2 Configuration**

**Basic Settings:**
• Status: {'✅ Running' if settings.get('aria2_enabled', True) else '❌ Stopped'}
• Host: {Config.ARIA2_HOST}
• Port: {Config.ARIA2_PORT}

**Download Settings:**
• Max Connections: {settings.get('aria2_connections', 10)}
• Split: {settings.get('aria2_split', 10)}
• Min Split Size: {settings.get('aria2_min_split', '20M')}

**Speed Limits:**
• Max Download: {settings.get('aria2_max_download', '0 (Unlimited)')}
• Max Upload: {settings.get('aria2_max_upload', '0 (Unlimited)')}

**Advanced:**
• File Allocation: {settings.get('aria2_allocation', 'prealloc')}
• Check Certificate: {'✅' if settings.get('aria2_check_cert', True) else '❌'}
• Continue: {'✅' if settings.get('aria2_continue', True) else '❌'}

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Start/Stop", callback_data="aria2_toggle"),
            InlineKeyboardButton("Restart", callback_data="aria2_restart")
        ],
        [
            InlineKeyboardButton("Connections", callback_data="aria2_connections"),
            InlineKeyboardButton("Split", callback_data="aria2_split")
        ],
        [
            InlineKeyboardButton("Max Download", callback_data="aria2_max_dl"),
            InlineKeyboardButton("Max Upload", callback_data="aria2_max_ul")
        ]
    ])
    
    await message.reply_text(aria2_config, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^aria2_"))
async def aria2_callback(client: Client, callback_query):
    """Handle aria2 settings callbacks"""
    user_id = callback_query.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "toggle":
        current = await settings_db.get_setting('aria2_enabled', True)
        await settings_db.update_setting('aria2_enabled', not current)
        await callback_query.answer(f"Aria2: {'Stopped' if current else 'Started'}")
        
    elif action == "restart":
        # Restart aria2
        import subprocess
        subprocess.run(["pkill", "aria2c"])
        await asyncio.sleep(2)
        subprocess.Popen([
            "aria2c",
            "--enable-rpc",
            f"--rpc-listen-port={Config.ARIA2_PORT}",
            f"--rpc-secret={Config.ARIA2_SECRET}",
            "--max-connection-per-server=10",
            "--split=10",
            "--daemon=true"
        ])
        await callback_query.answer("Aria2 restarted!")
        
    elif action == "connections":
        current = await settings_db.get_setting('aria2_connections', 10)
        new_value = current * 2 if current < 64 else 4
        await settings_db.update_setting('aria2_connections', new_value)
        await callback_query.answer(f"Connections: {new_value}")
        
    elif action == "split":
        current = await settings_db.get_setting('aria2_split', 10)
        new_value = current * 2 if current < 64 else 4
        await settings_db.update_setting('aria2_split', new_value)
        await callback_query.answer(f"Split: {new_value}")
        
    elif action == "max_dl":
        current = await settings_db.get_setting('aria2_max_download', 0)
        new_value = '10M' if current == 0 else 0
        await settings_db.update_setting('aria2_max_download', new_value)
        await callback_query.answer(f"Max Download: {new_value}")
        
    elif action == "max_ul":
        current = await settings_db.get_setting('aria2_max_upload', 0)
        new_value = '5M' if current == 0 else 0
        await settings_db.update_setting('aria2_max_upload', new_value)
        await callback_query.answer(f"Max Upload: {new_value}")
    
    # Update settings display
    await aria2_settings_command(client, callback_query.message)
