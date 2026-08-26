from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.queue import task_queue
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.database.settings import settings_db

@Client.on_callback_query(filters.regex("^cancel_"))
async def cancel_task_callback(client: Client, callback_query: CallbackQuery):
    """Handle task cancel callback"""
    task_id = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    # Cancel task
    if await task_queue.cancel_task(task_id):
        await tasks_db.update_task_status(task_id, 'cancelled')
        await callback_query.message.edit_text(
            f"✅ **Task {task_id} cancelled!**",
            parse_mode="markdown"
        )
        await callback_query.answer("Task cancelled!")
    else:
        await callback_query.answer("Task not found or already completed!", show_alert=True)

@Client.on_callback_query(filters.regex("^refresh_"))
async def refresh_task_callback(client: Client, callback_query: CallbackQuery):
    """Handle task refresh callback"""
    task_id = callback_query.data.split("_")[1]
    
    # Get task from database
    task = await tasks_db.get_task(task_id)
    
    if task:
        await callback_query.answer(
            f"Status: {task['status']}\nProgress: {task['progress']:.1f}%",
            show_alert=True
        )
    else:
        await callback_query.answer("Task not found!", show_alert=True)

@Client.on_callback_query(filters.regex("^menu_"))
async def menu_callback(client: Client, callback_query: CallbackQuery):
    """Handle menu callback"""
    task_id = callback_query.data.split("_")[1]
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{task_id}"),
            InlineKeyboardButton("♻️ Refresh", callback_data=f"refresh_{task_id}")
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data=f"status_{task_id}"),
            InlineKeyboardButton("🔙 Close", callback_data="close_menu")
        ]
    ])
    
    await callback_query.message.edit_reply_markup(keyboard)
    await callback_query.answer("Menu opened!")

@Client.on_callback_query(filters.regex("^status_"))
async def status_callback(client: Client, callback_query: CallbackQuery):
    """Handle status callback"""
    task_id = callback_query.data.split("_")[1]
    
    task = await tasks_db.get_task(task_id)
    
    if task:
        status_text = f"""
📊 **Task Status**

🔖 **Task ID:** `{task_id}`
📝 **Type:** {task['task_type']}
📊 **Status:** {task['status']}
📈 **Progress:** {task['progress']:.1f}%
💾 **Size:** {task['file_size']}
📁 **File:** {task['file_name'] or 'N/A'}
"""
        await callback_query.answer(status_text, show_alert=True)
    else:
        await callback_query.answer("Task not found!", show_alert=True)

@Client.on_callback_query(filters.regex("^close_menu$"))
async def close_menu_callback(client: Client, callback_query: CallbackQuery):
    """Close menu"""
    await callback_query.message.delete()
    await callback_query.answer("Closed!")

@Client.on_callback_query(filters.regex("^view_queue$"))
async def view_queue_callback(client: Client, callback_query: CallbackQuery):
    """View queue status"""
    queue_status = task_queue.get_queue_status()
    
    queue_text = f"""
📊 **Queue Status**

🔄 **Active Tasks:** {queue_status['active']}
⏳ **Waiting Tasks:** {queue_status['waiting']}
📈 **Total:** {queue_status['total']}
🎯 **Max:** {queue_status['max']}
"""
    
    await callback_query.message.edit_text(
        queue_text,
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("♻️ Refresh", callback_data="refresh_status")]
        ])
    )
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^help_"))
async def help_callback(client: Client, callback_query: CallbackQuery):
    """Handle help callbacks"""
    topic = callback_query.data.split("_")[1] if len(callback_query.data.split("_")) > 1 else "main"
    
    help_texts = {
        "main": "📚 **Help Menu**\n\nSelect a topic:",
        "mirror": "📥 **Mirror Commands:**\n\n/mirror <url> - Mirror to cloud\n/mirror - Reply to file\n/cancel - Cancel task",
        "leech": "📤 **Leech Commands:**\n\n/leech <url> - Leech to Telegram\n/ytdl <url> - YouTube leech\n/cancel - Cancel task",
        "settings": "⚙️ **Settings:**\n\n/settings - Bot settings\n/thumbnail - Set thumbnail\n/rename - Rename file",
        "admin": "👑 **Admin Commands:**\n\n/admin - Admin panel\n/broadcast - Broadcast message\n/ban - Ban user\n/unban - Unban user"
    }
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 Mirror", callback_data="help_mirror"),
            InlineKeyboardButton("📤 Leech", callback_data="help_leech")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
            InlineKeyboardButton("👑 Admin", callback_data="help_admin")
        ],
        [
            InlineKeyboardButton("🔙 Main", callback_data="help_main")
        ]
    ])
    
    await callback_query.message.edit_text(
        help_texts.get(topic, help_texts["main"]),
        parse_mode="markdown",
        reply_markup=keyboard
    )
    await callback_query.answer()
