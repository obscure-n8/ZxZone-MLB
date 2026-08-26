import os
import asyncio
import aiohttp
from typing import Optional
from bot.config import Config

class KeepAliveSystem:
    """Anti-sleep system for Heroku"""
    
    def __init__(self):
        self.is_heroku = self.detect_heroku()
        self.app_url = os.getenv('APP_URL', '')
        self.keep_alive_task = None
        self.last_ping = 0
        self.ping_interval = 300  # 5 minutes
        
    def detect_heroku(self) -> bool:
        """Detect Heroku environment"""
        return 'DYNO' in os.environ
        
    async def start(self):
        """Start keep alive system"""
        if not self.is_heroku:
            return  # Only for Heroku
            
        if not self.app_url:
            # Auto detect app URL
            self.app_url = self.get_heroku_url()
            
        if self.app_url:
            self.keep_alive_task = asyncio.create_task(self._keep_alive_loop())
            
    def get_heroku_url(self) -> str:
        """Get Heroku app URL"""
        app_name = os.getenv('HEROKU_APP_NAME', '')
        if app_name:
            return f"https://{app_name}.herokuapp.com"
        return ''
        
    async def _keep_alive_loop(self):
        """Keep alive loop"""
        while True:
            try:
                # Ping self
                await self.ping_self()
                
                # Ping external URLs
                await self.ping_external()
                
                # Wait before next ping
                await asyncio.sleep(self.ping_interval)
                
            except:
                await asyncio.sleep(60)
                
    async def ping_self(self):
        """Ping own app URL"""
        if not self.app_url:
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.app_url, timeout=10) as response:
                    self.last_ping = time.time()
        except:
            pass
            
    async def ping_external(self):
        """Ping external URLs to keep network active"""
        external_urls = [
            'https://www.google.com',
            'https://www.cloudflare.com',
            'https://httpbin.org/get'
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                for url in external_urls:
                    async with session.get(url, timeout=5) as response:
                        pass
        except:
            pass
            
    def get_status(self) -> dict:
        """Get keep alive status"""
        return {
            'active': self.is_heroku,
            'app_url': self.app_url,
            'last_ping': self.last_ping,
            'interval': self.ping_interval
        }

# Create instance
keep_alive = KeepAliveSystem()
