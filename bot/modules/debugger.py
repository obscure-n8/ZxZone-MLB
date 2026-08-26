import os
import sys
import time
import asyncio
import traceback
from typing import Dict, Optional
from bot.config import Config

class Debugger:
    """Debug and troubleshooting system"""
    
    def __init__(self):
        self.debug_mode = False
        self.debug_info = {}
        self.performance_stats = {}
        
    def enable_debug(self):
        """Enable debug mode"""
        self.debug_mode = True
        
    def disable_debug(self):
        """Disable debug mode"""
        self.debug_mode = False
        
    async def debug_function(self, func, *args, **kwargs):
        """Debug a function with timing"""
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            if self.debug_mode:
                end_time = time.time()
                self.performance_stats[func.__name__] = {
                    'execution_time': end_time - start_time,
                    'success': True,
                    'timestamp': time.time()
                }
                
            return result
            
        except Exception as e:
            if self.debug_mode:
                end_time = time.time()
                self.performance_stats[func.__name__] = {
                    'execution_time': end_time - start_time,
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'timestamp': time.time()
                }
                
            raise
            
    async def get_bot_status(self) -> Dict:
        """Get detailed bot status"""
        status = {
            'python_version': sys.version,
            'platform': sys.platform,
            'debug_mode': self.debug_mode,
            'config': {
                'bot_username': Config.BOT_USERNAME,
                'owner_id': Config.OWNER_ID,
                'max_tasks': Config.BOT_MAX_TASKS
            },
            'performance': self.performance_stats,
            'timestamp': time.time()
        }
        
        return status
        
    async def diagnose_issue(self) -> Dict:
        """Diagnose common issues"""
        issues = []
        
        # Check config
        try:
            Config.validate_config()
        except Exception as e:
            issues.append(f'Config error: {str(e)}')
            
        # Check database
        try:
            from bot.database.db import db
            if not await db.ping():
                issues.append('Database connection failed')
        except:
            issues.append('Database not configured')
            
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            if free < 1024 * 1024 * 1024:  # < 1GB
                issues.append('Low disk space')
        except:
            pass
            
        # Check memory
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                issues.append('High memory usage')
        except:
            pass
            
        return {
            'healthy': len(issues) == 0,
            'issues': issues,
            'diagnosis_time': time.time()
        }
        
    async def get_performance_report(self) -> Dict:
        """Get performance report"""
        total_functions = len(self.performance_stats)
        successful = sum(1 for s in self.performance_stats.values() if s.get('success'))
        failed = total_functions - successful
        
        avg_time = sum(s.get('execution_time', 0) for s in self.performance_stats.values()) / total_functions if total_functions > 0 else 0
        
        return {
            'total_functions': total_functions,
            'successful': successful,
            'failed': failed,
            'average_time': avg_time,
            'detailed_stats': self.performance_stats
        }

# Create instance
debugger = Debugger()
