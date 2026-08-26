# Add this to existing leech.py

from bot.core.fast_processor import fast_processor
from bot.core.heroku_speed import heroku_speed

@Client.on_message(filters.command("fastleech") & filters.private)
async def fast_leech_command(client: Client, message: Message):
    """Fast leech command - optimized for Heroku"""
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /fastleech <url>")
        return
    
    url = message.command[1]
    
    status_msg = await message.reply_text("⚡ **Fast Leech Started...**")
    
    try:
        # Check if M3U8
        if 'm3u8' in url.lower():
            result = await heroku_speed.process_m3u8_fast(url)
        else:
            # Regular download
            file_path = os.path.join(Config.DOWNLOAD_DIR, f"fast_{int(time.time())}.mp4")
            success = await heroku_speed.fast_download(url, file_path)
            
            if success:
                result = {'success': True, 'file': file_path}
            else:
                result = {'success': False}
                
        if result['success']:
            # Split and upload
            await heroku_speed.fast_split_and_upload(
                client,
                result['file'],
                message.chat.id
            )
            
            await status_msg.edit_text("✅ **Fast Leech Complete!**")
            
            # Clean up
            if os.path.exists(result['file']):
                os.remove(result['file'])
                
        else:
            await status_msg.edit_text("❌ **Fast leech failed!**")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
