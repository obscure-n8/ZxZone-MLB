import time
import hashlib
import asyncio
from typing import Optional, Dict, List
from bot.database.db import db

class LinkGenerator:
    def __init__(self):
        self.collection = db.links
        self.link_cache = {}
        self.cache_timeout = 3600
        
    async def generate_link(
        self,
        user_id: int,
        file_id: str,
        file_name: str,
        expiry: int = 86400,  # 24 hours default
        max_downloads: int = 0,  # 0 = unlimited
        password: str = None
    ) -> str:
        """Generate download link"""
        # Create unique token
        token = self._generate_token(user_id, file_id)
        
        link_data = {
            'token': token,
            'user_id': user_id,
            'file_id': file_id,
            'file_name': file_name,
            'created_at': time.time(),
            'expiry': time.time() + expiry,
            'max_downloads': max_downloads,
            'downloads': 0,
            'password': password,
            'active': True
        }
        
        await self.collection.insert_one(link_data)
        
        # Cache
        self.link_cache[token] = link_data
        
        return token
        
    def _generate_token(self, user_id: int, file_id: str) -> str:
        """Generate unique token"""
        data = f"{user_id}_{file_id}_{time.time()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
        
    async def validate_link(self, token: str, password: str = None) -> Optional[Dict]:
        """Validate download link"""
        # Check cache first
        if token in self.link_cache:
            link_data = self.link_cache[token]
        else:
            link_data = await self.collection.find_one({'token': token})
            if link_data:
                self.link_cache[token] = link_data
                
        if not link_data:
            return None
            
        # Check if active
        if not link_data['active']:
            return None
            
        # Check expiry
        if time.time() > link_data['expiry']:
            await self.deactivate_link(token)
            return None
            
        # Check download limit
        if link_data['max_downloads'] > 0:
            if link_data['downloads'] >= link_data['max_downloads']:
                await self.deactivate_link(token)
                return None
                
        # Check password
        if link_data.get('password'):
            if password != link_data['password']:
                return {'error': 'password_required'}
                
        return link_data
        
    async def increment_download(self, token: str):
        """Increment download count"""
        await self.collection.update_one(
            {'token': token},
            {'$inc': {'downloads': 1}}
        )
        
        # Update cache
        if token in self.link_cache:
            self.link_cache[token]['downloads'] += 1
            
    async def deactivate_link(self, token: str) -> bool:
        """Deactivate link"""
        await self.collection.update_one(
            {'token': token},
            {'$set': {'active': False}}
        )
        
        if token in self.link_cache:
            self.link_cache[token]['active'] = False
            
        return True
        
    async def get_user_links(self, user_id: int) -> List[Dict]:
        """Get all links created by user"""
        links = []
        cursor = self.collection.find({'user_id': user_id})
        async for link in cursor:
            links.append(link)
        return links
        
    async def cleanup_expired_links(self):
        """Clean up expired links"""
        current_time = time.time()
        
        result = await self.collection.update_many(
            {'expiry': {'$lt': current_time}, 'active': True},
            {'$set': {'active': False}}
        )
        
        # Clear cache
        self.link_cache.clear()
        
        return result.modified_count
        
    async def get_link_stats(self, token: str) -> Dict:
        """Get link statistics"""
        link_data = await self.collection.find_one({'token': token})
        
        if not link_data:
            return {}
            
        return {
            'created_at': link_data['created_at'],
            'expiry': link_data['expiry'],
            'downloads': link_data['downloads'],
            'max_downloads': link_data['max_downloads'],
            'active': link_data['active'],
            'time_left': max(0, link_data['expiry'] - time.time())
        }

# Create instance
link_generator = LinkGenerator()
