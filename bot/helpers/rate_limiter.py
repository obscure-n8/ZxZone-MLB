import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
from bot.config import Config

class RateLimiter:
    """Advanced rate limiting system"""
    
    def __init__(self):
        self.user_requests = defaultdict(list)
        self.task_limits = defaultdict(int)
        self.banned_users = set()
        self.warning_users = defaultdict(int)
        
    async def check_rate_limit(
        self,
        user_id: int,
        action: str = "default",
        max_requests: int = 10,
        time_window: int = 60
    ) -> bool:
        """Check if user is rate limited"""
        current_time = time.time()
        
        # Clean old requests
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if current_time - req_time < time_window
        ]
        
        # Check if user is banned
        if user_id in self.banned_users:
            return False
            
        # Check request limit
        if len(self.user_requests[user_id]) >= max_requests:
            # Add warning
            self.warning_users[user_id] += 1
            
            # Auto ban after 3 warnings
            if self.warning_users[user_id] >= 3:
                self.banned_users.add(user_id)
                
            return False
            
        # Add request
        self.user_requests[user_id].append(current_time)
        return True
        
    async def check_task_limit(self, user_id: int, task_type: str) -> bool:
        """Check if user can add more tasks"""
        current_tasks = self.task_limits.get(user_id, 0)
        max_tasks = await self.get_max_tasks(user_id, task_type)
        
        if max_tasks == 0:  # Unlimited
            return True
            
        return current_tasks < max_tasks
        
    async def get_max_tasks(self, user_id: int, task_type: str) -> int:
        """Get maximum tasks for user"""
        # Check user specific limit first
        from bot.database.users import users_db
        user_settings = await users_db.get_user_settings(user_id)
        
        if task_type in user_settings:
            return user_settings[task_type]
            
        # Use global limits
        from bot.helpers.settings_manager import settings_manager
        return await settings_manager.get_task_limit(task_type, user_id)
        
    async def add_task(self, user_id: int, task_id: str):
        """Add task to tracking"""
        self.task_limits[user_id] += 1
        
    async def remove_task(self, user_id: int, task_id: str):
        """Remove task from tracking"""
        if self.task_limits[user_id] > 0:
            self.task_limits[user_id] -= 1
            
    async def get_user_task_count(self, user_id: int) -> int:
        """Get current task count for user"""
        return self.task_limits.get(user_id, 0)
        
    async def reset_user(self, user_id: int):
        """Reset user rate limits"""
        self.user_requests[user_id] = []
        self.task_limits[user_id] = 0
        self.warning_users[user_id] = 0
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            
    async def ban_user(self, user_id: int):
        """Ban user from rate limiter"""
        self.banned_users.add(user_id)
        
    async def unban_user(self, user_id: int):
        """Unban user from rate limiter"""
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            
    async def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        return user_id in self.banned_users
        
    async def get_warning_count(self, user_id: int) -> int:
        """Get warning count for user"""
        return self.warning_users.get(user_id, 0)
        
    async def cleanup(self):
        """Clean up old data"""
        current_time = time.time()
        
        # Clean old requests (older than 1 hour)
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if current_time - req_time < 3600
            ]
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
                
        # Reset task limits for inactive users
        for user_id in list(self.task_limits.keys()):
            if not self.user_requests.get(user_id):
                del self.task_limits[user_id]

# Create instance
rate_limiter = RateLimiter()
