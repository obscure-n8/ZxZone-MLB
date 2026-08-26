import os
import asyncio
from typing import Dict, Optional
from bot.config import Config

class VideoConverter:
    """Video converter addon"""
    
    def __init__(self):
        self.convert_dir = os.path.join(Config.DOWNLOAD_DIR, 'converted')
        os.makedirs(self.convert_dir, exist_ok=True)
        
    async def convert(self, file_path: str, target_format: str) -> Dict:
        """Convert video format"""
        try:
            output_path = os.path.join(
                self.convert_dir,
                f"{os.path.splitext(os.path.basename(file_path))[0]}.{target_format}"
            )
            
            command = f"ffmpeg -i '{file_path}' -c:v libx264 -c:a aac '{output_path}'"
            
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
                
        except:
            pass
            
        return {'success': False}
        
    async def extract_audio(self, video_path: str, audio_format: str = 'mp3') -> Dict:
        """Extract audio from video"""
        try:
            output_path = os.path.join(
                self.convert_dir,
                f"{os.path.splitext(os.path.basename(video_path))[0]}.{audio_format}"
            )
            
            command = f"ffmpeg -i '{video_path}' -vn -acodec libmp3lame '{output_path}'"
            
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
                
        except:
            pass
            
        return {'success': False}
        
    async def compress_video(self, file_path: str, quality: str = 'medium') -> Dict:
        """Compress video"""
        try:
            quality_settings = {
                'low': '-crf 28 -preset fast',
                'medium': '-crf 23 -preset medium',
                'high': '-crf 18 -preset slow'
            }
            
            output_path = os.path.join(
                self.convert_dir,
                f"{os.path.splitext(os.path.basename(file_path))[0]}_compressed.mp4"
            )
            
            command = f"ffmpeg -i '{file_path}' {quality_settings.get(quality, quality_settings['medium'])} '{output_path}'"
            
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
                
        except:
            pass
            
        return {'success': False}
