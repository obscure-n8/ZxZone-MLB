from datetime import datetime
from bot.database.db import db

class TaskDB:
    def __init__(self):
        self.collection = db.tasks
        
    async def add_task(self, task_id: str, user_id: int, task_type: str, url: str = ""):
        """Add new task"""
        await self.collection.insert_one({
            'task_id': task_id,
            'user_id': user_id,
            'task_type': task_type,  # leech/mirror/ytdl
            'url': url,
            'status': 'queued',  # queued/downloading/uploading/completed/failed/cancelled
            'created_at': datetime.now(),
            'started_at': None,
            'completed_at': None,
            'file_name': "",
            'file_size': 0,
            'progress': 0,
            'speed': 0,
            'error': ""
        })
        
    async def update_task_status(self, task_id: str, status: str):
        """Update task status"""
        update_data = {'status': status}
        if status == 'download':
            update_data['started_at'] = datetime.now()
        elif status in ['completed', 'failed', 'cancelled']:
            update_data['completed_at'] = datetime.now()
            
        await self.collection.update_one(
            {'task_id': task_id},
            {'$set': update_data}
        )
        
    async def update_task_progress(self, task_id: str, progress: float, speed: float = 0):
        """Update task progress"""
        await self.collection.update_one(
            {'task_id': task_id},
            {'$set': {
                'progress': progress,
                'speed': speed
            }}
        )
        
    async def update_task_info(self, task_id: str, file_name: str, file_size: int):
        """Update task file info"""
        await self.collection.update_one(
            {'task_id': task_id},
            {'$set': {
                'file_name': file_name,
                'file_size': file_size
            }}
        )
        
    async def get_task(self, task_id: str):
        """Get task by ID"""
        return await self.collection.find_one({'task_id': task_id})
        
    async def get_user_tasks(self, user_id: int, limit: int = 10):
        """Get user tasks"""
        tasks = []
        cursor = self.collection.find({'user_id': user_id}).sort('created_at', -1).limit(limit)
        async for task in cursor:
            tasks.append(task)
        return tasks
        
    async def get_active_tasks(self):
        """Get all active tasks"""
        tasks = []
        cursor = self.collection.find({'status': {'$in': ['queued', 'download', 'upload']}})
        async for task in cursor:
            tasks.append(task)
        return tasks
        
    async def get_completed_tasks(self):
        """Get completed tasks"""
        tasks = []
        cursor = self.collection.find({'status': 'completed'}).sort('completed_at', -1).limit(20)
        async for task in cursor:
            tasks.append(task)
        return tasks
        
    async def delete_task(self, task_id: str):
        """Delete task"""
        await self.collection.delete_one({'task_id': task_id})
        
    async def clear_completed(self, user_id: int = None):
        """Clear completed tasks"""
        query = {'status': 'completed'}
        if user_id:
            query['user_id'] = user_id
        await self.collection.delete_many(query)
        
    async def get_task_stats(self):
        """Get task statistics"""
        total = await self.collection.count_documents({})
        completed = await self.collection.count_documents({'status': 'completed'})
        failed = await self.collection.count_documents({'status': 'failed'})
        active = await self.collection.count_documents({'status': {'$in': ['queued', 'download', 'upload']}})
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'active': active
        }

# Create instance
tasks_db = TaskDB()
