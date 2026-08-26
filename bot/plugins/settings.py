from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.users import users_db
from bot.database.settings import settings_db

@Client.on_message(filters.command("settings") & filters.private)
async def settings_command(client: Client, message: Message):
    """Handle /settings command"""
    user = message.from_user
    
    # Get user settings
    user_settings = await users_db.get_user_settings(user.id)
    
    # Get bot settings
    bot_settings = await settings_db.get_settings()
    
    settings_text = f"""
⚙️ **Bot Settings**

👤 **User Settings:**
• Upload Mode: `{user_settings.get('upload_mode', 'document')}`
• Leech Limit: {user_settings.get('leech_limit', 0)}
• Mirror Limit: {user_settings.get('mirror_limit', 0)}

🤖 **Bot Settings:**
• Max Tasks/User: {bot_settings.get('max_tasks_per_user', 3)}
• Max Total Tasks: {bot_settings.get('max_total_tasks', 50)}
• Force Subscribe: {bot_settings.get('force_subscribe', True)}
• Maintenance: {bot_settings.get('maintenance_mode', False)}

💡 Use buttons below to change settings
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Upload Mode", callback_data="set_upload_mode"),
            InlineKeyboardButton("🎨 Thumbnail", callback_data="set_thumbnail")
        ],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
            InlineKeyboardButton("🔙 Main Menu", callback_data="start")
        ]
    ])
    
    await message.reply_text(settings_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^settings$"))
async def settings_callback(client: Client, callback_query: CallbackQuery):
    """Handle settings callback"""
    await settings_command(client, callback_query.message)
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^set_upload_mode$"))
async def set_upload_mode(client: Client, callback_query: CallbackQuery):
    """Set upload mode"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Document", callback_data="mode_document"),
            InlineKeyboardButton("🎬 Video", callback_data="mode_video")
        ],
        [
            InlineKeyboardButton("🎵 Audio", callback_data="mode_audio"),
            InlineKeyboardButton("🔙 Back", callback_data="settings")
        ]
    ])
    
    await callback_query.message.edit_text(
        "📤 **Select Upload Mode:**\n\n"
        "• Document: Send as file\n"
        "• Video: Send as video (streamable)\n"
        "• Audio: Send as audio",
        reply_markup=keyboard,
        parse_mode="markdown"
    )
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^mode_"))
async def mode_selected(client: Client, callback_query: CallbackQuery):
    """Handle mode selection"""
    mode = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    # Update user settings
    user_settings = await users_db.get_user_settings(user_id)
    user_settings['upload_mode'] = mode
    await users_db.update_user_settings(user_id, user_settings)
    
    await callback_query.message.edit_text(
        f"✅ **Upload mode set to:** `{mode}`",
        parse_mode="markdown"
    )
    await callback_query.answer("Settings updated!")

@Client.on_callback_query(filters.regex("^set_thumbnail$"))
async def set_thumbnail(client: Client, callback_query: CallbackQuery):
    """Set thumbnail instructions"""
    await callback_query.message.edit_text(
        "🎨 **Set Custom Thumbnail:**\n\n"
        "Send me an image to set as thumbnail\n\n"
        "**Requirements:**\n"
        "• Image format: JPG, PNG, WEBP\n"
        "• Max size: 320x320\n\n"
        "📤 Send image now or /cancel to cancel",
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="settings")]
        ])
    )
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^my_stats$"))
async def my_stats_callback(client: Client, callback_query: CallbackQuery):
    """Show user statistics"""
    user_id = callback_query.from_user.id
    user_data = await users_db.get_user(user_id)
    
    if user_data:
        stats_text = f"""
📊 **Your Statistics**

👤 **User:** {user_data.get('first_name', 'Unknown')}
🆔 **ID:** {user_id}

📈 **Activity:**
• Total Tasks: {user_data.get('total_tasks', 0)}
• Downloads: {user_data.get('total_downloads', 0)}
• Uploads: {user_data.get('total_uploads', 0)}

💎 **Status:** {'Premium' if user_data.get('is_premium') else 'Free'}
📅 **Joined:** {user_data.get('joined_at', 'Unknown')}
"""
        await callback_query.message.edit_text(
            stats_text,
            parse_mode="markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
        )
    await callback_query.answer()

@Client.on_message(filters.photo & filters.private)
async def handle_thumbnail(client: Client, message: Message):
    """Handle thumbnail upload"""
    user_id = message.from_user.id
    
    # Check if user is in thumbnail setting mode
    user_settings = await users_db.get_user_settings(user_id)
    
    if user_settings.get('awaiting_thumbnail', False):
        # Save thumbnail
        from bot.helpers.thumbnail import ThumbnailManager
        thumbnail_manager = ThumbnailManager(Config.THUMB_DIR)
        
        # Download photo
        photo_path = await message.download()
        thumbnail_path = thumbnail_manager.save_thumbnail(user_id, photo_path)
        
        # Update user settings
        user_settings['default_thumbnail'] = thumbnail_path
        user_settings['awaiting_thumbnail'] = False
        await users_db.update_user_settings(user_id, user_settings)
        
        await message.reply_text("✅ **Thumbnail set successfully!**")
        
        # Clean up
        import os
        if os.path.exists(photo_path):
            os.remove(photo_path)
    else:
        await message.reply_text("📸 Nice photo! Use /settings to set as thumbnail.")
