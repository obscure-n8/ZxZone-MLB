import os
import asyncio
from typing import Optional, Dict, List
from pyrogram import Client
from bot.config import Config
from bot.helpers.utils import Utils

class ChannelMirror:
    def __init__(self):
        self.active_mirrors = {}
        self.mirror_settings = {}
        
    async def start_mirror(
        self,
        client: Client,
        source_chat: int,
        target_chat: int,
        mirror_type: str = "all",  # all/documents/videos/photos
        copy_caption: bool = True,
        delete_original: bool = False
    ) -> str:
        """Start channel mirroring"""
        mirror_id = Utils.generate_task_id()
        
        self.mirror_settings[mirror_id] = {
            'source_chat': source_chat,
            'target_chat': target_chat,
            'mirror_type': mirror_type,
            'copy_caption': copy_caption,
            'delete_original': delete_original,
            'active': True,
            'started_at': asyncio.get_event_loop().time(),
            'total_mirrored': 0,
            'last_message_id': 0
        }
        
        # Start mirror task
        asyncio.create_task(self._mirror_loop(client, mirror_id))
        
        return mirror_id
        
    async def _mirror_loop(self, client: Client, mirror_id: str):
        """Mirror loop"""
        settings = self.mirror_settings[mirror_id]
        
        while settings['active']:
            try:
                # Get messages from source chat
                messages = await client.get_history(
                    settings['source_chat'],
                    limit=10
                )
                
                for message in reversed(messages):
                    if message.id <= settings['last_message_id']:
                        continue
                        
                    # Update last message ID
                    settings['last_message_id'] = message.id
                    
                    # Check mirror type
                    if not self._should_mirror(message, settings['mirror_type']):
                        continue
                        
                    # Copy message to target
                    await self._copy_message(client, message, settings)
                    
                    settings['total_mirrored'] += 1
                    
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                await asyncio.sleep(30)  # Wait longer on error
                
    def _should_mirror(self, message, mirror_type: str) -> bool:
        """Check if message should be mirrored"""
        if mirror_type == "all":
            return True
        elif mirror_type == "documents":
            return bool(message.document)
        elif mirror_type == "videos":
            return bool(message.video)
        elif mirror_type == "photos":
            return bool(message.photo)
        return False
        
    async def _copy_message(self, client: Client, message, settings: Dict):
        """Copy message to target chat"""
        try:
            # Copy based on message type
            if message.document:
                await client.send_document(
                    settings['target_chat'],
                    message.document.file_id,
                    caption=message.caption if settings['copy_caption'] else None
                )
            elif message.video:
                await client.send_video(
                    settings['target_chat'],
                    message.video.file_id,
                    caption=message.caption if settings['copy_caption'] else None
                )
            elif message.photo:
                await client.send_photo(
                    settings['target_chat'],
                    message.photo.file_id,
                    caption=message.caption if settings['copy_caption'] else None
                )
            elif message.text:
                await client.send_message(
                    settings['target_chat'],
                    message.text
                )
                
            # Delete original if needed
            if settings['delete_original']:
                await message.delete()
                
        except Exception as e:
            print(f"Copy error: {e}")
            
    async def stop_mirror(self, mirror_id: str) -> bool:
        """Stop mirroring"""
        if mirror_id in self.mirror_settings:
            self.mirror_settings[mirror_id]['active'] = False
            return True
        return False
        
    async def get_mirror_status(self, mirror_id: str) -> Optional[Dict]:
        """Get mirror status"""
        return self.mirror_settings.get(mirror_id)
        
    async def get_all_mirrors(self) -> Dict:
        """Get all active mirrors"""
        return self.mirror_settings
        
    async def pause_mirror(self, mirror_id: str) -> bool:
        """Pause mirroring"""
        if mirror_id in self.mirror_settings:
            self.mirror_settings[mirror_id]['active'] = False
            return True
        return False
        
    async def resume_mirror(self, mirror_id: str) -> bool:
        """Resume mirroring"""
        if mirror_id in self.mirror_settings:
            self.mirror_settings[mirror_id]['active'] = True
            return True
        return False

# Create instance
channel_mirror = ChannelMirror()
