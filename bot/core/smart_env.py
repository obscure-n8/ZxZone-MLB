import os
import platform
import psutil
from typing import Dict

class SmartEnvironment:
    """Smart environment detection and optimization system"""
    
    def __init__(self):
        self.env_type = self.detect_environment()
        self.ram_limit = self.get_ram_limit()
        self.optimization_needed = self.check_optimization_needed()
        
    def detect_environment(self) -> str:
        """Detect environment type"""
        # Heroku detection
        if 'DYNO' in os.environ:
            return 'heroku'
            
        # Docker detection
        if os.path.exists('/.dockerenv'):
            return 'docker'
            
        # VPS detection (Linux without Docker)
        if platform.system() == 'Linux':
            return 'vps'
            
        # Windows
        if platform.system() == 'Windows':
            return 'windows'
            
        # Mac
        if platform.system() == 'Darwin':
            return 'mac'
            
        return 'unknown'
        
    def get_ram_limit(self) -> int:
        """Get RAM limit in MB"""
        try:
            # Heroku
            if self.env_type == 'heroku':
                dyno_type = os.getenv('DYNO_TYPE', 'free')
                ram_limits = {
                    'free': 512,
                    'eco': 512,
                    'hobby': 512,
                    'standard-1x': 512,
                    'standard-2x': 1024,
                    'performance-m': 2560,
                    'performance-l': 14336,
                }
                return ram_limits.get(dyno_type, 512)
                
            # Docker
            if self.env_type == 'docker':
                try:
                    with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                        limit = int(f.read().strip())
                    return limit // (1024 * 1024)
                except:
                    pass
                    
            # VPS/Windows/Mac - Get total RAM
            if self.env_type in ['vps', 'windows', 'mac']:
                total_ram = psutil.virtual_memory().total
                return total_ram // (1024 * 1024)
                
        except:
            pass
            
        return 512  # Default to 512MB if unknown
        
    def check_optimization_needed(self) -> bool:
        """Check if optimization is needed"""
        # VPS with 1GB+ RAM doesn't need optimization
        if self.env_type == 'vps' and self.ram_limit >= 1024:
            return False
            
        # Windows with 2GB+ RAM doesn't need optimization
        if self.env_type == 'windows' and self.ram_limit >= 2048:
            return False
            
        # Mac with 2GB+ RAM doesn't need optimization
        if self.env_type == 'mac' and self.ram_limit >= 2048:
            return False
            
        # Heroku always needs optimization
        if self.env_type == 'heroku':
            return True
            
        # Docker with less than 1GB needs optimization
        if self.env_type == 'docker' and self.ram_limit < 1024:
            return True
            
        return False
        
    def get_optimization_level(self) -> str:
        """Get optimization level"""
        if not self.optimization_needed:
            return 'none'
            
        if self.ram_limit <= 512:
            return 'high'
        elif self.ram_limit <= 1024:
            return 'medium'
        else:
            return 'low'
            
    def get_info(self) -> Dict:
        """Get environment info"""
        return {
            'environment': self.env_type,
            'ram_limit_mb': self.ram_limit,
            'optimization_needed': self.optimization_needed,
            'optimization_level': self.get_optimization_level(),
            'platform': platform.system(),
            'python_version': platform.python_version()
        }

# Create instance
smart_env = SmartEnvironment()
