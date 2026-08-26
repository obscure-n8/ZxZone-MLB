import os
import asyncio
from typing import Optional, Callable
from pyrogram import Client
from pyrogram.types import InputMediaDocument, InputMediaVideo, InputMediaPhoto
from bot.config import Config
from bot.helpers.utils import Utils

class UploadManager:
    def __init__(self):
        self.active_uploads = {}
        
    async def upload_to_telegram(
        self,
        client: Client,
        file_path: str,
        chat_id: int,
        caption: str = "",
        progress_callback: Optional[Callable] = None,
        as_video: bool = False,
        thumbnail: Optional[str] = None
    ):
        """Upload file to telegram"""
        try:
            file_size = os.path.getsize(file_path)
            
            # Check file size
            if file_size > Config.MAX_FILE_SIZE:
                return False, "File too large for Telegram"
                
            # Upload based on type
            if as_video and file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                await client.send_video(
                    chat_id=chat_id,
                    video=file_path,
                    caption=caption,
                    thumb=thumbnail,
                    progress=progress_callback if progress_callback else self.default_progress,
                    supports_streaming=True
                )
            elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                await client.send_photo(
                    chat_id=chat_id,
                    photo=file_path,
                    caption=caption
                )
            elif file_path.lower().endswith(('.mp3', '.m4a', '.wav', '.ogg')):
                await client.send_audio(
                    chat_id=chat_id,
                    audio=file_path,
                    caption=caption,
                    thumb=thumbnail,
                    progress=progress_callback if progress_callback else self.default_progress
                )
            else:
                await client.send_document(
                    chat_id=chat_id,
                    document=file_path,
                    caption=caption,
                    thumb=thumbnail,
                    progress=progress_callback if progress_callback else self.default_progress
                )
                
            return True, "Upload successful"
            
        except Exception as e:
            return False, str(e)
            
    async def upload_to_cloud(
        self,
        file_path: str,
        destination: str,
        progress_callback: Optional[Callable] = None
    ):
        """Upload to cloud storage using rclone"""
        try:
            # Use rclone for cloud upload
            command = f"rclone copy '{file_path}' '{Config.RCLONE_REMOTE}:{destination}' --progress"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                return True, "Cloud upload successful"
            else:
                return False, "Cloud upload failed"
                
        except Exception as e:
            return False, str(e)
            
    async def default_progress(self, current, total):
        """Default progress callback"""
        if total > 0:
            percentage = (current / total) * 100
            if percentage % 20 == 0:  # Log every 20%
                print(f"Upload progress: {percentage:.1f}%")
                
    def get_file_type(self, file_path: str) -> str:
        """Get file type for upload"""
        ext = Utils.get_file_extension(file_path)
        
        video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.webm']
        audio_exts = ['.mp3', '.m4a', '.wav', '.ogg', '.flac']
        photo_exts = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        doc_exts = ['.pdf', '.zip', '.rar', '.7z', '.apk', '.exe']
        
        if ext in video_exts:
            return 'video'
        elif ext in audio_exts:
            return 'audio'
        elif ext in photo_exts:
            return 'photo'
        elif ext in doc_exts:
            return 'document'
        else:
            return 'document'
            
    async def upload_multiple(
        self,
        client: Client,
        files: list,
        chat_id: int,
        caption: str = ""
    ):
        """Upload multiple files"""
        results = []
        for file_path in files:
            success, message = await self.upload_to_telegram(
                client, file_path, chat_id, caption
            )
            results.append({'file': file_path, 'success': success, 'message': message})
        return results

# Create instance
uploader = UploadManager()
