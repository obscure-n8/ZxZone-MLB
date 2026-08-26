from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.database.settings import settings_db

async def check_subscription(client: Client, user_id: int) -> bool:
    """Check if user is subscribed to channel"""
    if not Config.FORCE_SUBSCRIBE:
        return True
        
    try:
        # Check bot settings
        force_sub = await settings_db.get_setting('force_subscribe', True)
        if not force_sub:
            return True
            
        # Extract channel username from link
        channel_link = Config.UPDATE_CHANNEL
        if 't.me/' in channel_link:
            channel_username = channel_link.split('t.me/')[-1]
            if channel_username.startswith('+'):
                # Private channel - check via invite link
                return True  # Skip check for private channels
            else:
                # Public channel
                member = await client.get_chat_member(
                    chat_id=f"@{channel_username}",
                    user_id=user_id
                )
                return member.status in ['member', 'administrator', 'creator']
    except:
        return True  # Skip check on error
        
    return True

@Client.on_message(filters.private & filters.incoming)
async def force_sub_check(client: Client, message: Message):
    """Check subscription for all private messages"""
    user_id = message.from_user.id
    
    # Skip for admin
    if user_id in Config.SUDO_USERS:
        return
    
    # Check subscription
    if not await check_subscription(client, user_id):
        # Create join button
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Join Channel", url=Config.UPDATE_CHANNEL),
                InlineKeyboardButton("🔔 Support", url=Config.SUPPORT_GROUP)
            ],
            [
                InlineKeyboardButton("✅ I Joined", callback_data="check_sub")
            ]
        ])
        
        await message.reply_text(
            "⚠️ **You must join our channel to use this bot!**\n\n"
            "📢 Join the channel below and press 'I Joined' button.",
            reply_markup=keyboard,
            parse_mode="markdown"
        )
        return
    
    # Continue with normal processing
    # The message will be handled by other handlers

@Client.on_callback_query(filters.regex("^check_sub$"))
async def check_sub_callback(client: Client, callback_query):
    """Check subscription callback"""
    user_id = callback_query.from_user.id
    
    if await check_subscription(client, user_id):
        await callback_query.message.edit_text(
            "✅ **Subscription verified!**\n\n"
            "You can now use the bot.",
            parse_mode="markdown"
        )
        await callback_query.answer("Verified!")
    else:
        await callback_query.answer("You haven't joined yet!", show_alert=True)
