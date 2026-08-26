import os
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.users import users_db
from bot.database.settings import settings_db
from bot.database.tasks import tasks_db
from bot.helpers.progress import Progress

progress_helper = Progress()

class UserSettings:
    def __init__(self):
        self.default_settings = {
            'upload_mode': 'document',
            'ai_caption': False,
            'smart_organizer': False,
            'custom_thumbnail': None,
            'nsfw_filter': True,
            'metadata_settings': {
                'save_history': True,
                'show_in_stats': True,
                'delete_links': False
            },
            'misc_settings': {
                'progress_style': 'block',
                'caption_template': None,
                'language': 'en'
            }
        }
    
    async def get_user_settings(self, user_id: int) -> dict:
        """Get user settings with defaults"""
        settings = await users_db.get_user_settings(user_id)
        if not settings:
            settings = self.default_settings.copy()
            await users_db.update_user_settings(user_id, settings)
        return settings
    
    async def update_setting(self, user_id: int, key: str, value):
        """Update specific user setting"""
        settings = await self.get_user_settings(user_id)
        settings[key] = value
        await users_db.update_user_settings(user_id, settings)
        return settings
    
    async def toggle_setting(self, user_id: int, key: str) -> bool:
        """Toggle boolean setting"""
        settings = await self.get_user_settings(user_id)
        current = settings.get(key, False)
        settings[key] = not current
        await users_db.update_user_settings(user_id, settings)
        return settings[key]

class UserSettingsPanel:
    def __init__(self):
        self.usettings = UserSettings()
    
    async def show_main_panel(self, client: Client, message: Message):
        """Show main user settings panel"""
        user = message.from_user
        settings = await self.usettings.get_user_settings(user.id)
        
        # Get user stats for storage info
        user_data = await users_db.get_user(user.id)
        user_tasks = await tasks_db.get_user_tasks(user.id, 100)
        
        panel_text = f"""
⚙️ **User Settings Panel**

👤 **User:** {user.first_name}
🆔 **ID:** {user.id}

📊 **Current Settings:**
• Upload Mode: `{settings.get('upload_mode', 'document')}`
• AI Caption: `{'✅ ON' if settings.get('ai_caption') else '❌ OFF'}`
• Smart Organizer: `{'✅ ON' if settings.get('smart_organizer') else '❌ OFF'}`
• NSFW Filter: `{'✅ ON' if settings.get('nsfw_filter', True) else '❌ OFF'}`

💾 **Storage Used:** {len(user_tasks)} tasks in history

Select a category:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚙️ General Settings", callback_data="uset_general")
            ],
            [
                InlineKeyboardButton("📥 Mirror Settings", callback_data="uset_mirror"),
                InlineKeyboardButton("📤 Leech Settings", callback_data="uset_leech")
            ],
            [
                InlineKeyboardButton("🤖 AI Caption Settings", callback_data="uset_ai_caption"),
                InlineKeyboardButton("📁 Smart Organizer", callback_data="uset_organizer")
            ],
            [
                InlineKeyboardButton("🎨 Custom Thumbnail", callback_data="uset_thumbnail"),
                InlineKeyboardButton("🛡 NSFW Filter", callback_data="uset_nsfw")
            ],
            [
                InlineKeyboardButton("📝 Metadata Settings", callback_data="uset_metadata"),
                InlineKeyboardButton("🔧 Misc Settings", callback_data="uset_misc")
            ],
            [
                InlineKeyboardButton("💾 Storage & Plan", callback_data="uset_storage")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="uset_close")
            ]
        ])
        
        await message.reply_text(panel_text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_general_settings(self, callback_query: CallbackQuery):
        """Show general settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        
        text = f"""
⚙️ **General Settings**

📤 **Upload Mode:** {settings.get('upload_mode', 'document')}

Select upload mode:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📄 Document", callback_data="uset_mode_document"),
                InlineKeyboardButton("🎬 Video", callback_data="uset_mode_video")
            ],
            [
                InlineKeyboardButton("🎵 Audio", callback_data="uset_mode_audio"),
                InlineKeyboardButton("📸 Photo", callback_data="uset_mode_photo")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_mirror_settings(self, callback_query: CallbackQuery):
        """Show mirror settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        
        mirror_settings = settings.get('mirror_settings', {})
        
        text = f"""
📥 **Mirror Settings**

• Default Upload: {mirror_settings.get('default_upload', 'rc')}
• Auto Delete: {mirror_settings.get('auto_delete', False)}
• Stop Duplicate: {mirror_settings.get('stop_duplicate', False)}

Select option:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Upload Mode", callback_data="uset_mirror_upload"),
                InlineKeyboardButton("Auto Delete", callback_data="uset_mirror_autodel")
            ],
            [
                InlineKeyboardButton("Stop Duplicate", callback_data="uset_mirror_dup"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_leech_settings(self, callback_query: CallbackQuery):
        """Show leech settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        
        leech_settings = settings.get('leech_settings', {})
        
        text = f"""
📤 **Leech Settings**

• Split Size: {leech_settings.get('split_size', '2GB')}
• As Document: {leech_settings.get('as_document', False)}
• Media Group: {leech_settings.get('media_group', False)}

Select option:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Split Size", callback_data="uset_leech_split"),
                InlineKeyboardButton("As Document", callback_data="uset_leech_doc")
            ],
            [
                InlineKeyboardButton("Media Group", callback_data="uset_leech_group"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_ai_caption_settings(self, callback_query: CallbackQuery):
        """Show AI caption settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        ai_enabled = settings.get('ai_caption', False)
        
        text = f"""
🤖 **AI Caption Settings**

• Status: {'✅ Enabled' if ai_enabled else '❌ Disabled'}

**What AI Caption does:**
- Auto detects file type
- Generates smart captions
- Adds quality info
- Includes category tags

Toggle AI caption:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Enable AI Caption" if not ai_enabled else "❌ Disable AI Caption",
                    callback_data="uset_ai_toggle"
                )
            ],
            [
                InlineKeyboardButton("📝 Custom Format", callback_data="uset_ai_format"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_organizer_settings(self, callback_query: CallbackQuery):
        """Show smart organizer settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        organizer_enabled = settings.get('smart_organizer', False)
        
        text = f"""
📁 **Smart Organizer Settings**

• Status: {'✅ Enabled' if organizer_enabled else '❌ Disabled'}

**What Smart Organizer does:**
- Auto sorts files by type
- Creates category folders
- Movies, Books, Documents
- Removes duplicates

Toggle organizer:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Enable Organizer" if not organizer_enabled else "❌ Disable Organizer",
                    callback_data="uset_org_toggle"
                )
            ],
            [
                InlineKeyboardButton("📂 Categories", callback_data="uset_org_categories"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_thumbnail_settings(self, callback_query: CallbackQuery):
        """Show custom thumbnail settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        has_thumbnail = settings.get('custom_thumbnail') is not None
        
        text = f"""
🎨 **Custom Thumbnail Settings**

• Status: {'✅ Set' if has_thumbnail else '❌ Not Set'}

**How to set:**
1. Send me an image
2. Reply with /setthumb
3. Done!

Options:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🖼 Set Thumbnail", callback_data="uset_thumb_set"),
                InlineKeyboardButton("🗑 Remove", callback_data="uset_thumb_remove")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_nsfw_settings(self, callback_query: CallbackQuery):
        """Show NSFW filter settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        nsfw_enabled = settings.get('nsfw_filter', True)
        
        text = f"""
🛡 **NSFW Filter Settings**

• Status: {'✅ Enabled' if nsfw_enabled else '❌ Disabled'}

**What NSFW Filter does:**
- Blocks 18+ content
- Filters explicit material
- Protects your group
- Auto moderation

Toggle NSFW filter:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Enable Filter" if not nsfw_enabled else "❌ Disable Filter",
                    callback_data="uset_nsfw_toggle"
                )
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_metadata_settings(self, callback_query: CallbackQuery):
        """Show metadata settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        metadata = settings.get('metadata_settings', {})
        
        text = f"""
📝 **Metadata Settings**

• Save History: {'✅' if metadata.get('save_history', True) else '❌'}
• Show in Stats: {'✅' if metadata.get('show_in_stats', True) else '❌'}
• Delete Links: {'✅' if metadata.get('delete_links', False) else '❌'}

Select option:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Save History", callback_data="uset_meta_history"),
                InlineKeyboardButton("Show in Stats", callback_data="uset_meta_stats")
            ],
            [
                InlineKeyboardButton("Delete Links", callback_data="uset_meta_links"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_misc_settings(self, callback_query: CallbackQuery):
        """Show miscellaneous settings"""
        user_id = callback_query.from_user.id
        settings = await self.usettings.get_user_settings(user_id)
        misc = settings.get('misc_settings', {})
        
        text = f"""
🔧 **Miscellaneous Settings**

• Progress Style: {misc.get('progress_style', 'block')}
• Language: {misc.get('language', 'en')}
• Caption Template: {'Custom' if misc.get('caption_template') else 'Default'}

Select option:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Progress Style", callback_data="uset_misc_progress"),
                InlineKeyboardButton("Language", callback_data="uset_misc_lang")
            ],
            [
                InlineKeyboardButton("Caption Template", callback_data="uset_misc_caption"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    
    async def show_storage_plan(self, callback_query: CallbackQuery):
        """Show storage and plan information"""
        user_id = callback_query.from_user.id
        user_data = await users_db.get_user(user_id)
        user_tasks = await tasks_db.get_user_tasks(user_id, 1000)
        
        # Calculate storage
        total_size = sum(task.get('file_size', 0) for task in user_tasks)
        completed = sum(1 for t in user_tasks if t.get('status') == 'completed')
        failed = sum(1 for t in user_tasks if t.get('status') == 'failed')
        
        # Get plan info
        is_premium = user_data.get('is_premium', False)
        plan = user_data.get('premium_plan', 'Free')
        premium_expiry = user_data.get('premium_expiry', 0)
        
        if premium_expiry:
            days_left = max(0, (premium_expiry - time.time()) // (24 * 3600))
        else:
            days_left = 0
        
        text = f"""
💾 **Storage & Plan**

👤 **User:** {user_data.get('first_name', 'Unknown')}

📊 **Plan:** {'💎 Premium' if is_premium else '🆓 Free'}
{'⏰ Days Left: ' + str(int(days_left)) if is_premium else ''}

📈 **Statistics:**
• Total Tasks: {len(user_tasks)}
• Completed: {completed}
• Failed: {failed}
• Success Rate: {(completed / len(user_tasks) * 100) if user_tasks else 0:.1f}%

💾 **Storage Used:** {progress_helper.format_size(total_size)}

📦 **Task History:** {len(user_tasks)} files
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💎 Upgrade to Premium", callback_data="uset_upgrade"),
                InlineKeyboardButton("🔙 Back", callback_data="uset_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")

# Create instances
user_settings = UserSettings()
settings_panel = UserSettingsPanel()

# Command handler
@Client.on_message(filters.command("usettings") & filters.private)
async def usettings_command(client: Client, message: Message):
    """User settings command"""
    await settings_panel.show_main_panel(client, message)

# Callback handlers
@Client.on_callback_query(filters.regex("^uset_"))
async def usettings_callback(client: Client, callback_query: CallbackQuery):
    """Handle user settings callbacks"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    try:
        if data == "uset_general":
            await settings_panel.show_general_settings(callback_query)
            
        elif data == "uset_mirror":
            await settings_panel.show_mirror_settings(callback_query)
            
        elif data == "uset_leech":
            await settings_panel.show_leech_settings(callback_query)
            
        elif data == "uset_ai_caption":
            await settings_panel.show_ai_caption_settings(callback_query)
            
        elif data == "uset_organizer":
            await settings_panel.show_organizer_settings(callback_query)
            
        elif data == "uset_thumbnail":
            await settings_panel.show_thumbnail_settings(callback_query)
            
        elif data == "uset_nsfw":
            await settings_panel.show_nsfw_settings(callback_query)
            
        elif data == "uset_metadata":
            await settings_panel.show_metadata_settings(callback_query)
            
        elif data == "uset_misc":
            await settings_panel.show_misc_settings(callback_query)
            
        elif data == "uset_storage":
            await settings_panel.show_storage_plan(callback_query)
            
        elif data == "uset_back":
            await settings_panel.show_main_panel(client, callback_query.message)
            
        elif data == "uset_close":
            await callback_query.message.delete()
            
        elif data == "uset_ai_toggle":
            new_state = await user_settings.toggle_setting(user_id, 'ai_caption')
            await callback_query.answer(f"AI Caption: {'ON' if new_state else 'OFF'}")
            await settings_panel.show_ai_caption_settings(callback_query)
            
        elif data == "uset_org_toggle":
            new_state = await user_settings.toggle_setting(user_id, 'smart_organizer')
            await callback_query.answer(f"Smart Organizer: {'ON' if new_state else 'OFF'}")
            await settings_panel.show_organizer_settings(callback_query)
            
        elif data == "uset_nsfw_toggle":
            new_state = await user_settings.toggle_setting(user_id, 'nsfw_filter')
            await callback_query.answer(f"NSFW Filter: {'ON' if new_state else 'OFF'}")
            await settings_panel.show_nsfw_settings(callback_query)
            
        elif data == "uset_mode_document":
            await user_settings.update_setting(user_id, 'upload_mode', 'document')
            await callback_query.answer("Upload mode: Document")
            await settings_panel.show_general_settings(callback_query)
            
        elif data == "uset_mode_video":
            await user_settings.update_setting(user_id, 'upload_mode', 'video')
            await callback_query.answer("Upload mode: Video")
            await settings_panel.show_general_settings(callback_query)
            
        elif data == "uset_mode_audio":
            await user_settings.update_setting(user_id, 'upload_mode', 'audio')
            await callback_query.answer("Upload mode: Audio")
            await settings_panel.show_general_settings(callback_query)
            
        elif data == "uset_mode_photo":
            await user_settings.update_setting(user_id, 'upload_mode', 'photo')
            await callback_query.answer("Upload mode: Photo")
            await settings_panel.show_general_settings(callback_query)
            
        elif data == "uset_thumb_set":
            await callback_query.message.edit_text(
                "🖼 **Send me an image to set as thumbnail:**\n\n"
                "Reply to image with /setthumb",
                parse_mode="markdown"
            )
            
        elif data == "uset_thumb_remove":
            await user_settings.update_setting(user_id, 'custom_thumbnail', None)
            await callback_query.answer("Thumbnail removed!")
            await settings_panel.show_thumbnail_settings(callback_query)
            
        elif data == "uset_meta_history":
            settings = await user_settings.get_user_settings(user_id)
            settings['metadata_settings']['save_history'] = not settings['metadata_settings'].get('save_history', True)
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer("History setting updated!")
            await settings_panel.show_metadata_settings(callback_query)
            
        elif data == "uset_meta_stats":
            settings = await user_settings.get_user_settings(user_id)
            settings['metadata_settings']['show_in_stats'] = not settings['metadata_settings'].get('show_in_stats', True)
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer("Stats setting updated!")
            await settings_panel.show_metadata_settings(callback_query)
            
        elif data == "uset_meta_links":
            settings = await user_settings.get_user_settings(user_id)
            settings['metadata_settings']['delete_links'] = not settings['metadata_settings'].get('delete_links', False)
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer("Link setting updated!")
            await settings_panel.show_metadata_settings(callback_query)
            
        elif data == "uset_upgrade":
            from bot.plugins.premium import premium_command
            await premium_command(client, callback_query.message)
            
        elif data == "uset_misc_progress":
            settings = await user_settings.get_user_settings(user_id)
            current = settings['misc_settings'].get('progress_style', 'block')
            new_style = 'square' if current == 'block' else 'block'
            settings['misc_settings']['progress_style'] = new_style
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer(f"Progress: {new_style}")
            await settings_panel.show_misc_settings(callback_query)
            
        elif data == "uset_misc_lang":
            settings = await user_settings.get_user_settings(user_id)
            current = settings['misc_settings'].get('language', 'en')
            new_lang = 'bn' if current == 'en' else 'en'
            settings['misc_settings']['language'] = new_lang
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer(f"Language: {new_lang}")
            await settings_panel.show_misc_settings(callback_query)
            
        elif data == "uset_misc_caption":
            await callback_query.message.edit_text(
                "📝 **Send your caption template:**\n\n"
                "Use {filename}, {size}, {quality} as variables.\n"
                "Reply with /setcaption <template>",
                parse_mode="markdown"
            )
            
        elif data == "uset_ai_format":
            await callback_query.message.edit_text(
                "📝 **Send your AI caption format:**\n\n"
                "Use {filename}, {size}, {quality}, {category} as variables.\n"
                "Reply with /setaicaption <format>",
                parse_mode="markdown"
            )
            
        elif data == "uset_org_categories":
            await callback_query.message.edit_text(
                "📂 **Smart Organizer Categories:**\n\n"
                "• Movies\n• TV Series\n• Music\n• Books\n• Documents\n• Software\n• Archives\n\n"
                "Files will be auto-sorted into these folders.",
                parse_mode="markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="uset_organizer")]
                ])
            )
            
        elif data == "uset_leech_split":
            await callback_query.message.edit_text(
                "📤 **Leech Split Settings:**\n\n"
                "Send split size in MB.\n"
                "Reply with /setsplit <size_mb>",
                parse_mode="markdown"
            )
            
        elif data == "uset_leech_doc":
            settings = await user_settings.get_user_settings(user_id)
            if 'leech_settings' not in settings:
                settings['leech_settings'] = {}
            settings['leech_settings']['as_document'] = not settings['leech_settings'].get('as_document', False)
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer("Leech setting updated!")
            await settings_panel.show_leech_settings(callback_query)
            
        elif data == "uset_leech_group":
            settings = await user_settings.get_user_settings(user_id)
            if 'leech_settings' not in settings:
                settings['leech_settings'] = {}
            settings['leech_settings']['media_group'] = not settings['leech_settings'].get('media_group', False)
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer("Media group updated!")
            await settings_panel.show_leech_settings(callback_query)
            
        elif data == "uset_mirror_upload":
            settings = await user_settings.get_user_settings(user_id)
            if 'mirror_settings' not in settings:
                settings['mirror_settings'] = {}
            current = settings['mirror_settings'].get('default_upload', 'rc')
            new_mode = 'telegram' if current == 'rc' else 'rc'
            settings['mirror_settings']['default_upload'] = new_mode
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer(f"Upload: {new_mode}")
            await settings_panel.show_mirror_settings(callback_query)
            
        elif data == "uset_mirror_autodel":
            settings = await user_settings.get_user_settings(user_id)
            if 'mirror_settings' not in settings:
                settings['mirror_settings'] = {}
            settings['mirror_settings']['auto_delete'] = not settings['mirror_settings'].get('auto_delete', False)
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer("Auto delete updated!")
            await settings_panel.show_mirror_settings(callback_query)
            
        elif data == "uset_mirror_dup":
            settings = await user_settings.get_user_settings(user_id)
            if 'mirror_settings' not in settings:
                settings['mirror_settings'] = {}
            settings['mirror_settings']['stop_duplicate'] = not settings['mirror_settings'].get('stop_duplicate', False)
            await users_db.update_user_settings(user_id, settings)
            await callback_query.answer("Duplicate setting updated!")
            await settings_panel.show_mirror_settings(callback_query)
            
    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)
