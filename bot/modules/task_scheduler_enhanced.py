import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from bot.database.db import db

class EnhancedScheduler:
    """Enhanced task scheduler"""
    
    def __init__(self):
        self.schedules = {}
        self.running_tasks = {}
        
    async def schedule_task(
        self,
        task_id: str,
        task_type: str,
        task_data: Dict,
        schedule_time: Optional[datetime] = None,
        interval: Optional[int] = None,
        repeat: bool = False
    ) -> bool:
        """Schedule a task"""
        try:
            self.schedules[task_id] = {
                'task_type': task_type,
                'task_data': task_data,
                'schedule_time': schedule_time,
                'interval': interval,
                'repeat': repeat,
                'created_at': datetime.now(),
                'last_run': None,
                'next_run': schedule_time or (datetime.now() + timedelta(seconds=interval) if interval else None),
                'active': True,
                'runs': 0
            }
            
            await db.schedules.insert_one(self.schedules[task_id])
            return True
            
        except:
            return False
            
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel scheduled task"""
        if task_id in self.schedules:
            self.schedules[task_id]['active'] = False
            await db.schedules.update_one(
                {'task_id': task_id},
                {'$set': {'active': False}}
            )
            return True
        return False
        
    async def get_due_tasks(self) -> List[Dict]:
        """Get due tasks"""
        current_time = datetime.now()
        due_tasks = []
        
        for task_id, task in self.schedules.items():
            if task['active'] and task['next_run'] and task['next_run'] <= current_time:
                due_tasks.append(task)
                
        return due_tasks
        
    async def run_scheduler(self):
        """Run scheduler loop"""
        asyncio.create_task(self._scheduler_loop())
        
    async def _scheduler_loop(self):
        """Scheduler main loop"""
        while True:
            try:
                due_tasks = await self.get_due_tasks()
                
                for task in due_tasks:
                    await self.execute_task(task)
                    
                await asyncio.sleep(1)
                
            except:
                await asyncio.sleep(5)
                
    async def execute_task(self, task: Dict):
        """Execute scheduled task"""
        try:
            task['runs'] += 1
            task['last_run'] = datetime.now()
            
            # Update next run
            if task['repeat'] and task['interval']:
                task['next_run'] = datetime.now() + timedelta(seconds=task['interval'])
            else:
                task['active'] = False
                
            # Execute based on type
            if task['task_type'] == 'backup':
                from bot.modules.backup import backup_manager
                await backup_manager.create_backup()
                
            elif task['task_type'] == 'cleanup':
                from bot.modules.file_ops import file_ops
                await file_ops.cleanup_temp_files()
                
            elif task['task_type'] == 'monitor':
                from bot.modules.monitor_enhanced import enhanced_monitor
                await enhanced_monitor.get_full_status()
                
        except:
            pass

# Create instance
enhanced_scheduler = EnhancedScheduler()
