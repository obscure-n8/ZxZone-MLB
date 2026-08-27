from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.permissions import permission_system

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Help command - shows all available commands"""
    user = message.from_user
    
    # Check user access level
    is_admin = await permission_system.is_admin(user.id)
    is_sudo = await permission_system.is_sudo(user.id)
    is_owner = await permission_system.is_owner(user.id)
    
    # Build help text based on user level
    help_text = f"""
📚 **ZxZone-MLB Help Menu**

👤 **User:** {user.first_name}

**📥 Download Commands:**
• /leech <url> - Leech to Telegram
• /mirror <url> - Mirror to cloud
• /qbleech <url> - Queue batch leech
• /qbmirror <url> - Queue batch mirror
• /ytdlleech <url> - YouTube leech
• /yt-dl <url> - YouTube download
• /jdmirror <url> - JD mirror
• /jdleech <url> - JD leech
• /rclone <cmd> - Rclone operations

**⚙️ User Commands:**
• /usetting - User settings
• /thumb - Set thumbnail
• /help - This menu
• /start - Start bot

**📊 Status Commands:**
• /stats - Your statistics
• /mysession - Check session status
"""
    
    # Add admin commands if user is admin
    if is_admin:
        help_text += """
**👑 Admin Commands:**
• /bsetting - Bot settings
• /restart - Restart bot
• /cancelalltask - Cancel all tasks
• /admin - Admin panel
• /logs - View logs
"""
    
    # Add sudo commands if user is sudo
    if is_sudo:
        help_text += """
**🔑 Sudo Commands:**
• /addsudo <id> - Add sudo user
• /removesudo <id> - Remove sudo
• /sudolist - List sudo users
• /broadcast - Broadcast message
"""
    
    # Add owner commands if user is owner
    if is_owner:
        help_text += """
**👑 Owner Commands:**
• /owner - Owner panel
• /addadmin <id> - Add admin
• /removeadmin <id> - Remove admin
• /backup - Create backup
• /update - Update bot
"""
    
    help_text += f"""
**📢 Channel:** {Config.UPDATE_CHANNEL}
**📦 Repo:** {Config.REPO_LINK}

**Powered By Zonexus Hub** ❞
"""
    
    # Create buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Repo", url=Config.REPO_LINK),
            InlineKeyboardButton("📢 Channel", url=Config.UPDATE_CHANNEL)
        ],
        [
            InlineKeyboardButton("🔙 Back to Start", callback_data="start")
        ]
    ])
    
    await message.reply_text(help_text, reply_markup=keyboard, parse_mode="markdown")
