from datetime import datetime
from bot.database.db import db

class UserDB:
    def __init__(self):
        self.collection = db.users
        
    async def add_user(self, user_id: int, username: str = "", first_name: str = ""):
        """Add new user to database"""
        user = await self.get_user(user_id)
        if not user:
            await self.collection.insert_one({
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'joined_at': datetime.now(),
                'total_tasks': 0,
                'total_downloads': 0,
                'total_uploads': 0,
                'is_banned': False,
                'is_premium': False,
                'settings': {
                    'upload_mode': 'document',
                    'default_thumbnail': None,
                    'leech_limit': 0,
                    'mirror_limit': 0
                }
            })
        else:
            # Update user info
            await self.collection.update_one(
                {'user_id': user_id},
                {'$set': {
                    'username': username,
                    'first_name': first_name,
                    'last_seen': datetime.now()
                }}
            )
            
    async def get_user(self, user_id: int):
        """Get user from database"""
        return await self.collection.find_one({'user_id': user_id})
        
    async def update_user(self, user_id: int, update_data: dict):
        """Update user data"""
        await self.collection.update_one(
            {'user_id': user_id},
            {'$set': update_data}
        )
        
    async def increment_tasks(self, user_id: int):
        """Increment user task count"""
        await self.collection.update_one(
            {'user_id': user_id},
            {'$inc': {'total_tasks': 1}}
        )
        
    async def increment_downloads(self, user_id: int):
        """Increment user download count"""
        await self.collection.update_one(
            {'user_id': user_id},
            {'$inc': {'total_downloads': 1}}
        )
        
    async def increment_uploads(self, user_id: int):
        """Increment user upload count"""
        await self.collection.update_one(
            {'user_id': user_id},
            {'$inc': {'total_uploads': 1}}
        )
        
    async def ban_user(self, user_id: int):
        """Ban user"""
        await self.update_user(user_id, {'is_banned': True})
        
    async def unban_user(self, user_id: int):
        """Unban user"""
        await self.update_user(user_id, {'is_banned': False})
        
    async def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        user = await self.get_user(user_id)
        return user.get('is_banned', False) if user else False
        
    async def set_premium(self, user_id: int, is_premium: bool = True):
        """Set user premium status"""
        await self.update_user(user_id, {'is_premium': is_premium})
        
    async def get_user_settings(self, user_id: int) -> dict:
        """Get user settings"""
        user = await self.get_user(user_id)
        if user:
            return user.get('settings', {})
        return {}
        
    async def update_user_settings(self, user_id: int, settings: dict):
        """Update user settings"""
        await self.collection.update_one(
            {'user_id': user_id},
            {'$set': {'settings': settings}}
        )
        
    async def get_all_users(self) -> list:
        """Get all users"""
        users = []
        async for user in self.collection.find():
            users.append(user)
        return users
        
    async def get_total_users(self) -> int:
        """Get total user count"""
        return await self.collection.count_documents({})
        
    async def get_active_today(self) -> int:
        """Get users active today"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.collection.count_documents({'last_seen': {'$gte': today}})

# Create instance
users_db = UserDB()
