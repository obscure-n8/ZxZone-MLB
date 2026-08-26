import os
import time
import asyncio
from typing import Dict, List, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.uploader import uploader
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

class VideoMergeSession:
    def __init__(self):
        self.active_sessions = {}
        self.session_timeout = 600  # 10 minutes
        
    def create_session(self, user_id: int) -> str:
        """Create new merge session"""
        session_id = Utils.generate_task_id()
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'videos': [],
            'created_at': time.time(),
            'active': True,
            'current_index': 0
        }
        return session_id
        
    def add_video(self, session_id: str, file_path: str, file_info: Dict):
        """Add video to session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['videos'].append({
                'file_path': file_path,
                'file_info': file_info,
                'added_at': time.time()
            })
            return True
        return False
        
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session info"""
        return self.active_sessions.get(session_id)
        
    def remove_session(self, session_id: str):
        """Remove session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
    def is_session_active(self, session_id: str) -> bool:
        """Check if session is active"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        if not session['active']:
            return False
            
        if time.time() - session['created_at'] > self.session_timeout:
            return False
            
        return True

# Create instance
merge_session = VideoMergeSession()

@Client.on_message(filters.command("vmerge") & filters.private)
async def vmerge_command(client: Client, message: Message):
    """Start video merge session"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check if URL/file provided
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(
            "🎬 **Video Merge System**\n\n"
            "📝 **Usage:**\n"
            "/vmerge <url> - Start merge with URL\n"
            "/vmerge - Reply to video file\n\n"
            "**Commands during session:**\n"
            "/addvideo <url> - Add more videos\n"
            "/addvideo - Reply to video\n"
            "/mergelist - View videos\n"
            "/mergefinish - Finish and merge\n"
            "/mergecancel - Cancel session",
            parse_mode="markdown"
        )
        return
    
    # Create session
    session_id = merge_session.create_session(user.id)
    
    # Get first video
    if message.reply_to_message:
        if not message.reply_to_message.video and not message.reply_to_message.document:
            await message.reply_text("❌ **Reply to a video file!**")
            return
            
        status_msg = await message.reply_text("📥 **Downloading first video...**")
        
        try:
            file_path = await message.reply_to_message.download()
            file_info = {
                'name': os.path.basename(file_path),
                'size': os.path.getsize(file_path)
            }
            
            merge_session.add_video(session_id, file_path, file_info)
            
            await status_msg.edit_text(
                f"🎬 **Video Merge Session Started!**\n\n"
                f"🔖 **Session ID:** `{session_id}`\n"
                f"📊 **Videos Added:** 1\n\n"
                f"**Next steps:**\n"
                f"• Send more videos with /addvideo\n"
                f"• View list with /mergelist\n"
                f"• Finish with /mergefinish",
                parse_mode="markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📊 View List", callback_data=f"vmerge_list_{session_id}"),
                        InlineKeyboardButton("✅ Finish", callback_data=f"vmerge_finish_{session_id}")
                    ]
                ])
            )
            
        except Exception as e:
            await status_msg.edit_text(f"❌ **Error:** {str(e)}")
            merge_session.remove_session(session_id)
            
    else:
        url = message.command[1]
        status_msg = await message.reply_text("📥 **Downloading first video...**")
        
        try:
            from bot.modules.downloader import downloader
            file_path = os.path.join(Config.DOWNLOAD_DIR, f"vmerge_{session_id}_1.mp4")
            
            success = await downloader.download_file(url, file_path)
            
            if success:
                file_info = {
                    'name': os.path.basename(file_path),
                    'size': os.path.getsize(file_path)
                }
                
                merge_session.add_video(session_id, file_path, file_info)
                
                await status_msg.edit_text(
                    f"🎬 **Video Merge Session Started!**\n\n"
                    f"🔖 **Session ID:** `{session_id}`\n"
                    f"📊 **Videos Added:** 1\n\n"
                    f"**Next steps:**\n"
                    f"• Add more videos with /addvideo\n"
                    f"• View list with /mergelist\n"
                    f"• Finish with /mergefinish",
                    parse_mode="markdown"
                )
            else:
                await status_msg.edit_text("❌ **Download failed!**")
                merge_session.remove_session(session_id)
                
        except Exception as e:
            await status_msg.edit_text(f"❌ **Error:** {str(e)}")
            merge_session.remove_session(session_id)

@Client.on_message(filters.command("addvideo") & filters.private)
async def add_video_command(client: Client, message: Message):
    """Add video to merge session"""
    user = message.from_user
    
    # Find active session for user
    session_id = find_user_session(user.id)
    
    if not session_id:
        await message.reply_text("❌ **No active merge session!**\n\nStart with /vmerge")
        return
    
    # Check if URL or file
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/addvideo <url> - Add video by URL\n"
            "/addvideo - Reply to video file",
            parse_mode="markdown"
        )
        return
    
    status_msg = await message.reply_text("📥 **Downloading video...**")
    
    try:
        if message.reply_to_message:
            if not message.reply_to_message.video and not message.reply_to_message.document:
                await status_msg.edit_text("❌ **Reply to a video file!**")
                return
                
            file_path = await message.reply_to_message.download()
        else:
            url = message.command[1]
            from bot.modules.downloader import downloader
            
            video_count = len(merge_session.get_session(session_id)['videos']) + 1
            file_path = os.path.join(Config.DOWNLOAD_DIR, f"vmerge_{session_id}_{video_count}.mp4")
            
            success = await downloader.download_file(url, file_path)
            
            if not success:
                await status_msg.edit_text("❌ **Download failed!**")
                return
                
        file_info = {
            'name': os.path.basename(file_path),
            'size': os.path.getsize(file_path)
        }
        
        merge_session.add_video(session_id, file_path, file_info)
        
        session = merge_session.get_session(session_id)
        video_count = len(session['videos'])
        total_size = sum(v['file_info']['size'] for v in session['videos'])
        
        await status_msg.edit_text(
            f"✅ **Video Added!**\n\n"
            f"📊 **Total Videos:** {video_count}\n"
            f"💾 **Total Size:** {progress_helper.format_size(total_size)}\n\n"
            f"• Add more with /addvideo\n"
            f"• Finish with /mergefinish",
            parse_mode="markdown"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.command("mergelist") & filters.private)
async def merge_list_command(client: Client, message: Message):
    """View merge session list"""
    user = message.from_user
    
    session_id = find_user_session(user.id)
    
    if not session_id:
        await message.reply_text("❌ **No active merge session!**")
        return
    
    session = merge_session.get_session(session_id)
    videos = session['videos']
    
    list_text = f"🎬 **Video Merge List**\n\n"
    list_text += f"🔖 **Session ID:** `{session_id}`\n"
    list_text += f"📊 **Total Videos:** {len(videos)}\n\n"
    
    for i, video in enumerate(videos, 1):
        list_text += f"{i}. {video['file_info']['name']}\n"
        list_text += f"   💾 Size: {progress_helper.format_size(video['file_info']['size'])}\n\n"
        
    total_size = sum(v['file_info']['size'] for v in videos)
    list_text += f"📦 **Total Size:** {progress_helper.format_size(total_size)}"
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Finish", callback_data=f"vmerge_finish_{session_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"vmerge_cancel_{session_id}")
        ]
    ])
    
    await message.reply_text(list_text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_message(filters.command("mergefinish") & filters.private)
async def merge_finish_command(client: Client, message: Message):
    """Finish and merge videos"""
    user = message.from_user
    
    session_id = find_user_session(user.id)
    
    if not session_id:
        await message.reply_text("❌ **No active merge session!**")
        return
    
    session = merge_session.get_session(session_id)
    videos = session['videos']
    
    if len(videos) < 2:
        await message.reply_text("❌ **Need at least 2 videos to merge!**")
        return
    
    status_msg = await message.reply_text(
        f"🎬 **Starting Merge...**\n\n"
        f"📊 Videos: {len(videos)}\n"
        f"⏳ Processing..."
    )
    
    try:
        # Merge videos
        merged_path = await merge_videos(videos, status_msg)
        
        if merged_path:
            merged_size = os.path.getsize(merged_path)
            
            # Get user split size
            user_data = await users_db.get_user(user.id)
            is_premium = user_data.get('is_premium', False) if user_data else False
            has_session = user_data.get('has_session', False) if user_data else False
            
            if is_premium and has_session:
                split_size = 4 * 1024 * 1024 * 1024  # 4GB
            elif is_premium:
                split_size = 3 * 1024 * 1024 * 1024  # 3GB
            else:
                split_size = 2 * 1024 * 1024 * 1024  # 2GB
                
            # Check if dump channel configured
            dump_chat = Config.LEECH_DUMP_CHAT
            
            await status_msg.edit_text("📤 **Uploading merged video...**")
            
            if dump_chat:
                # Upload to dump channel
                await uploader.upload_to_telegram(
                    client,
                    merged_path,
                    int(dump_chat),
                    caption=f"🎬 Merged Video\n📊 {len(videos)} videos merged",
                    user_id=user.id
                )
                upload_destination = "Dump Channel"
            else:
                # Upload to user DM
                await uploader.upload_to_telegram(
                    client,
                    merged_path,
                    message.chat.id,
                    caption=f"🎬 Merged Video\n📊 {len(videos)} videos merged",
                    user_id=user.id
                )
                upload_destination = "Your DM"
                
            await status_msg.edit_text(
                f"✅ **Merge Complete!**\n\n"
                f"📊 Videos Merged: {len(videos)}\n"
                f"💾 Final Size: {progress_helper.format_size(merged_size)}\n"
                f"📤 Uploaded to: {upload_destination}",
                parse_mode="markdown"
            )
            
            # Clean up
            for video in videos:
                if os.path.exists(video['file_path']):
                    os.remove(video['file_path'])
                    
            if os.path.exists(merged_path):
                os.remove(merged_path)
                
            merge_session.remove_session(session_id)
            
        else:
            await status_msg.edit_text("❌ **Merge failed!**")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.command("mergecancel") & filters.private)
async def merge_cancel_command(client: Client, message: Message):
    """Cancel merge session"""
    user = message.from_user
    
    session_id = find_user_session(user.id)
    
    if not session_id:
        await message.reply_text("❌ **No active merge session!**")
        return
    
    session = merge_session.get_session(session_id)
    
    # Clean up videos
    for video in session['videos']:
        if os.path.exists(video['file_path']):
            os.remove(video['file_path'])
            
    merge_session.remove_session(session_id)
    
    await message.reply_text("✅ **Merge session cancelled!**")

@Client.on_callback_query(filters.regex("^vmerge_"))
async def vmerge_callback(client: Client, callback_query: CallbackQuery):
    """Handle merge callbacks"""
    data = callback_query.data
    parts = data.split('_')
    action = parts[1]
    session_id = parts[2] if len(parts) > 2 else ''
    
    if action == "list":
        session = merge_session.get_session(session_id)
        if session:
            videos = session['videos']
            list_text = f"📊 **Videos:** {len(videos)}\n\n"
            for i, video in enumerate(videos, 1):
                list_text += f"{i}. {video['file_info']['name']}\n"
            await callback_query.answer(list_text, show_alert=True)
            
    elif action == "finish":
        await callback_query.message.edit_text("✅ **Finishing merge...**")
        # Trigger merge finish
        await merge_finish_command(client, callback_query.message)
        
    elif action == "cancel":
        if session_id in merge_session.active_sessions:
            session = merge_session.get_session(session_id)
            for video in session['videos']:
                if os.path.exists(video['file_path']):
                    os.remove(video['file_path'])
            merge_session.remove_session(session_id)
        await callback_query.message.edit_text("❌ **Session cancelled!**")

async def merge_videos(videos: List[Dict], status_msg: Message) -> Optional[str]:
    """Merge multiple videos using ffmpeg"""
    try:
        # Create file list
        file_list_path = os.path.join(Config.DOWNLOAD_DIR, f"merge_list_{int(time.time())}.txt")
        
        with open(file_list_path, 'w') as f:
            for video in videos:
                f.write(f"file '{video['file_path']}'\n")
                
        # Output path
        output_path = os.path.join(Config.DOWNLOAD_DIR, f"merged_{int(time.time())}.mp4")
        
        # Merge command
        command = f"ffmpeg -f concat -safe 0 -i '{file_list_path}' -c copy '{output_path}'"
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.wait()
        
        # Clean up file list
        if os.path.exists(file_list_path):
            os.remove(file_list_path)
            
        if os.path.exists(output_path):
            return output_path
            
    except Exception as e:
        print(f"Merge error: {e}")
        
    return None

def find_user_session(user_id: int) -> Optional[str]:
    """Find active session for user"""
    for session_id, session in merge_session.active_sessions.items():
        if session['user_id'] == user_id and session['active']:
            return session_id
    return None
