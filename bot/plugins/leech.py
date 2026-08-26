import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.downloader import downloader
from bot.modules.uploader import uploader
from bot.modules.queue import task_queue
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

@Client.on_message(filters.command("leech") & filters.private)
async def leech_command(client: Client, message: Message):
    """Handle /leech command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check user task limit
    user_tasks = task_queue.get_active_count()
    if user_tasks >= Config.MAX_TASKS_PER_USER:
        await message.reply_text(
            f"⚠️ **Task limit reached!**\n"
            f"Max tasks per user: {Config.MAX_TASKS_PER_USER}"
        )
        return
    
    # Check if URL provided
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /leech <url>\n\n"
            "Or send me a direct link directly!",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    
    # Validate URL
    if not Utils.is_valid_url(url) and not Utils.is_magnet_link(url):
        await message.reply_text("❌ **Invalid URL!**")
        return
    
    # Generate task ID
    task_id = Utils.generate_task_id()
    
    # Create initial status message
    status_msg = await message.reply_text(
        f"📥 **Task Added**\n\n"
        f"🔖 **Task ID:** `{task_id}`\n"
        f"🔗 **URL:** {url[:50]}...\n"
        f"📊 **Mode:** Leech\n\n"
        f"⏳ **Status:** Initializing...",
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{task_id}"),
                InlineKeyboardButton("♻️ Refresh", callback_data=f"refresh_{task_id}")
            ]
        ])
    )
    
    # Add task to database
    await tasks_db.add_task(task_id, user.id, 'leech', url)
    await users_db.increment_tasks(user.id)
    
    # Start leech process
    await process_leech_task(client, message, url, task_id, status_msg)

async def process_leech_task(client, message, url, task_id, status_msg):
    """Process leech task"""
    user = message.from_user
    file_path = os.path.join(Config.DOWNLOAD_DIR, f"{task_id}_{time.time()}")
    
    try:
        # Update status
        await tasks_db.update_task_status(task_id, 'download')
        
        # Download file
        success = await downloader.download_with_retry(
            url,
            file_path,
            progress_callback=lambda downloaded, total, start_time: update_leech_progress(
                status_msg, task_id, downloaded, total, start_time, user
            )
        )
        
        if not success:
            await status_msg.edit_text("❌ **Download failed!**")
            await tasks_db.update_task_status(task_id, 'failed')
            return
        
        # Update status
        await tasks_db.update_task_status(task_id, 'upload')
        
        # Get file name
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Upload to Telegram
        success, msg = await uploader.upload_to_telegram(
            client,
            file_path,
            message.chat.id,
            caption=f"**File:** {file_name}\n**Size:** {progress_helper.format_size(file_size)}",
            progress_callback=lambda current, total: update_upload_progress(
                status_msg, task_id, current, total, user, file_name
            )
        )
        
        if success:
            await status_msg.edit_text(
                f"✅ **Leech Complete!**\n\n"
                f"📁 **File:** {file_name}\n"
                f"💾 **Size:** {progress_helper.format_size(file_size)}\n"
                f"🔖 **Task ID:** `{task_id}`",
                parse_mode="markdown"
            )
            await tasks_db.update_task_status(task_id, 'completed')
            await users_db.increment_downloads(user.id)
        else:
            await status_msg.edit_text(f"❌ **Upload failed:** {msg}")
            await tasks_db.update_task_status(task_id, 'failed')
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await tasks_db.update_task_status(task_id, 'failed')
        
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

async def update_leech_progress(status_msg, task_id, downloaded, total, start_time, user):
    """Update leech download progress"""
    current_time = time.time()
    if current_time - progress_helper.last_update_time < 2:
        return
        
    progress_helper.last_update_time = current_time
    percentage = (downloaded / total) * 100 if total > 0 else 0
    speed = downloaded / (current_time - start_time) if current_time > start_time else 0
    eta = (total - downloaded) / speed if speed > 0 else 0
    
    system = progress_helper.get_system_stats()
    progress_bar = progress_helper.get_progress_bar(percentage)
    
    progress_text = f"""
**Zonexus M/L Bot 1**
┌ **{Config.BOT_USERNAME}**
└ `/leech1 {task_id}`

▍ **Powered By Zonexus Hub** ❞

1. `Downloading...`
┌ **Task By {user.first_name}**
│ {progress_bar} {percentage:.1f}%
│ **Status** : Download
│ **Total** : {progress_helper.format_size(total)} | **Done** : {progress_helper.format_size(downloaded)}
│ **Speed** : {progress_helper.format_speed(speed)} | **ETA** : {progress_helper.format_eta(eta)}
│ **Engine** : Aria2 v1.37.0 | **Mode** : `#Leech`
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

async def update_upload_progress(status_msg, task_id, current, total, user, file_name):
    """Update upload progress"""
    current_time = time.time()
    if current_time - progress_helper.last_update_time < 2:
        return
        
    progress_helper.last_update_time = current_time
    percentage = (current / total) * 100 if total > 0 else 0
    
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
│ **Status** : Upload
│ **Total** : {progress_helper.format_size(total)} | **Done** : {progress_helper.format_size(current)}
│ **Engine** : Aria2 v1.37.0 | **Mode** : `#Leech`
> **Stop** : `/c_{task_id}`

⬢ **BOT STATS**
┌ **CPU** : {system['cpu']}% | **RAM** : {system['ram']}%
└ **FREE** : {system['free_disk']}
"""
    
    try:
        await status_msg.edit_text(progress_text, parse_mode="markdown")
    except:
        pass
