import re
import asyncio
from typing import List, Dict, Optional
from bot.database.db import db

class FilterSystem:
    def __init__(self):
        self.collection = db.filters
        self.filter_cache = {}
        self.cache_timeout = 300
        
    async def add_filter(
        self,
        chat_id: int,
        keyword: str,
        file_id: str,
        file_name: str,
        file_size: int,
        file_type: str = "document"
    ) -> bool:
        """Add filter for chat"""
        filter_data = {
            'chat_id': chat_id,
            'keyword': keyword.lower(),
            'file_id': file_id,
            'file_name': file_name,
            'file_size': file_size,
            'file_type': file_type,
            'created_at': asyncio.get_event_loop().time()
        }
        
        await self.collection.update_one(
            {'chat_id': chat_id, 'keyword': keyword.lower()},
            {'$set': filter_data},
            upsert=True
        )
        
        # Clear cache
        self.filter_cache.pop(chat_id, None)
        
        return True
        
    async def remove_filter(self, chat_id: int, keyword: str) -> bool:
        """Remove filter"""
        result = await self.collection.delete_one({
            'chat_id': chat_id,
            'keyword': keyword.lower()
        })
        
        # Clear cache
        self.filter_cache.pop(chat_id, None)
        
        return result.deleted_count > 0
        
    async def get_filters(self, chat_id: int) -> List[Dict]:
        """Get all filters for chat"""
        # Check cache
        if chat_id in self.filter_cache:
            return self.filter_cache[chat_id]
            
        filters = []
        cursor = self.collection.find({'chat_id': chat_id})
        async for filter_data in cursor:
            filters.append(filter_data)
            
        # Update cache
        self.filter_cache[chat_id] = filters
        
        return filters
        
    async def search_filter(self, chat_id: int, query: str) -> Optional[Dict]:
        """Search for matching filter"""
        filters = await self.get_filters(chat_id)
        
        # Exact match first
        query_lower = query.lower()
        for filter_data in filters:
            if filter_data['keyword'] == query_lower:
                return filter_data
                
        # Partial match
        for filter_data in filters:
            if filter_data['keyword'] in query_lower or query_lower in filter_data['keyword']:
                return filter_data
                
        return None
        
    async def get_all_filter_chats(self) -> List[int]:
        """Get all chats with filters"""
        chats = await self.collection.distinct('chat_id')
        return chats
        
    async def count_filters(self, chat_id: int) -> int:
        """Count filters for chat"""
        return await self.collection.count_documents({'chat_id': chat_id})
        
    async def clear_filters(self, chat_id: int) -> bool:
        """Clear all filters for chat"""
        result = await self.collection.delete_many({'chat_id': chat_id})
        self.filter_cache.pop(chat_id, None)
        return result.deleted_count > 0

# Create instance
filter_system = FilterSystem()
