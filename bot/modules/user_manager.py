import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from bot.database.users import users_db
from bot.database.tasks import tasks_db

class UserManager:
    def __init__(self):
        self.user_cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.banned_users = set()
        self.muted_users = set()
        
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user with cache"""
        # Check cache
        if user_id in self.user_cache:
            cached = self.user_cache[user_id]
            if time.time() - cached['time'] < self.cache_timeout:
                return cached['data']
                
        # Get from database
        user = await users_db.get_user(user_id)
        
        # Update cache
        if user:
            self.user_cache[user_id] = {
                'data': user,
                'time': time.time()
            }
            
        return user
        
    async def add_user(
        self,
        user_id: int,
        username: str = "",
        first_name: str = ""
    ) -> bool:
        """Add new user"""
        await users_db.add_user(user_id, username, first_name)
        return True
        
    async def ban_user(self, user_id: int, reason: str = "") -> bool:
        """Ban user"""
        await users_db.ban_user(user_id)
        self.banned_users.add(user_id)
        return True
        
    async def unban_user(self, user_id: int) -> bool:
        """Unban user"""
        await users_db.unban_user(user_id)
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
        return True
        
    async def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        if user_id in self.banned_users:
            return True
        return await users_db.is_banned(user_id)
        
    async def mute_user(self, user_id: int, duration: int = 3600) -> bool:
        """Mute user for duration (seconds)"""
        self.muted_users.add(user_id)
        await users_db.update_user(user_id, {
            'muted_until': time.time() + duration
        })
        return True
        
    async def unmute_user(self, user_id: int) -> bool:
        """Unmute user"""
        if user_id in self.muted_users:
            self.muted_users.remove(user_id)
        await users_db.update_user(user_id, {
            'muted_until': None
        })
        return True
        
    async def is_muted(self, user_id: int) -> bool:
        """Check if user is muted"""
        if user_id in self.muted_users:
            return True
            
        user = await self.get_user(user_id)
        if user and user.get('muted_until'):
            if user['muted_until'] > time.time():
                return True
                
        return False
        
    async def get_user_stats(self, user_id: int) -> Dict:
        """Get comprehensive user statistics"""
        user = await self.get_user(user_id)
        if not user:
            return {}
            
        # Get task statistics
        user_tasks = await tasks_db.get_user_tasks(user_id, 100)
        
        stats = {
            'user_id': user_id,
            'first_name': user.get('first_name', ''),
            'username': user.get('username', ''),
            'joined_at': user.get('joined_at'),
            'total_tasks': user.get('total_tasks', 0),
            'total_downloads': user.get('total_downloads', 0),
            'total_uploads': user.get('total_uploads', 0),
            'is_premium': user.get('is_premium', False),
            'is_banned': user.get('is_banned', False),
            'tasks_completed': sum(1 for t in user_tasks if t.get('status') == 'completed'),
            'tasks_failed': sum(1 for t in user_tasks if t.get('status') == 'failed'),
        }
        
        return stats
        
    async def get_top_users(self, limit: int = 10) -> List[Dict]:
        """Get top users by task count"""
        users = await users_db.get_all_users()
        
        # Sort by total tasks
        sorted_users = sorted(
            users,
            key=lambda u: u.get('total_tasks', 0),
            reverse=True
        )
        
        return sorted_users[:limit]
        
    async def get_active_users(self, days: int = 7) -> List[Dict]:
        """Get users active in last N days"""
        users = await users_db.get_all_users()
        cutoff = time.time() - (days * 24 * 3600)
        
        active_users = []
        for user in users:
            last_seen = user.get('last_seen', 0)
            if isinstance(last_seen, datetime):
                last_seen = last_seen.timestamp()
            if last_seen > cutoff:
                active_users.append(user)
                
        return active_users
        
    async def update_user_activity(self, user_id: int):
        """Update user last seen time"""
        await users_db.update_user(user_id, {
            'last_seen': datetime.now()
        })
        
    async def get_user_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        user = await self.get_user(user_id)
        if user:
            return user.get('settings', {})
        return {}
        
    async def update_user_settings(self, user_id: int, settings: Dict):
        """Update user settings"""
        await users_db.update_user_settings(user_id, settings)
        
        # Update cache
        if user_id in self.user_cache:
            self.user_cache[user_id]['data']['settings'] = settings
            self.user_cache[user_id]['time'] = time.time()

# Create instance
user_manager = UserManager()
