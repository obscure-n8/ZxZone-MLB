import os
import asyncio
from typing import Optional, Callable
from pyrogram import Client
from bot.config import Config
from bot.helpers.utils import Utils
from bot.database.users import users_db

class UploadManager:
    def __init__(self):
        self.active_uploads = {}
        
    async def get_split_size(self, user_id: int) -> int:
        """Get split size based on user type"""
        try:
            # Check if user is premium
            user = await users_db.get_user(user_id)
            is_premium = user.get('is_premium', False) if user else False
            
            # Check if user has session string
            has_session = bool(user.get('session_string', '')) if user else False
            
            if is_premium and has_session:
                # Premium + Session = 4GB split
                return 4 * 1024 * 1024 * 1024  # 4GB
            elif is_premium:
                # Premium only = 3GB split
                return 3 * 1024 * 1024 * 1024  # 3GB
            elif has_session:
                # Session only = 2.5GB split
                return 2.5 * 1024 * 1024 * 1024  # 2.5GB
            else:
                # Normal user = 2GB split
                return 2 * 1024 * 1024 * 1024  # 2GB
                
        except:
            return 2 * 1024 * 1024 * 1024  # Default 2GB
            
    async def upload_to_telegram(
        self,
        client: Client,
        file_path: str,
        chat_id: int,
        caption: str = "",
        progress_callback: Optional[Callable] = None,
        as_video: bool = False,
        thumbnail: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """Upload file to telegram with smart split"""
        try:
            file_size = os.path.getsize(file_path)
            
            # Check if file needs splitting
            if user_id:
                split_size = await self.get_split_size(user_id)
            else:
                split_size = 2 * 1024 * 1024 * 1024  # Default 2GB
                
            if file_size > split_size:
                # Split and upload
                return await self.split_and_upload(
                    client, file_path, chat_id, caption, split_size, user_id
                )
            else:
                # Direct upload
                await self.direct_upload(
                    client, file_path, chat_id, caption, as_video, thumbnail
                )
                
            return True, "Upload successful"
            
        except Exception as e:
            return False, str(e)
            
    async def split_and_upload(self, client, file_path, chat_id, caption, split_size, user_id):
        """Split large file and upload parts"""
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Calculate number of parts
            num_parts = (file_size + split_size - 1) // split_size
            
            # Split file
            parts = []
            with open(file_path, 'rb') as f:
                for i in range(num_parts):
                    part_path = f"{file_path}.part{i+1:03d}"
                    with open(part_path, 'wb') as part_file:
                        remaining = min(split_size, file_size - (i * split_size))
                        while remaining > 0:
                            chunk = f.read(min(1024 * 1024, remaining))
                            if not chunk:
                                break
                            part_file.write(chunk)
                            remaining -= len(chunk)
                    parts.append(part_path)
                    
            # Upload each part
            for i, part_path in enumerate(parts, 1):
                part_caption = f"{caption}\n\n📦 Part {i}/{num_parts}"
                
                await client.send_document(
                    chat_id,
                    part_path,
                    caption=part_caption,
                    progress=self.default_progress
                )
                
                # Delete uploaded part
                os.remove(part_path)
                
            return True, f"Uploaded in {num_parts} parts"
            
        except Exception as e:
            return False, str(e)
            
    async def direct_upload(self, client, file_path, chat_id, caption, as_video, thumbnail):
        """Direct upload without splitting"""
        if as_video and file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            await client.send_video(
                chat_id,
                file_path,
                caption=caption,
                thumb=thumbnail,
                supports_streaming=True
            )
        else:
            await client.send_document(
                chat_id,
                file_path,
                caption=caption,
                thumb=thumbnail
            )
            
    async def upload_to_dump(self, client: Client, file_path: str, user_id: int = None):
        """Upload file to dump channel"""
        try:
            dump_chat = Config.LEECH_DUMP_CHAT
            
            if not dump_chat:
                return False, "Dump channel not configured"
                
            # Upload to dump channel
            await client.send_document(
                int(dump_chat),
                file_path,
                caption=f"📦 Dump Upload\n👤 User: {user_id or 'Unknown'}"
            )
            
            return True, "Uploaded to dump channel"
            
        except Exception as e:
            return False, str(e)
            
    async def default_progress(self, current, total):
        """Default progress callback"""
        if total > 0:
            percentage = (current / total) * 100
            if percentage % 20 == 0:
                print(f"Upload progress: {percentage:.1f}%")

# Create instance
uploader = UploadManager()
