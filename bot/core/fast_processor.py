import os
import asyncio
import subprocess
import tempfile
from typing import Dict, Optional
from bot.config import Config

class FastProcessor:
    """Heroku-optimized fast file processor"""
    
    def __init__(self):
        self.is_heroku = 'DYNO' in os.environ
        self.temp_dir = tempfile.gettempdir()
        self.processing_strategy = self.get_strategy()
        
    def get_strategy(self) -> str:
        """Get processing strategy based on environment"""
        if self.is_heroku:
            # Heroku: Use streaming instead of full download
            return 'streaming'
        else:
            # VPS: Use full download (faster)
            return 'full'
            
    async def process_file(self, file_path: str, operation: str) -> Dict:
        """Process file with optimal strategy"""
        if self.processing_strategy == 'streaming':
            return await self.stream_process(file_path, operation)
        else:
            return await self.full_process(file_path, operation)
            
    async def stream_process(self, file_path: str, operation: str) -> Dict:
        """Stream processing for Heroku (no full download)"""
        try:
            if operation == 'split':
                return await self.stream_split(file_path)
            elif operation == 'archive':
                return await self.stream_archive(file_path)
            elif operation == 'm3u8':
                return await self.stream_m3u8(file_path)
                
        except:
            return {'success': False}
            
    async def full_process(self, file_path: str, operation: str) -> Dict:
        """Full processing for VPS (faster)"""
        try:
            if operation == 'split':
                return await self.full_split(file_path)
            elif operation == 'archive':
                return await self.full_archive(file_path)
                
        except:
            return {'success': False}
            
    async def stream_split(self, file_path: str) -> Dict:
        """Stream split without loading full file"""
        try:
            file_size = os.path.getsize(file_path)
            chunk_size = 500 * 1024 * 1024  # 500MB chunks for Heroku
            
            # Use ffmpeg for streaming split
            command = f"ffmpeg -i '{file_path}' -c copy -f segment -segment_time 600 -segment_size {chunk_size} '{file_path}_part_%03d.mp4'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            # Get split files
            split_files = []
            for i in range(100):
                part_path = f"{file_path}_part_{i:03d}.mp4"
                if os.path.exists(part_path):
                    split_files.append(part_path)
                else:
                    break
                    
            return {
                'success': True,
                'files': split_files,
                'method': 'stream_split'
            }
            
        except:
            return {'success': False}
            
    async def stream_archive(self, file_path: str) -> Dict:
        """Stream archive without full download"""
        try:
            # Use tar for streaming archive
            archive_path = f"{file_path}.tar.gz"
            
            command = f"tar -czf '{archive_path}' '{file_path}' --warning=no-file-changed"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if os.path.exists(archive_path):
                return {
                    'success': True,
                    'archive': archive_path,
                    'method': 'stream_archive'
                }
                
        except:
            pass
            
        return {'success': False}
        
    async def stream_m3u8(self, url: str) -> Dict:
        """Stream M3U8 download for Heroku"""
        try:
            # Use yt-dlp for efficient m3u8 download
            output_path = os.path.join(Config.DOWNLOAD_DIR, 'm3u8_download.mp4')
            
            command = f"yt-dlp --no-part --no-cache-dir --concurrent-fragments 3 '{url}' -o '{output_path}'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if os.path.exists(output_path):
                return {
                    'success': True,
                    'file': output_path,
                    'method': 'stream_m3u8'
                }
                
        except:
            pass
            
        return {'success': False}
        
    async def fast_split_upload(self, client, file_path: str, chat_id: int):
        """Fast split and upload for Heroku"""
        try:
            # Split file
            split_result = await self.stream_split(file_path)
            
            if not split_result['success']:
                return False
                
            # Upload each part immediately
            for part_path in split_result['files']:
                await client.send_document(
                    chat_id,
                    part_path,
                    progress=self.upload_progress
                )
                
                # Delete uploaded part to save space
                os.remove(part_path)
                
            return True
            
        except:
            return False
            
    async def upload_progress(self, current, total):
        """Upload progress callback"""
        if total > 0:
            percent = (current / total) * 100
            if percent % 20 == 0:
                print(f"Upload: {percent:.1f}%")

# Create instance
fast_processor = FastProcessor()
