from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.helpers.utils import Utils

@Client.on_message(filters.command("ytdlleech") & filters.private)
async def ytdlleech_command(client: Client, message: Message):
    """YouTube leech - Download and upload to Telegram"""
    user = message.from_user
    
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if Config.DISABLE_YTDLP:
        await message.reply_text("❌ **YT-DLP is disabled!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /ytdlleech <youtube_url>",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text(
        f"📹 **YouTube Leech Started**\n\n"
        f"🔖 Task ID: `{task_id}`\n"
        f"⏳ Downloading..."
    )
    
    await tasks_db.add_task(task_id, user.id, 'ytdlleech', url)
    
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(Config.DOWNLOAD_DIR, f'{task_id}_%(title)s.%(ext)s'),
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            await status_msg.edit_text("📤 **Uploading to Telegram...**")
            
            from bot.modules.uploader import uploader
            success, msg = await uploader.upload_to_telegram(
                client, file_path, message.chat.id,
                caption=f"📹 {info.get('title', 'YouTube Video')}",
                user_id=user.id
            )
            
            if success:
                await status_msg.edit_text("✅ **YouTube Leech Complete!**")
                await tasks_db.update_task_status(task_id, 'completed')
            else:
                await status_msg.edit_text(f"❌ **Upload failed:** {msg}")
                
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.command("yt-dl") & filters.private)
async def ytdl_command(client: Client, message: Message):
    """YouTube download - Download only"""
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /yt-dl <youtube_url>")
        return
    
    url = message.command[1]
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text("📹 **YouTube Download Started...**")
    
    await tasks_db.add_task(task_id, user.id, 'ytdl', url)
    
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(Config.DOWNLOAD_DIR, f'{task_id}_%(title)s.%(ext)s'),
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            await status_msg.edit_text(
                f"✅ **Download Complete!**\n\n"
                f"📁 File: {os.path.basename(file_path)}"
            )
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
