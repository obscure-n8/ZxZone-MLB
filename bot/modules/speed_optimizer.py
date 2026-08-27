import os
import time
import asyncio
import psutil
from typing import Dict, Optional
from bot.config import Config

class SpeedOptimizer:
    """Speed optimization system"""
    
    def __init__(self):
        self.speed_stats = {}
        self.optimization_level = self.detect_environment()
        
    def detect_environment(self) -> str:
        """Detect environment for speed optimization"""
        if 'DYNO' in os.environ:
            return 'heroku'
        else:
            return 'vps'
            
    async def optimize_download_speed(self) -> Dict:
        """Optimize download speed settings"""
        try:
            if self.optimization_level == 'vps':
                settings = {
                    'connections': 16,
                    'split': 16,
                    'buffer_size': 1024 * 1024 * 4,  # 4MB buffer
                    'timeout': 300
                }
            else:
                settings = {
                    'connections': 8,
                    'split': 8,
                    'buffer_size': 1024 * 1024,  # 1MB buffer
                    'timeout': 120
                }
                
            return {'success': True, 'settings': settings}
            
        except:
            return {'success': False}
            
    async def optimize_upload_speed(self, user_id: Optional[int] = None) -> Dict:
        """Optimize upload speed"""
        try:
            # Check user session/premium
            has_session = False
            is_premium = False
            
            if user_id:
                from bot.database.users import users_db
                user = await users_db.get_user(user_id)
                has_session = user.get('has_session', False) if user else False
                is_premium = user.get('is_premium', False) if user else False
                
            if has_session and is_premium:
                speed = 20  # MB/s
            elif has_session or is_premium:
                speed = 15  # MB/s
            else:
                speed = 10  # MB/s
                
            return {
                'success': True,
                'speed': speed,
                'has_session': has_session,
                'is_premium': is_premium
            }
            
        except:
            return {'success': False, 'speed': 10}
            
    async def get_system_speed(self) -> Dict:
        """Get current system speed"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            
            return {
                'cpu': cpu_percent,
                'memory': memory.percent,
                'disk_read': disk_io.read_bytes,
                'disk_write': disk_io.write_bytes
            }
            
        except:
            return {}
            
    async def monitor_speed(self, task_id: str):
        """Monitor task speed"""
        asyncio.create_task(self._speed_monitor(task_id))
        
    async def _speed_monitor(self, task_id: str):
        """Speed monitoring loop"""
        while True:
            try:
                stats = await self.get_system_speed()
                self.speed_stats[task_id] = stats
                await asyncio.sleep(5)
            except:
                break

# Create instance
speed_optimizer = SpeedOptimizer()
