import os
import json
import asyncio
from typing import Dict, Optional, List
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.settings import settings_db
from bot.helpers.permissions import permission_system

class BotSettingsPanel:
    def __init__(self):
        self.config_variables = [
            # Required
            'BOT_TOKEN', 'API_ID', 'API_HASH', 'OWNER_ID',
            # Limits
            'BOT_MAX_TASKS', 'USER_MAX_TASKS', 'DIRECT_LIMIT', 'MEGA_LIMIT',
            'TORRENT_LIMIT', 'GD_DL_LIMIT', 'RC_DL_LIMIT', 'CLONE_LIMIT',
            'JD_LIMIT', 'NZB_LIMIT', 'YTDLP_LIMIT', 'PLAYLIST_LIMIT',
            'LEECH_LIMIT', 'EXTRACT_LIMIT', 'ARCHIVE_LIMIT', 'STORAGE_LIMIT',
            # Upload
            'DEFAULT_UPLOAD', 'AS_DOCUMENT', 'EQUAL_SPLITS', 'MEDIA_GROUP',
            'LEECH_SPLIT_SIZE', 'LEECH_PREFIX', 'LEECH_SUFFIX',
            # Disable Options
            'DISABLE_TORRENTS', 'DISABLE_LEECH', 'DISABLE_MIRROR',
            'DISABLE_BULK', 'DISABLE_MULTI', 'DISABLE_SEED',
            'DISABLE_FF_MODE', 'DISABLE_JD', 'DISABLE_NZB',
            'DISABLE_RSS', 'DISABLE_SEARCH', 'DISABLE_STREAM',
            'DISABLE_YTDLP', 'DISABLE_MEGA',
            # API Keys
            'FILELION_API', 'STREAMWISH_API', 'ALLDEBRID_API_KEY',
            'INSTADL_API', 'HYDRA_API_KEY',
            'MEGA_EMAIL', 'MEGA_PASSWORD',
            # Queue
            'QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD',
            # Torrent
            'TORRENT_TIMEOUT', 'BASE_URL',
            # RSS
            'RSS_DELAY', 'RSS_CHAT', 'RSS_SIZE_LIMIT',
            # Search
            'SEARCH_API_LINK', 'SEARCH_LIMIT',
            # YT
            'YT_CATEGORY_ID', 'YT_PRIVACY_STATUS',
            # Bot Settings
            'BOT_PM', 'SET_COMMANDS', 'TIMEZONE',
            'FORCE_SUB_IDS', 'MEDIA_STORE', 'DELETE_LINKS',
            'VERIFY_TIMEOUT', 'LOGIN_PASS',
            # Channels
            'UPDATE_CHANNEL', 'REPO_LINK',
            'LEECH_DUMP_CHAT', 'LINKS_LOG_ID', 'MIRROR_LOG_ID',
            # Rclone
            'RCLONE_PATH', 'RCLONE_FLAGS', 'RCLONE_SERVE_URL',
            'SHOW_CLOUD_LINK', 'RCLONE_SERVE_PORT',
            # JD
            'JD_EMAIL', 'JD_PASS',
            # Misc
            'SUDO_USERS', 'AUTHORIZED_CHATS', 'CMD_SUFFIX',
            'DEFAULT_LANG', 'AUTHOR_NAME', 'AUTHOR_URL',
            'UPSTREAM_REPO', 'UPSTREAM_BRANCH',
            'ENABLE_TELEMETRY', 'TG_PROXY'
        ]
        self.page_size = 8
        self.current_page = {}
        self.edit_mode = {}
        self.temp_values = {}
        
    async def show_main_panel(self, client: Client, message: Message):
        """Show main bot settings panel"""
        user = message.from_user
        
        if not await permission_system.is_admin(user.id):
            await message.reply_text("❌ **You are not authorized!**")
            return
        
        settings = await settings_db.get_settings()
        
        panel_text = f"""
⚙️ **Bot Settings Panel**

👑 **Admin:** {user.first_name}

📊 **Quick Stats:**
• Total Config Variables: {len(self.config_variables)}
• Bot: @{Config.BOT_USERNAME}
• Max Tasks: {settings.get('bot_max_tasks', Config.BOT_MAX_TASKS)}

Select a category:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔧 Config Variables", callback_data="bset_config"),
                InlineKeyboardButton("📁 Private Files", callback_data="bset_files")
            ],
            [
                InlineKeyboardButton("⚡ Aria2c Settings", callback_data="bset_aria2"),
                InlineKeyboardButton("🔗 JDownloader", callback_data="bset_jd")
            ],
            [
                InlineKeyboardButton("📊 Limits", callback_data="bset_limits"),
                InlineKeyboardButton("🎛 Disable Options", callback_data="bset_disable")
            ],
            [
                InlineKeyboardButton("🔑 API Keys", callback_data="bset_api"),
                InlineKeyboardButton("📤 Upload Settings", callback_data="bset_upload")
            ],
            [
                InlineKeyboardButton("🔒 Security", callback_data="bset_security"),
                InlineKeyboardButton("📡 Channels", callback_data="bset_channels")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="bset_close")
            ]
        ])
        
        await message.reply_text(panel_text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_config_variables(self, callback_query: CallbackQuery, page: int = 0, category: str = 'all'):
        """Show config variables with pagination"""
        # Filter by category if needed
        variables = self.filter_variables(category)
        total_pages = (len(variables) + self.page_size - 1) // self.page_size
        page = max(0, min(page, total_pages - 1))
        
        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, len(variables))
        page_variables = variables[start_idx:end_idx]
        
        # Get current values
        settings = await settings_db.get_settings()
        
        text = f"""
🔧 **Config Variables** (Page {page + 1}/{total_pages})

Category: {category.upper()}
Total Variables: {len(variables)}

Click on a variable to edit:
"""
        
        # Create buttons (2 per row)
        buttons = []
        for i in range(0, len(page_variables), 2):
            row = []
            for var in page_variables[i:i+2]:
                # Get current value
                current_value = settings.get(var.lower(), getattr(Config, var, 'N/A'))
                
                # Check if in edit mode
                if var in self.edit_mode and self.edit_mode[var]:
                    display_value = self.temp_values.get(var, current_value)
                    button_label = f"✏️ {var}: {display_value}"
                else:
                    # Truncate if too long
                    display_value = str(current_value)[:20] + '...' if len(str(current_value)) > 20 else str(current_value)
                    button_label = f"{var}: {display_value}"
                
                row.append(InlineKeyboardButton(
                    button_label,
                    callback_data=f"bset_var_{var}"
                ))
            buttons.append(row)
        
        # Add navigation row
        nav_row = [
            InlineKeyboardButton("🔙 Back", callback_data="bset_main"),
            InlineKeyboardButton("💾 Save All", callback_data="bset_save_all"),
            InlineKeyboardButton("❌ Close", callback_data="bset_close")
        ]
        buttons.append(nav_row)
        
        # Page navigation numbers
        page_nav = []
        for i in range(total_pages):
            page_nav.append(InlineKeyboardButton(
                str(i + 1),
                callback_data=f"bset_page_{category}_{i}"
            ))
        buttons.append(page_nav)
        
        keyboard = InlineKeyboardMarkup(buttons)
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    def filter_variables(self, category: str) -> List[str]:
        """Filter variables by category"""
        if category == 'all':
            return self.config_variables
            
        categories = {
            'limits': ['BOT_MAX_TASKS', 'USER_MAX_TASKS', 'DIRECT_LIMIT', 'MEGA_LIMIT',
                      'TORRENT_LIMIT', 'GD_DL_LIMIT', 'RC_DL_LIMIT', 'CLONE_LIMIT',
                      'JD_LIMIT', 'NZB_LIMIT', 'YTDLP_LIMIT', 'PLAYLIST_LIMIT',
                      'LEECH_LIMIT', 'EXTRACT_LIMIT', 'ARCHIVE_LIMIT', 'STORAGE_LIMIT',
                      'QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD'],
            'disable': ['DISABLE_TORRENTS', 'DISABLE_LEECH', 'DISABLE_MIRROR',
                       'DISABLE_BULK', 'DISABLE_MULTI', 'DISABLE_SEED',
                       'DISABLE_FF_MODE', 'DISABLE_JD', 'DISABLE_NZB',
                       'DISABLE_RSS', 'DISABLE_SEARCH', 'DISABLE_STREAM',
                       'DISABLE_YTDLP', 'DISABLE_MEGA'],
            'api': ['FILELION_API', 'STREAMWISH_API', 'ALLDEBRID_API_KEY',
                   'INSTADL_API', 'HYDRA_API_KEY', 'MEGA_EMAIL', 'MEGA_PASSWORD',
                   'SEARCH_API_LINK', 'JD_EMAIL', 'JD_PASS'],
            'upload': ['DEFAULT_UPLOAD', 'AS_DOCUMENT', 'EQUAL_SPLITS', 'MEDIA_GROUP',
                      'LEECH_SPLIT_SIZE', 'LEECH_PREFIX', 'LEECH_SUFFIX',
                      'RCLONE_PATH', 'RCLONE_FLAGS', 'SHOW_CLOUD_LINK'],
            'security': ['FORCE_SUB_IDS', 'MEDIA_STORE', 'DELETE_LINKS',
                        'VERIFY_TIMEOUT', 'LOGIN_PASS', 'AUTHORIZED_CHATS',
                        'SUDO_USERS', 'BOT_PM'],
            'channels': ['UPDATE_CHANNEL', 'REPO_LINK', 'LEECH_DUMP_CHAT',
                        'LINKS_LOG_ID', 'MIRROR_LOG_ID', 'RSS_CHAT']
        }
        
        return categories.get(category, self.config_variables)
    
    async def show_limits_settings(self, callback_query: CallbackQuery):
        """Show limits settings"""
        await self.show_config_variables(callback_query, category='limits')
    
    async def show_disable_settings(self, callback_query: CallbackQuery):
        """Show disable options"""
        await self.show_config_variables(callback_query, category='disable')
    
    async def show_api_settings(self, callback_query: CallbackQuery):
        """Show API keys"""
        await self.show_config_variables(callback_query, category='api')
    
    async def show_upload_settings(self, callback_query: CallbackQuery):
        """Show upload settings"""
        await self.show_config_variables(callback_query, category='upload')
    
    async def show_security_settings(self, callback_query: CallbackQuery):
        """Show security settings"""
        await self.show_config_variables(callback_query, category='security')
    
    async def show_channels_settings(self, callback_query: CallbackQuery):
        """Show channels settings"""
        await self.show_config_variables(callback_query, category='channels')
    
    async def handle_config_edit(self, callback_query: CallbackQuery, variable: str):
        """Handle config variable edit request"""
        # Toggle edit mode
        if variable in self.edit_mode:
            self.edit_mode[variable] = not self.edit_mode[variable]
        else:
            self.edit_mode[variable] = True
            
        # Get current value
        settings = await settings_db.get_settings()
        current_value = settings.get(variable.lower(), getattr(Config, variable, 'N/A'))
        self.temp_values[variable] = current_value
        
        text = f"""
✏️ **Edit Config Variable**

**Variable:** {variable}
**Current Value:** {current_value}

Send me the new value:
`/setvar {variable} <new_value>`

Or click variable button again to cancel edit.
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 Back to Config", callback_data=f"bset_config"),
                InlineKeyboardButton("💾 Save", callback_data=f"bset_save_{variable}")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def save_config_value(self, variable: str, value: str) -> bool:
        """Save config value to database and update Config class"""
        try:
            # Convert value to appropriate type
            original_value = getattr(Config, variable, '')
            
            if isinstance(original_value, bool):
                value = value.lower() == 'true'
            elif isinstance(original_value, int):
                value = int(value)
            elif isinstance(original_value, float):
                value = float(value)
            elif isinstance(original_value, list):
                value = value.split()
            
            # Save to database
            settings = await settings_db.get_settings()
            settings[variable.lower()] = value
            await settings_db.update_settings(settings)
            
            # Update Config class dynamically
            setattr(Config, variable, value)
            
            # Clear edit mode
            self.edit_mode[variable] = False
            self.temp_values.pop(variable, None)
            
            return True
        except Exception as e:
            return False
    
    async def save_all_settings(self, callback_query: CallbackQuery):
        """Save all pending settings"""
        if not self.temp_values:
            await callback_query.answer("No pending changes!", show_alert=True)
            return
        
        success_count = 0
        failed_count = 0
        
        for variable, value in self.temp_values.items():
            if await self.save_config_value(variable, value):
                success_count += 1
            else:
                failed_count += 1
        
        await callback_query.answer(
            f"Saved: {success_count}, Failed: {failed_count}",
            show_alert=True
        )
        
        await self.show_config_variables(callback_query)
    
    async def show_private_files(self, callback_query: CallbackQuery):
        """Show private files management"""
        text = f"""
📁 **Private Files Management**

Upload configuration files:

Current Status:
• rclone.conf: {'✅' if os.path.exists(Config.RCLONE_CONFIG) else '❌'}
• cookies.txt: {'✅' if os.path.exists(os.path.join(Config.CONFIG_DIR, 'cookies.txt')) else '❌'}
• token.json: {'✅' if os.path.exists(os.path.join(Config.CONFIG_DIR, 'token.json')) else '❌'}
• accounts.zip: {'✅' if os.path.exists(os.path.join(Config.CONFIG_DIR, 'accounts.zip')) else '❌'}

Commands:
`/upload rclone` - Upload rclone.conf
`/upload cookies` - Upload cookies.txt
`/upload token` - Upload token.json
`/upload accounts` - Upload accounts.zip
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📄 rclone.conf", callback_data="bset_file_rclone"),
                InlineKeyboardButton("🍪 cookies.txt", callback_data="bset_file_cookies")
            ],
            [
                InlineKeyboardButton("🔑 token.json", callback_data="bset_file_token"),
                InlineKeyboardButton("📦 accounts.zip", callback_data="bset_file_accounts")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="bset_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_aria2_settings(self, callback_query: CallbackQuery):
        """Show Aria2c settings"""
        settings = await settings_db.get_settings()
        aria2_settings = settings.get('aria2_settings', {})
        
        text = f"""
⚡ **Aria2c Settings**

Current configuration:
• Max Connections: {aria2_settings.get('max_connections', 10)}
• Download Speed: {aria2_settings.get('max_download_speed', 'Unlimited')}
• Upload Speed: {aria2_settings.get('max_upload_speed', 'Unlimited')}
• Split: {aria2_settings.get('split', 10)}
• Min Split Size: {aria2_settings.get('min_split_size', '20M')}
• File Allocation: {aria2_settings.get('file_allocation', 'prealloc')}

Commands:
`/setaria2 connections <number>`
`/setaria2 download <speed>`
`/setaria2 upload <speed>`
`/setaria2 split <number>`
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔗 Connections", callback_data="bset_aria2_connections"),
                InlineKeyboardButton("⬇️ Download Speed", callback_data="bset_aria2_download")
            ],
            [
                InlineKeyboardButton("⬆️ Upload Speed", callback_data="bset_aria2_upload"),
                InlineKeyboardButton("🔀 Split", callback_data="bset_aria2_split")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="bset_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_jdownloader_settings(self, callback_query: CallbackQuery):
        """Show JDownloader settings"""
        settings = await settings_db.get_settings()
        jd_settings = settings.get('jd_settings', {})
        
        text = f"""
🔗 **JDownloader Sync**

Current status:
• Email: {'✅ Set' if jd_settings.get('email') else '❌ Not Set'}
• Password: {'✅ Set' if jd_settings.get('password') else '❌ Not Set'}
• Connection: {'✅ Active' if settings.get('jd_connected', False) else '❌ Inactive'}

Commands:
`/setjdemail <email>`
`/setjdpass <password>`
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📧 Set Email", callback_data="bset_jd_email"),
                InlineKeyboardButton("🔑 Set Password", callback_data="bset_jd_pass")
            ],
            [
                InlineKeyboardButton("📊 View Status", callback_data="bset_jd_status"),
                InlineKeyboardButton("🔄 Test", callback_data="bset_jd_test")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="bset_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

# Create instance
bsettings_panel = BotSettingsPanel()

# Command handler
@Client.on_message(filters.command("bsettings") & filters.private)
async def bsettings_command(client: Client, message: Message):
    """Bot settings command"""
    await bsettings_panel.show_main_panel(client, message)

# Callback handlers
@Client.on_callback_query(filters.regex("^bset_"))
async def bsettings_callback(client: Client, callback_query: CallbackQuery):
    """Handle bot settings callbacks"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if not await permission_system.is_admin(user_id):
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    try:
        if data == "bset_main":
            await bsettings_panel.show_main_panel(client, callback_query.message)
            
        elif data == "bset_config":
            await bsettings_panel.show_config_variables(callback_query)
            
        elif data == "bset_files":
            await bsettings_panel.show_private_files(callback_query)
            
        elif data == "bset_aria2":
            await bsettings_panel.show_aria2_settings(callback_query)
            
        elif data == "bset_jd":
            await bsettings_panel.show_jdownloader_settings(callback_query)
            
        elif data == "bset_limits":
            await bsettings_panel.show_limits_settings(callback_query)
            
        elif data == "bset_disable":
            await bsettings_panel.show_disable_settings(callback_query)
            
        elif data == "bset_api":
            await bsettings_panel.show_api_settings(callback_query)
            
        elif data == "bset_upload":
            await bsettings_panel.show_upload_settings(callback_query)
            
        elif data == "bset_security":
            await bsettings_panel.show_security_settings(callback_query)
            
        elif data == "bset_channels":
            await bsettings_panel.show_channels_settings(callback_query)
            
        elif data == "bset_save_all":
            await bsettings_panel.save_all_settings(callback_query)
            
        elif data == "bset_close":
            await callback_query.message.delete()
            
        elif data.startswith("bset_page_"):
            parts = data.split("_")
            category = parts[2] if len(parts) > 3 else 'all'
            page = int(parts[-1])
            await bsettings_panel.show_config_variables(callback_query, page, category)
            
        elif data.startswith("bset_var_"):
            variable = data.replace("bset_var_", "")
            await bsettings_panel.handle_config_edit(callback_query, variable)
            
        elif data.startswith("bset_save_"):
            variable = data.replace("bset_save_", "")
            if variable in bsettings_panel.temp_values:
                value = bsettings_panel.temp_values[variable]
                if await bsettings_panel.save_config_value(variable, str(value)):
                    await callback_query.answer("✅ Saved!", show_alert=True)
                else:
                    await callback_query.answer("❌ Failed!", show_alert=True)
                await bsettings_panel.show_config_variables(callback_query)
            
        elif data == "bset_file_rclone":
            await callback_query.message.edit_text(
                "📄 **Upload rclone.conf:**\n\nReply with `/upload rclone`",
                parse_mode="markdown"
            )
            
        elif data == "bset_file_cookies":
            await callback_query.message.edit_text(
                "🍪 **Upload cookies.txt:**\n\nReply with `/upload cookies`",
                parse_mode="markdown"
            )
            
        elif data == "bset_file_token":
            await callback_query.message.edit_text(
                "🔑 **Upload token.json:**\n\nReply with `/upload token`",
                parse_mode="markdown"
            )
            
        elif data == "bset_file_accounts":
            await callback_query.message.edit_text(
                "📦 **Upload accounts.zip:**\n\nReply with `/upload accounts`",
                parse_mode="markdown"
            )
            
        elif data.startswith("bset_aria2_"):
            action = data.replace("bset_aria2_", "")
            await callback_query.message.edit_text(
                f"⚡ **Set {action}:**\n\nReply with `/setaria2 {action} <value>`",
                parse_mode="markdown"
            )
            
        elif data.startswith("bset_jd_"):
            action = data.replace("bset_jd_", "")
            if action == "email":
                await callback_query.message.edit_text(
                    "📧 **Set JD Email:**\n\nReply with `/setjdemail <email>`",
                    parse_mode="markdown"
                )
            elif action == "pass":
                await callback_query.message.edit_text(
                    "🔑 **Set JD Password:**\n\nReply with `/setjdpass <password>`",
                    parse_mode="markdown"
                )
            elif action == "status":
                await callback_query.answer("Checking status...", show_alert=True)
            elif action == "test":
                await callback_query.answer("Testing connection...", show_alert=True)
                
    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)

# Additional command handlers
@Client.on_message(filters.command("setvar") & filters.private)
async def set_var_command(client: Client, message: Message):
    """Set config variable command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 3:
        await message.reply_text("📝 **Usage:** /setvar <VARIABLE> <value>")
        return
    
    variable = message.command[1].upper()
    value = " ".join(message.command[2:])
    
    # Store in temp values
    bsettings_panel.temp_values[variable] = value
    
    await message.reply_text(
        f"📝 **Value stored!**\n\n"
        f"🔧 Variable: {variable}\n"
        f"📝 Value: {value}\n\n"
        f"Click 'Save All' in panel to apply!",
        parse_mode="markdown"
    )
