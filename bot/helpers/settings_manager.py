import os
import json
from typing import Any, Optional
from bot.config import Config
from bot.database.settings import settings_db

class SettingsManager:
    """Dynamic settings manager for bot"""
    
    def __init__(self):
        self.settings_cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.last_cache_update = {}
        
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting with cache support"""
        # Check cache first
        if key in self.settings_cache:
            return self.settings_cache.get(key, default)
            
        # Get from database
        value = await settings_db.get_setting(key, default)
        
        # Update cache
        self.settings_cache[key] = value
        self.last_cache_update[key] = os.time()
        
        return value
        
    async def set_setting(self, key: str, value: Any):
        """Set setting and update cache"""
        await settings_db.update_setting(key, value)
        self.settings_cache[key] = value
        self.last_cache_update[key] = os.time()
        
    async def get_all_settings(self) -> dict:
        """Get all settings"""
        return await settings_db.get_settings()
        
    async def update_bulk_settings(self, settings: dict):
        """Update multiple settings at once"""
        await settings_db.update_settings(settings)
        self.settings_cache.update(settings)
        
    async def reset_setting(self, key: str):
        """Reset setting to default"""
        if key in self.settings_cache:
            del self.settings_cache[key]
        await settings_db.update_setting(key, None)
        
    async def toggle_setting(self, key: str) -> bool:
        """Toggle boolean setting"""
        current = await self.get_setting(key, False)
        new_value = not current
        await self.set_setting(key, new_value)
        return new_value
        
    async def get_user_settings(self, user_id: int) -> dict:
        """Get user specific settings"""
        from bot.database.users import users_db
        return await users_db.get_user_settings(user_id)
        
    async def update_user_settings(self, user_id: int, settings: dict):
        """Update user specific settings"""
        from bot.database.users import users_db
        await users_db.update_user_settings(user_id, settings)
        
    async def get_task_limit(self, task_type: str, user_id: Optional[int] = None) -> int:
        """Get task limit for specific type"""
        limit_map = {
            'direct': Config.DIRECT_LIMIT,
            'mega': Config.MEGA_LIMIT,
            'torrent': Config.TORRENT_LIMIT,
            'gdrive': Config.GD_DL_LIMIT,
            'rclone': Config.RC_DL_LIMIT,
            'clone': Config.CLONE_LIMIT,
            'jdownloader': Config.JD_LIMIT,
            'nzb': Config.NZB_LIMIT,
            'ytdlp': Config.YTDLP_LIMIT,
            'playlist': Config.PLAYLIST_LIMIT,
            'leech': Config.LEECH_LIMIT,
            'extract': Config.EXTRACT_LIMIT,
            'archive': Config.ARCHIVE_LIMIT,
            'storage': Config.STORAGE_LIMIT,
        }
        
        return limit_map.get(task_type, 0)
        
    async def is_feature_enabled(self, feature: str) -> bool:
        """Check if feature is enabled"""
        disable_map = {
            'torrents': Config.DISABLE_TORRENTS,
            'leech': Config.DISABLE_LEECH,
            'mirror': Config.DISABLE_MIRROR,
            'bulk': Config.DISABLE_BULK,
            'multi': Config.DISABLE_MULTI,
            'seed': Config.DISABLE_SEED,
            'ffmpeg': Config.DISABLE_FF_MODE,
            'jdownloader': Config.DISABLE_JD,
            'nzb': Config.DISABLE_NZB,
            'rss': Config.DISABLE_RSS,
            'search': Config.DISABLE_SEARCH,
            'stream': Config.DISABLE_STREAM,
            'ytdlp': Config.DISABLE_YTDLP,
            'mega': Config.DISABLE_MEGA,
        }
        
        return not disable_map.get(feature, False)
        
    async def get_queue_settings(self) -> dict:
        """Get queue configuration"""
        return {
            'all': Config.QUEUE_ALL,
            'download': Config.QUEUE_DOWNLOAD,
            'upload': Config.QUEUE_UPLOAD,
        }
        
    def get_env_var(self, key: str, default: Any = None) -> Any:
        """Get environment variable"""
        return os.getenv(key, default)
        
    def set_env_var(self, key: str, value: Any):
        """Set environment variable (runtime only)"""
        os.environ[key] = str(value)

# Create instance
settings_manager = SettingsManager()
