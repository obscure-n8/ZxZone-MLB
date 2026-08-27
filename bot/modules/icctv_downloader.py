import os
import re
import json
import asyncio
import aiohttp
from typing import Dict, Optional
from bot.config import Config
from bot.helpers.utils import Utils

class IccTvDownloader:
    """Icc.Tv webpage video downloader"""
    
    def __init__(self):
        self.download_dir = os.path.join(Config.DOWNLOAD_DIR, 'icctv')
        os.makedirs(self.download_dir, exist_ok=True)
        self.session = None
        
    async def detect_icctv(self, url: str) -> bool:
        """Check if URL is from Icc.Tv"""
        icctv_patterns = [
            'icc.tv',
            'icctv',
            'icc.tv/video',
            'icc.tv/live'
        ]
        
        return any(pattern in url.lower() for pattern in icctv_patterns)
        
    async def download(self, url: str, quality: str = 'best') -> Dict:
        """Download video from Icc.Tv"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # Get page content
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {'success': False, 'error': f'HTTP {response.status}'}
                    
                html = await response.text()
                
            # Extract video URL from webpage
            video_url = await self.extract_video_url(html)
            
            if not video_url:
                return {'success': False, 'error': 'Video URL not found'}
                
            # Download video
            file_path = os.path.join(self.download_dir, f"icctv_{int(time.time())}.mp4")
            
            async with self.session.get(video_url) as response:
                if response.status != 200:
                    return {'success': False, 'error': 'Video download failed'}
                    
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
                'source': 'Icc.Tv'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def extract_video_url(self, html: str) -> Optional[str]:
        """Extract video URL from HTML"""
        # Method 1: Look for m3u8
        m3u8_pattern = r'(https?://[^\s"\']+\.m3u8[^\s"\']*)'
        m3u8_matches = re.findall(m3u8_pattern, html)
        if m3u8_matches:
            return m3u8_matches[0]
            
        # Method 2: Look for mp4
        mp4_pattern = r'(https?://[^\s"\']+\.mp4[^\s"\']*)'
        mp4_matches = re.findall(mp4_pattern, html)
        if mp4_matches:
            return mp4_matches[0]
            
        # Method 3: Look for JSON data
        json_pattern = r'<script[^>]*type="application/json"[^>]*>(.*?)</script>'
        json_matches = re.findall(json_pattern, html, re.DOTALL)
        
        for json_str in json_matches:
            try:
                data = json.loads(json_str)
                video_url = self.extract_from_json(data)
                if video_url:
                    return video_url
            except:
                pass
                
        # Method 4: Look for video source tags
        source_pattern = r'<source[^>]*src="([^"]+)"[^>]*>'
        source_matches = re.findall(source_pattern, html)
        if source_matches:
            return source_matches[0]
            
        return None
        
    def extract_from_json(self, data, depth=0):
        """Extract video URL from JSON data recursively"""
        if depth > 5:
            return None
            
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if '.m3u8' in value or '.mp4' in value:
                        if value.startswith('http'):
                            return value
                elif isinstance(value, (dict, list)):
                    result = self.extract_from_json(value, depth + 1)
                    if result:
                        return result
                        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    result = self.extract_from_json(item, depth + 1)
                    if result:
                        return result
                        
        return None
        
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
            self.session = None

# Create instance
icctv_downloader = IccTvDownloader()
