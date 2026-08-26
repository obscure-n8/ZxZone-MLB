from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.database.users import users_db
from bot.database.settings import settings_db

@Client.on_message(filters.command("usettings") & filters.private)
async def usettings_command(client: Client, message: Message):
    """User settings panel"""
    user = message.from_user
    
    # Get user settings
    user_settings = await users_db.get_user_settings(user.id)
    
    settings_text = f"""
👤 **User Settings Panel**

**Download Settings:**
• Upload Mode: {user_settings.get('upload_mode', 'document')}
• Thumbnail: {'✅ Set' if user_settings.get('default_thumbnail') else '❌ Not set'}

**Task Settings:**
• Leech Limit: {user_settings.get('leech_limit', 'Default')}
• Mirror Limit: {user_settings.get('mirror_limit', 'Default')}

**Display Settings:**
• Caption Template: {user_settings.get('caption_template', 'Default')}
• Progress Style: {user_settings.get('progress_style', 'Block')}

**Privacy:**
• Show in Stats: {'✅' if user_settings.get('show_in_stats', True) else '❌'}
• Save History: {'✅' if user_settings.get('save_history', True) else '❌'}

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Upload Mode", callback_data="uset_upload"),
            InlineKeyboardButton("🎨 Thumbnail", callback_data="uset_thumb")
        ],
        [
            InlineKeyboardButton("📝 Caption", callback_data="uset_caption"),
            InlineKeyboardButton("📊 Progress", callback_data="uset_progress")
        ],
        [
            InlineKeyboardButton("🔒 Privacy", callback_data="uset_privacy"),
            InlineKeyboardButton("⚙️ Reset", callback_data="uset_reset")
        ]
    ])
    
    await message.reply_text(settings_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^uset_"))
async def usettings_callback(client: Client, callback_query):
    """Handle user settings callbacks"""
    user_id = callback_query.from_user.id
    action = callback_query.data.split("_")[1]
    
    if action == "upload":
        # Show upload mode options
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📄 Document", callback_data="uset_mode_document"),
                InlineKeyboardButton("🎬 Video", callback_data="uset_mode_video")
            ],
            [
                InlineKeyboardButton("🎵 Audio", callback_data="uset_mode_audio"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(
            "📤 **Select Upload Mode:**",
            reply_markup=keyboard,
            parse_mode="markdown"
        )
        
    elif action == "mode_document":
        await users_db.update_user_settings(user_id, {'upload_mode': 'document'})
        await callback_query.answer("Upload mode set to Document!")
        
    elif action == "mode_video":
        await users_db.update_user_settings(user_id, {'upload_mode': 'video'})
        await callback_query.answer("Upload mode set to Video!")
        
    elif action == "mode_audio":
        await users_db.update_user_settings(user_id, {'upload_mode': 'audio'})
        await callback_query.answer("Upload mode set to Audio!")
        
    elif action == "thumb":
        await callback_query.message.edit_text(
            "🎨 **Set Thumbnail:**\n\n"
            "Send me an image to set as thumbnail.\n"
            "Use /cancel to cancel.",
            parse_mode="markdown"
        )
        
    elif action == "caption":
        await callback_query.message.edit_text(
            "📝 **Caption Settings:**\n\n"
            "Send your caption template.\n"
            "Use {filename}, {size}, {quality} as variables.",
            parse_mode="markdown"
        )
        
    elif action == "progress":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("●○ Blocks", callback_data="uset_prog_block"),
                InlineKeyboardButton("█░ Blocks", callback_data="uset_prog_square")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(
            "📊 **Select Progress Style:**",
            reply_markup=keyboard,
            parse_mode="markdown"
        )
        
    elif action == "prog_block":
        await users_db.update_user_settings(user_id, {'progress_style': 'block'})
        await callback_query.answer("Progress style set to Block!")
        
    elif action == "prog_square":
        await users_db.update_user_settings(user_id, {'progress_style': 'square'})
        await callback_query.answer("Progress style set to Square!")
        
    elif action == "privacy":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Show in Stats", callback_data="uset_priv_stats"),
                InlineKeyboardButton("Save History", callback_data="uset_priv_history")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(
            "🔒 **Privacy Settings:**",
            reply_markup=keyboard,
            parse_mode="markdown"
        )
        
    elif action == "priv_stats":
        current = await users_db.get_user_settings(user_id)
        current['show_in_stats'] = not current.get('show_in_stats', True)
        await users_db.update_user_settings(user_id, current)
        await callback_query.answer(f"Show in Stats: {'OFF' if not current['show_in_stats'] else 'ON'}")
        
    elif action == "priv_history":
        current = await users_db.get_user_settings(user_id)
        current['save_history'] = not current.get('save_history', True)
        await users_db.update_user_settings(user_id, current)
        await callback_query.answer(f"Save History: {'OFF' if not current['save_history'] else 'ON'}")
        
    elif action == "reset":
        await users_db.update_user_settings(user_id, {
            'upload_mode': 'document',
            'default_thumbnail': None,
            'caption_template': None,
            'progress_style': 'block',
            'show_in_stats': True,
            'save_history': True
        })
        await callback_query.answer("Settings reset to default!")
        
    elif action == "back":
        await usettings_command(client, callback_query.message)
    
    await callback_query.answer()
