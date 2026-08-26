import time
import psutil
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.progress import Progress
from bot.modules.queue import task_queue
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.database.settings import settings_db

progress_helper = Progress()

@Client.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    """Handle /status command"""
    user = message.from_user
    
    # Get system stats
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/')
    
    # Get bot stats
    queue_status = task_queue.get_queue_status()
    task_stats = await tasks_db.get_task_stats()
    total_users = await users_db.get_total_users()
    
    # Calculate uptime
    uptime = time.time() - client.start_time if hasattr(client, 'start_time') else 0
    
    status_text = f"""
📊 **Bot Status**

⚙️ **System:**
• CPU: {cpu}%
• RAM: {ram}%
• Disk: {disk.percent}%

🤖 **Bot:**
• Uptime: {progress_helper.format_eta(uptime)}
• Users: {total_users}
• Active Tasks: {queue_status['active']}
• Queued Tasks: {queue_status['waiting']}

📈 **Statistics:**
• Total Tasks: {task_stats['total']}
• Completed: {task_stats['completed']}
• Failed: {task_stats['failed']}

⏰ **Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("♻️ Refresh", callback_data="refresh_status"),
            InlineKeyboardButton("📊 Queue", callback_data="view_queue")
        ]
    ])
    
    await message.reply_text(status_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^refresh_status$"))
async def refresh_status(client: Client, callback_query):
    """Refresh status"""
    await status_command(client, callback_query.message)
    await callback_query.answer("Status refreshed!")

@Client.on_message(filters.command("stats") & filters.private)
async def user_stats(client: Client, message: Message):
    """Handle /stats command for user statistics"""
    user = message.from_user
    
    # Get user from database
    user_data = await users_db.get_user(user.id)
    if not user_data:
        await message.reply_text("❌ **User not found!**")
        return
    
    # Get user tasks
    user_tasks = await tasks_db.get_user_tasks(user.id, 10)
    
    stats_text = f"""
📊 **Your Statistics**

👤 **User:** {user.first_name}
🆔 **ID:** {user.id}

📈 **Activity:**
• Total Tasks: {user_data.get('total_tasks', 0)}
• Downloads: {user_data.get('total_downloads', 0)}
• Uploads: {user_data.get('total_uploads', 0)}

💎 **Status:** {'Premium' if user_data.get('is_premium') else 'Free'}

📝 **Recent Tasks:**
"""
    
    for task in user_tasks[:5]:
        stats_text += f"• {task.get('task_id', 'N/A')} - {task.get('status', 'unknown')}\n"
    
    await message.reply_text(stats_text, parse_mode="markdown")

@Client.on_message(filters.command("speedtest") & filters.private)
async def speedtest_command(client: Client, message: Message):
    """Handle /speedtest command"""
    status_msg = await message.reply_text("🚀 **Running speed test...**")
    
    try:
        import speedtest
        st = speedtest.Speedtest()
        
        # Get best server
        await status_msg.edit_text("📡 **Finding best server...**")
        st.get_best_server()
        
        # Download speed
        await status_msg.edit_text("⬇️ **Testing download speed...**")
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        
        # Upload speed
        await status_msg.edit_text("⬆️ **Testing upload speed...**")
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        
        # Ping
        ping = st.results.ping
        
        result_text = f"""
🚀 **Speed Test Results**

📡 **Server:** {st.results.server['sponsor']}
📍 **Location:** {st.results.server['name']}, {st.results.server['country']}

⬇️ **Download:** {download_speed:.2f} Mbps
⬆️ **Upload:** {upload_speed:.2f} Mbps
🔴 **Ping:** {ping:.2f} ms
"""
        
        await status_msg.edit_text(result_text, parse_mode="markdown")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Speed test failed:** {str(e)}")
