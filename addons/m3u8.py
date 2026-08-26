import os
import asyncio
from typing import Dict, Optional
from bot.config import Config

class M3U8Downloader:
    """M3U8 stream downloader"""
    
    def __init__(self):
        self.download_dir = os.path.join(Config.DOWNLOAD_DIR, 'm3u8')
        os.makedirs(self.download_dir, exist_ok=True)
        
    async def download(self, url: str, quality: str = 'best') -> Dict:
        """Download M3U8 stream"""
        try:
            output_path = os.path.join(self.download_dir, f"m3u8_{int(time.time())}.mp4")
            
            # Quality settings
            if quality == 'best':
                format_option = 'best'
            elif quality == '1080p':
                format_option = 'best[height<=1080]'
            elif quality == '720p':
                format_option = 'best[height<=720]'
            elif quality == '480p':
                format_option = 'best[height<=480]'
            else:
                format_option = 'best'
                
            # Download with yt-dlp
            command = f"yt-dlp -f '{format_option}' --no-part --concurrent-fragments 5 '{url}' -o '{output_path}'"
            
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
                    'size': os.path.getsize(output_path)
                }
                
        except Exception as e:
            pass
            
        return {'success': False}
        
    async def download_archive(self, url: str) -> Dict:
        """Download M3U8 and create archive"""
        try:
            result = await self.download(url)
            
            if result['success']:
                # Create archive
                import zipfile
                archive_path = result['file'] + '.zip'
                
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(result['file'], os.path.basename(result['file']))
                    
                return {
                    'success': True,
                    'file': archive_path,
                    'size': os.path.getsize(archive_path)
                }
                
        except:
            pass
            
        return {'success': False}
