from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from bot.config import Config
from bot.database.users import users_db

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    
    # Add user to database
    await users_db.add_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or ""
    )
    
    # Create buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Repo", url=Config.REPO_LINK),
            InlineKeyboardButton("📢 Channel", url=Config.UPDATE_CHANNEL)
        ],
        [
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="status"),
            InlineKeyboardButton("👤 My Stats", callback_data="my_stats")
        ]
    ])
    
    # Send welcome message
    welcome_text = f"""
**Zonexus M/L Bot** 🔥

**Powered By Zonexus Hub** ❞

👋 Welcome **{user.first_name}**!

I'm **{Config.BOT_USERNAME}** - Powerful Mirror/Leech Bot

**✨ Features:**
• 🔥 Direct Link Download
• 🧲 Torrent & Magnet Support
• 📹 YouTube/YT-DLP
• ☁️ Google Drive/Mega
• 🔄 Rclone Support
• 📦 File Operations

**📝 Commands:**
• /mirror - Mirror to Cloud
• /leech - Leech to Telegram
• /ytdl - YouTube Download
• /settings - Bot Settings
• /status - Check Status
"""
    
    await message.reply_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="markdown"
    )

@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client: Client, callback_query):
    """Handle help callback"""
    help_text = """
📚 **Help Menu**

🔹 **Mirror Commands:**
• /mirror <url> - Mirror to cloud
• /mirror - Reply to file
• /cancel - Cancel task

🔹 **Leech Commands:**
• /leech <url> - Leech to Telegram
• /ytdl <url> - YouTube leech
• /cancel - Cancel task

🔹 **Utility:**
• /status - Bot status
• /speedtest - Check speed
• /stats - Your statistics
• /settings - Bot settings

💡 **Tips:**
- Send direct links
- Support magnet links
- Max file size: 2GB
"""
    await callback_query.message.edit_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="start")]
        ]),
        parse_mode="markdown"
    )

@Client.on_callback_query(filters.regex("^start$"))
async def start_callback(client: Client, callback_query):
    """Handle start callback"""
    await start_command(client, callback_query.message)
