from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.permissions import permission_system
from bot.database.settings import settings_db

@Client.on_message(filters.command("premium") & filters.private)
async def premium_hosts_command(client: Client, message: Message):
    """Premium host manager"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    settings = await settings_db.get_settings()
    
    premium_text = f"""
💎 **Premium Host Manager**

**Supported Premium Hosts:**

1. **Mega** - {Config.MEGA_EMAIL or 'Not configured'}
2. **FileLion** - {'✅' if Config.FILELION_API else '❌ Not configured'}
3. **StreamWish** - {'✅' if Config.STREAMWISH_API else '❌ Not configured'}
4. **AllDebrid** - {'✅' if Config.ALLDEBRID_API_KEY else '❌ Not configured'}

**JDownloader Premium:**
• Email: {Config.JD_EMAIL or 'Not set'}
• Status: {'✅' if settings.get('jd_premium', False) else '❌'}

**Premium Features:**
• High Speed Download
• No Waiting Time
• Parallel Downloads
• Resume Support
• Direct Links

Select option:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔷 Mega", callback_data="prem_mega"),
            InlineKeyboardButton("🦁 FileLion", callback_data="prem_filelion")
        ],
        [
            InlineKeyboardButton("📺 StreamWish", callback_data="prem_streamwish"),
            InlineKeyboardButton("⚡ AllDebrid", callback_data="prem_alldebrid")
        ],
        [
            InlineKeyboardButton("🔧 JDownloader", callback_data="prem_jd"),
            InlineKeyboardButton("📊 Status", callback_data="prem_status")
        ]
    ])
    
    await message.reply_text(premium_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^prem_"))
async def premium_callback(client: Client, callback_query):
    """Handle premium host callbacks"""
    user_id = callback_query.from_user.id
    
    if not await permission_system.is_admin(user_id):
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "mega":
        await callback_query.message.edit_text(
            "🔷 **Mega Premium Setup:**\n\n"
            "Send your Mega credentials:\n"
            "/setmega email password",
            parse_mode="markdown"
        )
        
    elif action == "filelion":
        await callback_query.message.edit_text(
            "🦁 **FileLion Premium:**\n\n"
            "Send your FileLion API key:\n"
            "/setfilelion api_key",
            parse_mode="markdown"
        )
        
    elif action == "streamwish":
        await callback_query.message.edit_text(
            "📺 **StreamWish Premium:**\n\n"
            "Send your StreamWish API key:\n"
            "/setstreamwish api_key",
            parse_mode="markdown"
        )
        
    elif action == "alldebrid":
        await callback_query.message.edit_text(
            "⚡ **AllDebrid Premium:**\n\n"
            "Send your AllDebrid API key:\n"
            "/setalldebrid api_key",
            parse_mode="markdown"
        )
        
    elif action == "jd":
        await callback_query.message.edit_text(
            "🔧 **JDownloader Premium:**\n\n"
            "Send your JD credentials:\n"
            "/setjd email password",
            parse_mode="markdown"
        )
        
    elif action == "status":
        status_text = """
💎 **Premium Host Status**

"""
        if Config.MEGA_EMAIL:
            status_text += "✅ Mega: Configured\n"
        else:
            status_text += "❌ Mega: Not configured\n"
            
        if Config.FILELION_API:
            status_text += "✅ FileLion: Configured\n"
        else:
            status_text += "❌ FileLion: Not configured\n"
            
        if Config.STREAMWISH_API:
            status_text += "✅ StreamWish: Configured\n"
        else:
            status_text += "❌ StreamWish: Not configured\n"
            
        if Config.ALLDEBRID_API_KEY:
            status_text += "✅ AllDebrid: Configured\n"
        else:
            status_text += "❌ AllDebrid: Not configured\n"
            
        await callback_query.message.edit_text(status_text, parse_mode="markdown")
    
    await callback_query.answer()

@Client.on_message(filters.command("setmega") & filters.private)
async def set_mega_command(client: Client, message: Message):
    """Set Mega credentials"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 3:
        await message.reply_text("📝 **Usage:** /setmega email password")
        return
    
    email = message.command[1]
    password = message.command[2]
    
    # Update config
    Config.MEGA_EMAIL = email
    Config.MEGA_PASSWORD = password
    
    await message.reply_text("✅ **Mega credentials set!**")

@Client.on_message(filters.command("setjd") & filters.private)
async def set_jd_command(client: Client, message: Message):
    """Set JDownloader credentials"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 3:
        await message.reply_text("📝 **Usage:** /setjd email password")
        return
    
    email = message.command[1]
    password = message.command[2]
    
    Config.JD_EMAIL = email
    Config.JD_PASS = password
    
    await message.reply_text("✅ **JDownloader credentials set!**")
