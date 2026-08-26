import os
import asyncio
import aiohttp
from typing import Dict, List, Optional
from bot.config import Config

class JDownloaderManager:
    """JDownloader integration manager"""
    
    def __init__(self):
        self.jd_url = Config.BASE_URL or "http://localhost:3128"
        self.jd_email = Config.JD_EMAIL
        self.jd_pass = Config.JD_PASS
        self.session = None
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to JDownloader"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.jd_url}/api") as response:
                if response.status == 200:
                    self.connected = True
                    return True
                    
        except:
            self.connected = False
        return False
        
    async def disconnect(self):
        """Disconnect from JDownloader"""
        if self.session:
            await self.session.close()
            self.session = None
            self.connected = False
            
    async def add_links(self, links: List[str], package_name: str = "") -> Dict:
        """Add links to JDownloader"""
        try:
            if not self.connected:
                await self.connect()
                
            if not self.connected:
                return {'success': False, 'error': 'Not connected'}
                
            # Prepare data
            data = {
                'links': '\n'.join(links),
                'packageName': package_name or 'ZxZone Downloads'
            }
            
            async with self.session.post(
                f"{self.jd_url}/api/addLinks",
                json=data
            ) as response:
                result = await response.json()
                return {'success': True, 'data': result}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def start_downloads(self) -> bool:
        """Start all downloads"""
        try:
            async with self.session.get(f"{self.jd_url}/api/startDownloads") as response:
                return response.status == 200
        except:
            return False
            
    async def stop_downloads(self) -> bool:
        """Stop all downloads"""
        try:
            async with self.session.get(f"{self.jd_url}/api/stopDownloads") as response:
                return response.status == 200
        except:
            return False
            
    async def pause_downloads(self) -> bool:
        """Pause all downloads"""
        try:
            async with self.session.get(f"{self.jd_url}/api/pauseDownloads") as response:
                return response.status == 200
        except:
            return False
            
    async def get_status(self) -> Dict:
        """Get download status"""
        try:
            async with self.session.get(f"{self.jd_url}/api/getStatus") as response:
                if response.status == 200:
                    return await response.json()
        except:
            pass
        return {}
        
    async def get_download_list(self) -> List[Dict]:
        """Get download list"""
        try:
            async with self.session.get(f"{self.jd_url}/api/getDownloads") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('downloads', [])
        except:
            pass
        return []
        
    async def get_link_info(self, url: str) -> Dict:
        """Get link information"""
        try:
            async with self.session.post(
                f"{self.jd_url}/api/getLinkInfo",
                json={'url': url}
            ) as response:
                if response.status == 200:
                    return await response.json()
        except:
            pass
        return {}
        
    async def grab_links_from_page(self, url: str) -> List[str]:
        """Grab all links from webpage"""
        try:
            async with self.session.post(
                f"{self.jd_url}/api/grabLinks",
                json={'url': url}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('links', [])
        except:
            pass
        return []
        
    async def check_premium_status(self) -> Dict:
        """Check premium account status"""
        try:
            async with self.session.get(f"{self.jd_url}/api/getPremiumStatus") as response:
                if response.status == 200:
                    return await response.json()
        except:
            pass
        return {}
        
    async def get_speed_limits(self) -> Dict:
        """Get speed limits"""
        try:
            async with self.session.get(f"{self.jd_url}/api/getSpeedLimits") as response:
                if response.status == 200:
                    return await response.json()
        except:
            pass
        return {}
        
    async def set_speed_limit(self, download_speed: int = 0, upload_speed: int = 0) -> bool:
        """Set speed limits (bytes/s, 0 = unlimited)"""
        try:
            async with self.session.post(
                f"{self.jd_url}/api/setSpeedLimit",
                json={
                    'download': download_speed,
                    'upload': upload_speed
                }
            ) as response:
                return response.status == 200
        except:
            return False
            
    async def get_statistics(self) -> Dict:
        """Get download statistics"""
        try:
            async with self.session.get(f"{self.jd_url}/api/getStatistics") as response:
                if response.status == 200:
                    return await response.json()
        except:
            pass
        return {}

# Create instance
jdownloader = JDownloaderManager()
