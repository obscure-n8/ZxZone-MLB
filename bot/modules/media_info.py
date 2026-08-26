import os
import asyncio
from typing import Optional
from PIL import Image
from bot.helpers.utils import Utils

class MediaInfo:
    def __init__(self):
        self.supported_video = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv']
        self.supported_audio = ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.opus']
        self.supported_image = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']
        self.supported_archive = ['.zip', '.rar', '.7z', '.tar', '.gz']
        
    async def get_file_info(self, file_path: str) -> dict:
        """Get comprehensive file information"""
        try:
            if not os.path.exists(file_path):
                return {}
                
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            extension = Utils.get_file_extension(file_path)
            
            info = {
                'name': file_name,
                'size': file_size,
                'extension': extension,
                'type': self.get_file_type(extension),
                'created': os.path.getctime(file_path),
                'modified': os.path.getmtime(file_path)
            }
            
            # Get media specific info
            if extension in self.supported_video:
                video_info = await self.get_video_info(file_path)
                info.update(video_info)
            elif extension in self.supported_audio:
                audio_info = await self.get_audio_info(file_path)
                info.update(audio_info)
            elif extension in self.supported_image:
                image_info = await self.get_image_info(file_path)
                info.update(image_info)
                
            return info
            
        except Exception as e:
            return {'error': str(e)}
            
    def get_file_type(self, extension: str) -> str:
        """Get file type from extension"""
        if extension in self.supported_video:
            return 'video'
        elif extension in self.supported_audio:
            return 'audio'
        elif extension in self.supported_image:
            return 'image'
        elif extension in self.supported_archive:
            return 'archive'
        else:
            return 'document'
            
    async def get_video_info(self, file_path: str) -> dict:
        """Get video information using ffprobe"""
        try:
            process = await asyncio.create_subprocess_shell(
                f"ffprobe -v quiet -print_format json -show_streams -show_format '{file_path}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                data = json.loads(stdout.decode())
                
                video_stream = None
                audio_stream = None
                
                for stream in data.get('streams', []):
                    if stream['codec_type'] == 'video' and not video_stream:
                        video_stream = stream
                    elif stream['codec_type'] == 'audio' and not audio_stream:
                        audio_stream = stream
                        
                info = {}
                
                if video_stream:
                    info['width'] = video_stream.get('width')
                    info['height'] = video_stream.get('height')
                    info['video_codec'] = video_stream.get('codec_name')
                    info['fps'] = video_stream.get('avg_frame_rate')
                    
                if audio_stream:
                    info['audio_codec'] = audio_stream.get('codec_name')
                    
                format_info = data.get('format', {})
                info['duration'] = float(format_info.get('duration', 0))
                info['bitrate'] = int(format_info.get('bit_rate', 0))
                
                return info
                
        except:
            pass
        return {}
        
    async def get_audio_info(self, file_path: str) -> dict:
        """Get audio information"""
        try:
            process = await asyncio.create_subprocess_shell(
                f"ffprobe -v quiet -print_format json -show_format '{file_path}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                data = json.loads(stdout.decode())
                format_info = data.get('format', {})
                
                return {
                    'duration': float(format_info.get('duration', 0)),
                    'bitrate': int(format_info.get('bit_rate', 0)),
                    'artist': format_info.get('tags', {}).get('artist'),
                    'album': format_info.get('tags', {}).get('album'),
                    'title': format_info.get('tags', {}).get('title')
                }
                
        except:
            pass
        return {}
        
    async def get_image_info(self, file_path: str) -> dict:
        """Get image information"""
        try:
            with Image.open(file_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                }
        except:
            pass
        return {}
        
    def format_duration(self, seconds: float) -> str:
        """Format duration to human readable"""
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

# Create instance
media_info = MediaInfo()
