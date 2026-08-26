import os
import json
import asyncio
from typing import Dict, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.settings import settings_db
from bot.helpers.permissions import permission_system

class BotSettingsPanel:
    def __init__(self):
        self.config_variables = [
            'AS_DOCUMENT', 'AUTHORIZED_CHATS', 'BASE_URL', 'BASE_URL_PORT',
            'HELPER_TOKENS', 'BOT_MAX_TASKS', 'BOT_PM', 'CMD_SUFFIX',
            'CF_TUNNEL', 'DEFAULT_LANG', 'DEFAULT_UPLOAD', 'DELETE_LINKS',
            'DIRECT_LIMIT', 'DISABLE_TORRENTS', 'DISABLE_LEECH'
        ]
        self.page_size = 10
        self.current_page = {}
        
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

📊 **Current Configuration:**
• Bot: {Config.BOT_USERNAME}
• Max Tasks: {settings.get('bot_max_tasks', Config.BOT_MAX_TASKS)}
• Upload Mode: {settings.get('default_upload', Config.DEFAULT_UPLOAD)}

Select a category:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔧 Config Variables", callback_data="bset_config"),
                InlineKeyboardButton("📁 Private Files", callback_data="bset_files")
            ],
            [
                InlineKeyboardButton("⚡ Aria2c Settings", callback_data="bset_aria2"),
                InlineKeyboardButton("🔗 JDownloader Sync", callback_data="bset_jd")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="bset_back"),
                InlineKeyboardButton("❌ Close", callback_data="bset_close")
            ]
        ])
        
        await message.reply_text(panel_text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_config_variables(self, callback_query: CallbackQuery, page: int = 0):
        """Show config variables with pagination"""
        total_pages = (len(self.config_variables) + self.page_size - 1) // self.page_size
        page = max(0, min(page, total_pages - 1))
        
        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.config_variables))
        page_variables = self.config_variables[start_idx:end_idx]
        
        # Get current values
        settings = await settings_db.get_settings()
        
        text = f"""
🔧 **Config Variables** (Page {page + 1}/{total_pages})

Click on a variable to edit its value:
"""
        
        # Create buttons (2 per row)
        buttons = []
        for i in range(0, len(page_variables), 2):
            row = []
            for var in page_variables[i:i+2]:
                # Get current value
                current_value = settings.get(var.lower(), getattr(Config, var, 'N/A'))
                # Truncate if too long
                display_value = str(current_value)[:15] + '...' if len(str(current_value)) > 15 else str(current_value)
                
                button_label = f"{var}={display_value}"
                row.append(InlineKeyboardButton(
                    button_label,
                    callback_data=f"bset_var_{var}"
                ))
            buttons.append(row)
        
        # Add Edit button if odd number
        if len(page_variables) % 2 != 0:
            buttons[-1].append(InlineKeyboardButton(
                "Edit",
                callback_data=f"bset_var_{page_variables[-1]}"
            ))
        
        # Add navigation row
        nav_row = [
            InlineKeyboardButton("🔙 Back", callback_data="bset_main"),
            InlineKeyboardButton("❌ Close", callback_data="bset_close")
        ]
        buttons.append(nav_row)
        
        # Page navigation numbers
        page_nav = []
        for i in range(total_pages):
            page_nav.append(InlineKeyboardButton(
                str(i + 1),
                callback_data=f"bset_page_{i}"
            ))
        buttons.append(page_nav)
        
        keyboard = InlineKeyboardMarkup(buttons)
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_private_files(self, callback_query: CallbackQuery):
        """Show private files management"""
        text = f"""
📁 **Private Files Management**

Upload configuration files to manage bot:

**Files to upload:**
• rclone.conf - Cloud storage config
• cookies.txt - YT-DLP cookies
• token.json - Google Drive token
• accounts.zip - Service accounts

Reply with file and command:
`/upload rclone` - Upload rclone.conf
`/upload cookies` - Upload cookies.txt
`/upload token` - Upload token.json
`/upload accounts` - Upload accounts.zip

Current files:
• rclone.conf: {'✅' if os.path.exists(Config.RCLONE_CONFIG) else '❌'}
• cookies.txt: {'✅' if os.path.exists(os.path.join(Config.CONFIG_DIR, 'cookies.txt')) else '❌'}
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
• Download Speed Limit: {aria2_settings.get('max_download_speed', 'Unlimited')}
• Upload Speed Limit: {aria2_settings.get('max_upload_speed', 'Unlimited')}
• Split: {aria2_settings.get('split', 10)}

Select setting to modify:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔗 Max Connections", callback_data="bset_aria2_connections"),
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
        jd_email = jd_settings.get('email', Config.JD_EMAIL)
        jd_pass = jd_settings.get('password', Config.JD_PASS)
        
        text = f"""
🔗 **JDownloader Sync**

Current status:
• Email: {'✅ Set' if jd_email else '❌ Not Set'}
• Password: {'✅ Set' if jd_pass else '❌ Not Set'}
• Connection: {'✅ Active' if settings.get('jd_connected', False) else '❌ Inactive'}

Select option:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📧 Set JD Email", callback_data="bset_jd_email"),
                InlineKeyboardButton("🔑 Set JD Password", callback_data="bset_jd_pass")
            ],
            [
                InlineKeyboardButton("📊 View Status", callback_data="bset_jd_status"),
                InlineKeyboardButton("🔄 Test Connection", callback_data="bset_jd_test")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="bset_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def handle_config_edit(self, callback_query: CallbackQuery, variable: str):
        """Handle config variable edit request"""
        text = f"""
✏️ **Edit Config Variable**

**Variable:** {variable}

**Current Value:** {getattr(Config, variable, 'N/A')}

Send me the new value for this variable.

Reply with:
`/setvar {variable} <new_value>`

Example:
`/setvar BOT_MAX_TASKS 100`

⚠️ Changes will apply instantly without restart!
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Config", callback_data="bset_config")]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def save_config_value(self, variable: str, value: str) -> bool:
        """Save config value to database and update Config class"""
        try:
            # Convert value to appropriate type
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
            
            # Save to database
            settings = await settings_db.get_settings()
            settings[variable.lower()] = value
            await settings_db.update_settings(settings)
            
            # Update Config class dynamically
            setattr(Config, variable, value)
            
            return True
        except:
            return False
    
    async def handle_file_upload(self, client: Client, message: Message, file_type: str):
        """Handle private file upload"""
        if not message.reply_to_message or not message.reply_to_message.document:
            await message.reply_text("❌ **Reply to a file with the command!**")
            return
        
        file_commands = {
            'rclone': ('rclone.conf', Config.RCLONE_CONFIG),
            'cookies': ('cookies.txt', os.path.join(Config.CONFIG_DIR, 'cookies.txt')),
            'token': ('token.json', os.path.join(Config.CONFIG_DIR, 'token.json')),
            'accounts': ('accounts.zip', os.path.join(Config.CONFIG_DIR, 'accounts.zip')),
        }
        
        if file_type not in file_commands:
            await message.reply_text("❌ **Invalid file type!**")
            return
        
        file_name, file_path = file_commands[file_type]
        
        status_msg = await message.reply_text(f"📥 **Downloading {file_name}...**")
        
        try:
            # Download file
            downloaded_path = await message.reply_to_message.download()
            
            # Move to config directory
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            os.rename(downloaded_path, file_path)
            
            await status_msg.edit_text(
                f"✅ **{file_name} uploaded successfully!**\n\n"
                f"📁 Location: {file_path}\n"
                f"🔄 Reloading engine..."
            )
            
            # Reload engine (restart bot for changes to take effect)
            await asyncio.sleep(2)
            
            # Trigger restart
            import sys
            os.execv(sys.executable, [sys.executable, "-m", "bot"])
            
        except Exception as e:
            await status_msg.edit_text(f"❌ **Error:** {str(e)}")
    
    async def update_aria2_settings(self, setting_type: str, value):
        """Update Aria2 settings via JSON-RPC"""
        try:
            import aria2p
            
            aria2 = aria2p.API(
                aria2p.Client(
                    host=Config.ARIA2_HOST,
                    port=Config.ARIA2_PORT,
                    secret=Config.ARIA2_SECRET
                )
            )
            
            if setting_type == 'connections':
                await aria2.set_global_options({'max-concurrent-downloads': str(value)})
            elif setting_type == 'download_speed':
                await aria2.set_global_options({'max-download-limit': str(value)})
            elif setting_type == 'upload_speed':
                await aria2.set_global_options({'max-upload-limit': str(value)})
            elif setting_type == 'split':
                await aria2.set_global_options({'split': str(value)})
                
            # Save to database
            settings = await settings_db.get_settings()
            if 'aria2_settings' not in settings:
                settings['aria2_settings'] = {}
            
            key_map = {
                'connections': 'max_connections',
                'download_speed': 'max_download_speed',
                'upload_speed': 'max_upload_speed',
                'split': 'split'
            }
            
            settings['aria2_settings'][key_map[setting_type]] = value
            await settings_db.update_settings(settings)
            
            return True
        except Exception as e:
            return False
    
    async def test_jdownloader(self) -> Dict:
        """Test JDownloader connection"""
        try:
            from bot.modules.jdownloader import jdownloader
            
            if not jdownloader.connected:
                await jdownloader.connect()
                
            if jdownloader.connected:
                status = await jdownloader.get_status()
                return {'success': True, 'status': status}
            else:
                return {'success': False, 'error': 'Connection failed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

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
            
        elif data == "bset_back":
            await bsettings_panel.show_main_panel(client, callback_query.message)
            
        elif data == "bset_close":
            await callback_query.message.delete()
            
        elif data.startswith("bset_page_"):
            page = int(data.split("_")[2])
            await bsettings_panel.show_config_variables(callback_query, page)
            
        elif data.startswith("bset_var_"):
            variable = data.replace("bset_var_", "")
            await bsettings_panel.handle_config_edit(callback_query, variable)
            
        elif data == "bset_file_rclone":
            await callback_query.message.edit_text(
                "📄 **Upload rclone.conf:**\n\n"
                "Reply to rclone.conf file with:\n"
                "`/upload rclone`",
                parse_mode="markdown"
            )
            
        elif data == "bset_file_cookies":
            await callback_query.message.edit_text(
                "🍪 **Upload cookies.txt:**\n\n"
                "Reply to cookies.txt file with:\n"
                "`/upload cookies`",
                parse_mode="markdown"
            )
            
        elif data == "bset_file_token":
            await callback_query.message.edit_text(
                "🔑 **Upload token.json:**\n\n"
                "Reply to token.json file with:\n"
                "`/upload token`",
                parse_mode="markdown"
            )
            
        elif data == "bset_file_accounts":
            await callback_query.message.edit_text(
                "📦 **Upload accounts.zip:**\n\n"
                "Reply to accounts.zip file with:\n"
                "`/upload accounts`",
                parse_mode="markdown"
            )
            
        elif data == "bset_aria2_connections":
            await callback_query.message.edit_text(
                "🔗 **Set Max Connections:**\n\n"
                "Reply with:\n"
                "`/setaria2 connections <number>`",
                parse_mode="markdown"
            )
            
        elif data == "bset_aria2_download":
            await callback_query.message.edit_text(
                "⬇️ **Set Download Speed Limit:**\n\n"
                "Reply with:\n"
                "`/setaria2 download <speed>`\n"
                "Example: 10M, 5M, 0 (unlimited)",
                parse_mode="markdown"
            )
            
        elif data == "bset_aria2_upload":
            await callback_query.message.edit_text(
                "⬆️ **Set Upload Speed Limit:**\n\n"
                "Reply with:\n"
                "`/setaria2 upload <speed>`\n"
                "Example: 5M, 2M, 0 (unlimited)",
                parse_mode="markdown"
            )
            
        elif data == "bset_aria2_split":
            await callback_query.message.edit_text(
                "🔀 **Set Split Count:**\n\n"
                "Reply with:\n"
                "`/setaria2 split <number>`",
                parse_mode="markdown"
            )
            
        elif data == "bset_jd_email":
            await callback_query.message.edit_text(
                "📧 **Set JD Email:**\n\n"
                "Reply with:\n"
                "`/setjdemail <email>`",
                parse_mode="markdown"
            )
            
        elif data == "bset_jd_pass":
            await callback_query.message.edit_text(
                "🔑 **Set JD Password:**\n\n"
                "Reply with:\n"
                "`/setjdpass <password>`",
                parse_mode="markdown"
            )
            
        elif data == "bset_jd_status":
            result = await bsettings_panel.test_jdownloader()
            if result['success']:
                await callback_query.answer("✅ JDownloader connected!", show_alert=True)
            else:
                await callback_query.answer(f"❌ {result['error']}", show_alert=True)
                
        elif data == "bset_jd_test":
            await callback_query.answer("Testing connection...", show_alert=True)
            result = await bsettings_panel.test_jdownloader()
            if result['success']:
                await callback_query.answer("✅ Connection successful!", show_alert=True)
            else:
                await callback_query.answer(f"❌ {result['error']}", show_alert=True)
                
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
    
    if await bsettings_panel.save_config_value(variable, value):
        await message.reply_text(
            f"✅ **Config updated!**\n\n"
            f"🔧 Variable: {variable}\n"
            f"📝 New Value: {value}",
            parse_mode="markdown"
        )
    else:
        await message.reply_text("❌ **Failed to update config!**")

@Client.on_message(filters.command("upload") & filters.private)
async def upload_file_command(client: Client, message: Message):
    """Upload private file command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/upload rclone - Upload rclone.conf\n"
            "/upload cookies - Upload cookies.txt\n"
            "/upload token - Upload token.json\n"
            "/upload accounts - Upload accounts.zip",
            parse_mode="markdown"
        )
        return
    
    file_type = message.command[1].lower()
    await bsettings_panel.handle_file_upload(client, message, file_type)

@Client.on_message(filters.command("setaria2") & filters.private)
async def set_aria2_command(client: Client, message: Message):
    """Set Aria2 settings command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 3:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/setaria2 connections <number>\n"
            "/setaria2 download <speed>\n"
            "/setaria2 upload <speed>\n"
            "/setaria2 split <number>",
            parse_mode="markdown"
        )
        return
    
    setting_type = message.command[1].lower()
    value = message.command[2]
    
    if await bsettings_panel.update_aria2_settings(setting_type, value):
        await message.reply_text(f"✅ **Aria2 setting updated!**")
    else:
        await message.reply_text("❌ **Failed to update Aria2 setting!**")

@Client.on_message(filters.command("setjdemail") & filters.private)
async def set_jd_email_command(client: Client, message: Message):
    """Set JD email command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /setjdemail <email>")
        return
    
    email = message.command[1]
    settings = await settings_db.get_settings()
    
    if 'jd_settings' not in settings:
        settings['jd_settings'] = {}
    settings['jd_settings']['email'] = email
    
    await settings_db.update_settings(settings)
    Config.JD_EMAIL = email
    
    await message.reply_text("✅ **JD Email set!**")

@Client.on_message(filters.command("setjdpass") & filters.private)
async def set_jd_pass_command(client: Client, message: Message):
    """Set JD password command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /setjdpass <password>")
        return
    
    password = message.command[1]
    settings = await settings_db.get_settings()
    
    if 'jd_settings' not in settings:
        settings['jd_settings'] = {}
    settings['jd_settings']['password'] = password
    
    await settings_db.update_settings(settings)
    Config.JD_PASS = password
    
    await message.reply_text("✅ **JD Password set!**")
