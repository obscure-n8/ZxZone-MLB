import os
import asyncio
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from bot.config import Config

class WatermarkManager:
    def __init__(self):
        self.watermark_dir = os.path.join(Config.THUMB_DIR, "watermarks")
        os.makedirs(self.watermark_dir, exist_ok=True)
        
    async def create_text_watermark(
        self,
        text: str,
        output_path: str,
        font_size: int = 36,
        opacity: int = 128,
        color: tuple = (255, 255, 255)
    ) -> Optional[str]:
        """Create text watermark"""
        try:
            # Create transparent image
            img = Image.new('RGBA', (500, 100), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Try to load font
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
                
            # Draw text
            draw.text((10, 10), text, fill=(*color, opacity), font=font)
            
            # Save
            img.save(output_path, 'PNG')
            return output_path
            
        except:
            return None
            
    async def add_image_watermark(
        self,
        image_path: str,
        watermark_path: str,
        position: str = 'bottom-right',
        scale: float = 0.2
    ) -> Optional[str]:
        """Add image watermark to image"""
        try:
            base_image = Image.open(image_path).convert('RGBA')
            watermark = Image.open(watermark_path).convert('RGBA')
            
            # Scale watermark
            wm_width = int(base_image.width * scale)
            wm_height = int(watermark.height * (wm_width / watermark.width))
            watermark = watermark.resize((wm_width, wm_height), Image.Resampling.LANCZOS)
            
            # Calculate position
            positions = {
                'top-left': (10, 10),
                'top-right': (base_image.width - wm_width - 10, 10),
                'bottom-left': (10, base_image.height - wm_height - 10),
                'bottom-right': (base_image.width - wm_width - 10, base_image.height - wm_height - 10),
                'center': ((base_image.width - wm_width) // 2, (base_image.height - wm_height) // 2)
            }
            
            pos = positions.get(position, positions['bottom-right'])
            
            # Paste watermark
            base_image.paste(watermark, pos, watermark)
            
            # Save
            output_path = f"{os.path.splitext(image_path)[0]}_watermarked.png"
            base_image.convert('RGB').save(output_path, 'PNG')
            
            return output_path
            
        except:
            return None
            
    async def add_video_watermark(
        self,
        video_path: str,
        watermark_path: str,
        position: str = 'bottom-right'
    ) -> Optional[str]:
        """Add watermark to video"""
        try:
            output_path = f"{os.path.splitext(video_path)[0]}_watermarked.mp4"
            
            # Position settings for ffmpeg
            positions = {
                'top-left': 'x=10:y=10',
                'top-right': 'x=W-w-10:y=10',
                'bottom-left': 'x=10:y=H-h-10',
                'bottom-right': 'x=W-w-10:y=H-h-10',
                'center': 'x=(W-w)/2:y=(H-h)/2'
            }
            
            pos = positions.get(position, positions['bottom-right'])
            
            command = f"ffmpeg -i '{video_path}' -i '{watermark_path}' -filter_complex \"overlay={pos}\" '{output_path}'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
                
        except:
            pass
        return None
        
    async def create_copyright_watermark(
        self,
        text: str,
        output_path: str
    ) -> Optional[str]:
        """Create copyright watermark"""
        return await self.create_text_watermark(
            f"© {text}",
            output_path,
            font_size=24,
            opacity=160
        )

# Create instance
watermark_manager = WatermarkManager()
