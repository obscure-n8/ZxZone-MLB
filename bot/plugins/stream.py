import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.stream import stream_manager
from bot.helpers.utils import Utils
from bot.database.users import users_db

@Client.on_message(filters.command("stream") & filters.private)
async def stream_command(client: Client, message: Message):
    """Handle /stream command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check if streaming is disabled
    if Config.DISABLE_STREAM:
        await message.reply_text("❌ **Streaming is disabled!**")
        return
    
    # Check if URL provided
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /stream <url>\n\n"
            "Stream video directly in Telegram!",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    
    if not Utils.is_valid_url(url):
        await message.reply_text("❌ **Invalid URL!**")
        return
    
    # Create status message
    status_msg = await message.reply_text(
        "🎬 **Streaming Started**\n\n"
        f"🔗 URL: {url[:50]}...\n"
        f"⏳ Preparing stream...",
        parse_mode="markdown"
    )
    
    try:
        # Download file
        from bot.modules.downloader import downloader
        file_path = os.path.join(Config.DOWNLOAD_DIR, f"stream_{Utils.generate_task_id()}")
        
        await status_msg.edit_text("📥 **Downloading for stream...**")
        
        success = await downloader.download_file(url, file_path)
        
        if not success:
            await status_msg.edit_text("❌ **Download failed!**")
            return
            
        # Create stream
        await status_msg.edit_text("🎬 **Creating stream...**")
        
        stream_id = await stream_manager.create_stream(file_path, "video")
        
        if stream_id:
            # Send stream
            await status_msg.edit_text("📤 **Sending stream...**")
            
            await stream_manager.stream_file(client, message, file_path, "video")
            
            await status_msg.edit_text("✅ **Stream completed!**")
        else:
            await status_msg.edit_text("❌ **Failed to create stream!**")
            
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.video & filters.private)
async def stream_video_file(client: Client, message: Message):
    """Stream video file directly"""
    user = message.from_user
    
    if not message.video:
        return
        
    video = message.video
    file_size = video.file_size
    
    # Check if file can be streamed
    if file_size > 2 * 1024 * 1024 * 1024:
        await message.reply_text("❌ **File too large for streaming!**")
        return
        
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Stream", callback_data=f"stream_{message.id}"),
            InlineKeyboardButton("⬇️ Download", callback_data=f"download_{message.id}")
        ]
    ])
    
    await message.reply_text(
        f"🎬 **Video Ready!**\n\n"
        f"📁 File: {video.file_name}\n"
        f"💾 Size: {file_size / (1024*1024):.2f} MB\n"
        f"⏱ Duration: {video.duration} seconds\n\n"
        f"Choose an option:",
        reply_markup=keyboard,
        parse_mode="markdown"
    )

@Client.on_callback_query(filters.regex("^stream_"))
async def stream_callback(client: Client, callback_query):
    """Handle stream callback"""
    message_id = int(callback_query.data.split("_")[1])
    
    # Get the video message
    video_message = await client.get_messages(
        callback_query.message.chat.id,
        message_id
    )
    
    if video_message.video:
        await callback_query.answer("Starting stream...")
        
        # Download and stream
        file_path = await video_message.download()
        await stream_manager.stream_file(
            client,
            callback_query.message,
            file_path,
            "video"
        )
        
        # Clean up
        import os
        if os.path.exists(file_path):
            os.remove(file_path)

@Client.on_callback_query(filters.regex("^download_"))
async def download_callback(client: Client, callback_query):
    """Handle download callback"""
    message_id = int(callback_query.data.split("_")[1])
    
    video_message = await client.get_messages(
        callback_query.message.chat.id,
        message_id
    )
    
    if video_message.video:
        await callback_query.answer("Downloading...")
        
        file_path = await video_message.download()
        
        await client.send_document(
            callback_query.message.chat.id,
            file_path
        )
        
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
