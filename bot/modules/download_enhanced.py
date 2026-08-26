import os
import asyncio
import aiohttp
import aiofiles
from typing import Dict, Optional, Callable
from bot.config import Config

class EnhancedDownloader:
    """Enhanced download system with advanced features"""
    
    def __init__(self):
        self.active_downloads = {}
        self.download_history = []
        self.speed_limits = {}
        
    async def download_with_features(
        self,
        url: str,
        file_path: str,
        progress_callback: Optional[Callable] = None,
        speed_limit: int = 0,  # 0 = unlimited
        max_retries: int = 5,
        resume: bool = True
    ) -> Dict:
        """Download with advanced features"""
        try:
            # Check if partial file exists for resume
            downloaded_bytes = 0
            if resume and os.path.exists(file_path):
                downloaded_bytes = os.path.getsize(file_path)
                
            headers = {}
            if downloaded_bytes > 0:
                headers['Range'] = f'bytes={downloaded_bytes}-'
                
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    
                    if response.status == 206:  # Partial content
                        mode = 'ab'
                    elif response.status == 200:
                        mode = 'wb'
                        downloaded_bytes = 0
                    else:
                        return {'success': False, 'error': f'HTTP {response.status}'}
                        
                    total_size = downloaded_bytes + int(response.headers.get('content-length', 0))
                    start_time = asyncio.get_event_loop().time()
                    last_speed_check = start_time
                    bytes_since_check = 0
                    
                    async with aiofiles.open(file_path, mode) as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            # Apply speed limit
                            if speed_limit > 0:
                                bytes_since_check += len(chunk)
                                current_time = asyncio.get_event_loop().time()
                                elapsed = current_time - last_speed_check
                                
                                if elapsed >= 1:
                                    current_speed = bytes_since_check / elapsed
                                    if current_speed > speed_limit:
                                        wait_time = (bytes_since_check / speed_limit) - elapsed
                                        if wait_time > 0:
                                            await asyncio.sleep(wait_time)
                                            
                                    bytes_since_check = 0
                                    last_speed_check = current_time
                                    
                            await f.write(chunk)
                            downloaded_bytes += len(chunk)
                            
                            if progress_callback:
                                await progress_callback(
                                    downloaded=downloaded_bytes,
                                    total=total_size,
                                    start_time=start_time
                                )
                                
            return {
                'success': True,
                'file': file_path,
                'size': downloaded_bytes,
                'resumed': downloaded_bytes > 0
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def download_with_mirror_fallback(
        self,
        urls: List[str],
        file_path: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """Download with mirror fallback"""
        for i, url in enumerate(urls):
            result = await self.download_with_features(url, file_path, progress_callback)
            
            if result['success']:
                return {
                    'success': True,
                    'file': file_path,
                    'mirror_used': i + 1,
                    'total_mirrors': len(urls)
                }
                
        return {'success': False, 'error': 'All mirrors failed'}
        
    async def download_with_schedule(
        self,
        url: str,
        file_path: str,
        schedule_time: Optional[float] = None
    ) -> Dict:
        """Download with scheduling"""
        if schedule_time:
            current_time = asyncio.get_event_loop().time()
            if schedule_time > current_time:
                wait_time = schedule_time - current_time
                await asyncio.sleep(wait_time)
                
        return await self.download_with_features(url, file_path)
        
    async def set_user_speed_limit(self, user_id: int, speed_limit: int):
        """Set speed limit for user"""
        self.speed_limits[user_id] = speed_limit
        
    async def get_user_speed_limit(self, user_id: int) -> int:
        """Get user speed limit"""
        return self.speed_limits.get(user_id, 0)
        
    async def cancel_download(self, url: str) -> bool:
        """Cancel active download"""
        if url in self.active_downloads:
            self.active_downloads[url]['cancelled'] = True
            return True
        return False
        
    async def get_download_stats(self) -> Dict:
        """Get download statistics"""
        return {
            'active': len(self.active_downloads),
            'completed': len(self.download_history),
            'speed_limits': len(self.speed_limits)
        }

# Create instance
enhanced_downloader = EnhancedDownloader()
