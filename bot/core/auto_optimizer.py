import gc
import asyncio
import psutil
from typing import Dict, Optional
from bot.config import Config
from bot.core.smart_env import smart_env

class AutoOptimizer:
    """Maximum performance optimization system"""
    
    def __init__(self):
        self.env = smart_env
        self.is_active = self.env.optimization_needed
        self.level = self.env.get_optimization_level()
        self.workers = 200
        
    async def apply_optimizations(self):
        """Apply optimized settings"""
        if not self.is_active:
            # VPS - Maximum Power Mode
            self.apply_vps_maximum_power()
            return
            
        if self.level == 'high':
            self.apply_heroku_free_optimization()
        elif self.level == 'medium':
            self.apply_heroku_standard_optimization()
        elif self.level == 'low':
            self.apply_heroku_performance_optimization()
            
    def apply_vps_maximum_power(self):
        """VPS Maximum Power - No limits"""
        # Max tasks
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS < 100:
            Config.BOT_MAX_TASKS = 100
            
        if Config.USER_MAX_TASKS == 0 or Config.USER_MAX_TASKS < 10:
            Config.USER_MAX_TASKS = 10
            
        if Config.QUEUE_LIMIT == 0 or Config.QUEUE_LIMIT < 100:
            Config.QUEUE_LIMIT = 100
            
        # Enable all features
        Config.DISABLE_STREAM = False
        Config.DISABLE_SEARCH = False
        Config.DISABLE_MULTI = False
        Config.DISABLE_BULK = False
        Config.DISABLE_SEED = False
        Config.DISABLE_FF_MODE = False
        Config.DISABLE_JD = False
        Config.DISABLE_NZB = False
        Config.DISABLE_RSS = False
        Config.DISABLE_YTDLP = False
        Config.DISABLE_MEGA = False
        Config.DISABLE_TORRENTS = False
        Config.DISABLE_LEECH = False
        Config.DISABLE_MIRROR = False
        
        # Max workers
        self.workers = 500
        
        # Max split size for faster downloads
        Config.LEECH_SPLIT_SIZE = 0  # No limit
        
        # Enable 4K
        Config.MAX_VIDEO_HEIGHT = 2160
        
    def apply_heroku_free_optimization(self):
        """Heroku Free - Smart optimization"""
        # Smart task limits
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS > 15:
            Config.BOT_MAX_TASKS = 15
            
        if Config.USER_MAX_TASKS == 0 or Config.USER_MAX_TASKS > 3:
            Config.USER_MAX_TASKS = 3
            
        if Config.QUEUE_LIMIT == 0 or Config.QUEUE_LIMIT > 10:
            Config.QUEUE_LIMIT = 10
            
        # Disable only heavy features
        Config.DISABLE_STREAM = True
        Config.DISABLE_MULTI = True
        Config.DISABLE_SEED = True
        Config.DISABLE_NZB = True
        
        # Keep essential features enabled
        Config.DISABLE_SEARCH = False
        Config.DISABLE_BULK = False
        Config.DISABLE_FF_MODE = False
        Config.DISABLE_JD = False
        Config.DISABLE_RSS = False
        Config.DISABLE_YTDLP = False
        Config.DISABLE_MEGA = False
        Config.DISABLE_TORRENTS = False
        Config.DISABLE_LEECH = False
        Config.DISABLE_MIRROR = False
        
        # Moderate workers
        self.workers = 100
        
        # 1080p limit
        Config.MAX_VIDEO_HEIGHT = 1080
        
    def apply_heroku_standard_optimization(self):
        """Heroku Standard - Better optimization"""
        # Good task limits
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS > 30:
            Config.BOT_MAX_TASKS = 30
            
        if Config.USER_MAX_TASKS == 0 or Config.USER_MAX_TASKS > 5:
            Config.USER_MAX_TASKS = 5
            
        if Config.QUEUE_LIMIT == 0 or Config.QUEUE_LIMIT > 20:
            Config.QUEUE_LIMIT = 20
            
        # Disable minimal features
        Config.DISABLE_STREAM = True
        Config.DISABLE_MULTI = True
        
        # Keep most features
        Config.DISABLE_SEARCH = False
        Config.DISABLE_BULK = False
        Config.DISABLE_FF_MODE = False
        Config.DISABLE_JD = False
        Config.DISABLE_NZB = False
        Config.DISABLE_RSS = False
        Config.DISABLE_YTDLP = False
        Config.DISABLE_MEGA = False
        Config.DISABLE_TORRENTS = False
        Config.DISABLE_LEECH = False
        Config.DISABLE_MIRROR = False
        Config.DISABLE_SEED = False
        
        # Good workers
        self.workers = 150
        
        # 4K support
        Config.MAX_VIDEO_HEIGHT = 2160
        
    def apply_heroku_performance_optimization(self):
        """Heroku Performance - Near VPS"""
        # High task limits
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS > 50:
            Config.BOT_MAX_TASKS = 50
            
        if Config.USER_MAX_TASKS == 0 or Config.USER_MAX_TASKS > 8:
            Config.USER_MAX_TASKS = 8
            
        if Config.QUEUE_LIMIT == 0 or Config.QUEUE_LIMIT > 40:
            Config.QUEUE_LIMIT = 40
            
        # Almost all features enabled
        Config.DISABLE_STREAM = False
        Config.DISABLE_SEARCH = False
        Config.DISABLE_MULTI = False
        Config.DISABLE_BULK = False
        Config.DISABLE_SEED = False
        Config.DISABLE_FF_MODE = False
        Config.DISABLE_JD = False
        Config.DISABLE_NZB = False
        Config.DISABLE_RSS = False
        Config.DISABLE_YTDLP = False
        Config.DISABLE_MEGA = False
        Config.DISABLE_TORRENTS = False
        Config.DISABLE_LEECH = False
        Config.DISABLE_MIRROR = False
        
        # High workers
        self.workers = 300
        
        # 4K support
        Config.MAX_VIDEO_HEIGHT = 2160
        
    def get_workers(self) -> int:
        """Get worker count"""
        return self.workers
        
    async def start_background_optimization(self):
        """Start background optimization"""
        asyncio.create_task(self._optimization_loop())
        
    async def _optimization_loop(self):
        """Background optimization loop"""
        while True:
            try:
                # For VPS - keep full power
                if not self.is_active:
                    await asyncio.sleep(600)
                    continue
                    
                # For Heroku - optimize memory
                gc.collect()
                
                # Check memory
                memory = psutil.Process().memory_info().rss / (1024 * 1024)
                
                if memory > 450:
                    # High memory - reduce load
                    Config.QUEUE_LIMIT = min(Config.QUEUE_LIMIT, 5)
                elif memory > 350:
                    Config.QUEUE_LIMIT = min(Config.QUEUE_LIMIT, 10)
                    
                await asyncio.sleep(300)
                
            except:
                await asyncio.sleep(60)

# Create instance
auto_optimizer = AutoOptimizer()
