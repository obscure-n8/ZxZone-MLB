import time
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from bot.config import Config
from bot.database.tasks import tasks_db
from bot.helpers.rate_limiter import rate_limiter

class TaskManager:
    """Advanced task management system"""
    
    def __init__(self):
        self.active_tasks = {}
        self.task_queue = asyncio.Queue()
        self.task_history = []
        self.task_stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0,
            'active': 0
        }
        
    async def create_task(
        self,
        user_id: int,
        task_type: str,
        url: str = "",
        options: Dict = None
    ) -> Optional[str]:
        """Create new task"""
        from bot.helpers.utils import Utils
        
        # Check rate limit
        if not await rate_limiter.check_task_limit(user_id, task_type):
            return None
            
        # Generate task ID
        task_id = Utils.generate_task_id()
        
        # Create task data
        task_data = {
            'task_id': task_id,
            'user_id': user_id,
            'type': task_type,
            'url': url,
            'options': options or {},
            'status': 'queued',
            'progress': 0,
            'speed': 0,
            'eta': 0,
            'file_name': '',
            'file_size': 0,
            'created_at': time.time(),
            'started_at': None,
            'completed_at': None,
            'error': None
        }
        
        # Add to queue
        await self.task_queue.put(task_data)
        
        # Save to database
        await tasks_db.add_task(task_id, user_id, task_type, url)
        
        # Update stats
        self.task_stats['total'] += 1
        
        # Update rate limiter
        await rate_limiter.add_task(user_id, task_id)
        
        return task_id
        
    async def process_queue(self):
        """Process task queue"""
        while True:
            try:
                # Get task from queue
                task = await self.task_queue.get()
                
                # Check if task should be processed
                if await self.can_process_task(task):
                    # Start task
                    asyncio.create_task(self.execute_task(task))
                else:
                    # Re-queue task
                    await asyncio.sleep(5)
                    await self.task_queue.put(task)
                    
            except Exception as e:
                print(f"Queue processing error: {e}")
                
    async def can_process_task(self, task: Dict) -> bool:
        """Check if task can be processed"""
        # Check total active tasks
        if self.task_stats['active'] >= Config.BOT_MAX_TASKS:
            return False
            
        # Check user task limit
        user_id = task['user_id']
        user_tasks = await self.get_user_active_tasks(user_id)
        
        if len(user_tasks) >= Config.USER_MAX_TASKS:
            return False
            
        return True
        
    async def execute_task(self, task: Dict):
        """Execute task"""
        task_id = task['task_id']
        user_id = task['user_id']
        
        try:
            # Update status
            task['status'] = 'active'
            task['started_at'] = time.time()
            self.active_tasks[task_id] = task
            self.task_stats['active'] += 1
            
            # Execute based on type
            if task['type'] == 'leech':
                await self.execute_leech(task)
            elif task['type'] == 'mirror':
                await self.execute_mirror(task)
            elif task['type'] == 'ytdlp':
                await self.execute_ytdlp(task)
            elif task['type'] == 'torrent':
                await self.execute_torrent(task)
                
            # Mark as completed
            task['status'] = 'completed'
            task['completed_at'] = time.time()
            self.task_stats['completed'] += 1
            
        except Exception as e:
            # Mark as failed
            task['status'] = 'failed'
            task['error'] = str(e)
            task['completed_at'] = time.time()
            self.task_stats['failed'] += 1
            
        finally:
            # Clean up
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            self.task_stats['active'] -= 1
            
            # Update rate limiter
            await rate_limiter.remove_task(user_id, task_id)
            
            # Update database
            await tasks_db.update_task_status(task_id, task['status'])
            
            # Add to history
            self.task_history.append(task)
            if len(self.task_history) > 100:
                self.task_history.pop(0)
                
    async def execute_leech(self, task: Dict):
        """Execute leech task"""
        from bot.modules.downloader import downloader
        from bot.modules.uploader import uploader
        
        # Download
        await downloader.download_file(
            task['url'],
            task.get('file_path', ''),
            progress_callback=lambda **kwargs: self.update_progress(task['task_id'], **kwargs)
        )
        
        # Upload
        await uploader.upload_to_telegram(
            None,  # client
            task.get('file_path', ''),
            task.get('chat_id', 0)
        )
        
    async def execute_mirror(self, task: Dict):
        """Execute mirror task"""
        from bot.modules.downloader import downloader
        from bot.modules.rclone import rclone_manager
        
        # Download
        await downloader.download_file(
            task['url'],
            task.get('file_path', '')
        )
        
        # Upload to cloud
        await rclone_manager.upload_file(
            task.get('file_path', ''),
            task.get('destination', '')
        )
        
    async def execute_ytdlp(self, task: Dict):
        """Execute yt-dlp task"""
        import yt_dlp
        
        with yt_dlp.YoutubeDL(Config.YTDLP_OPTIONS) as ydl:
            ydl.download([task['url']])
            
    async def execute_torrent(self, task: Dict):
        """Execute torrent task"""
        import aria2p
        
        aria2 = aria2p.API(
            aria2p.Client(
                host=Config.ARIA2_HOST,
                port=Config.ARIA2_PORT,
                secret=Config.ARIA2_SECRET
            )
        )
        
        download = aria2.add_magnet(task['url'])
        while not download.is_complete:
            await asyncio.sleep(1)
            
    async def update_progress(self, task_id: str, **kwargs):
        """Update task progress"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.update(kwargs)
            
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task['status'] = 'cancelled'
            task['completed_at'] = time.time()
            
            del self.active_tasks[task_id]
            self.task_stats['cancelled'] += 1
            self.task_stats['active'] -= 1
            
            await tasks_db.update_task_status(task_id, 'cancelled')
            return True
        return False
        
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get task status"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        return await tasks_db.get_task(task_id)
        
    async def get_user_active_tasks(self, user_id: int) -> List[Dict]:
        """Get active tasks for user"""
        return [
            task for task in self.active_tasks.values()
            if task['user_id'] == user_id
        ]
        
    async def get_all_active_tasks(self) -> List[Dict]:
        """Get all active tasks"""
        return list(self.active_tasks.values())
        
    async def get_task_history(self, limit: int = 10) -> List[Dict]:
        """Get task history"""
        return self.task_history[-limit:]
        
    async def get_stats(self) -> Dict:
        """Get task statistics"""
        return {
            **self.task_stats,
            'queued': self.task_queue.qsize(),
            'timestamp': datetime.now().isoformat()
        }
        
    async def pause_task(self, task_id: str) -> bool:
        """Pause task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['paused'] = True
            return True
        return False
        
    async def resume_task(self, task_id: str) -> bool:
        """Resume paused task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['paused'] = False
            return True
        return False

# Create instance
task_manager = TaskManager()
