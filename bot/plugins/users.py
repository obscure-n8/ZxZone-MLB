from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.user_manager import user_manager
from bot.helpers.progress import Progress

progress_helper = Progress()

@Client.on_message(filters.command("users") & filters.private)
async def users_command(client: Client, message: Message):
    """Show user statistics (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    # Get statistics
    total_users = await user_manager.get_active_users(30)  # Active in 30 days
    top_users = await user_manager.get_top_users(5)
    
    stats_text = f"""
👥 **User Statistics**

📊 **Total Active Users (30 days):** {len(total_users)}

🏆 **Top Users:**

"""
    
    for i, top_user in enumerate(top_users, 1):
        stats_text += f"{i}. {top_user.get('first_name', 'Unknown')} - {top_user.get('total_tasks', 0)} tasks\n"
    
    await message.reply_text(stats_text, parse_mode="markdown")

@Client.on_message(filters.command("ban") & filters.private)
async def ban_command(client: Client, message: Message):
    """Ban user (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /ban <user_id> [reason]")
        return
    
    target_user_id = int(message.command[1])
    reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason provided"
    
    await user_manager.ban_user(target_user_id, reason)
    
    await message.reply_text(
        f"✅ **User banned!**\n\n"
        f"👤 User ID: {target_user_id}\n"
        f"📝 Reason: {reason}",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("unban") & filters.private)
async def unban_command(client: Client, message: Message):
    """Unban user (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /unban <user_id>")
        return
    
    target_user_id = int(message.command[1])
    
    await user_manager.unban_user(target_user_id)
    
    await message.reply_text(
        f"✅ **User unbanned!**\n\n"
        f"👤 User ID: {target_user_id}",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("mute") & filters.private)
async def mute_command(client: Client, message: Message):
    """Mute user (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /mute <user_id> [duration_minutes]",
            parse_mode="markdown"
        )
        return
    
    target_user_id = int(message.command[1])
    duration = int(message.command[2]) * 60 if len(message.command) > 2 else 3600
    
    await user_manager.mute_user(target_user_id, duration)
    
    await message.reply_text(
        f"✅ **User muted!**\n\n"
        f"👤 User ID: {target_user_id}\n"
        f"⏰ Duration: {duration // 60} minutes",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("userinfo") & filters.private)
async def userinfo_command(client: Client, message: Message):
    """Get user information"""
    user = message.from_user
    
    # Check if admin or self
    if user.id not in Config.SUDO_USERS and len(message.command) > 1:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    target_user_id = int(message.command[1]) if len(message.command) > 1 else user.id
    
    # Get user stats
    stats = await user_manager.get_user_stats(target_user_id)
    
    if not stats:
        await message.reply_text("❌ **User not found!**")
        return
    
    info_text = f"""
👤 **User Information**

🆔 **User ID:** {stats['user_id']}
📝 **Name:** {stats['first_name']}
👥 **Username:** @{stats['username']} if {stats['username']} else 'N/A'

📊 **Statistics:**
• Total Tasks: {stats['total_tasks']}
• Downloads: {stats['total_downloads']}
• Uploads: {stats['total_uploads']}
• Completed: {stats['tasks_completed']}
• Failed: {stats['tasks_failed']}

💎 **Premium:** {'Yes' if stats['is_premium'] else 'No'}
🚫 **Banned:** {'Yes' if stats['is_banned'] else 'No'}
📅 **Joined:** {stats['joined_at']}
"""
    
    await message.reply_text(info_text, parse_mode="markdown")

@Client.on_message(filters.command("topusers") & filters.private)
async def top_users_command(client: Client, message: Message):
    """Show top users"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    top_users = await user_manager.get_top_users(10)
    
    if not top_users:
        await message.reply_text("📊 **No users found!**")
        return
    
    top_text = "🏆 **Top 10 Users:**\n\n"
    
    medals = ['🥇', '🥈', '🥉'] + [''] * 7
    
    for i, top_user in enumerate(top_users, 1):
        medal = medals[i-1] if i <= len(medals) else ''
        top_text += f"{medal} **{i}.** {top_user.get('first_name', 'Unknown')}\n"
        top_text += f"   📊 Tasks: {top_user.get('total_tasks', 0)}\n"
        top_text += f"   ⬇️ Downloads: {top_user.get('total_downloads', 0)}\n\n"
    
    await message.reply_text(top_text, parse_mode="markdown")
