import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.settings import settings_db
from bot.helpers.permissions import permission_system

class BotSettingsComplete:
    def __init__(self):
        self.config_pages = {
            1: ['LEECH_LIMIT'],
            2: ['JD_LIMIT'],
            3: ['YTDLP_LIMIT'],
            4: ['VT_ENABLED'],
            5: ['AUTHORIZED_CHATS'],
            6: ['SUDO_USERS'],
            7: ['QUEUE_DOWNLOAD'],
            8: ['QUEUE_UPLOAD'],
            9: ['MAX_CONCURRENT_DOWNLOADS'],
            10: ['MAX_CONCURRENT_UPLOADS'],
            11: ['MAX_TORRENT_SIZE'],
            12: ['DEFAULT_SPLIT_SIZE'],
            13: ['SESSION_SPLIT_SIZE'],
            14: ['DEFAULT_UPLOAD_SPEED'],
            15: ['SESSION_UPLOAD_SPEED']
        }
        
        self.aria2_pages = {
            1: ['DOWNLOAD_PATH'],
            2: ['MAX_CONNECTIONS'],
            3: ['SPEED_LIMIT'],
            4: ['RETRY_COUNT'],
            5: ['TIMEOUT']
        }
    
    async def show_main_menu(self, callback_query: CallbackQuery):
        """Show main bot settings menu"""
        user_id = callback_query.from_user.id
        
        if not await permission_system.is_admin(user_id):
            await callback_query.answer("❌ Admin only!", show_alert=True)
            return
        
        text = f"""
🔧 **Bot Settings**

Select a category:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚙️ Configure Variables", callback_data="bset_config_page_1"),
                InlineKeyboardButton("📥 Aria2 Settings", callback_data="bset_aria2_page_1")
            ],
            [
                InlineKeyboardButton("🔒 Private Files", callback_data="bset_private"),
                InlineKeyboardButton("📡 JD Account", callback_data="bset_jd")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="bset_close")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_config_page(self, callback_query: CallbackQuery, page: int):
        """Show configure variables page"""
        variables = self.config_pages.get(page, [])
        
        text = f"""
⚙️ **Configure Variables** (Page {page}/15)

Variables:
"""
        for var in variables:
            value = getattr(Config, var, 'N/A')
            text += f"• {var}: {value}\n"
        
        text += "\nClick variable to edit:"
        
        buttons = []
        for var in variables:
            buttons.append([InlineKeyboardButton(f"✏️ {var}", callback_data=f"bset_edit_{var}")])
        
        # Navigation
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"bset_config_page_{page-1}"))
        if page < 15:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"bset_config_page_{page+1}"))
        buttons.append(nav_row)
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="bset_main")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_aria2_page(self, callback_query: CallbackQuery, page: int):
        """Show Aria2 settings page"""
        variables = self.aria2_pages.get(page, [])
        
        text = f"""
📥 **Aria2 Settings** (Page {page}/5)

Settings:
"""
        for var in variables:
            value = getattr(Config, var, 'N/A')
            text += f"• {var}: {value}\n"
        
        buttons = []
        for var in variables:
            buttons.append([InlineKeyboardButton(f"✏️ {var}", callback_data=f"bset_aria2_edit_{var}")])
        
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"bset_aria2_page_{page-1}"))
        if page < 5:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"bset_aria2_page_{page+1}"))
        buttons.append(nav_row)
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="bset_main")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_private_files(self, callback_query: CallbackQuery):
        """Show private files"""
        text = f"""
🔒 **Private Files**

• Cookies: {'✅' if os.path.exists(os.path.join(Config.CONFIG_DIR, 'cookies.txt')) else '❌'}
• Token.pickle: {'✅' if os.path.exists(os.path.join(Config.CONFIG_DIR, 'token.pickle')) else '❌'}
• Rclone Config: {'✅' if os.path.exists(Config.RCLONE_CONFIG) else '❌'}

Upload commands:
/uploadcookies - Upload cookies
/uploadtoken - Upload token
/uploadrclone - Upload rclone config
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍪 Cookies", callback_data="bset_priv_cookies"),
                InlineKeyboardButton("🔑 Token", callback_data="bset_priv_token")
            ],
            [
                InlineKeyboardButton("☁️ Rclone", callback_data="bset_priv_rclone"),
                InlineKeyboardButton("🔙 Back", callback_data="bset_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_jd_account(self, callback_query: CallbackQuery):
        """Show JD Account settings"""
        settings = await settings_db.get_settings()
        jd_email = settings.get('jd_email', '')
        jd_pass = settings.get('jd_password', '')
        
        text = f"""
📡 **JD Account**

• Email: {'✅ Set' if jd_email else '❌ Not Set'}
• Password: {'✅ Set' if jd_pass else '❌ Not Set'}

Commands:
/setjdemail <email> - Set email
/setjdpass <password> - Set password
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📧 Set Email", callback_data="bset_jd_email"),
                InlineKeyboardButton("🔑 Set Password", callback_data="bset_jd_pass")
            ],
            [
                InlineKeyboardButton("💾 Save", callback_data="bset_jd_save"),
                InlineKeyboardButton("🗑 Delete", callback_data="bset_jd_delete")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="bset_main")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

# Create instance
bot_settings_complete = BotSettingsComplete()

@Client.on_message(filters.command("bsetting") & filters.private)
async def bsetting_command(client: Client, message: Message):
    """Bot settings command"""
    await bot_settings_complete.show_main_menu(message)

@Client.on_callback_query(filters.regex("^bset_"))
async def bsettings_callback(client: Client, callback_query: CallbackQuery):
    """Handle bot settings callbacks"""
    data = callback_query.data
    
    if data == "bset_main":
        await bot_settings_complete.show_main_menu(callback_query)
    elif data.startswith("bset_config_page_"):
        page = int(data.split("_")[-1])
        await bot_settings_complete.show_config_page(callback_query, page)
    elif data.startswith("bset_aria2_page_"):
        page = int(data.split("_")[-1])
        await bot_settings_complete.show_aria2_page(callback_query, page)
    elif data == "bset_private":
        await bot_settings_complete.show_private_files(callback_query)
    elif data == "bset_jd":
        await bot_settings_complete.show_jd_account(callback_query)
    elif data == "bset_close":
        await callback_query.message.delete()
    
    await callback_query.answer()
