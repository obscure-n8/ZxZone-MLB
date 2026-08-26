import os
from PIL import Image
from typing import Optional

class ThumbnailManager:
    def __init__(self, thumb_dir: str):
        self.thumb_dir = thumb_dir
        os.makedirs(thumb_dir, exist_ok=True)
        
    def save_thumbnail(self, user_id: int, file_path: str) -> str:
        """Save user thumbnail"""
        # Create user directory
        user_dir = os.path.join(self.thumb_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # Generate thumbnail path
        thumb_path = os.path.join(user_dir, "thumbnail.jpg")
        
        # Process image
        img = Image.open(file_path)
        img = img.convert('RGB')
        img.thumbnail((320, 320), Image.Resampling.LANCZOS)
        img.save(thumb_path, 'JPEG', quality=85)
        
        return thumb_path
        
    def get_thumbnail(self, user_id: int) -> Optional[str]:
        """Get user thumbnail"""
        thumb_path = os.path.join(self.thumb_dir, str(user_id), "thumbnail.jpg")
        return thumb_path if os.path.exists(thumb_path) else None
        
    def delete_thumbnail(self, user_id: int) -> bool:
        """Delete user thumbnail"""
        thumb_path = os.path.join(self.thumb_dir, str(user_id), "thumbnail.jpg")
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
            return True
        return False
        
    def process_thumbnail(self, user_id: int, file_path: str) -> Optional[str]:
        """Process and save thumbnail from various sources"""
        try:
            # Check if file is image
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                return self.save_thumbnail(user_id, file_path)
            elif file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                # For video files, extract thumbnail using ffmpeg
                import subprocess
                thumb_path = os.path.join(self.thumb_dir, str(user_id), "thumbnail.jpg")
                os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
                
                cmd = [
                    'ffmpeg', '-i', file_path,
                    '-ss', '00:00:02',
                    '-vframes', '1',
                    '-vf', 'scale=320:-1',
                    thumb_path
                ]
                subprocess.run(cmd, capture_output=True)
                return thumb_path if os.path.exists(thumb_path) else None
        except Exception:
            return None
