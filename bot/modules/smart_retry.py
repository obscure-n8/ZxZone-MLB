import time
import asyncio
from typing import Optional, Dict, Callable
from bot.helpers.utils import Utils

class SmartRetry:
    """Intelligent retry system"""
    
    def __init__(self):
        self.retry_stats = {}
        self.retry_configs = {
            'download': {
                'max_retries': 5,
                'base_delay': 2,
                'max_delay': 60,
                'backoff_factor': 2
            },
            'upload': {
                'max_retries': 3,
                'base_delay': 5,
                'max_delay': 30,
                'backoff_factor': 1.5
            },
            'api': {
                'max_retries': 4,
                'base_delay': 1,
                'max_delay': 15,
                'backoff_factor': 2
            }
        }
        
    async def execute_with_retry(
        self,
        func: Callable,
        task_type: str = 'api',
        *args,
        **kwargs
    ) -> Optional[any]:
        """Execute function with smart retry"""
        config = self.retry_configs.get(task_type, self.retry_configs['api'])
        
        for attempt in range(config['max_retries']):
            try:
                # Try to execute
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                # Check if retryable error
                if not self.is_retryable_error(e):
                    raise
                    
                # Calculate delay
                delay = self.calculate_delay(attempt, config)
                
                # Update stats
                self.update_stats(task_type, attempt, e)
                
                # Wait before retry
                await asyncio.sleep(delay)
                
        return None
        
    def is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable"""
        retryable_errors = [
            'ConnectionError',
            'TimeoutError',
            'NetworkError',
            'ServerError',
            '500',
            '502',
            '503',
            '504',
            'RateLimit',
            'TooManyRequests',
        ]
        
        error_str = str(error)
        return any(e in error_str for e in retryable_errors)
        
    def calculate_delay(self, attempt: int, config: Dict) -> float:
        """Calculate retry delay with exponential backoff"""
        delay = config['base_delay'] * (config['backoff_factor'] ** attempt)
        return min(delay, config['max_delay'])
        
    def update_stats(self, task_type: str, attempt: int, error: Exception):
        """Update retry statistics"""
        if task_type not in self.retry_stats:
            self.retry_stats[task_type] = {
                'total_retries': 0,
                'successful_retries': 0,
                'failed_retries': 0,
                'errors': {}
            }
            
        stats = self.retry_stats[task_type]
        stats['total_retries'] += 1
        
        error_type = type(error).__name__
        if error_type not in stats['errors']:
            stats['errors'][error_type] = 0
        stats['errors'][error_type] += 1
        
    async def download_with_smart_retry(
        self,
        url: str,
        file_path: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download with smart retry"""
        from bot.modules.downloader import downloader
        
        async def download_task():
            return await downloader.download_file(url, file_path, progress_callback)
            
        result = await self.execute_with_retry(
            download_task,
            'download'
        )
        
        return result if result is not None else False
        
    async def upload_with_smart_retry(
        self,
        client,
        file_path: str,
        chat_id: int,
        **kwargs
    ) -> Dict:
        """Upload with smart retry"""
        from bot.modules.uploader import uploader
        
        async def upload_task():
            return await uploader.upload_to_telegram(
                client, file_path, chat_id, **kwargs
            )
            
        result = await self.execute_with_retry(
            upload_task,
            'upload'
        )
        
        return result if result else (False, "Upload failed after retries")
        
    async def get_retry_stats(self) -> Dict:
        """Get retry statistics"""
        return self.retry_stats
        
    async def clear_stats(self):
        """Clear retry statistics"""
        self.retry_stats.clear()

# Create instance
smart_retry = SmartRetry()
