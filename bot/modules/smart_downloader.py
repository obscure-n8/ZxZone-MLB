import os
import asyncio
from typing import Dict, Optional
from bot.config import Config
from bot.modules.icctv_downloader import icctv_downloader
from bot.modules.viking_downloader import viking_downloader
from bot.modules.downloader import downloader

class SmartDownloader:
    """Smart downloader - auto detect and download"""
    
    def __init__(self):
        self.downloaders = []
        
    async def smart_download(self, url: str, file_path: str) -> Dict:
        """Download from any supported source"""
        
        # Check Icc.Tv
        if await icctv_downloader.detect_icctv(url):
            return await icctv_downloader.download(url)
            
        # Check Viking files
        if await viking_downloader.detect_viking(url):
            return await viking_downloader.download(url)
            
        # Check M3U8
        if 'm3u8' in url.lower():
            from bot.core.heroku_speed import heroku_speed
            return await heroku_speed.process_m3u8_fast(url)
            
        # Check Mega
        if 'mega.nz' in url.lower():
            from bot.plugins.mega import mega_command
            return {'success': True, 'special': 'mega'}
            
        # Check Gofile
        if 'gofile.io' in url.lower():
            from bot.plugins.gofile import gofile_command
            return {'success': True, 'special': 'gofile'}
            
        # Check Pixeldrain
        if 'pixeldrain.com' in url.lower():
            return await self.download_pixeldrain(url, file_path)
            
        # Check Google Drive
        if 'drive.google.com' in url.lower():
            return {'success': True, 'special': 'gdrive'}
            
        # Direct download
        success = await downloader.download_file(url, file_path)
        
        if success:
            return {'success': True, 'file': file_path}
            
        return {'success': False, 'error': 'Download failed'}
        
    async def download_pixeldrain(self, url: str, file_path: str) -> Dict:
        """Download from Pixeldrain"""
        try:
            import aiohttp
            import aiofiles
            
            # Convert to direct link
            file_id = url.split('/')[-1]
            direct_url = f"https://pixeldrain.com/api/file/{file_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(direct_url) as response:
                    if response.status != 200:
                        return {'success': False, 'error': 'Download failed'}
                        
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            await f.write(chunk)
                            
            return {'success': True, 'file': file_path}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Create instance
smart_downloader = SmartDownloader()
