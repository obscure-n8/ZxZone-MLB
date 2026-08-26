import gc
import asyncio
from typing import Dict, Optional
from bot.config import Config
from bot.core.smart_env import smart_env

class AutoOptimizer:
    """Automatic optimization system"""
    
    def __init__(self):
        self.env = smart_env
        self.is_active = self.env.optimization_needed
        self.level = self.env.get_optimization_level()
        
    async def apply_optimizations(self):
        """Apply optimizations based on environment"""
        if not self.is_active:
            # VPS/Windows with enough RAM - Full power
            self.apply_full_power()
            return
            
        if self.level == 'high':
            self.apply_high_optimization()
        elif self.level == 'medium':
            self.apply_medium_optimization()
        elif self.level == 'low':
            self.apply_low_optimization()
            
    def apply_full_power(self):
        """Full power settings for VPS"""
        # No changes - Keep all features enabled
        pass
        
    def apply_high_optimization(self):
        """High optimization for 512MB RAM environments"""
        # Reduce task limits
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS > 10:
            Config.BOT_MAX_TASKS = 10
            
        if Config.USER_MAX_TASKS == 0 or Config.USER_MAX_TASKS > 2:
            Config.USER_MAX_TASKS = 2
            
        if Config.QUEUE_LIMIT == 0 or Config.QUEUE_LIMIT > 5:
            Config.QUEUE_LIMIT = 5
            
        # Disable heavy features
        Config.DISABLE_STREAM = True
        Config.DISABLE_SEARCH = True
        Config.DISABLE_MULTI = True
        Config.DISABLE_BULK = True
        Config.DISABLE_SEED = True
        
        # Reduce workers
        self.workers = 50
        
    def apply_medium_optimization(self):
        """Medium optimization for 1GB RAM environments"""
        # Moderate task limits
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS > 25:
            Config.BOT_MAX_TASKS = 25
            
        if Config.USER_MAX_TASKS == 0 or Config.USER_MAX_TASKS > 4:
            Config.USER_MAX_TASKS = 4
            
        if Config.QUEUE_LIMIT == 0 or Config.QUEUE_LIMIT > 12:
            Config.QUEUE_LIMIT = 12
            
        # Disable some features
        Config.DISABLE_STREAM = True
        Config.DISABLE_MULTI = True
        
        # Moderate workers
        self.workers = 100
        
    def apply_low_optimization(self):
        """Low optimization for 2GB+ RAM environments"""
        # Slight reduction
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS > 40:
            Config.BOT_MAX_TASKS = 40
            
        if Config.QUEUE_LIMIT == 0 or Config.QUEUE_LIMIT > 20:
            Config.QUEUE_LIMIT = 20
            
        # Keep most features
        self.workers = 150
        
    def get_workers(self) -> int:
        """Get optimized worker count"""
        if not self.is_active:
            return 200  # Full power for VPS
            
        return getattr(self, 'workers', 100)
        
    async def start_background_optimization(self):
        """Start background optimization loop"""
        if not self.is_active:
            return  # No need for VPS
            
        asyncio.create_task(self._optimization_loop())
        
    async def _optimization_loop(self):
        """Background optimization loop"""
        while True:
            try:
                # Garbage collection
                gc.collect()
                
                # Clear caches
                import functools
                for obj in gc.get_objects():
                    if isinstance(obj, functools._lru_cache_wrapper):
                        obj.cache_clear()
                        
                await asyncio.sleep(300)  # Every 5 minutes
                
            except:
                await asyncio.sleep(60)

# Create instance
auto_optimizer = AutoOptimizer()
