import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.rclone import rclone_manager
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

@Client.on_message(filters.command("gdrive") & filters.private)
async def gdrive_command(client: Client, message: Message):
    """Handle /gdrive command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check rclone
    if not await rclone_manager.check_remote():
        await message.reply_text("❌ **Rclone not configured!**")
        return
    
    # Check command arguments
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/gdrive list - List files\n"
            "/gdrive upload - Upload file (reply to file)\n"
            "/gdrive link <path> - Get link",
            parse_mode="markdown"
        )
        return
    
    action = message.command[1].lower()
    
    if action == "list":
        files = await rclone_manager.list_files()
        if files:
            file_list = "\n".join([f"• {f}" for f in files[:20]])
            await message.reply_text(f"📁 **Files:**\n\n{file_list}")
        else:
            await message.reply_text("📁 **No files found!**")
            
    elif action == "link":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /gdrive link <path>")
            return
        path = message.command[2]
        link = await rclone_manager.get_file_link(path)
        if link:
            await message.reply_text(f"🔗 **Link:** {link}")
        else:
            await message.reply_text("❌ **Failed to get link!**")

@Client.on_message(filters.command("upload") & filters.private)
async def upload_command(client: Client, message: Message):
    """Handle /upload command for cloud upload"""
    user = message.from_user
    
    if not message.reply_to_message:
        await message.reply_text("📝 **Usage:** Reply to a file with /upload")
        return
    
    replied = message.reply_to_message
    
    if not replied.document and not replied.video and not replied.audio:
        await message.reply_text("❌ **Reply to a file!**")
        return
    
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text(
        f"☁️ **Cloud Upload Started**\n\n"
        f"🔖 **Task ID:** `{task_id}`\n"
        f"📊 **Status:** Downloading...",
        parse_mode="markdown"
    )
    
    try:
        # Download file
        file_path = await replied.download()
        file_name = os.path.basename(file_path)
        
        await status_msg.edit_text(
            f"☁️ **Cloud Upload Started**\n\n"
            f"🔖 **Task ID:** `{task_id}`\n"
            f"📁 **File:** {file_name}\n"
            f"📊 **Status:** Uploading to cloud...",
            parse_mode="markdown"
        )
        
        # Upload to cloud
        success, msg = await rclone_manager.upload_file(
            file_path,
            progress_callback=lambda p: update_cloud_progress(status_msg, task_id, p, user, file_name)
        )
        
        if success:
            await status_msg.edit_text(
                f"✅ **Upload Complete!**\n\n"
                f"📁 **File:** {file_name}\n"
                f"☁️ **Destination:** {Config.RCLONE_REMOTE}\n"
                f"🔖 **Task ID:** `{task_id}`",
                parse_mode="markdown"
            )
            await users_db.increment_uploads(user.id)
        else:
            await status_msg.edit_text(f"❌ **Upload failed:** {msg}")
            
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

async def update_cloud_progress(status_msg, task_id, percentage, user, file_name):
    """Update cloud upload progress"""
    system = progress_helper.get_system_stats()
    progress_bar = progress_helper.get_progress_bar(percentage)
    
    progress_text = f"""
**Zonexus M/L Bot 1**
┌ **{Config.BOT_USERNAME}**
└ `/leech1 {task_id}`

▍ **Powered By Zonexus Hub** ❞

1. `{file_name}`
┌ **Task By {user.first_name}**
│ {progress_bar} {percentage:.1f}%
│ **Status** : Cloud Upload
│ **Engine** : Rclone | **Mode** : `#Cloud`
> **Stop** : `/c_{task_id}`

⬢ **BOT STATS**
┌ **CPU** : {system['cpu']}% | **RAM** : {system['ram']}%
└ **FREE** : {system['free_disk']}
"""
    
    try:
        await status_msg.edit_text(progress_text, parse_mode="markdown")
    except:
        pass
