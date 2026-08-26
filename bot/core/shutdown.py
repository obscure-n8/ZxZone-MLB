import time
import asyncio
import signal
import sys
from typing import Optional
from bot.config import Config

class ShutdownManager:
    """Graceful shutdown management system"""
    
    def __init__(self):
        self.shutdown_hooks = []
        self.is_shutting_down = False
        self.shutdown_reason = ""
        
    def register_hook(self, hook_func):
        """Register shutdown hook"""
        self.shutdown_hooks.append(hook_func)
        
    async def shutdown(self, reason: str = "Manual shutdown"):
        """Graceful shutdown"""
        if self.is_shutting_down:
            return
            
        self.is_shutting_down = True
        self.shutdown_reason = reason
        
        print(f"\n🔄 Shutting down: {reason}")
        
        # Execute shutdown hooks in order
        for hook in self.shutdown_hooks:
            try:
                print(f"  - Running: {hook.__name__}")
                await hook()
            except Exception as e:
                print(f"  - Error in {hook.__name__}: {e}")
                
        print("✅ Shutdown complete!")
        
    async def cleanup_tasks(self):
        """Clean up running tasks"""
        from bot.modules.queue import task_queue
        from bot.modules.scheduler import smart_scheduler
        
        # Stop scheduler
        await smart_scheduler.stop_scheduler()
        
        # Cancel active tasks
        for task_id in list(task_queue.active_tasks.keys()):
            await task_queue.cancel_task(task_id)
            
    async def cleanup_database(self):
        """Close database connections"""
        from bot.database.db import db
        await db.close()
        
    async def cleanup_files(self):
        """Clean up temporary files"""
        import shutil
        from pathlib import Path
        
        temp_dir = Path(Config.BASE_DIR) / "downloads" / "temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir(exist_ok=True)
            
    async def save_state(self):
        """Save bot state before shutdown"""
        from bot.database.settings import settings_db
        
        await settings_db.update_setting('last_shutdown', time.time())
        await settings_db.update_setting('shutdown_reason', self.shutdown_reason)
        
    def setup_signal_handlers(self):
        """Setup signal handlers"""
        def signal_handler(signum, frame):
            reason = signal.Signals(signum).name
            asyncio.create_task(self.shutdown(reason))
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

# Create instance
shutdown_manager = ShutdownManager()

# Register default hooks
shutdown_manager.register_hook(shutdown_manager.cleanup_tasks)
shutdown_manager.register_hook(shutdown_manager.save_state)
shutdown_manager.register_hook(shutdown_manager.cleanup_database)
shutdown_manager.register_hook(shutdown_manager.cleanup_files)
