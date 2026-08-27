import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.users import users_db
from bot.database.settings import settings_db
from bot.helpers.permissions import permission_system

class UserSettingsComplete:
    def __init__(self):
        self.default_settings = {
            'leech': {
                'split_size': 2 * 1024 * 1024 * 1024,  # 2GB
                'queue_download': 10,
                'leech_limit': 4 * 1024 * 1024 * 1024,  # 4GB
                'download_path': 'downloads/'
            },
            'general': {
                'upload_speed': 10,  # MB/s
                'vt_enabled': True,
                'queue_upload': 5,
                'language': 'English'
            },
            'private': {
                'cookies': None,
                'token_pickle': None,
                'gofile_api': None,
                'pixeldrain_api': None,
                'rclone_config': None,
                'shortner_config': None
            }
        }
    
    async def get_settings(self, user_id: int) -> dict:
        """Get user settings"""
        settings = await users_db.get_user_settings(user_id)
        if not settings:
            settings = self.default_settings.copy()
            await users_db.update_user_settings(user_id, settings)
        return settings
    
    async def show_leech_settings(self, callback_query: CallbackQuery):
        """Show Leech Settings"""
        user_id = callback_query.from_user.id
        settings = await self.get_settings(user_id)
        leech = settings.get('leech', {})
        
        text = f"""
📥 **Leech Settings**

• Split Size: {leech.get('split_size', 2*1024*1024*1024) // (1024*1024*1024)} GB
• Queue Download: {leech.get('queue_download', 10)}
• Leech Limit: {leech.get('leech_limit', 4*1024*1024*1024) // (1024*1024*1024)} GB
• Download Path: {leech.get('download_path', 'downloads/')}

Select option to change:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📦 Split Size", callback_data="uleech_split"),
                InlineKeyboardButton("⬇️ Queue Download", callback_data="uleech_queue")
            ],
            [
                InlineKeyboardButton("📊 Leech Limit", callback_data="uleech_limit"),
                InlineKeyboardButton("📁 Download Path", callback_data="uleech_path")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="usettings_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_general_settings(self, callback_query: CallbackQuery):
        """Show General Settings"""
        user_id = callback_query.from_user.id
        settings = await self.get_settings(user_id)
        general = settings.get('general', {})
        
        text = f"""
⚙️ **General Settings**

• Upload Speed: {general.get('upload_speed', 10)} MB/s
• VT Enabled: {'✅ On' if general.get('vt_enabled', True) else '❌ Off'}
• Queue Upload: {general.get('queue_upload', 5)}
• Language: {general.get('language', 'English')}

Select option to change:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬆️ Upload Speed", callback_data="ugen_speed"),
                InlineKeyboardButton("🎬 VT Converter", callback_data="ugen_vt")
            ],
            [
                InlineKeyboardButton("📤 Queue Upload", callback_data="ugen_queue"),
                InlineKeyboardButton("🌐 Language", callback_data="ugen_lang")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="usettings_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_private_files(self, callback_query: CallbackQuery):
        """Show Private Files"""
        user_id = callback_query.from_user.id
        settings = await self.get_settings(user_id)
        private = settings.get('private', {})
        
        text = f"""
🔒 **Private Files**

• Cookies: {'✅ Set' if private.get('cookies') else '❌ Not Set'}
• Token.pickle: {'✅ Set' if private.get('token_pickle') else '❌ Not Set'}
• Gofile API: {'✅ Set' if private.get('gofile_api') else '❌ Not Set'}
• Pixeldrain API: {'✅ Set' if private.get('pixeldrain_api') else '❌ Not Set'}
• Rclone Config: {'✅ Set' if private.get('rclone_config') else '❌ Not Set'}
• Shortner Config: {'✅ Set' if private.get('shortner_config') else '❌ Not Set'}

Upload or set:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍪 Cookies", callback_data="upriv_cookies"),
                InlineKeyboardButton("🔑 Token", callback_data="upriv_token")
            ],
            [
                InlineKeyboardButton("📁 Gofile API", callback_data="upriv_gofile"),
                InlineKeyboardButton("📁 Pixeldrain", callback_data="upriv_pixeldrain")
            ],
            [
                InlineKeyboardButton("☁️ Rclone", callback_data="upriv_rclone"),
                InlineKeyboardButton("🔗 Shortner", callback_data="upriv_shortner")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="usettings_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_main_menu(self, callback_query: CallbackQuery):
        """Show main user settings menu"""
        text = f"""
⚙️ **User Settings**

Select a category:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📥 Leech Settings", callback_data="usettings_leech"),
                InlineKeyboardButton("⚙️ General Settings", callback_data="usettings_general")
            ],
            [
                InlineKeyboardButton("🔒 Private Files", callback_data="usettings_private")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="usettings_close")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

# Create instance
user_settings_complete = UserSettingsComplete()

@Client.on_message(filters.command("usetting") & filters.private)
async def usetting_command(client: Client, message: Message):
    """User settings command"""
    await user_settings_complete.show_main_menu(message)

@Client.on_callback_query(filters.regex("^usettings_"))
async def usettings_callback(client: Client, callback_query: CallbackQuery):
    """Handle user settings callbacks"""
    data = callback_query.data
    
    if data == "usettings_leech":
        await user_settings_complete.show_leech_settings(callback_query)
    elif data == "usettings_general":
        await user_settings_complete.show_general_settings(callback_query)
    elif data == "usettings_private":
        await user_settings_complete.show_private_files(callback_query)
    elif data == "usettings_close":
        await callback_query.message.delete()
    elif data == "usettings_main":
        await user_settings_complete.show_main_menu(callback_query)
    
    await callback_query.answer()
