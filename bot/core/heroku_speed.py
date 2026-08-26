import os
import asyncio
import aiohttp
import aiofiles
from typing import Dict, Optional
from bot.config import Config

class HerokuSpeedOptimizer:
    """Speed optimizer for Heroku"""
    
    def __init__(self):
        self.is_heroku = 'DYNO' in os.environ
        self.use_streaming = self.is_heroku
        self.chunk_size = self.get_chunk_size()
        
    def get_chunk_size(self) -> int:
        """Get optimal chunk size"""
        if self.is_heroku:
            return 256 * 1024  # 256KB chunks for Heroku
        else:
            return 1024 * 1024  # 1MB chunks for VPS
            
    async def fast_download(self, url: str, file_path: str) -> bool:
        """Fast download optimized for Heroku"""
        try:
            if self.use_streaming:
                return await self.stream_download(url, file_path)
            else:
                return await self.full_download(url, file_path)
                
        except:
            return False
            
    async def stream_download(self, url: str, file_path: str) -> bool:
        """Stream download for Heroku (no disk caching)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                        
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(self.chunk_size):
                            await f.write(chunk)
                            
            return True
            
        except:
            return False
            
    async def full_download(self, url: str, file_path: str) -> bool:
        """Full download for VPS (faster)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                        
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            await f.write(chunk)
                            
            return True
            
        except:
            return False
            
    async def process_m3u8_fast(self, url: str) -> Dict:
        """Fast M3U8 processing"""
        try:
            output_path = os.path.join(Config.DOWNLOAD_DIR, 'output.mp4')
            
            if self.is_heroku:
                # Heroku: Use concurrent fragments
                command = f"yt-dlp --concurrent-fragments 5 --no-part '{url}' -o '{output_path}'"
            else:
                # VPS: Use maximum speed
                command = f"yt-dlp --concurrent-fragments 10 --no-part '{url}' -o '{output_path}'"
                
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if os.path.exists(output_path):
                return {'success': True, 'file': output_path}
                
        except:
            pass
            
        return {'success': False}
        
    async def fast_split_and_upload(self, client, file_path: str, chat_id: int):
        """Fast split and upload"""
        try:
            file_size = os.path.getsize(file_path)
            
            if self.is_heroku:
                # Heroku: Split in smaller chunks
                split_size = 500 * 1024 * 1024  # 500MB
            else:
                # VPS: Split in larger chunks
                split_size = 1900 * 1024 * 1024  # 1.9GB
                
            # Split file
            parts = []
            with open(file_path, 'rb') as f:
                part_num = 1
                while True:
                    chunk = f.read(split_size)
                    if not chunk:
                        break
                        
                    part_path = f"{file_path}.part{part_num:03d}"
                    with open(part_path, 'wb') as part_file:
                        part_file.write(chunk)
                        
                    parts.append(part_path)
                    part_num += 1
                    
            # Upload parts
            for part_path in parts:
                await client.send_document(chat_id, part_path)
                os.remove(part_path)  # Delete after upload
                
            return True
            
        except:
            return False

# Create instance
heroku_speed = HerokuSpeedOptimizer()
