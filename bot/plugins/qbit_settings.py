import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.database.settings import settings_db

@Client.on_message(filters.command("qbit") & filters.private)
async def qbit_settings_command(client: Client, message: Message):
    """Qbittorrent settings panel"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    settings = await settings_db.get_settings()
    
    qbit_config = f"""
🔧 **Qbittorrent Configuration**

**Basic Settings:**
• Status: {'✅ Enabled' if settings.get('qbit_enabled', False) else '❌ Disabled'}
• Web UI: {Config.BASE_URL or 'Not configured'}

**Connection Settings:**
• Max Connections: {settings.get('qbit_connections', 100)}
• Max Uploads: {settings.get('qbit_max_uploads', 4)}
• Max Downloads: {settings.get('qbit_max_downloads', 3)}

**Speed Limits:**
• Download: {settings.get('qbit_download_limit', 'Unlimited')}
• Upload: {settings.get('qbit_upload_limit', 'Unlimited')}

**Torrent Settings:**
• Auto Delete: {'✅' if settings.get('qbit_auto_delete', False) else '❌'}
• Seed Time: {settings.get('qbit_seed_time', '24h')}
• Seed Ratio: {settings.get('qbit_seed_ratio', '1.0')}

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Enable/Disable", callback_data="qbit_toggle"),
            InlineKeyboardButton("Restart", callback_data="qbit_restart")
        ],
        [
            InlineKeyboardButton("Connections", callback_data="qbit_connections"),
            InlineKeyboardButton("Speed Limits", callback_data="qbit_speed")
        ],
        [
            InlineKeyboardButton("Seed Settings", callback_data="qbit_seed"),
            InlineKeyboardButton("Auto Delete", callback_data="qbit_autodel")
        ]
    ])
    
    await message.reply_text(qbit_config, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^qbit_"))
async def qbit_callback(client: Client, callback_query):
    """Handle qbittorrent settings callbacks"""
    user_id = callback_query.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "toggle":
        current = await settings_db.get_setting('qbit_enabled', False)
        await settings_db.update_setting('qbit_enabled', not current)
        await callback_query.answer(f"Qbittorrent: {'Disabled' if current else 'Enabled'}")
        
    elif action == "restart":
        # Restart qbittorrent
        import subprocess
        subprocess.run(["pkill", "qbittorrent-nox"])
        await asyncio.sleep(2)
        subprocess.Popen(["qbittorrent-nox", "--daemon"])
        await callback_query.answer("Qbittorrent restarted!")
        
    elif action == "connections":
        current = await settings_db.get_setting('qbit_connections', 100)
        new_value = current * 2 if current < 1000 else 50
        await settings_db.update_setting('qbit_connections', new_value)
        await callback_query.answer(f"Max Connections: {new_value}")
        
    elif action == "speed":
        current = await settings_db.get_setting('qbit_download_limit', 0)
        new_value = '10MiB' if current == 0 else 0
        await settings_db.update_setting('qbit_download_limit', new_value)
        await settings_db.update_setting('qbit_upload_limit', new_value)
        await callback_query.answer(f"Speed Limit: {new_value}")
        
    elif action == "seed":
        current = await settings_db.get_setting('qbit_seed_ratio', 1.0)
        new_value = 2.0 if current == 1.0 else 1.0
        await settings_db.update_setting('qbit_seed_ratio', new_value)
        await callback_query.answer(f"Seed Ratio: {new_value}")
        
    elif action == "autodel":
        current = await settings_db.get_setting('qbit_auto_delete', False)
        await settings_db.update_setting('qbit_auto_delete', not current)
        await callback_query.answer(f"Auto Delete: {'OFF' if current else 'ON'}")
    
    # Update display
    await qbit_settings_command(client, callback_query.message)
