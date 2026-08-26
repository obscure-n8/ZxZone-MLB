import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.database.settings import settings_db

class UploadPaths:
    def __init__(self):
        self.paths = {
            'rclone': 'Rclone Cloud',
            'gdrive': 'Google Drive',
            'telegram': 'Telegram',
            'dump': 'Dump Channel'
        }
    
    async def get_upload_paths(self) -> dict:
        """Get all upload paths"""
        settings = await settings_db.get_settings()
        return settings.get('upload_paths', {})
    
    async def set_upload_path(self, path_name: str, path_value: str):
        """Set upload path"""
        settings = await settings_db.get_settings()
        
        if 'upload_paths' not in settings:
            settings['upload_paths'] = {}
            
        settings['upload_paths'][path_name] = path_value
        await settings_db.update_settings(settings)
        
    async def get_user_upload_path(self, user_id: int) -> str:
        """Get user's default upload path"""
        from bot.database.users import users_db
        user_settings = await users_db.get_user_settings(user_id)
        return user_settings.get('upload_path', 'telegram')

# Create instance
upload_paths = UploadPaths()

@Client.on_message(filters.command("uploadpath") & filters.private)
async def upload_path_command(client: Client, message: Message):
    """Setup upload paths"""
    user = message.from_user
    
    # Check admin
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **Admin only!**")
        return
    
    paths = await upload_paths.get_upload_paths()
    
    text = f"""
📤 **Upload Paths Setup**

Current Paths:

"""
    for path_name, path_value in paths.items():
        text += f"• {path_name}: {path_value}\n"
    
    text += """
**How to set:**

/rclonepath <remote:folder> - Set Rclone path
/gdrivepath <folder_id> - Set Google Drive path
/dumppath <channel_id> - Set Dump channel
/telegrampath - Set Telegram as default

**Example:**
/rclonepath gdrive:Movies
/gdrivepath 1abc123xyz
/dumppath -1001234567890
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 Rclone", callback_data="upath_rclone"),
            InlineKeyboardButton("🔵 GDrive", callback_data="upath_gdrive")
        ],
        [
            InlineKeyboardButton("📱 Telegram", callback_data="upath_telegram"),
            InlineKeyboardButton("📦 Dump", callback_data="upath_dump")
        ]
    ])
    
    await message.reply_text(text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_message(filters.command("rclonepath") & filters.private)
async def set_rclone_path(client: Client, message: Message):
    """Set Rclone upload path"""
    user = message.from_user
    
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **Admin only!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /rclonepath <remote:folder>\n\n"
            "Example:\n"
            "/rclonepath gdrive:Movies\n"
            "/rclonepath mega:Videos",
            parse_mode="markdown"
        )
        return
    
    path = message.command[1]
    await upload_paths.set_upload_path('rclone', path)
    
    await message.reply_text(f"✅ **Rclone path set:** {path}")

@Client.on_message(filters.command("gdrivepath") & filters.private)
async def set_gdrive_path(client: Client, message: Message):
    """Set Google Drive upload path"""
    user = message.from_user
    
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **Admin only!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /gdrivepath <folder_id>\n\n"
            "Example:\n"
            "/gdrivepath 1abc123xyz456",
            parse_mode="markdown"
        )
        return
    
    path = message.command[1]
    await upload_paths.set_upload_path('gdrive', path)
    
    await message.reply_text(f"✅ **GDrive path set:** {path}")

@Client.on_message(filters.command("dumppath") & filters.private)
async def set_dump_path(client: Client, message: Message):
    """Set Dump channel"""
    user = message.from_user
    
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **Admin only!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /dumppath <channel_id>\n\n"
            "Example:\n"
            "/dumppath -1001234567890",
            parse_mode="markdown"
        )
        return
    
    path = message.command[1]
    await upload_paths.set_upload_path('dump', path)
    Config.LEECH_DUMP_CHAT = path
    
    await message.reply_text(f"✅ **Dump channel set:** {path}")

@Client.on_message(filters.command("telegrampath") & filters.private)
async def set_telegram_path(client: Client, message: Message):
    """Set Telegram as default upload path"""
    user = message.from_user
    
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **Admin only!**")
        return
    
    await upload_paths.set_upload_path('telegram', 'default')
    await message.reply_text("✅ **Telegram set as default upload path!**")

@Client.on_callback_query(filters.regex("^upath_"))
async def upload_path_callback(client: Client, callback_query):
    """Handle upload path callbacks"""
    data = callback_query.data
    path_type = data.split("_")[1]
    
    instructions = {
        'rclone': "Send /rclonepath <remote:folder>",
        'gdrive': "Send /gdrivepath <folder_id>",
        'telegram': "Send /telegrampath to set default",
        'dump': "Send /dumppath <channel_id>"
    }
    
    await callback_query.answer(instructions.get(path_type, ""), show_alert=True)
