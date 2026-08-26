import os
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.database.users import users_db

@Client.on_message(filters.command("setsession") & filters.private)
async def set_session_command(client: Client, message: Message):
    """Set user session string for premium features"""
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /setsession <session_string>\n\n"
            "Session string দিলে আপনি পাবেন:\n"
            "• 4GB split size\n"
            "• Direct upload without bot\n"
            "• Premium features",
            parse_mode="markdown"
        )
        return
    
    session_string = message.command[1]
    
    # Save session string
    await users_db.update_user(user.id, {
        'session_string': session_string,
        'has_session': True
    })
    
    await message.reply_text(
        "✅ **Session string set!**\n\n"
        "এখন আপনি premium features পাবেন:\n"
        "• 4GB split size\n"
        "• Faster upload\n"
        "• Direct streaming",
        parse_mode="markdown"
    )

@Client.on_message(filters.command("clearsession") & filters.private)
async def clear_session_command(client: Client, message: Message):
    """Clear user session string"""
    user = message.from_user
    
    await users_db.update_user(user.id, {
        'session_string': None,
        'has_session': False
    })
    
    await message.reply_text("✅ **Session string cleared!**")

@Client.on_message(filters.command("mysession") & filters.private)
async def my_session_command(client: Client, message: Message):
    """Check session status"""
    user = message.from_user
    user_data = await users_db.get_user(user.id)
    
    has_session = user_data.get('has_session', False) if user_data else False
    is_premium = user_data.get('is_premium', False) if user_data else False
    
    status_text = f"""
📊 **Your Account Status:**

👤 User: {user.first_name}

⚡ Session: {'✅ Active' if has_session else '❌ Not set'}
💎 Premium: {'✅ Active' if is_premium else '❌ Not premium'}

📦 Split Size: {await get_split_size_text(user.id)}
"""
    
    await message.reply_text(status_text, parse_mode="markdown")

async def get_split_size_text(user_id: int) -> str:
    """Get split size text"""
    user = await users_db.get_user(user_id)
    has_session = user.get('has_session', False) if user else False
    is_premium = user.get('is_premium', False) if user else False
    
    if is_premium and has_session:
        return "4GB (Maximum)"
    elif is_premium:
        return "3GB (Premium)"
    elif has_session:
        return "2.5GB (Session)"
    else:
        return "2GB (Default)"
