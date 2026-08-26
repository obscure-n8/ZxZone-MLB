import time
from typing import Optional
from bot.config import Config

class StatusManager:
    def __init__(self):
        self.active_tasks = {}
        self.completed_tasks = []
        self.failed_tasks = []
        
    def add_task(self, task_id: str, task_info: dict):
        """Add new task to active tasks"""
        self.active_tasks[task_id] = {
            **task_info,
            'start_time': time.time(),
            'status': 'starting'
        }
        
    def update_task(self, task_id: str, **kwargs):
        """Update task information"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].update(kwargs)
            
    def get_task(self, task_id: str) -> Optional[dict]:
        """Get task information"""
        return self.active_tasks.get(task_id)
        
    def remove_task(self, task_id: str):
        """Remove task from active tasks"""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            if task.get('status') == 'completed':
                self.completed_tasks.append(task)
            else:
                self.failed_tasks.append(task)
                
    def get_active_count(self) -> int:
        """Get number of active tasks"""
        return len(self.active_tasks)
        
    def get_completed_count(self) -> int:
        """Get number of completed tasks"""
        return len(self.completed_tasks)
        
    def get_failed_count(self) -> int:
        """Get number of failed tasks"""
        return len(self.failed_tasks)
        
    def get_all_active(self) -> dict:
        """Get all active tasks"""
        return self.active_tasks
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['status'] = 'cancelled'
            self.remove_task(task_id)
            return True
        return False
        
    def get_user_tasks(self, user_id: int) -> list:
        """Get tasks by user"""
        return [
            task for task_id, task in self.active_tasks.items()
            if task.get('user_id') == user_id
        ]
        
    def can_add_task(self, user_id: int) -> bool:
        """Check if user can add more tasks"""
        user_tasks = self.get_user_tasks(user_id)
        return len(user_tasks) < Config.MAX_TASKS_PER_USER
        
    def get_queue_position(self, task_id: str) -> int:
        """Get task position in queue"""
        return list(self.active_tasks.keys()).index(task_id) + 1
