import os
import asyncio
import psutil
from typing import Dict
from bot.config import Config

class VPSOptimizer:
    """VPS optimization for 8GB RAM system"""
    
    def __init__(self):
        self.total_ram = psutil.virtual_memory().total
        self.total_cpu = psutil.cpu_count()
        self.ram_gb = self.total_ram / (1024**3)
        self.optimization_level = self.get_level()
        
    def get_level(self) -> str:
        """Get optimization level based on resources"""
        if self.ram_gb >= 8 and self.total_cpu >= 4:
            return 'maximum'
        elif self.ram_gb >= 4 and self.total_cpu >= 2:
            return 'high'
        else:
            return 'standard'
            
    def get_max_tasks(self) -> int:
        """Get maximum tasks based on RAM"""
        # 1GB RAM = ~12 tasks
        return int(self.ram_gb * 12)
        
    def get_max_workers(self) -> int:
        """Get workers based on CPU"""
        # 1 CPU = ~50 workers
        return self.total_cpu * 50
        
    def get_split_size(self) -> int:
        """Get split size based on RAM"""
        if self.ram_gb >= 8:
            return 4 * 1024 * 1024 * 1024  # 4GB
        elif self.ram_gb >= 4:
            return 3 * 1024 * 1024 * 1024  # 3GB
        else:
            return 2 * 1024 * 1024 * 1024  # 2GB
            
    async def apply_optimizations(self):
        """Apply VPS optimizations"""
        max_tasks = self.get_max_tasks()
        workers = self.get_max_workers()
        split_size = self.get_split_size()
        
        # Update Config
        if Config.BOT_MAX_TASKS == 0 or Config.BOT_MAX_TASKS > max_tasks:
            Config.BOT_MAX_TASKS = max_tasks
            
        if Config.USER_MAX_TASKS == 0 or Config.USER_MAX_TASKS > 10:
            Config.USER_MAX_TASKS = 10
            
        Config.LEECH_SPLIT_SIZE = split_size
        
        # Enable all features
        Config.DISABLE_STREAM = False
        Config.DISABLE_SEARCH = False
        Config.DISABLE_MULTI = False
        Config.DISABLE_BULK = False
        
        return {
            'max_tasks': Config.BOT_MAX_TASKS,
            'workers': workers,
            'split_size': split_size,
            'ram': self.ram_gb,
            'cpu': self.total_cpu
        }
        
    def get_stats(self) -> Dict:
        """Get VPS stats"""
        return {
            'ram_gb': self.ram_gb,
            'cpu_count': self.total_cpu,
            'max_tasks': self.get_max_tasks(),
            'workers': self.get_max_workers(),
            'split_size': self.get_split_size(),
            'level': self.optimization_level
        }

# Create instance
vps_optimizer = VPSOptimizer()
