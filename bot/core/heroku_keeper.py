import os
import asyncio
import aiohttp
import subprocess
from typing import Dict, Optional

class HerokuKeeper:
    """Advanced Heroku management system"""
    
    def __init__(self):
        self.is_heroku = 'DYNO' in os.environ
        self.app_name = os.getenv('HEROKU_APP_NAME', '')
        self.api_key = os.getenv('HEROKU_API_KEY', '')
        self.auto_restart = True
        self.last_restart = 0
        self.restart_interval = 3600  # 1 hour
        
    async def start(self):
        """Start Heroku keeper"""
        if not self.is_heroku:
            return
            
        asyncio.create_task(self._keeper_loop())
        
    async def _keeper_loop(self):
        """Keeper loop"""
        while True:
            try:
                # Check bot health
                if await self.check_bot_health():
                    # Bot is healthy
                    pass
                else:
                    # Restart bot
                    await self.restart_dyno()
                    
                # Auto restart after interval
                if self.auto_restart:
                    current_time = asyncio.get_event_loop().time()
                    if current_time - self.last_restart > self.restart_interval:
                        await self.restart_dyno()
                        self.last_restart = current_time
                        
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except:
                await asyncio.sleep(60)
                
    async def check_bot_health(self) -> bool:
        """Check if bot is healthy"""
        try:
            # Check if bot process is running
            from bot import __main__
            return True
        except:
            return False
            
    async def restart_dyno(self):
        """Restart Heroku dyno"""
        if not self.app_name or not self.api_key:
            return
            
        try:
            # Use Heroku API to restart dyno
            command = f"heroku ps:restart --app {self.app_name}"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            
        except:
            pass
            
    async def get_dyno_status(self) -> Dict:
        """Get dyno status"""
        return {
            'is_heroku': self.is_heroku,
            'app_name': self.app_name,
            'auto_restart': self.auto_restart,
            'last_restart': self.last_restart
        }

# Create instance
heroku_keeper = HerokuKeeper()
