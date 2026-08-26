from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.database.settings import settings_db

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in Config.SUDO_USERS

@Client.on_message(filters.command("admin") & filters.private)
async def admin_command(client: Client, message: Message):
    """Admin panel command"""
    user = message.from_user
    
    if not is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    admin_text = f"""
👑 **Admin Panel**

**Welcome:** {user.first_name}

📊 **Bot Statistics:**
• Total Users: {await users_db.get_total_users()}
• Active Today: {await users_db.get_active_today()}

📈 **Task Statistics:**
"""
    
    task_stats = await tasks_db.get_task_stats()
    admin_text += f"""
• Total Tasks: {task_stats['total']}
• Completed: {task_stats['completed']}
• Failed: {task_stats['failed']}
• Active: {task_stats['active']}
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("📊 Tasks", callback_data="admin_tasks")
        ],
        [
            InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_settings"),
            InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maintenance")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🔙 Close", callback_data="admin_close")
        ]
    ])
    
    await message.reply_text(admin_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^admin_"))
async def admin_callback(client: Client, callback_query):
    """Handle admin callbacks"""
    user_id = callback_query.from_user.id
    
    if not is_admin(user_id):
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "users":
        # Show user list
        users = await users_db.get_all_users()
        user_text = "👥 **User List:**\n\n"
        for user in users[:10]:
            user_text += f"• {user.get('first_name', 'Unknown')} (ID: {user.get('user_id')})\n"
        
        await callback_query.message.edit_text(
            user_text,
            parse_mode="markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
        
    elif action == "tasks":
        # Show active tasks
        active_tasks = await tasks_db.get_active_tasks()
        task_text = "📊 **Active Tasks:**\n\n"
        for task in active_tasks[:10]:
            task_text += f"• {task.get('task_id')} - {task.get('status')} ({task.get('task_type')})\n"
        
        await callback_query.message.edit_text(
            task_text,
            parse_mode="markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
        
    elif action == "settings":
        # Show bot settings
        bot_settings = await settings_db.get_settings()
        settings_text = "⚙️ **Bot Settings:**\n\n"
        for key, value in bot_settings.items():
            settings_text += f"• {key}: {value}\n"
        
        await callback_query.message.edit_text(
            settings_text,
            parse_mode="markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
        
    elif action == "maintenance":
        # Toggle maintenance mode
        current = await settings_db.get_setting('maintenance_mode', False)
        new_status = await settings_db.toggle_maintenance()
        await callback_query.answer(f"Maintenance: {'ON' if new_status else 'OFF'}")
        await admin_command(client, callback_query.message)
        
    elif action == "broadcast":
        await callback_query.message.edit_text(
            "📢 **Broadcast Mode:**\n\n"
            "Send me the message you want to broadcast.\n"
            "Use /cancel to cancel.",
            parse_mode="markdown"
        )
        
    elif action == "close":
        await callback_query.message.delete()
        
    elif action == "back":
        await admin_command(client, callback_query.message)
        
    await callback_query.answer()

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Broadcast message to all users"""
    user = message.from_user
    
    if not is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /broadcast <message>")
        return
    
    broadcast_text = " ".join(message.command[1:])
    
    # Get all users
    users = await users_db.get_all_users()
    
    sent_count = 0
    failed_count = 0
    
    status_msg = await message.reply_text(f"📢 **Broadcasting...**")
    
    for user_data in users:
        try:
            await client.send_message(
                user_data['user_id'],
                f"📢 **Broadcast:**\n\n{broadcast_text}"
            )
            sent_count += 1
        except:
            failed_count += 1
            
        # Update status every 20 users
        if (sent_count + failed_count) % 20 == 0:
            await status_msg.edit_text(
                f"📢 **Broadcasting:**\n\n"
                f"✅ Sent: {sent_count}\n"
                f"❌ Failed: {failed_count}"
            )
    
    await status_msg.edit_text(
        f"📢 **Broadcast Complete!**\n\n"
        f"✅ Sent: {sent_count}\n"
        f"❌ Failed: {failed_count}"
    )
