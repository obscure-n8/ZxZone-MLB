import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.modules.smart_downloader import smart_downloader
from bot.modules.notification import notification_system
from bot.modules.uploader import uploader
from bot.database.users import users_db
from bot.database.tasks import tasks_db

@Client.on_message(filters.command("leech") & filters.private)
async def leech_enhanced_command(client: Client, message: Message):
    """Enhanced leech with auto detection and notification"""
    user = message.from_user
    
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /leech <url>\n\n"
            "Supported:\n"
            "• Direct links\n"
            "• Icc.Tv videos\n"
            "• Viking files\n"
            "• M3U8 streams\n"
            "• Mega, Gofile, Pixeldrain\n"
            "• Google Drive\n"
            "• Torrent/Magnet",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    task_id = Utils.generate_task_id()
    
    # Send processing notification
    await notification_system.send_processing_message(
        client, user.id, "Leech", 1
    )
    
    status_msg = await message.reply_text(
        f"📥 **Leech Started**\n\n"
        f"🔖 Task ID: `{task_id}`\n"
        f"🔗 URL: {url[:50]}...\n"
        f"⏳ Downloading..."
    )
    
    await tasks_db.add_task(task_id, user.id, 'leech', url)
    
    try:
        # Smart download
        file_path = os.path.join(Config.DOWNLOAD_DIR, f"leech_{task_id}")
        
        result = await smart_downloader.smart_download(url, file_path)
        
        if result.get('special'):
            # Handle special downloaders
            if result['special'] == 'mega':
                await status_msg.edit_text("🔷 **Mega download...**")
                from bot.plugins.mega import mega_command
                await mega_command(client, message)
                return
            elif result['special'] == 'gofile':
                await status_msg.edit_text("📁 **Gofile download...**")
                from bot.plugins.gofile import gofile_command
                await gofile_command(client, message)
                return
            elif result['special'] == 'gdrive':
                await status_msg.edit_text("🔵 **Google Drive download...**")
                return
                
        if not result.get('success'):
            await status_msg.edit_text(f"❌ **Download failed:** {result.get('error', 'Unknown')}")
            await notification_system.send_error_message(client, user.id, result.get('error', 'Download failed'))
            return
            
        file_path = result.get('file', file_path)
        file_size = os.path.getsize(file_path)
        
        # Upload
        await status_msg.edit_text("📤 **Uploading...**")
        
        success, msg = await uploader.upload_to_telegram(
            client, file_path, message.chat.id,
            caption=f"📁 {os.path.basename(file_path)}",
            user_id=user.id
        )
        
        if success:
            await status_msg.edit_text("✅ **Leech Complete!**")
            await tasks_db.update_task_status(task_id, 'completed')
            await users_db.increment_downloads(user.id)
            
            # Send completion notification
            await notification_system.send_completion_message(
                client, user.id, user.username,
                files_sent=1, files_failed=0, task_type="Leech"
            )
        else:
            await status_msg.edit_text(f"❌ **Upload failed:** {msg}")
            await notification_system.send_error_message(client, user.id, msg)
            
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await notification_system.send_error_message(client, user.id, str(e))
