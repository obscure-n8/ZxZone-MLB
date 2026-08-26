from bot.database.db import db

class SettingsDB:
    def __init__(self):
        self.collection = db.settings
        
    async def get_settings(self, key: str = "bot_settings"):
        """Get bot settings"""
        settings = await self.collection.find_one({'key': key})
        return settings.get('data', {}) if settings else {}
        
    async def update_settings(self, data: dict, key: str = "bot_settings"):
        """Update bot settings"""
        await self.collection.update_one(
            {'key': key},
            {'$set': {'data': data}},
            upsert=True
        )
        
    async def get_setting(self, setting_key: str, default=None):
        """Get specific setting"""
        settings = await self.get_settings()
        return settings.get(setting_key, default)
        
    async def update_setting(self, setting_key: str, value):
        """Update specific setting"""
        settings = await self.get_settings()
        settings[setting_key] = value
        await self.update_settings(settings)
        
    async def set_default_settings(self):
        """Set default settings"""
        default = {
            'max_tasks_per_user': 3,
            'max_total_tasks': 50,
            'default_upload_mode': 'document',
            'allow_private_files': True,
            'force_subscribe': True,
            'maintenance_mode': False,
            'speed_limit': 0,  # 0 = unlimited
            'allowed_extensions': [],
            'blocked_extensions': [],
        }
        await self.update_settings(default)
        
    async def toggle_maintenance(self, status: bool = None):
        """Toggle maintenance mode"""
        current = await self.get_setting('maintenance_mode', False)
        new_status = status if status is not None else not current
        await self.update_setting('maintenance_mode', new_status)
        return new_status
        
    async def set_speed_limit(self, speed: int):
        """Set global speed limit (bytes/s)"""
        await self.update_setting('speed_limit', speed)
        
    async def add_allowed_extension(self, extension: str):
        """Add allowed extension"""
        extensions = await self.get_setting('allowed_extensions', [])
        if extension not in extensions:
            extensions.append(extension)
            await self.update_setting('allowed_extensions', extensions)
            
    async def remove_allowed_extension(self, extension: str):
        """Remove allowed extension"""
        extensions = await self.get_setting('allowed_extensions', [])
        if extension in extensions:
            extensions.remove(extension)
            await self.update_setting('allowed_extensions', extensions)
            
    async def add_blocked_extension(self, extension: str):
        """Add blocked extension"""
        extensions = await self.get_setting('blocked_extensions', [])
        if extension not in extensions:
            extensions.append(extension)
            await self.update_setting('blocked_extensions', extensions)
            
    async def remove_blocked_extension(self, extension: str):
        """Remove blocked extension"""
        extensions = await self.get_setting('blocked_extensions', [])
        if extension in extensions:
            extensions.remove(extension)
            await self.update_setting('blocked_extensions', extensions)

# Create instance
settings_db = SettingsDB()
