from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.helpers.permissions import permission_system
from bot.database.users import users_db

@Client.on_message(filters.command("addsudo") & filters.private)
async def add_sudo_command(client: Client, message: Message):
    """Add sudo user (owner only)"""
    user = message.from_user
    
    if not await permission_system.is_owner(user.id):
        await message.reply_text("❌ **Only owner can add sudo users!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /addsudo <user_id>")
        return
    
    target_user_id = int(message.command[1])
    
    # Check if already sudo
    if target_user_id in Config.SUDO_USERS:
        await message.reply_text(f"❌ **User {target_user_id} is already sudo!**")
        return
    
    # Add to sudo
    Config.SUDO_USERS.append(target_user_id)
    
    # Update database
    await users_db.update_user(target_user_id, {'is_sudo': True})
    
    await message.reply_text(
        f"✅ **Sudo User Added!**\n\n"
        f"👤 User ID: {target_user_id}\n"
        f"🔑 Access Level: Sudo",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("removesudo") & filters.private)
async def remove_sudo_command(client: Client, message: Message):
    """Remove sudo user (owner only)"""
    user = message.from_user
    
    if not await permission_system.is_owner(user.id):
        await message.reply_text("❌ **Only owner can remove sudo users!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /removesudo <user_id>")
        return
    
    target_user_id = int(message.command[1])
    
    # Check if in sudo
    if target_user_id not in Config.SUDO_USERS:
        await message.reply_text(f"❌ **User {target_user_id} is not sudo!**")
        return
    
    # Remove from sudo
    Config.SUDO_USERS.remove(target_user_id)
    
    # Update database
    await users_db.update_user(target_user_id, {'is_sudo': False})
    
    await message.reply_text(
        f"✅ **Sudo User Removed!**\n\n"
        f"👤 User ID: {target_user_id}",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("sudolist") & filters.private)
async def sudo_list_command(client: Client, message: Message):
    """List all sudo users (owner only)"""
    user = message.from_user
    
    if not await permission_system.is_owner(user.id):
        await message.reply_text("❌ **Only owner can view sudo list!**")
        return
    
    sudo_text = "👑 **Sudo Users List:**\n\n"
    sudo_text += f"👑 **Owner:** {Config.OWNER_ID}\n\n"
    sudo_text += "🔑 **Sudo Users:**\n"
    
    if Config.SUDO_USERS:
        for sudo_id in Config.SUDO_USERS:
            if sudo_id != Config.OWNER_ID:
                sudo_text += f"• {sudo_id}\n"
    else:
        sudo_text += "• No sudo users\n"
    
    await message.reply_text(sudo_text, parse_mode="markdown")

@Client.on_message(filters.command("myaccess") & filters.private)
async def my_access_command(client: Client, message: Message):
    """Check own access level"""
    user = message.from_user
    
    # Get permission info
    perm_info = await permission_system.get_permission_info(user.id)
    
    access_text = f"""
🔐 **Your Access Information**

👤 **User ID:** {user.id}
📝 **Name:** {user.first_name}

🎯 **Access Level:** {perm_info['level'].upper()}
📊 **Level Number:** {perm_info['level_number']}/5

✅ **Status:**
• Owner: {'✅' if perm_info['is_owner'] else '❌'}
• Sudo: {'✅' if perm_info['is_sudo'] else '❌'}
• Admin: {'✅' if perm_info['is_admin'] else '❌'}
• Premium: {'✅' if perm_info['is_premium'] else '❌'}

🔑 **Your Permissions:**
"""
    
    for permission in perm_info['permissions']:
        access_text += f"• {permission}\n"
    
    await message.reply_text(access_text, parse_mode="markdown")

@Client.on_message(filters.command("checkaccess") & filters.private)
async def check_access_command(client: Client, message: Message):
    """Check access level of user (sudo/owner only)"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /checkaccess <user_id>")
        return
    
    target_user_id = int(message.command[1])
    
    # Get target user info
    perm_info = await permission_system.get_permission_info(target_user_id)
    
    access_text = f"""
🔐 **User Access Information**

👤 **User ID:** {target_user_id}
🎯 **Access Level:** {perm_info['level'].upper()}

✅ **Status:**
• Owner: {'✅' if perm_info['is_owner'] else '❌'}
• Sudo: {'✅' if perm_info['is_sudo'] else '❌'}
• Admin: {'✅' if perm_info['is_admin'] else '❌'}
• Premium: {'✅' if perm_info['is_premium'] else '❌'}
• Banned: {'✅' if perm_info['is_banned'] else '❌'}
"""
    
    await message.reply_text(access_text, parse_mode="markdown")
