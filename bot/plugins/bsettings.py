from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.settings import settings_db
from bot.database.users import users_db

@Client.on_message(filters.command("bsettings") & filters.private)
async def bsettings_command(client: Client, message: Message):
    """Main bot settings panel"""
    user = message.from_user
    
    # Check if admin
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    # Get current settings
    settings = await settings_db.get_settings()
    
    settings_text = f"""
⚙️ **Bot Settings Panel**

👑 **Admin:** {user.first_name}

📊 **Current Configuration:**

🔧 **Download Engine:**
• Aria2: {'✅' if settings.get('aria2_enabled', True) else '❌'}
• Qbittorrent: {'✅' if settings.get('qbit_enabled', False) else '❌'}

📤 **Upload Settings:**
• Default Mode: {settings.get('default_upload_mode', 'document')}
• Max File Size: {settings.get('max_file_size', '2GB')}

⚡ **Task Limits:**
• Max Tasks/User: {settings.get('max_tasks_per_user', 3)}
• Max Total Tasks: {settings.get('max_total_tasks', 50)}
• Queue Limit: {settings.get('queue_limit', 20)}

🛡 **Security:**
• Force Subscribe: {'✅' if settings.get('force_subscribe', True) else '❌'}
• NSFW Filter: {'✅' if settings.get('nsfw_filter', True) else '❌'}

Select a category to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔧 Download Engine", callback_data="bset_download"),
            InlineKeyboardButton("📤 Upload Settings", callback_data="bset_upload")
        ],
        [
            InlineKeyboardButton("⚡ Task Limits", callback_data="bset_tasks"),
            InlineKeyboardButton("🛡 Security", callback_data="bset_security")
        ],
        [
            InlineKeyboardButton("🎨 Appearance", callback_data="bset_appearance"),
            InlineKeyboardButton("📊 Advanced", callback_data="bset_advanced")
        ]
    ])
    
    await message.reply_text(settings_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^bset_"))
async def bsettings_callback(client: Client, callback_query: CallbackQuery):
    """Handle bot settings callbacks"""
    user_id = callback_query.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "download":
        await show_download_settings(callback_query)
    elif action == "upload":
        await show_upload_settings(callback_query)
    elif action == "tasks":
        await show_task_settings(callback_query)
    elif action == "security":
        await show_security_settings(callback_query)
    elif action == "appearance":
        await show_appearance_settings(callback_query)
    elif action == "advanced":
        await show_advanced_settings(callback_query)
    
    await callback_query.answer()

async def show_download_settings(callback_query):
    """Show download engine settings"""
    settings = await settings_db.get_settings()
    
    text = f"""
🔧 **Download Engine Settings**

**Aria2 Settings:**
• Status: {'✅ Enabled' if settings.get('aria2_enabled', True) else '❌ Disabled'}
• Max Connections: {settings.get('aria2_connections', 10)}
• Split: {settings.get('aria2_split', 10)}
• Max Speed: {settings.get('aria2_max_speed', 'Unlimited')}

**Qbittorrent Settings:**
• Status: {'✅ Enabled' if settings.get('qbit_enabled', False) else '❌ Disabled'}
• Max Connections: {settings.get('qbit_connections', 100)}
• Upload Limit: {settings.get('qbit_upload_limit', 'Unlimited')}
• Download Limit: {settings.get('qbit_download_limit', 'Unlimited')}

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Aria2 On/Off", callback_data="toggle_aria2"),
            InlineKeyboardButton("Qbit On/Off", callback_data="toggle_qbit")
        ],
        [
            InlineKeyboardButton("Aria2 Speed", callback_data="set_aria2_speed"),
            InlineKeyboardButton("Qbit Speed", callback_data="set_qbit_speed")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="bset_back")
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

async def show_upload_settings(callback_query):
    """Show upload settings"""
    settings = await settings_db.get_settings()
    
    text = f"""
📤 **Upload Settings**

**Telegram Upload:**
• Mode: {settings.get('default_upload_mode', 'document')}
• Max Size: {settings.get('max_file_size', '2GB')}
• Split Size: {settings.get('split_size', '2GB')}

**Rclone Upload:**
• Status: {'✅ Enabled' if settings.get('rclone_enabled', True) else '❌ Disabled'}
• Remote: {settings.get('rclone_remote', 'gdrive')}
• Flags: {settings.get('rclone_flags', '')}

**Upload Options:**
• Show Cloud Link: {'✅' if settings.get('show_cloud_link', True) else '❌'}
• Delete After Upload: {'✅' if settings.get('delete_after_upload', False) else '❌'}

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Upload Mode", callback_data="set_upload_mode"),
            InlineKeyboardButton("Max Size", callback_data="set_max_size")
        ],
        [
            InlineKeyboardButton("Rclone Remote", callback_data="set_rclone_remote"),
            InlineKeyboardButton("Rclone Flags", callback_data="set_rclone_flags")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="bset_back")
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

async def show_task_settings(callback_query):
    """Show task limit settings"""
    settings = await settings_db.get_settings()
    
    text = f"""
⚡ **Task Limit Settings**

**User Limits:**
• Max Tasks/User: {settings.get('max_tasks_per_user', 3)}
• Max Leech/User: {settings.get('leech_limit', 0)}
• Max Mirror/User: {settings.get('mirror_limit', 0)}

**Global Limits:**
• Max Total Tasks: {settings.get('max_total_tasks', 50)}
• Queue Limit: {settings.get('queue_limit', 20)}

**Rate Limiting:**
• User Interval: {settings.get('user_time_interval', 0)}s
• Verify Timeout: {settings.get('verify_timeout', 0)}s

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Max Tasks/User", callback_data="set_max_tasks"),
            InlineKeyboardButton("Total Tasks", callback_data="set_total_tasks")
        ],
        [
            InlineKeyboardButton("Queue Limit", callback_data="set_queue_limit"),
            InlineKeyboardButton("Rate Limit", callback_data="set_rate_limit")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="bset_back")
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

async def show_security_settings(callback_query):
    """Show security settings"""
    settings = await settings_db.get_settings()
    
    text = f"""
🛡 **Security Settings**

**Content Filter:**
• NSFW Filter: {'✅' if settings.get('nsfw_filter', True) else '❌'}
• Spam Filter: {'✅' if settings.get('spam_filter', True) else '❌'}
• Malware Scan: {'✅' if settings.get('malware_scan', True) else '❌'}

**Access Control:**
• Force Subscribe: {'✅' if settings.get('force_subscribe', True) else '❌'}
• Private Mode: {'✅' if settings.get('private_mode', False) else '❌'}
• Authorized Chats: {settings.get('authorized_chats', 'All')}

**Rate Limiting:**
• Login Pass: {'✅' if settings.get('login_pass') else '❌'}
• Verify Timeout: {settings.get('verify_timeout', 0)}s

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("NSFW Filter", callback_data="toggle_nsfw"),
            InlineKeyboardButton("Spam Filter", callback_data="toggle_spam")
        ],
        [
            InlineKeyboardButton("Force Subscribe", callback_data="toggle_force_sub"),
            InlineKeyboardButton("Private Mode", callback_data="toggle_private")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="bset_back")
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

async def show_appearance_settings(callback_query):
    """Show appearance settings"""
    settings = await settings_db.get_settings()
    
    text = f"""
🎨 **Appearance Settings**

**Bot Profile:**
• Name: {settings.get('bot_name', Config.BOT_USERNAME)}
• Description: {settings.get('bot_description', '')}
• Profile Pic: {'✅' if settings.get('has_profile_pic') else '❌'}

**Messages:**
• Start Message: {'Custom' if settings.get('custom_start') else 'Default'}
• Help Message: {'Custom' if settings.get('custom_help') else 'Default'}
• Progress Style: {settings.get('progress_style', 'block')}

**Buttons:**
• Show Repo: {'✅' if settings.get('show_repo', True) else '❌'}
• Show Channel: {'✅' if settings.get('show_channel', True) else '❌'}

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Bot Name", callback_data="set_bot_name"),
            InlineKeyboardButton("Description", callback_data="set_bot_desc")
        ],
        [
            InlineKeyboardButton("Start Message", callback_data="set_start_msg"),
            InlineKeyboardButton("Help Message", callback_data="set_help_msg")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="bset_back")
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

async def show_advanced_settings(callback_query):
    """Show advanced settings"""
    settings = await settings_db.get_settings()
    
    text = f"""
📊 **Advanced Settings**

**System:**
• Timezone: {settings.get('timezone', 'Asia/Dhaka')}
• Log Level: {settings.get('log_level', 'INFO')}
• Telemetry: {'✅' if settings.get('telemetry', True) else '❌'}

**Features:**
• Auto Update: {'✅' if settings.get('auto_update', False) else '❌'}
• Backup: {'✅' if settings.get('auto_backup', False) else '❌'}
• Schedule: {'✅' if settings.get('scheduler', True) else '❌'}

**API:**
• StreamWish: {'✅' if settings.get('streamwish_api') else '❌'}
• FileLion: {'✅' if settings.get('filelion_api') else '❌'}
• Mega: {'✅' if settings.get('mega_email') else '❌'}

Select setting to modify:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Timezone", callback_data="set_timezone"),
            InlineKeyboardButton("Log Level", callback_data="set_log_level")
        ],
        [
            InlineKeyboardButton("Auto Update", callback_data="toggle_autoupdate"),
            InlineKeyboardButton("Auto Backup", callback_data="toggle_autobackup")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="bset_back")
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^bset_back$"))
async def bset_back_callback(client: Client, callback_query: CallbackQuery):
    """Back to main settings"""
    await bsettings_command(client, callback_query.message)
    await callback_query.answer()
