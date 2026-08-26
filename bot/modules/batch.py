import os
import asyncio
import aiohttp
import aiofiles
from typing import List, Optional, Callable
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress

progress_helper = Progress()

class BatchDownloader:
    def __init__(self):
        self.batch_tasks = {}
        self.max_concurrent = 3  # Max simultaneous downloads
        
    async def download_batch(
        self,
        urls: List[str],
        download_dir: str,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """Download multiple files simultaneously"""
        os.makedirs(download_dir, exist_ok=True)
        
        batch_id = Utils.generate_task_id()
        results = {
            'batch_id': batch_id,
            'total': len(urls),
            'completed': 0,
            'failed': 0,
            'files': []
        }
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def download_single(url: str, index: int):
            async with semaphore:
                try:
                    filename = self.get_filename(url, index)
                    file_path = os.path.join(download_dir, filename)
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:
                            if response.status != 200:
                                results['failed'] += 1
                                return
                            
                            total_size = int(response.headers.get('content-length', 0))
                            downloaded = 0
                            start_time = asyncio.get_event_loop().time()
                            
                            async with aiofiles.open(file_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(1024 * 1024):
                                    await f.write(chunk)
                                    downloaded += len(chunk)
                                    
                                    if progress_callback and total_size > 0:
                                        await progress_callback(
                                            batch_id=batch_id,
                                            file_index=index,
                                            file_name=filename,
                                            downloaded=downloaded,
                                            total=total_size,
                                            start_time=start_time,
                                            completed_files=results['completed'],
                                            total_files=len(urls)
                                        )
                            
                            results['completed'] += 1
                            results['files'].append({
                                'name': filename,
                                'path': file_path,
                                'size': total_size
                            })
                            
                except Exception as e:
                    results['failed'] += 1
        
        # Create tasks
        tasks = [download_single(url, i+1) for i, url in enumerate(urls)]
        
        # Run all tasks
        await asyncio.gather(*tasks)
        
        return results
        
    def get_filename(self, url: str, index: int) -> str:
        """Get filename from URL"""
        filename = url.split('/')[-1].split('?')[0]
        if not filename:
            filename = f"file_{index}"
        return Utils.clean_filename(filename)
        
    async def download_sequential(
        self,
        urls: List[str],
        download_dir: str,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """Download files one by one"""
        results = {
            'total': len(urls),
            'completed': 0,
            'failed': 0,
            'files': []
        }
        
        for i, url in enumerate(urls, 1):
            try:
                filename = self.get_filename(url, i)
                file_path = os.path.join(download_dir, filename)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        start_time = asyncio.get_event_loop().time()
                        
                        async with aiofiles.open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(1024 * 1024):
                                await f.write(chunk)
                                downloaded += len(chunk)
                                
                                if progress_callback:
                                    await progress_callback(
                                        file_index=i,
                                        file_name=filename,
                                        downloaded=downloaded,
                                        total=total_size,
                                        start_time=start_time,
                                        completed_files=results['completed'],
                                        total_files=len(urls)
                                    )
                        
                        results['completed'] += 1
                        results['files'].append({
                            'name': filename,
                            'path': file_path,
                            'size': total_size
                        })
                        
            except:
                results['failed'] += 1
                
        return results

# Create instance
batch_downloader = BatchDownloader()
