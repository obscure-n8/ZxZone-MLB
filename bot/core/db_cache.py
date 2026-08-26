import time
import asyncio
from typing import Dict, Optional, List

class DatabaseCache:
    """Smart database caching system"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300
        self.is_optimized = False
        self.hit_count = 0
        self.miss_count = 0
        
    def set_optimized(self, is_optimized: bool):
        """Set optimization mode"""
        self.is_optimized = is_optimized
        
        if not is_optimized:
            # VPS - longer cache
            self.cache_timeout = 600
        else:
            # Heroku - shorter cache to save memory
            self.cache_timeout = 300
            
    async def get(self, key: str, fetch_func=None):
        """Get from cache or fetch from database"""
        # If not optimized and key in cache
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached['time'] < self.cache_timeout:
                self.hit_count += 1
                return cached['data']
                
        # Fetch from database
        if fetch_func:
            data = await fetch_func()
            self.cache[key] = {
                'data': data,
                'time': time.time()
            }
            self.miss_count += 1
            return data
            
        return None
        
    async def set(self, key: str, data):
        """Set cache"""
        self.cache[key] = {
            'data': data,
            'time': time.time()
        }
        
    async def clear(self):
        """Clear cache"""
        self.cache.clear()
        
    async def cleanup(self):
        """Clean up expired cache"""
        current_time = time.time()
        
        for key in list(self.cache.keys()):
            if current_time - self.cache[key]['time'] > self.cache_timeout:
                del self.cache[key]
                
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'cache_size': len(self.cache),
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'timeout': self.cache_timeout,
            'optimized': self.is_optimized
        }

# Create instance
db_cache = DatabaseCache()
