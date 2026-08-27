import os
import time
import asyncio
from typing import Dict, List, Optional
from bot.config import Config

class BatchProcessor:
    """Batch processing system"""
    
    def __init__(self):
        self.batch_tasks = {}
        self.max_batch_size = 10
        
    async def process_batch(
        self,
        urls: List[str],
        task_type: str = 'leech',
        user_id: Optional[int] = None
    ) -> Dict:
        """Process multiple URLs in batch"""
        try:
            batch_id = f"batch_{int(time.time())}"
            
            self.batch_tasks[batch_id] = {
                'urls': urls,
                'task_type': task_type,
                'user_id': user_id,
                'status': 'processing',
                'completed': 0,
                'failed': 0,
                'total': len(urls),
                'start_time': time.time(),
                'results': []
            }
            
            # Process each URL
            for i, url in enumerate(urls, 1):
                try:
                    result = await self.process_single(url, task_type)
                    
                    if result['success']:
                        self.batch_tasks[batch_id]['completed'] += 1
                    else:
                        self.batch_tasks[batch_id]['failed'] += 1
                        
                    self.batch_tasks[batch_id]['results'].append({
                        'url': url,
                        'success': result['success'],
                        'result': result
                    })
                    
                except:
                    self.batch_tasks[batch_id]['failed'] += 1
                    
            self.batch_tasks[batch_id]['status'] = 'completed'
            
            return self.batch_tasks[batch_id]
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def process_single(self, url: str, task_type: str) -> Dict:
        """Process single URL"""
        try:
            from bot.modules.smart_downloader import smart_downloader
            
            file_path = os.path.join(Config.DOWNLOAD_DIR, f"batch_{int(time.time())}")
            result = await smart_downloader.smart_download(url, file_path)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def get_batch_status(self, batch_id: str) -> Dict:
        """Get batch processing status"""
        if batch_id in self.batch_tasks:
            task = self.batch_tasks[batch_id]
            
            return {
                'batch_id': batch_id,
                'status': task['status'],
                'completed': task['completed'],
                'failed': task['failed'],
                'total': task['total'],
                'progress': (task['completed'] + task['failed']) / task['total'] * 100 if task['total'] > 0 else 0
            }
            
        return {}
        
    async def cancel_batch(self, batch_id: str) -> bool:
        """Cancel batch processing"""
        if batch_id in self.batch_tasks:
            self.batch_tasks[batch_id]['status'] = 'cancelled'
            return True
        return False

# Create instance
batch_processor = BatchProcessor()
