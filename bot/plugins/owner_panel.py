import os
from bot.plugins.bsettings import bsettings_command
from bot.plugins.update import update_command
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.helpers.permissions import permission_system
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.database.settings import settings_db

@Client.on_message(filters.command("owner") & filters.private)
async def owner_panel_command(client: Client, message: Message):
    """Owner panel (owner only)"""
    user = message.from_user
    
    if not await permission_system.is_owner(user.id):
        await message.reply_text("❌ **Only owner can access this panel!**")
        return
    
    # Get statistics
    total_users = await users_db.get_total_users()
    total_sudo = len(Config.SUDO_USERS)
    task_stats = await tasks_db.get_task_stats()
    
    panel_text = f"""
👑 **Owner Control Panel**

**Welcome:** {user.first_name}

📊 **Bot Statistics:**
• Total Users: {total_users}
• Sudo Users: {total_sudo}
• Total Tasks: {task_stats['total']}
• Active Tasks: {task_stats['active']}

🔧 **Quick Actions:**
• Manage Sudo Users
• View Admin Logs
• System Settings
• Broadcast Message
• Backup System
• Update Bot

Select an option:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 Sudo Management", callback_data="owner_sudo"),
            InlineKeyboardButton("📋 Admin Logs", callback_data="owner_logs")
        ],
        [
            InlineKeyboardButton("⚙️ Bot Settings", callback_data="owner_settings"),
            InlineKeyboardButton("📢 Broadcast", callback_data="owner_broadcast")
        ],
        [
            InlineKeyboardButton("💾 Backup", callback_data="owner_backup"),
            InlineKeyboardButton("🔄 Update", callback_data="owner_update")
        ],
        [
            InlineKeyboardButton("📊 Advanced Stats", callback_data="owner_stats"),
            InlineKeyboardButton("🔒 Close", callback_data="owner_close")
        ]
    ])
    
    await message.reply_text(panel_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^owner_"))
async def owner_callback(client: Client, callback_query: CallbackQuery):
    """Handle owner panel callbacks"""
    user_id = callback_query.from_user.id
    
    if not await permission_system.is_owner(user_id):
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "sudo":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Add Sudo", callback_data="owner_addsudo"),
                InlineKeyboardButton("➖ Remove Sudo", callback_data="owner_remsudo")
            ],
            [
                InlineKeyboardButton("📋 Sudo List", callback_data="owner_sudolist"),
                InlineKeyboardButton("🔙 Back", callback_data="owner_back")
            ]
        ])
        
        await callback_query.message.edit_text(
            "👑 **Sudo Management**\n\nSelect an option:",
            reply_markup=keyboard,
            parse_mode="markdown"
        )
        
    elif action == "logs":
        from bot.plugins.admin_logs import admin_logger
        logs = await admin_logger.get_logs(10)
        
        if logs:
            log_text = "📋 **Recent Admin Logs:**\n\n"
            for log in logs:
                log_text += f"• {log['admin_id']} - {log['action']} - {log['timestamp'].strftime('%H:%M')}\n"
        else:
            log_text = "📋 **No logs found!**"
            
        await callback_query.message.edit_text(
            log_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="owner_back")]
            ]),
            parse_mode="markdown"
        )
        
    elif action == "settings":
        await bsettings_command(client, callback_query.message)
        
    elif action == "broadcast":
        await callback_query.message.edit_text(
            "📢 **Broadcast Mode:**\n\n"
            "Send me the message to broadcast.\n"
            "Use /cancel to cancel.",
            parse_mode="markdown"
        )
        
    elif action == "backup":
        from bot.modules.backup import backup_manager
        backup_path = await backup_manager.create_backup()
        
        if backup_path:
            await callback_query.message.edit_text(
                f"✅ **Backup created!**\n\n"
                f"📁 File: {os.path.basename(backup_path)}",
                parse_mode="markdown"
            )
        else:
            await callback_query.message.edit_text("❌ **Backup failed!**")
            
    elif action == "update":
        await update_command(client, callback_query.message)
        
    elif action == "stats":
        from bot.modules.analytics import analytics
        report = await analytics.generate_report()
        
        await callback_query.message.edit_text(
            report,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="owner_back")]
            ]),
            parse_mode="markdown"
        )
        
    elif action == "close":
        await callback_query.message.delete()
        
    elif action == "back":
        await owner_panel_command(client, callback_query.message)
    
    await callback_query.answer()

@Client.on_message(filters.command("addadmin") & filters.private)
async def add_admin_command(client: Client, message: Message):
    """Add admin (sudo/owner only)"""
    user = message.from_user
    
    if not await permission_system.is_sudo(user.id):
        await message.reply_text("❌ **Only sudo/owner can add admin!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /addadmin <user_id>")
        return
    
    target_user_id = int(message.command[1])
    
    await users_db.update_user(target_user_id, {'is_admin': True})
    
    await message.reply_text(
        f"✅ **Admin Added!**\n\n"
        f"👤 User ID: {target_user_id}\n"
        f"🔑 Access Level: Admin",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("removeadmin") & filters.private)
async def remove_admin_command(client: Client, message: Message):
    """Remove admin (sudo/owner only)"""
    user = message.from_user
    
    if not await permission_system.is_sudo(user.id):
        await message.reply_text("❌ **Only sudo/owner can remove admin!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /removeadmin <user_id>")
        return
    
    target_user_id = int(message.command[1])
    
    await users_db.update_user(target_user_id, {'is_admin': False})
    
    await message.reply_text(
        f"✅ **Admin Removed!**\n\n"
        f"👤 User ID: {target_user_id}",
        parse_mode="markdown"
    )
