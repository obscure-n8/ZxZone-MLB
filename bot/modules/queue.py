import asyncio
from typing import Optional
from bot.config import Config

class TaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=Config.QUEUE_LIMIT)
        self.active_tasks = {}
        self.waiting_tasks = []
        self.task_positions = {}
        
    async def add_task(self, task_id: str, task_data: dict) -> bool:
        """Add task to queue"""
        if len(self.active_tasks) >= Config.MAX_TOTAL_TASKS:
            return False
            
        task_data['task_id'] = task_id
        task_data['status'] = 'queued'
        
        # Add to waiting list
        self.waiting_tasks.append(task_data)
        self.task_positions[task_id] = len(self.waiting_tasks)
        
        # Try to process queue
        await self.process_queue()
        return True
        
    async def process_queue(self):
        """Process queue and start tasks"""
        while len(self.active_tasks) < Config.MAX_TOTAL_TASKS and self.waiting_tasks:
            # Get next task
            task = self.waiting_tasks.pop(0)
            task_id = task['task_id']
            
            # Update positions
            self.update_positions()
            
            # Add to active tasks
            task['status'] = 'active'
            self.active_tasks[task_id] = task
            
            # Start task in background
            asyncio.create_task(self.execute_task(task))
            
    async def execute_task(self, task: dict):
        """Execute task"""
        task_id = task['task_id']
        try:
            # Execute based on task type
            if task['type'] == 'download':
                await self.process_download(task)
            elif task['type'] == 'upload':
                await self.process_upload(task)
            elif task['type'] == 'leech':
                await self.process_leech(task)
                
            task['status'] = 'completed'
            
        except Exception as e:
            task['status'] = 'failed'
            task['error'] = str(e)
            
        finally:
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
            # Process next in queue
            await self.process_queue()
            
    async def process_download(self, task: dict):
        """Process download task"""
        from bot.modules.downloader import downloader
        
        await downloader.download_file(
            task['url'],
            task['file_path'],
            task.get('progress_callback')
        )
        
    async def process_upload(self, task: dict):
        """Process upload task"""
        from bot.modules.uploader import uploader
        
        await uploader.upload_file(
            task['file_path'],
            task.get('destination'),
            task.get('progress_callback')
        )
        
    async def process_leech(self, task: dict):
        """Process leech task"""
        from bot.modules.downloader import downloader
        from bot.modules.uploader import uploader
        
        # Download first
        await downloader.download_file(
            task['url'],
            task['file_path'],
            task.get('progress_callback')
        )
        
        # Then upload
        await uploader.upload_to_telegram(
            task['file_path'],
            task.get('chat_id'),
            task.get('progress_callback')
        )
        
    def update_positions(self):
        """Update queue positions"""
        for i, task in enumerate(self.waiting_tasks, 1):
            self.task_positions[task['task_id']] = i
            
    def get_position(self, task_id: str) -> int:
        """Get task position in queue"""
        return self.task_positions.get(task_id, 0)
        
    def get_active_count(self) -> int:
        """Get active task count"""
        return len(self.active_tasks)
        
    def get_waiting_count(self) -> int:
        """Get waiting task count"""
        return len(self.waiting_tasks)
        
    def get_queue_status(self) -> dict:
        """Get queue status"""
        return {
            'active': self.get_active_count(),
            'waiting': self.get_waiting_count(),
            'total': self.get_active_count() + self.get_waiting_count(),
            'max': Config.MAX_TOTAL_TASKS
        }
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        # Check active tasks
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['cancelled'] = True
            del self.active_tasks[task_id]
            await self.process_queue()
            return True
            
        # Check waiting tasks
        for task in self.waiting_tasks:
            if task['task_id'] == task_id:
                self.waiting_tasks.remove(task)
                self.update_positions()
                return True
                
        return False
        
    async def clear_completed(self):
        """Clear completed tasks"""
        completed = [tid for tid, task in self.active_tasks.items() 
                    if task['status'] == 'completed']
        for tid in completed:
            del self.active_tasks[tid]

# Create instance
task_queue = TaskQueue()
