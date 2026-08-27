import os
import re
import asyncio
import aiohttp
from typing import Dict, Optional
from bot.config import Config
from bot.helpers.utils import Utils

class VikingDownloader:
    """Viking files downloader"""
    
    def __init__(self):
        self.download_dir = os.path.join(Config.DOWNLOAD_DIR, 'viking')
        os.makedirs(self.download_dir, exist_ok=True)
        
    async def detect_viking(self, url: str) -> bool:
        """Check if URL is viking file"""
        viking_patterns = [
            'viking',
            'vikingfiles',
            'viking-file',
            'vikings'
        ]
        
        return any(pattern in url.lower() for pattern in viking_patterns)
        
    async def download(self, url: str) -> Dict:
        """Download from viking files"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get download page
                async with session.get(url) as response:
                    html = await response.text()
                    
                # Extract direct download link
                direct_url = await self.extract_download_link(html)
                
                if not direct_url:
                    return {'success': False, 'error': 'Download link not found'}
                    
                # Download file
                file_name = self.get_file_name(direct_url, url)
                file_path = os.path.join(self.download_dir, file_name)
                
                async with session.get(direct_url) as response:
                    if response.status != 200:
                        return {'success': False, 'error': 'Download failed'}
                        
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                return {
                    'success': True,
                    'file': file_path,
                    'size': downloaded,
                    'name': file_name
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def extract_download_link(self, html: str) -> Optional[str]:
        """Extract direct download link"""
        # Method 1: Direct link pattern
        direct_patterns = [
            r'href="(https?://[^"]*download[^"]*)"',
            r'href="(https?://[^"]*file[^"]*)"',
            r'data-url="([^"]+)"',
            r'data-href="([^"]+)"'
        ]
        
        for pattern in direct_patterns:
            matches = re.findall(pattern, html)
            if matches:
                return matches[0]
                
        return None
        
    def get_file_name(self, url: str, original_url: str) -> str:
        """Get file name from URL"""
        name = os.path.basename(url.split('?')[0])
        if not name or len(name) < 3:
            name = f"viking_{int(time.time())}.file"
        return Utils.clean_filename(name)

# Create instance
viking_downloader = VikingDownloader()
