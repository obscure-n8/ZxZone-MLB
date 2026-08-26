import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.hd_thumbnail import hd_thumbnail
from bot.database.users import users_db

@Client.on_message(filters.command("hdtumb") & filters.private)
async def hd_thumbnail_command(client: Client, message: Message):
    """HD Thumbnail command"""
    user = message.from_user
    
    # Show thumbnail settings
    stats = await hd_thumbnail.get_thumbnail_stats()
    
    text = f"""
🎨 **HD Thumbnail System**

✅ Status: {'Enabled' if stats['enabled'] else 'Disabled'}
📊 Total Thumbnails: {stats['total_thumbnails']}

**Features:**
• Auto HD thumbnail generation
• 1280x720 resolution
• 95% quality
• Multiple thumbnails
• Grid view
• Image enhancement

**Commands:**
/hdtumb - This menu
/hdtumb on - Enable auto thumbnail
/hdtumb off - Disable auto thumbnail
/hdtumb grid - Generate thumbnail grid

**Auto Thumbnail ON by default!**
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Enable", callback_data="hdtumb_on"),
            InlineKeyboardButton("❌ Disable", callback_data="hdtumb_off")
        ],
        [
            InlineKeyboardButton("🔲 Grid", callback_data="hdtumb_grid"),
            InlineKeyboardButton("📊 Stats", callback_data="hdtumb_stats")
        ]
    ])
    
    await message.reply_text(text, reply_markup=keyboard, parse_mode="markdown")

@Client.on_callback_query(filters.regex("^hdtumb_"))
async def hd_thumbnail_callback(client: Client, callback_query):
    """Handle HD thumbnail callbacks"""
    data = callback_query.data
    
    if data == "hdtumb_on":
        await hd_thumbnail.toggle_thumbnail(True)
        await callback_query.answer("HD Thumbnail Enabled!")
        
    elif data == "hdtumb_off":
        await hd_thumbnail.toggle_thumbnail(False)
        await callback_query.answer("HD Thumbnail Disabled!")
        
    elif data == "hdtumb_stats":
        stats = await hd_thumbnail.get_thumbnail_stats()
        await callback_query.answer(
            f"Total: {stats['total_thumbnails']} thumbnails",
            show_alert=True
        )
        
    elif data == "hdtumb_grid":
        await callback_query.answer("Reply to video with /hdtumbgrid")
        
    await callback_query.answer()

@Client.on_message(filters.command("hdtumbgrid") & filters.private)
async def hd_grid_command(client: Client, message: Message):
    """Generate thumbnail grid"""
    user = message.from_user
    
    if not message.reply_to_message:
        await message.reply_text("📝 **Usage:** Reply to video with /hdtumbgrid")
        return
        
    replied = message.reply_to_message
    
    if not replied.video and not replied.document:
        await message.reply_text("❌ **Reply to a video file!**")
        return
        
    status_msg = await message.reply_text("🎨 **Generating thumbnail grid...**")
    
    try:
        # Download video
        video_path = await replied.download()
        
        # Generate grid
        result = await hd_thumbnail.generate_thumbnail_grid(video_path, 4)
        
        if result['success']:
            # Send grid thumbnail
            await client.send_photo(
                message.chat.id,
                result['thumbnail'],
                caption="🎨 **HD Thumbnail Grid**\n\nGenerated automatically!"
            )
            
            await status_msg.edit_text("✅ **Thumbnail grid generated!**")
        else:
            await status_msg.edit_text("❌ **Failed to generate grid!**")
            
        # Clean up
        if os.path.exists(video_path):
            os.remove(video_path)
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
