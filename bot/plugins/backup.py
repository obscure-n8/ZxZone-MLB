import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.backup import backup_manager
from bot.modules.monitor import system_monitor
from bot.helpers.progress import Progress

progress_helper = Progress()

@Client.on_message(filters.command("backup") & filters.private)
async def backup_command(client: Client, message: Message):
    """Create backup (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    status_msg = await message.reply_text("🔄 **Creating backup...**")
    
    # Create backup
    backup_path = await backup_manager.create_backup()
    
    if backup_path and os.path.exists(backup_path):
        await status_msg.edit_text("📤 **Uploading backup...**")
        
        # Send backup file
        await client.send_document(
            message.chat.id,
            backup_path,
            caption=f"💾 **Backup Created!**\n\n"
                   f"📅 Date: {os.path.basename(backup_path)}\n"
                   f"💾 Size: {progress_helper.format_size(os.path.getsize(backup_path))}",
            parse_mode="markdown"
        )
        
        await status_msg.delete()
        
        # Clean up
        os.remove(backup_path)
    else:
        await status_msg.edit_text("❌ **Backup failed!**")

@Client.on_message(filters.command("restore") & filters.private)
async def restore_command(client: Client, message: Message):
    """Restore from backup (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text(
            "📝 **Usage:** Reply to a backup file with /restore",
            parse_mode="markdown"
        )
        return
    
    status_msg = await message.reply_text("🔄 **Restoring backup...**")
    
    # Download backup file
    backup_path = await message.reply_to_message.download()
    
    # Restore
    success = await backup_manager.restore_backup(backup_path)
    
    if success:
        await status_msg.edit_text("✅ **Backup restored successfully!**")
    else:
        await status_msg.edit_text("❌ **Restore failed!**")
        
    # Clean up
    if os.path.exists(backup_path):
        os.remove(backup_path)

@Client.on_message(filters.command("backups") & filters.private)
async def list_backups_command(client: Client, message: Message):
    """List available backups (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    backups = await backup_manager.list_backups()
    
    if not backups:
        await message.reply_text("📊 **No backups found!**")
        return
    
    backup_text = "💾 **Available Backups:**\n\n"
    
    for backup in backups[:10]:
        backup_text += f"📅 {backup['name']}\n"
        backup_text += f"   💾 Size: {progress_helper.format_size(backup['size'])}\n"
        backup_text += f"   ⏰ Created: {backup['created'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    await message.reply_text(backup_text, parse_mode="markdown")

@Client.on_message(filters.command("monitor") & filters.private)
async def monitor_command(client: Client, message: Message):
    """System monitoring (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    # Get system stats
    stats = await system_monitor.get_system_stats()
    uptime = await system_monitor.get_uptime()
    
    monitor_text = f"""
📊 **System Monitor**

🖥 **CPU:**
• Usage: {stats['cpu']['percent']}%
• Cores: {stats['cpu']['cores']}
• Frequency: {stats['cpu']['frequency']:.2f} MHz

💾 **Memory:**
• Total: {progress_helper.format_size(stats['memory']['total'])}
• Used: {progress_helper.format_size(stats['memory']['used'])}
• Available: {progress_helper.format_size(stats['memory']['available'])}
• Usage: {stats['memory']['percent']}%

💿 **Disk:**
• Total: {progress_helper.format_size(stats['disk']['total'])}
• Used: {progress_helper.format_size(stats['disk']['used'])}
• Free: {progress_helper.format_size(stats['disk']['free'])}
• Usage: {stats['disk']['percent']}%

🌐 **Network:**
• Sent: {progress_helper.format_size(stats['network']['bytes_sent'])}
• Received: {progress_helper.format_size(stats['network']['bytes_recv'])}

⏰ **Uptime:** {uptime['formatted']}

📈 **Process:**
• CPU: {stats['process']['cpu_percent']}%
• Memory: {stats['process']['memory_percent']}%
• Threads: {stats['process']['threads']}
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_monitor"),
            InlineKeyboardButton("📊 History", callback_data="monitor_history")
        ]
    ])
    
    await message.reply_text(
        monitor_text,
        reply_markup=keyboard,
        parse_mode="markdown"
    )

@Client.on_callback_query(filters.regex("^refresh_monitor$"))
async def refresh_monitor_callback(client: Client, callback_query):
    """Refresh monitor"""
    await monitor_command(client, callback_query.message)
    await callback_query.answer("Refreshed!")

@Client.on_callback_query(filters.regex("^monitor_history$"))
async def monitor_history_callback(client: Client, callback_query):
    """Show monitoring history"""
    history = system_monitor.stats_history[-10:]  # Last 10 records
    
    if not history:
        await callback_query.answer("No history available!")
        return
    
    history_text = "📈 **Recent System History:**\n\n"
    
    for stat in history:
        history_text += f"⏰ {stat['timestamp'].strftime('%H:%M:%S')} - "
        history_text += f"CPU: {stat['cpu']['percent']}% | "
        history_text += f"RAM: {stat['memory']['percent']}% | "
        history_text += f"Disk: {stat['disk']['percent']}%\n"
    
    await callback_query.message.edit_text(
        history_text,
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="refresh_monitor")]
        ])
    )
    await callback_query.answer()
