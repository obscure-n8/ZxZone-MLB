import os
import time
import asyncio
import subprocess
from typing import Optional, Dict
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.helpers.progress import Progress
from bot.modules.uploader import uploader

progress_helper = Progress()

class VideoTools:
    def __init__(self):
        self.active_panels = {}
        self.panel_timeout = 600  # 10 minutes
        
    async def show_video_panel(self, client: Client, message: Message, file_path: str, file_info: Dict = None):
        """Show video tools panel with inline buttons"""
        try:
            # Get video info
            if not file_info:
                file_info = await self.get_video_info(file_path)
            
            # Create panel ID
            panel_id = f"vt_{message.from_user.id}_{int(time.time())}"
            
            # Store panel info
            self.active_panels[panel_id] = {
                'file_path': file_path,
                'file_info': file_info,
                'user_id': message.from_user.id,
                'created_at': time.time(),
                'active': True
            }
            
            # Create message text
            file_name = os.path.basename(file_path)
            file_size = file_info.get('size', 0)
            duration = file_info.get('duration', 0)
            
            panel_text = f"""
🎬 **Video Tools Panel**

📁 **File:** {file_name}
💾 **Size:** {progress_helper.format_size(file_size)}
⏱ **Duration:** {progress_helper.format_eta(duration)}
⚡ **Time Left: 600.0 sec**

Select an option to process video:
"""
            
            # Create keyboard
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Encode", callback_data=f"vt_encode_{panel_id}"),
                    InlineKeyboardButton("Convert", callback_data=f"vt_convert_{panel_id}")
                ],
                [
                    InlineKeyboardButton("Multi-Resolution", callback_data=f"vt_multi_{panel_id}"),
                    InlineKeyboardButton("Video + Video", callback_data=f"vt_vidvid_{panel_id}")
                ],
                [
                    InlineKeyboardButton("Video + Audio", callback_data=f"vt_vidaud_{panel_id}"),
                    InlineKeyboardButton("Video + Subtitle", callback_data=f"vt_vidsub_{panel_id}")
                ],
                [
                    InlineKeyboardButton("Video+Audio+Sub", callback_data=f"vt_vas_{panel_id}"),
                    InlineKeyboardButton("IntroSub", callback_data=f"vt_introsub_{panel_id}")
                ],
                [
                    InlineKeyboardButton("HardSub", callback_data=f"vt_hardsub_{panel_id}"),
                    InlineKeyboardButton("Remove Subs", callback_data=f"vt_remsub_{panel_id}")
                ],
                [
                    InlineKeyboardButton("Remove Audio", callback_data=f"vt_remaud_{panel_id}"),
                    InlineKeyboardButton("Remove Streams", callback_data=f"vt_remstream_{panel_id}")
                ],
                [
                    InlineKeyboardButton("Strip Metadata", callback_data=f"vt_strip_{panel_id}"),
                    InlineKeyboardButton("Extract Subs/Audio", callback_data=f"vt_extract_{panel_id}")
                ],
                [
                    InlineKeyboardButton("Swap Audio", callback_data=f"vt_swapaud_{panel_id}"),
                    InlineKeyboardButton("Watermark", callback_data=f"vt_water_{panel_id}")
                ],
                [
                    InlineKeyboardButton("Convert Audio", callback_data=f"vt_convaud_{panel_id}"),
                    InlineKeyboardButton("Aspect Ratio", callback_data=f"vt_aspect_{panel_id}")
                ],
                [
                    InlineKeyboardButton("X Cancel", callback_data=f"vt_cancel_{panel_id}")
                ]
            ])
            
            await message.reply_text(
                panel_text,
                reply_markup=keyboard,
                parse_mode="markdown"
            )
            
            # Start timeout countdown
            asyncio.create_task(self.panel_timeout_countdown(panel_id))
            
        except Exception as e:
            await message.reply_text(f"❌ **Error:** {str(e)}")
    
    async def get_video_info(self, file_path: str) -> Dict:
        """Get video information using ffprobe"""
        try:
            command = f"ffprobe -v quiet -print_format json -show_streams -show_format '{file_path}'"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                data = json.loads(stdout.decode())
                
                video_stream = None
                audio_stream = None
                subtitle_stream = None
                
                for stream in data.get('streams', []):
                    if stream['codec_type'] == 'video' and not video_stream:
                        video_stream = stream
                    elif stream['codec_type'] == 'audio' and not audio_stream:
                        audio_stream = stream
                    elif stream['codec_type'] == 'subtitle' and not subtitle_stream:
                        subtitle_stream = stream
                
                format_info = data.get('format', {})
                
                return {
                    'size': int(format_info.get('size', 0)),
                    'duration': float(format_info.get('duration', 0)),
                    'width': video_stream.get('width', 0) if video_stream else 0,
                    'height': video_stream.get('height', 0) if video_stream else 0,
                    'video_codec': video_stream.get('codec_name', '') if video_stream else '',
                    'audio_codec': audio_stream.get('codec_name', '') if audio_stream else '',
                    'has_audio': audio_stream is not None,
                    'has_subtitle': subtitle_stream is not None,
                    'fps': video_stream.get('avg_frame_rate', '') if video_stream else ''
                }
                
        except:
            pass
        return {}
    
    async def panel_timeout_countdown(self, panel_id: str):
        """Countdown timer for panel timeout"""
        try:
            await asyncio.sleep(self.panel_timeout)
            
            if panel_id in self.active_panels:
                self.active_panels[panel_id]['active'] = False
                del self.active_panels[panel_id]
                
        except:
            pass
    
    async def check_panel_active(self, panel_id: str) -> bool:
        """Check if panel is still active"""
        if panel_id not in self.active_panels:
            return False
        if not self.active_panels[panel_id]['active']:
            return False
        if time.time() - self.active_panels[panel_id]['created_at'] > self.panel_timeout:
            return False
        return True
    
    async def run_ffmpeg(self, command: str, status_msg: Message):
        """Run FFmpeg command with progress"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0:
                return True, "Success"
            else:
                return False, "FFmpeg error"
                
        except Exception as e:
            return False, str(e)
    
    async def process_video(self, callback_query: CallbackQuery, action: str, panel_id: str):
        """Process video based on action"""
        if not await self.check_panel_active(panel_id):
            await callback_query.answer("Panel expired!", show_alert=True)
            return
        
        panel_info = self.active_panels[panel_id]
        file_path = panel_info['file_path']
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(Config.DOWNLOAD_DIR, f"{file_name}_{action}.mp4")
        
        await callback_query.answer(f"Processing {action}...")
        status_msg = await callback_query.message.reply_text(f"🔄 **Processing {action}...**")
        
        # Build FFmpeg commands
        commands = {
            'encode': f"ffmpeg -i '{file_path}' -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k '{output_path}'",
            'convert': f"ffmpeg -i '{file_path}' -c:v libx264 -c:a aac '{output_path}'",
            'hardsub': f"ffmpeg -i '{file_path}' -vf subtitles='{file_path}' '{output_path}'",
            'strip': f"ffmpeg -i '{file_path}' -map_metadata -1 -c copy '{output_path}'",
            'remaud': f"ffmpeg -i '{file_path}' -an -c:v copy '{output_path}'",
            'water': f"ffmpeg -i '{file_path}' -vf drawtext=text='ZxZone':fontsize=24:fontcolor=white:x=10:y=10 '{output_path}'",
            'convaud': f"ffmpeg -i '{file_path}' -vn -c:a aac -b:a 192k '{os.path.splitext(output_path)[0]}.m4a'",
            'aspect': f"ffmpeg -i '{file_path}' -vf scale=1280:720 '{output_path}'",
        }
        
        command = commands.get(action)
        if not command:
            await status_msg.edit_text(f"❌ **Unknown action:** {action}")
            return
        
        success, result = await self.run_ffmpeg(command, status_msg)
        
        if success and os.path.exists(output_path):
            await status_msg.edit_text("📤 **Uploading processed video...**")
            
            await uploader.upload_to_telegram(
                callback_query.message._client,
                output_path,
                callback_query.message.chat.id,
                caption=f"✅ Processed: {action}"
            )
            
            await status_msg.edit_text("✅ **Processing complete!**")
            os.remove(output_path)
        else:
            await status_msg.edit_text(f"❌ **Processing failed:** {result}")
    
    async def handle_callback(self, client: Client, callback_query: CallbackQuery):
        """Handle video tools callbacks"""
        data = callback_query.data
        
        if not data.startswith('vt_'):
            return
        
        parts = data.split('_')
        action = parts[1]
        panel_id = '_'.join(parts[2:])
        
        if action == 'cancel':
            if panel_id in self.active_panels:
                del self.active_panels[panel_id]
            await callback_query.message.delete()
            await callback_query.answer("Panel cancelled!")
            return
        
        await self.process_video(callback_query, action, panel_id)

# Create instance
video_tools = VideoTools()

# Command handler
@Client.on_message(filters.command("vt") & filters.private)
async def vt_command(client: Client, message: Message):
    """Video tools command"""
    if not message.reply_to_message:
        await message.reply_text(
            "📝 **Usage:** Reply to a video file with /vt\n\n"
            "Or use /leech <url> -vt",
            parse_mode="markdown"
        )
        return
    
    replied = message.reply_to_message
    
    if not replied.video and not replied.document:
        await message.reply_text("❌ **Reply to a video file!**")
        return
    
    status_msg = await message.reply_text("📥 **Downloading video...**")
    
    try:
        file_path = await replied.download()
        await status_msg.edit_text("🎬 **Opening Video Tools Panel...**")
        
        await video_tools.show_video_panel(client, message, file_path)
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

# Register callback handler
@Client.on_callback_query(filters.regex("^vt_"))
async def vt_callback_handler(client: Client, callback_query: CallbackQuery):
    await video_tools.handle_callback(client, callback_query)
