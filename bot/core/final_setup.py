import os
import asyncio
import logging
from typing import Dict
from bot.config import Config

logger = logging.getLogger(__name__)

class FinalSetup:
    """Final setup and integration system"""
    
    def __init__(self):
        self.components = {}
        
    async def initialize_all(self) -> Dict:
        """Initialize all bot components"""
        results = {}
        
        # Initialize components
        components = [
            ('Config', self.init_config),
            ('Database', self.init_database),
            ('Downloader', self.init_downloader),
            ('Uploader', self.init_uploader),
            ('Queue', self.init_queue),
            ('Scheduler', self.init_scheduler),
            ('Monitor', self.init_monitor),
            ('Backup', self.init_backup),
            ('AI', self.init_ai),
            ('Notification', self.init_notification),
        ]
        
        for name, init_func in components:
            try:
                await init_func()
                results[name] = 'OK'
                logger.info(f"{name}: Initialized successfully")
            except Exception as e:
                results[name] = f'ERROR: {str(e)}'
                logger.error(f"{name}: {str(e)}")
                
        return results
        
    async def init_config(self):
        """Initialize config"""
        Config.validate_config()
        Config.ensure_dirs()
        
    async def init_database(self):
        """Initialize database"""
        from bot.database.db import db
        if not await db.ping():
            raise Exception("Database connection failed")
            
    async def init_downloader(self):
        """Initialize downloader"""
        from bot.modules.downloader import downloader
        self.components['downloader'] = downloader
        
    async def init_uploader(self):
        """Initialize uploader"""
        from bot.modules.uploader import uploader
        self.components['uploader'] = uploader
        
    async def init_queue(self):
        """Initialize queue"""
        from bot.modules.queue import task_queue
        self.components['queue'] = task_queue
        
    async def init_scheduler(self):
        """Initialize scheduler"""
        from bot.modules.scheduler import smart_scheduler
        await smart_scheduler.start_scheduler()
        self.components['scheduler'] = smart_scheduler
        
    async def init_monitor(self):
        """Initialize monitor"""
        from bot.modules.monitor import system_monitor
        self.components['monitor'] = system_monitor
        
    async def init_backup(self):
        """Initialize backup"""
        from bot.modules.backup import backup_manager
        self.components['backup'] = backup_manager
        
    async def init_ai(self):
        """Initialize AI"""
        from bot.modules.ai_caption import ai_caption
        from bot.modules.smart_organizer import smart_organizer
        self.components['ai_caption'] = ai_caption
        self.components['organizer'] = smart_organizer
        
    async def init_notification(self):
        """Initialize notification"""
        from bot.modules.notification import notification_system
        self.components['notification'] = notification_system
        
    async def get_status(self) -> Dict:
        """Get initialization status"""
        return {
            'components': self.components,
            'bot': Config.BOT_USERNAME,
            'owner': Config.OWNER_ID
        }

# Create instance
final_setup = FinalSetup()
