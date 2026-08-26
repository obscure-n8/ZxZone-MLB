import os
import asyncio
import aiohttp
import aiofiles
from typing import Optional, Callable
from bot.config import Config
from bot.helpers.utils import Utils

class DownloadManager:
    def __init__(self):
        self.active_downloads = {}
        self.download_queue = asyncio.Queue()
        
    async def download_file(
        self,
        url: str,
        file_path: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download file with progress tracking"""
        try:
            # Create directory if not exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                    
                    # Get total size
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    start_time = asyncio.get_event_loop().time()
                    
                    # Download file
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Call progress callback
                            if progress_callback and total_size > 0:
                                await progress_callback(
                                    downloaded=downloaded,
                                    total=total_size,
                                    start_time=start_time
                                )
                            
            return True
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return False
    
    async def download_with_retry(
        self,
        url: str,
        file_path: str,
        max_retries: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download with retry logic"""
        for attempt in range(max_retries):
            if await self.download_file(url, file_path, progress_callback):
                return True
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        return False
    
    async def check_url(self, url: str) -> dict:
        """Check URL and get file info"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True) as response:
                    if response.status == 200:
                        return {
                            'valid': True,
                            'size': int(response.headers.get('content-length', 0)),
                            'type': response.headers.get('content-type', ''),
                            'filename': self.get_filename_from_url(url, response)
                        }
        except:
            pass
        return {'valid': False}
    
    def get_filename_from_url(self, url: str, response=None) -> str:
        """Extract filename from URL or headers"""
        # Try from content-disposition header
        if response and 'content-disposition' in response.headers:
            import re
            cd = response.headers['content-disposition']
            filename = re.findall('filename="?([^"]+)"?', cd)
            if filename:
                return Utils.clean_filename(filename[0])
        
        # Try from URL
        filename = url.split('/')[-1].split('?')[0]
        if filename:
            return Utils.clean_filename(filename)
        
        return f"file_{Utils.generate_task_id()}"
    
    async def download_aria2(
        self,
        url: str,
        file_path: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Download using aria2 for better performance"""
        try:
            import aria2p
            
            # Initialize aria2
            aria2 = aria2p.API(
                aria2p.Client(
                    host=Config.ARIA2_HOST,
                    port=Config.ARIA2_PORT,
                    secret=Config.ARIA2_SECRET
                )
            )
            
            # Add download
            download = aria2.add_uris([url], {'dir': os.path.dirname(file_path)})
            
            # Monitor progress
            while not download.is_complete:
                if download.is_failed:
                    return False
                    
                if progress_callback:
                    await progress_callback(
                        downloaded=download.completed_length,
                        total=download.total_length,
                        start_time=download.create_time
                    )
                    
                await asyncio.sleep(1)
            
            return True
            
        except:
            # Fallback to regular download
            return await self.download_file(url, file_path, progress_callback)
    
    async def cancel_download(self, task_id: str) -> bool:
        """Cancel active download"""
        if task_id in self.active_downloads:
            self.active_downloads[task_id]['cancelled'] = True
            return True
        return False
        
    def get_download_speed(self, task_id: str) -> float:
        """Get current download speed"""
        if task_id in self.active_downloads:
            return self.active_downloads[task_id].get('speed', 0)
        return 0

# Create instance
downloader = DownloadManager()
