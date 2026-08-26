import os
import time
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from bot.database.db import db

class SmartScheduler:
    """Intelligent task scheduling system"""
    
    def __init__(self):
        self.collection = db.schedules
        self.active_schedules = {}
        self.scheduler_task = None
        
    async def schedule_task(
        self,
        task_type: str,
        task_data: Dict,
        schedule_time: Optional[datetime] = None,
        interval: Optional[int] = None,
        repeat: bool = False
    ) -> str:
        """Schedule a task"""
        from bot.helpers.utils import Utils
        
        schedule_id = Utils.generate_task_id()
        
        schedule_info = {
            'schedule_id': schedule_id,
            'task_type': task_type,
            'task_data': task_data,
            'schedule_time': schedule_time,
            'interval': interval,
            'repeat': repeat,
            'created_at': datetime.now(),
            'last_run': None,
            'next_run': schedule_time or (datetime.now() + timedelta(seconds=interval) if interval else None),
            'active': True,
            'total_runs': 0
        }
        
        await self.collection.insert_one(schedule_info)
        self.active_schedules[schedule_id] = schedule_info
        
        return schedule_id
        
    async def start_scheduler(self):
        """Start scheduler loop"""
        if self.scheduler_task:
            return
            
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
    async def stop_scheduler(self):
        """Stop scheduler"""
        if self.scheduler_task:
            self.scheduler_task.cancel()
            self.scheduler_task = None
            
    async def _scheduler_loop(self):
        """Scheduler main loop"""
        while True:
            try:
                current_time = datetime.now()
                
                for schedule_id, schedule in list(self.active_schedules.items()):
                    if not schedule['active']:
                        continue
                        
                    next_run = schedule['next_run']
                    if next_run and current_time >= next_run:
                        # Execute task
                        await self.execute_schedule(schedule)
                        
                        # Update schedule
                        if schedule['repeat'] and schedule['interval']:
                            schedule['next_run'] = current_time + timedelta(seconds=schedule['interval'])
                            schedule['last_run'] = current_time
                            schedule['total_runs'] += 1
                        else:
                            schedule['active'] = False
                            
                        # Update database
                        await self.collection.update_one(
                            {'schedule_id': schedule_id},
                            {'$set': schedule}
                        )
                        
                await asyncio.sleep(1)
                
            except Exception as e:
                await asyncio.sleep(5)
                
    async def execute_schedule(self, schedule: Dict):
        """Execute scheduled task"""
        task_type = schedule['task_type']
        task_data = schedule['task_data']
        
        try:
            if task_type == 'backup':
                from bot.modules.backup import backup_manager
                await backup_manager.create_backup()
                
            elif task_type == 'cleanup':
                await self.cleanup_old_files()
                
            elif task_type == 'broadcast':
                # Handle broadcast
                pass
                
            elif task_type == 'download':
                from bot.modules.downloader import downloader
                await downloader.download_file(
                    task_data.get('url'),
                    task_data.get('file_path')
                )
                
        except Exception as e:
            print(f"Schedule execution error: {e}")
            
    async def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel scheduled task"""
        if schedule_id in self.active_schedules:
            self.active_schedules[schedule_id]['active'] = False
            await self.collection.update_one(
                {'schedule_id': schedule_id},
                {'$set': {'active': False}}
            )
            return True
        return False
        
    async def get_schedules(self, user_id: Optional[int] = None) -> List[Dict]:
        """Get schedules"""
        query = {'user_id': user_id} if user_id else {}
        schedules = []
        cursor = self.collection.find(query)
        async for schedule in cursor:
            schedules.append(schedule)
        return schedules
        
    async def cleanup_old_files(self, days: int = 7):
        """Clean up old files"""
        from bot.config import Config
        import shutil
        
        cutoff = time.time() - (days * 24 * 3600)
        
        for root, dirs, files in os.walk(Config.DOWNLOAD_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) < cutoff:
                    try:
                        os.remove(file_path)
                    except:
                        pass
                        
    async def get_scheduler_stats(self) -> Dict:
        """Get scheduler statistics"""
        total = len(self.active_schedules)
        active = sum(1 for s in self.active_schedules.values() if s['active'])
        completed = sum(1 for s in self.active_schedules.values() if not s['active'])
        
        return {
            'total_schedules': total,
            'active_schedules': active,
            'completed_schedules': completed,
            'next_runs': [
                {'id': s['schedule_id'], 'next_run': s['next_run']}
                for s in self.active_schedules.values() if s['active']
            ]
        }

# Create instance
smart_scheduler = SmartScheduler()
