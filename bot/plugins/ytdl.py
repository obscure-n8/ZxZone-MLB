import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.uploader import uploader
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

@Client.on_message(filters.command("ytdl") & filters.private)
async def ytdl_command(client: Client, message: Message):
    """Handle /ytdl command for YouTube downloads"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check if URL provided
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /ytdl <youtube_url>",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    task_id = Utils.generate_task_id()
    
    # Create status message
    status_msg = await message.reply_text(
        f"📥 **YouTube Download Started**\n\n"
        f"🔖 **Task ID:** `{task_id}`\n"
        f"🔗 **URL:** {url[:50]}...\n\n"
        f"⏳ **Status:** Fetching video info...",
        parse_mode="markdown"
    )
    
    # Add task to database
    await tasks_db.add_task(task_id, user.id, 'ytdl', url)
    await users_db.increment_tasks(user.id)
    
    try:
        # Download using yt-dlp
        from yt_dlp import YoutubeDL
        
        # Create download directory
        download_dir = os.path.join(Config.DOWNLOAD_DIR, f"ytdl_{task_id}")
        os.makedirs(download_dir, exist_ok=True)
        
        # Update options
        ytdl_options = Config.YTDLP_OPTIONS.copy()
        ytdl_options['outtmpl'] = os.path.join(download_dir, '%(title)s.%(ext)s')
        ytdl_options['progress_hooks'] = [
            lambda d: asyncio_run(update_ytdl_progress(status_msg, task_id, d, user))
        ]
        
        # Download video
        with YoutubeDL(ytdl_options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # Upload to Telegram
            await status_msg.edit_text("📤 **Uploading to Telegram...**")
            
            success, msg = await uploader.upload_to_telegram(
                client,
                file_path,
                message.chat.id,
                caption=f"**Title:** {info.get('title', 'Unknown')}\n"
                       f"**Duration:** {progress_helper.format_eta(info.get('duration', 0))}",
                as_video=True
            )
            
            if success:
                await status_msg.edit_text(
                    f"✅ **Download Complete!**\n\n"
                    f"📹 **Title:** {info.get('title', 'Unknown')}\n"
                    f"💾 **Size:** {progress_helper.format_size(os.path.getsize(file_path))}",
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
            if os.path.exists(download_dir):
                os.rmdir(download_dir)
                
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await tasks_db.update_task_status(task_id, 'failed')

def asyncio_run(coro):
    """Run async function"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)
    loop.close()

async def update_ytdl_progress(status_msg, task_id, data, user):
    """Update YouTube download progress"""
    if data['status'] == 'downloading':
        downloaded = data.get('downloaded_bytes', 0)
        total = data.get('total_bytes', 0)
        
        if total > 0:
            percentage = (downloaded / total) * 100
            speed = data.get('speed', 0)
            eta = data.get('eta', 0)
            
            system = progress_helper.get_system_stats()
            progress_bar = progress_helper.get_progress_bar(percentage)
            
            progress_text = f"""
**Zonexus M/L Bot 1**
┌ **{Config.BOT_USERNAME}**
└ `/leech1 {task_id}`

▍ **Powered By Zonexus Hub** ❞

1. `{data.get('filename', 'Downloading...')}`
┌ **Task By {user.first_name}**
│ {progress_bar} {percentage:.1f}%
│ **Status** : Download
│ **Total** : {progress_helper.format_size(total)} | **Done** : {progress_helper.format_size(downloaded)}
│ **Speed** : {progress_helper.format_speed(speed)} | **ETA** : {progress_helper.format_eta(eta)}
│ **Engine** : YT-DLP | **Mode** : `#YTDL`
> **Stop** : `/c_{task_id}`

⬢ **BOT STATS**
┌ **CPU** : {system['cpu']}% | **RAM** : {system['ram']}%
└ **FREE** : {system['free_disk']}
"""
            
            try:
                await status_msg.edit_text(
                    progress_text,
                    parse_mode="markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{task_id}")]
                    ])
                )
            except:
                pass
