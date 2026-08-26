import importlib
import asyncio
from typing import Dict, Optional

class LazyImports:
    """Lazy import system - only loads modules when needed"""
    
    def __init__(self):
        self.loaded = {}
        self.loading = {}
        self.is_optimized = False
        
    def set_optimized(self, is_optimized: bool):
        """Set optimization mode"""
        self.is_optimized = is_optimized
        
    async def get_module(self, module_name: str):
        """Get module with lazy loading"""
        # If not optimized, import directly
        if not self.is_optimized:
            return importlib.import_module(module_name)
            
        # Check cache
        if module_name in self.loaded:
            return self.loaded[module_name]
            
        # Check if loading
        if module_name in self.loading:
            return await self.loading[module_name]
            
        # Load in background
        task = asyncio.create_task(self._load_module(module_name))
        self.loading[module_name] = task
        
        try:
            module = await task
            self.loaded[module_name] = module
            return module
        finally:
            del self.loading[module_name]
            
    async def _load_module(self, module_name: str):
        """Load module"""
        try:
            return importlib.import_module(module_name)
        except:
            return None
            
    async def unload_module(self, module_name: str):
        """Unload module to free memory"""
        if not self.is_optimized:
            return
            
        if module_name in self.loaded:
            del self.loaded[module_name]
            
        import sys
        if module_name in sys.modules:
            del sys.modules[module_name]
            
        import gc
        gc.collect()

# Create instance
lazy_imports = LazyImports()
