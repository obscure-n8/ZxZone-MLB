import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.uploader import uploader
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

@Client.on_message(filters.command("mega") & filters.private)
async def mega_command(client: Client, message: Message):
    """Handle /mega command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /mega <mega_link>\n\n"
            "Download from Mega.nz",
            parse_mode="markdown"
        )
        return
    
    mega_link = message.command[1]
    
    if not mega_link.startswith('https://mega'):
        await message.reply_text("❌ **Invalid Mega link!**")
        return
    
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text(
        f"🔷 **Mega Download Started**\n\n"
        f"🔖 **Task ID:** `{task_id}`\n"
        f"📊 **Status:** Initializing...",
        parse_mode="markdown"
    )
    
    await tasks_db.add_task(task_id, user.id, 'mega', mega_link)
    
    try:
        from mega import Mega
        
        mega = Mega()
        m = mega.login()
        
        # Download file
        file_info = m.download_url(mega_link, Config.DOWNLOAD_DIR, progress_callback)
        
        if file_info:
            file_path = os.path.join(Config.DOWNLOAD_DIR, file_info)
            file_name = os.path.basename(file_path)
            
            await status_msg.edit_text("📤 **Uploading to Telegram...**")
            
            success, msg = await uploader.upload_to_telegram(
                client,
                file_path,
                message.chat.id,
                caption=f"🔷 **Mega File:** {file_name}"
            )
            
            if success:
                await status_msg.edit_text(
                    f"✅ **Mega Download Complete!**\n\n"
                    f"📁 **File:** {file_name}",
                    parse_mode="markdown"
                )
                await tasks_db.update_task_status(task_id, 'completed')
                await users_db.increment_downloads(user.id)
            else:
                await status_msg.edit_text(f"❌ **Upload failed:** {msg}")
                await tasks_db.update_task_status(task_id, 'failed')
                
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await tasks_db.update_task_status(task_id, 'failed')

def progress_callback(current, total):
    """Progress callback for mega"""
    if total > 0:
        percentage = (current / total) * 100
        print(f"Mega download: {percentage:.1f}%")
