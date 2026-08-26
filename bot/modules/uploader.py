import os
import asyncio
from typing import Optional, Callable
from pyrogram import Client
from bot.config import Config
from bot.helpers.utils import Utils

class UploadManager:
    def __init__(self):
        self.active_uploads = {}
        
    async def get_split_size(self, user_id: int) -> int:
        """Get split size based on user type"""
        try:
            from bot.database.users import users_db
            user = await users_db.get_user(user_id)
            is_premium = user.get('is_premium', False) if user else False
            has_session = user.get('has_session', False) if user else False
            
            if is_premium and has_session:
                return 4 * 1024 * 1024 * 1024  # 4GB
            elif is_premium:
                return 3 * 1024 * 1024 * 1024  # 3GB
            elif has_session:
                return 2.5 * 1024 * 1024 * 1024  # 2.5GB
            else:
                return 2 * 1024 * 1024 * 1024  # 2GB
        except:
            return 2 * 1024 * 1024 * 1024  # 2GB
            
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
        """Upload file to telegram with auto HD thumbnail"""
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # Auto generate HD thumbnail for videos
            if not thumbnail and file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                try:
                    from bot.modules.hd_thumbnail import hd_thumbnail
                    
                    if hd_thumbnail.enabled:
                        result = await hd_thumbnail.generate_hd_thumbnail(
                            file_path,
                            quality='hd',
                            width=1280,
                            height=720
                        )
                        
                        if result['success']:
                            thumbnail = result['thumbnail']
                except:
                    pass
            
            # Check if file needs splitting
            if user_id:
                split_size = await self.get_split_size(user_id)
            else:
                split_size = 2 * 1024 * 1024 * 1024  # Default 2GB
                
            if file_size > split_size:
                # Split and upload
                return await self.split_and_upload(
                    client, file_path, chat_id, caption, split_size, user_id, thumbnail
                )
            else:
                # Direct upload
                await self.direct_upload(
                    client, file_path, chat_id, caption, as_video, thumbnail
                )
                
            # Clean up thumbnail after upload
            if thumbnail and os.path.exists(thumbnail):
                try:
                    os.remove(thumbnail)
                except:
                    pass
                    
            return True, "Upload successful"
            
        except Exception as e:
            return False, str(e)
            
    async def split_and_upload(self, client, file_path, chat_id, caption, split_size, user_id, thumbnail=None):
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
                part_caption = f"{caption}\n\nPart {i}/{num_parts}"
                
                # Check if part is video
                if part_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                    await client.send_video(
                        chat_id,
                        part_path,
                        caption=part_caption,
                        thumb=thumbnail if i == 1 else None,
                        supports_streaming=True,
                        width=1280,
                        height=720
                    )
                else:
                    await client.send_document(
                        chat_id,
                        part_path,
                        caption=part_caption,
                        thumb=thumbnail if i == 1 else None
                    )
                    
                # Delete uploaded part
                os.remove(part_path)
                
            return True, f"Uploaded in {num_parts} parts"
            
        except Exception as e:
            return False, str(e)
            
    async def direct_upload(self, client, file_path, chat_id, caption, as_video, thumbnail=None):
        """Direct upload without splitting"""
        if file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
            await client.send_video(
                chat_id,
                file_path,
                caption=caption,
                thumb=thumbnail,
                supports_streaming=True,
                width=1280,
                height=720
            )
        elif file_path.lower().endswith(('.mp3', '.m4a', '.wav', '.ogg')):
            await client.send_audio(
                chat_id,
                file_path,
                caption=caption,
                thumb=thumbnail
            )
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            await client.send_photo(
                chat_id,
                file_path,
                caption=caption
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
                
            # Auto generate HD thumbnail
            thumbnail = None
            if file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                try:
                    from bot.modules.hd_thumbnail import hd_thumbnail
                    
                    if hd_thumbnail.enabled:
                        result = await hd_thumbnail.generate_hd_thumbnail(
                            file_path,
                            quality='hd',
                            width=1280,
                            height=720
                        )
                        
                        if result['success']:
                            thumbnail = result['thumbnail']
                except:
                    pass
                    
            # Upload to dump channel
            if file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                await client.send_video(
                    int(dump_chat),
                    file_path,
                    caption=f"Dump Upload\nUser: {user_id or 'Unknown'}",
                    thumb=thumbnail,
                    supports_streaming=True,
                    width=1280,
                    height=720
                )
            else:
                await client.send_document(
                    int(dump_chat),
                    file_path,
                    caption=f"Dump Upload\nUser: {user_id or 'Unknown'}",
                    thumb=thumbnail
                )
                
            # Clean up thumbnail
            if thumbnail and os.path.exists(thumbnail):
                try:
                    os.remove(thumbnail)
                except:
                    pass
                    
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
