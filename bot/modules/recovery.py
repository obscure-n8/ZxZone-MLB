import os
import time
import asyncio
import subprocess
from typing import Dict, Optional
from bot.config import Config

class RecoverySystem:
    """Auto recovery system"""
    
    def __init__(self):
        self.recovery_count = 0
        self.last_recovery = 0
        self.recovery_log = []
        
    async def monitor_bot_health(self):
        """Monitor bot health"""
        asyncio.create_task(self._health_loop())
        
    async def _health_loop(self):
        """Health monitoring loop"""
        while True:
            try:
                # Check bot health
                health = await self.check_health()
                
                if not health['healthy']:
                    await self.perform_recovery(health['issue'])
                    
                await asyncio.sleep(60)  # Check every minute
                
            except:
                await asyncio.sleep(30)
                
    async def check_health(self) -> Dict:
        """Check bot health"""
        issues = []
        
        # Check database
        try:
            from bot.database.db import db
            if not await db.ping():
                issues.append('database')
        except:
            issues.append('database')
            
        # Check memory
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 95:
                issues.append('memory')
        except:
            pass
            
        # Check disk
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            if free < 100 * 1024 * 1024:  # < 100MB
                issues.append('disk')
        except:
            pass
            
        return {
            'healthy': len(issues) == 0,
            'issue': issues[0] if issues else None,
            'issues': issues
        }
        
    async def perform_recovery(self, issue: str):
        """Perform recovery based on issue"""
        try:
            self.recovery_count += 1
            self.last_recovery = time.time()
            
            recovery_actions = {
                'database': self.recover_database,
                'memory': self.recover_memory,
                'disk': self.recover_disk
            }
            
            action = recovery_actions.get(issue)
            if action:
                await action()
                
            self.recovery_log.append({
                'issue': issue,
                'time': time.time(),
                'recovery_count': self.recovery_count
            })
            
        except:
            pass
            
    async def recover_database(self):
        """Recover database connection"""
        try:
            from bot.database.db import db
            await db.close()
            await asyncio.sleep(5)
            await db.ping()
        except:
            pass
            
    async def recover_memory(self):
        """Recover from high memory usage"""
        try:
            import gc
            gc.collect()
            
            # Clear caches
            import functools
            for obj in gc.get_objects():
                if isinstance(obj, functools._lru_cache_wrapper):
                    obj.cache_clear()
                    
        except:
            pass
            
    async def recover_disk(self):
        """Recover from low disk space"""
        try:
            # Clean temp files
            temp_dir = os.path.join(Config.DOWNLOAD_DIR, 'temp')
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                os.makedirs(temp_dir, exist_ok=True)
                
            # Clean old logs
            log_dir = os.path.join(Config.BASE_DIR, 'data', 'logs')
            if os.path.exists(log_dir):
                for file in os.listdir(log_dir):
                    file_path = os.path.join(log_dir, file)
                    if os.path.getsize(file_path) > 10 * 1024 * 1024:  # > 10MB
                        os.remove(file_path)
                        
        except:
            pass
            
    async def get_recovery_stats(self) -> Dict:
        """Get recovery statistics"""
        return {
            'total_recoveries': self.recovery_count,
            'last_recovery': self.last_recovery,
            'recovery_log': self.recovery_log[-10:]
        }

# Create instance
recovery_system = RecoverySystem()
