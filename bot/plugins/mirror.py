import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.downloader import downloader
from bot.modules.queue import task_queue
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

@Client.on_message(filters.command("mirror") & filters.private)
async def mirror_command(client: Client, message: Message):
    """Handle /mirror command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check if URL provided
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /mirror <url>\n\n"
            "Or send me a direct link directly!",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    
    # Validate URL
    if not Utils.is_valid_url(url) and not Utils.is_magnet_link(url):
        await message.reply_text("❌ **Invalid URL!**")
        return
    
    # Check queue limit
    if task_queue.get_waiting_count() >= Config.QUEUE_LIMIT:
        await message.reply_text("⚠️ **Queue is full!** Please try later.")
        return
    
    # Generate task ID
    task_id = Utils.generate_task_id()
    
    # Create initial status message
    status_msg = await message.reply_text(
        f"📥 **Task Added to Queue**\n\n"
        f"🔖 **Task ID:** `{task_id}`\n"
        f"🔗 **URL:** {url[:50]}...\n"
        f"📊 **Queue Position:** {task_queue.get_waiting_count() + 1}\n\n"
        f"⏳ **Status:** Waiting...",
        parse_mode="markdown"
    )
    
    # Add task to database
    await tasks_db.add_task(task_id, user.id, 'mirror', url)
    await users_db.increment_tasks(user.id)
    
    # Add to queue
    await task_queue.add_task(task_id, {
        'type': 'download',
        'url': url,
        'user_id': user.id,
        'message': status_msg,
        'file_path': os.path.join(Config.DOWNLOAD_DIR, f"{task_id}_{time.time()}"),
        'progress_callback': lambda downloaded, total, start_time: update_progress(
            status_msg, task_id, downloaded, total, start_time, user, 'Mirror'
        )
    })

async def update_progress(status_msg, task_id, downloaded, total, start_time, user, mode):
    """Update progress message"""
    # Update every 2 seconds
    current_time = time.time()
    if current_time - progress_helper.last_update_time < 2:
        return
        
    progress_helper.last_update_time = current_time
    
    # Calculate progress
    percentage = (downloaded / total) * 100 if total > 0 else 0
    speed = downloaded / (current_time - start_time) if current_time > start_time else 0
    eta = (total - downloaded) / speed if speed > 0 else 0
    
    # Get system stats
    system = progress_helper.get_system_stats()
    progress_bar = progress_helper.get_progress_bar(percentage)
    
    # Create progress text
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
│ **Engine** : Aria2 v1.37.0 | **Mode** : `#{mode}`
> **Stop** : `/c_{task_id}`

⬢ **BOT STATS**
┌ **CPU** : {system['cpu']}% | **RAM** : {system['ram']}%
└ **FREE** : {system['free_disk']}
"""
    
    try:
        await status_msg.edit_text(progress_text, parse_mode="markdown")
    except:
        pass

@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client: Client, message: Message):
    """Handle /cancel command"""
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /cancel <task_id>")
        return
    
    task_id = message.command[1]
    
    # Cancel task
    if await task_queue.cancel_task(task_id):
        await tasks_db.update_task_status(task_id, 'cancelled')
        await message.reply_text(f"✅ **Task {task_id} cancelled!**")
    else:
        await message.reply_text(f"❌ **Task {task_id} not found!**")
