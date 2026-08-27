import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.modules.smart_downloader import smart_downloader
from bot.modules.notification import notification_system
from bot.modules.uploader import uploader
from bot.modules.ai_enhanced import ai_enhanced
from bot.modules.speed_optimizer import speed_optimizer
from bot.modules.auto_organizer_enhanced import auto_organizer_enhanced
from bot.database.users import users_db
from bot.database.tasks import tasks_db

@Client.on_message(filters.command("leech") & filters.private)
async def leech_final_command(client: Client, message: Message):
    """Final enhanced leech command"""
    user = message.from_user
    
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /leech <url> [flags]\n\n"
            "Flags:\n"
            "-vt : Video tools\n"
            "-dump : Upload to dump\n"
            "-fast : Fast mode\n\n"
            "Supported:\n"
            "• Direct, M3U8, Icc.Tv, Viking\n"
            "• Mega, Gofile, Pixeldrain\n"
            "• Google Drive, Torrent/Magnet",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    flags = message.command[2:] if len(message.command) > 2 else []
    
    task_id = Utils.generate_task_id()
    start_time = time.time()
    
    # Send processing notification
    await notification_system.send_processing_message(client, user.id, "Leech", 1)
    
    status_msg = await message.reply_text(
        f"📥 **Leech Started**\n\n"
        f"🔖 Task ID: `{task_id}`\n"
        f"👤 User: {user.first_name}\n"
        f"🔗 URL: {url[:50]}...\n"
        f"⏳ Downloading..."
    )
    
    await tasks_db.add_task(task_id, user.id, 'leech', url)
    
    try:
        # Optimize speed
        speed_settings = await speed_optimizer.optimize_download_speed()
        
        # Smart download
        file_path = os.path.join(Config.DOWNLOAD_DIR, f"leech_{task_id}")
        
        result = await smart_downloader.smart_download(url, file_path)
        
        if not result.get('success'):
            error = result.get('error', 'Download failed')
            await status_msg.edit_text(f"❌ **Download failed:** {error}")
            await notification_system.send_error_message(client, user.id, error)
            return
            
        file_path = result.get('file', file_path)
        file_size = os.path.getsize(file_path)
        
        # Generate AI caption
        caption = await ai_enhanced.generate_smart_caption(
            os.path.basename(file_path), file_size
        )
        
        # Optimize upload speed
        upload_settings = await speed_optimizer.optimize_upload_speed(user.id)
        
        # Upload
        await status_msg.edit_text(
            f"📤 **Uploading...**\n\n"
            f"⚡ Speed: {upload_settings['speed']} MB/s"
        )
        
        if '-dump' in flags:
            success, msg = await uploader.upload_to_dump(client, file_path, user.id)
        else:
            success, msg = await uploader.upload_to_telegram(
                client, file_path, message.chat.id,
                caption=caption,
                user_id=user.id
            )
            
        if success:
            elapsed_time = time.time() - start_time
            
            await status_msg.edit_text(
                f"✅ **Leech Complete!**\n\n"
                f"📁 File: {os.path.basename(file_path)}\n"
                f"💾 Size: {file_size / (1024*1024):.2f} MB\n"
                f"⏱ Time: {elapsed_time:.1f}s\n"
                f"🔖 Task ID: `{task_id}`"
            )
            
            await tasks_db.update_task_status(task_id, 'completed')
            await users_db.increment_downloads(user.id)
            
            # Send completion notification
            await notification_system.send_completion_message(
                client, user.id, user.username,
                files_sent=1, files_failed=0, task_type="Leech"
            )
            
            # Organize file
            await auto_organizer_enhanced.organize_file(file_path)
            
        else:
            await status_msg.edit_text(f"❌ **Upload failed:** {msg}")
            await notification_system.send_error_message(client, user.id, msg)
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await notification_system.send_error_message(client, user.id, str(e))
