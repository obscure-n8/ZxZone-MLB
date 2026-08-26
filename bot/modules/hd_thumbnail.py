import os
import asyncio
import subprocess
from typing import Dict, Optional
from PIL import Image
from bot.config import Config

class HDThumbnailGenerator:
    """HD Thumbnail auto generation system"""
    
    def __init__(self):
        self.thumb_dir = os.path.join(Config.THUMB_DIR, 'auto_hd')
        os.makedirs(self.thumb_dir, exist_ok=True)
        self.enabled = True  # Default enabled
        
    async def generate_hd_thumbnail(
        self,
        video_path: str,
        timestamp: str = '00:00:02',
        quality: str = 'hd',
        width: int = 1280,
        height: int = 720
    ) -> Dict:
        """Generate HD thumbnail from video"""
        try:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            thumb_path = os.path.join(self.thumb_dir, f"{video_name}_thumb.jpg")
            
            # Quality settings
            quality_settings = {
                'hd': {
                    'width': 1280,
                    'height': 720,
                    'quality': 95,
                    'scale': 'scale=1280:720'
                },
                'full_hd': {
                    'width': 1920,
                    'height': 1080,
                    'quality': 95,
                    'scale': 'scale=1920:1080'
                },
                'sd': {
                    'width': 640,
                    'height': 360,
                    'quality': 85,
                    'scale': 'scale=640:360'
                }
            }
            
            settings = quality_settings.get(quality, quality_settings['hd'])
            
            # Generate thumbnail using ffmpeg
            command = (
                f"ffmpeg -i '{video_path}' "
                f"-ss {timestamp} "
                f"-vframes 1 "
                f"-vf '{settings['scale']}' "
                f"-q:v {settings['quality']} "
                f"'{thumb_path}'"
            )
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if os.path.exists(thumb_path):
                # Optimize thumbnail
                await self.optimize_thumbnail(thumb_path)
                
                return {
                    'success': True,
                    'thumbnail': thumb_path,
                    'quality': quality,
                    'width': settings['width'],
                    'height': settings['height'],
                    'size': os.path.getsize(thumb_path)
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
        return {'success': False, 'error': 'Failed to generate thumbnail'}
        
    async def optimize_thumbnail(self, thumb_path: str):
        """Optimize thumbnail for best quality"""
        try:
            with Image.open(thumb_path) as img:
                # Convert to RGB
                img = img.convert('RGB')
                
                # Enhance quality
                from PIL import ImageEnhance
                
                # Sharpness
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.2)
                
                # Contrast
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.1)
                
                # Color
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.1)
                
                # Save with high quality
                img.save(thumb_path, 'JPEG', quality=95, optimize=True)
                
        except:
            pass
            
    async def generate_multiple_thumbnails(
        self,
        video_path: str,
        count: int = 3
    ) -> Dict:
        """Generate multiple thumbnails from video"""
        try:
            # Get video duration
            duration = await self.get_video_duration(video_path)
            
            if duration == 0:
                return {'success': False, 'error': 'Cannot get duration'}
                
            thumbnails = []
            
            for i in range(count):
                # Calculate timestamp
                timestamp = (duration / (count + 1)) * (i + 1)
                time_str = self.format_timestamp(timestamp)
                
                # Generate thumbnail
                result = await self.generate_hd_thumbnail(
                    video_path,
                    timestamp=time_str,
                    quality='hd'
                )
                
                if result['success']:
                    thumbnails.append(result['thumbnail'])
                    
            return {
                'success': True,
                'thumbnails': thumbnails,
                'count': len(thumbnails)
            }
            
        except:
            return {'success': False}
            
    async def get_video_duration(self, video_path: str) -> float:
        """Get video duration"""
        try:
            command = f"ffprobe -v quiet -print_format json -show_format '{video_path}'"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            import json
            data = json.loads(stdout.decode())
            return float(data['format']['duration'])
            
        except:
            return 0
            
    def format_timestamp(self, seconds: float) -> str:
        """Format timestamp for ffmpeg"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        
    async def generate_thumbnail_grid(
        self,
        video_path: str,
        grid_size: int = 4
    ) -> Dict:
        """Generate thumbnail grid (4 thumbnails in one image)"""
        try:
            # Generate multiple thumbnails
            result = await self.generate_multiple_thumbnails(video_path, grid_size)
            
            if not result['success']:
                return result
                
            # Create grid
            thumbnails = result['thumbnails']
            
            if len(thumbnails) < 2:
                return {'success': False}
                
            # Open first thumbnail
            with Image.open(thumbnails[0]) as first:
                thumb_width = first.width
                thumb_height = first.height
                
            # Create grid canvas
            grid_width = thumb_width * 2
            grid_height = thumb_height * 2
            grid = Image.new('RGB', (grid_width, grid_height), 'white')
            
            # Paste thumbnails
            positions = [(0, 0), (thumb_width, 0), (0, thumb_height), (thumb_width, thumb_height)]
            
            for i, thumb_path in enumerate(thumbnails[:4]):
                if i < len(positions):
                    with Image.open(thumb_path) as thumb:
                        grid.paste(thumb, positions[i])
                        
            # Save grid
            grid_path = os.path.join(self.thumb_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}_grid.jpg")
            grid.save(grid_path, 'JPEG', quality=95)
            
            return {
                'success': True,
                'thumbnail': grid_path,
                'grid_size': f"{grid_width}x{grid_height}"
            }
            
        except:
            return {'success': False}
            
    async def set_thumbnail_quality(self, quality: str):
        """Set thumbnail quality"""
        self.quality = quality
        
    async def toggle_thumbnail(self, enabled: bool):
        """Toggle thumbnail generation"""
        self.enabled = enabled
        
    async def get_thumbnail_stats(self) -> Dict:
        """Get thumbnail statistics"""
        thumbnails = []
        
        for file in os.listdir(self.thumb_dir):
            file_path = os.path.join(self.thumb_dir, file)
            thumbnails.append({
                'name': file,
                'size': os.path.getsize(file_path),
                'created': os.path.getctime(file_path)
            })
            
        return {
            'enabled': self.enabled,
            'total_thumbnails': len(thumbnails),
            'thumb_dir': self.thumb_dir,
            'thumbnails': thumbnails[:10]
        }

# Create instance
hd_thumbnail = HDThumbnailGenerator()
