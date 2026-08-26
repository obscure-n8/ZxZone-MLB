import os
import sys
import time
import asyncio
from pathlib import Path
from bot.config import Config

class StartupManager:
    """Bot startup management system"""
    
    def __init__(self):
        self.startup_time = time.time()
        self.startup_steps = []
        self.errors = []
        
    async def initialize(self):
        """Initialize bot components"""
        steps = [
            ('Config Validation', self.validate_config),
            ('Directory Setup', self.setup_directories),
            ('Database Connection', self.connect_database),
            ('Aria2 Setup', self.setup_aria2),
            ('Rclone Setup', self.setup_rclone),
            ('Session Setup', self.setup_sessions),
            ('Plugin Loading', self.load_plugins),
            ('Queue System', self.init_queue),
            ('Scheduler', self.init_scheduler),
            ('Web Server', self.init_web_server),
        ]
        
        for step_name, step_func in steps:
            try:
                start = time.time()
                await step_func()
                duration = time.time() - start
                self.startup_steps.append({
                    'step': step_name,
                    'status': 'success',
                    'duration': duration
                })
            except Exception as e:
                self.errors.append({
                    'step': step_name,
                    'error': str(e)
                })
                self.startup_steps.append({
                    'step': step_name,
                    'status': 'failed',
                    'duration': time.time() - start
                })
                
    async def validate_config(self):
        """Validate configuration"""
        Config.validate_config()
        
    async def setup_directories(self):
        """Create necessary directories"""
        directories = [
            'downloads',
            'downloads/temp',
            'downloads/queue',
            'downloads/completed',
            'thumbnails',
            'thumbnails/users',
            'thumbnails/watermarks',
            'encode',
            'config',
            'sessions',
            'data',
            'data/backups',
            'data/logs',
            'data/temp',
        ]
        
        for directory in directories:
            path = Path(Config.BASE_DIR) / directory
            path.mkdir(parents=True, exist_ok=True)
            
    async def connect_database(self):
        """Connect to database"""
        from bot.database.db import db
        if not await db.ping():
            raise Exception("Database connection failed")
            
    async def setup_aria2(self):
        """Setup aria2"""
        import subprocess
        
        # Check if aria2 is installed
        result = subprocess.run(['which', 'aria2c'], capture_output=True)
        if result.returncode != 0:
            raise Exception("Aria2 not installed")
            
    async def setup_rclone(self):
        """Setup rclone"""
        import subprocess
        
        # Check if rclone is installed
        result = subprocess.run(['which', 'rclone'], capture_output=True)
        if result.returncode != 0:
            raise Exception("Rclone not installed")
            
    async def setup_sessions(self):
        """Setup bot sessions"""
        session_dir = Path(Config.BASE_DIR) / "sessions"
        session_dir.mkdir(exist_ok=True)
        
    async def load_plugins(self):
        """Load bot plugins"""
        # This is handled by Pyrogram
        pass
        
    async def init_queue(self):
        """Initialize queue system"""
        from bot.modules.queue import task_queue
        # Start queue processing
        asyncio.create_task(task_queue.process_queue())
        
    async def init_scheduler(self):
        """Initialize scheduler"""
        from bot.modules.scheduler import smart_scheduler
        await smart_scheduler.start_scheduler()
        
    async def init_web_server(self):
        """Initialize web server"""
        # Web server is optional
        pass
        
    def get_startup_report(self) -> dict:
        """Get startup report"""
        total_time = time.time() - self.startup_time
        
        return {
            'total_time': total_time,
            'steps': self.startup_steps,
            'errors': self.errors,
            'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'python_version': sys.version,
            'platform': sys.platform
        }

# Create instance
startup_manager = StartupManager()
