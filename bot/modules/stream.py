import time
import os
import asyncio
import aiohttp
from typing import Optional, Dict
from bot.config import Config

class StreamManager:
    def __init__(self):
        self.active_streams = {}
        self.stream_servers = {}
        self.max_stream_size = 2 * 1024 * 1024 * 1024  # 2GB
        
    async def create_stream(
        self,
        file_path: str,
        stream_type: str = "video",  # video/audio
        quality: str = "auto"
    ) -> Optional[str]:
        """Create stream from file"""
        try:
            if not os.path.exists(file_path):
                return None
                
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_stream_size:
                return None
                
            # Generate stream ID
            stream_id = f"stream_{int(time.time())}_{os.path.basename(file_path)[:10]}"
            
            # Create stream info
            self.active_streams[stream_id] = {
                'file_path': file_path,
                'type': stream_type,
                'quality': quality,
                'created_at': time.time(),
                'active': True
            }
            
            return stream_id
            
        except:
            return None
            
    async def get_stream_url(self, stream_id: str) -> Optional[str]:
        """Get stream URL"""
        if stream_id not in self.active_streams:
            return None
            
        stream = self.active_streams[stream_id]
        file_path = stream['file_path']
        
        # Generate stream URL based on type
        if stream['type'] == 'video':
            return await self.create_video_stream(file_path)
        elif stream['type'] == 'audio':
            return await self.create_audio_stream(file_path)
            
        return None
        
    async def create_video_stream(self, file_path: str) -> Optional[str]:
        """Create video streaming URL"""
        try:
            # Use ffmpeg for HLS streaming
            output_dir = os.path.join(Config.DOWNLOAD_DIR, "streams")
            os.makedirs(output_dir, exist_ok=True)
            
            stream_id = os.path.splitext(os.path.basename(file_path))[0]
            hls_path = os.path.join(output_dir, f"{stream_id}.m3u8")
            
            command = f"ffmpeg -i '{file_path}' -codec: copy -start_number 0 -hls_time 10 -hls_list_size 0 -f hls '{hls_path}'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0:
                return hls_path
                
        except:
            pass
        return None
        
    async def create_audio_stream(self, file_path: str) -> Optional[str]:
        """Create audio streaming URL"""
        try:
            # For audio, direct file URL
            return file_path
        except:
            return None
            
    async def stream_file(self, client, message, file_path: str, stream_type: str = "video"):
        """Stream file to Telegram"""
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            if stream_type == "video":
                await client.send_video(
                    chat_id=message.chat.id,
                    video=file_path,
                    caption=file_name,
                    supports_streaming=True,
                    progress=self.progress_callback
                )
            elif stream_type == "audio":
                await client.send_audio(
                    chat_id=message.chat.id,
                    audio=file_path,
                    caption=file_name,
                    progress=self.progress_callback
                )
                
            return True
            
        except Exception as e:
            return False
            
    async def get_stream_info(self, stream_id: str) -> Optional[Dict]:
        """Get stream information"""
        return self.active_streams.get(stream_id)
        
    async def stop_stream(self, stream_id: str) -> bool:
        """Stop active stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['active'] = False
            del self.active_streams[stream_id]
            return True
        return False
        
    async def cleanup_streams(self):
        """Clean up inactive streams"""
        current_time = time.time()
        for stream_id in list(self.active_streams.keys()):
            stream = self.active_streams[stream_id]
            if not stream['active'] or current_time - stream['created_at'] > 3600:
                del self.active_streams[stream_id]
                
    async def progress_callback(self, current, total):
        """Progress callback for streaming"""
        if total > 0:
            percentage = (current / total) * 100
            if percentage % 20 == 0:
                print(f"Stream progress: {percentage:.1f}%")

# Create instance
stream_manager = StreamManager()
