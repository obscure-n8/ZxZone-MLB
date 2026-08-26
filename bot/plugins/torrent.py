import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.uploader import uploader
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

@Client.on_message(filters.command("torrent") & filters.private)
async def torrent_command(client: Client, message: Message):
    """Handle /torrent command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check if magnet link or torrent file
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /torrent <magnet_link>\n\n"
            "Or reply to a .torrent file",
            parse_mode="markdown"
        )
        return
    
    magnet_link = message.command[1]
    
    if not Utils.is_magnet_link(magnet_link):
        await message.reply_text("❌ **Invalid magnet link!**")
        return
    
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text(
        f"🧲 **Torrent Added**\n\n"
        f"🔖 **Task ID:** `{task_id}`\n"
        f"📊 **Status:** Fetching metadata...",
        parse_mode="markdown"
    )
    
    # Add task to database
    await tasks_db.add_task(task_id, user.id, 'torrent', magnet_link)
    await users_db.increment_tasks(user.id)
    
    try:
        # Use aria2 for torrent download
        import aria2p
        
        aria2 = aria2p.API(
            aria2p.Client(
                host=Config.ARIA2_HOST,
                port=Config.ARIA2_PORT,
                secret=Config.ARIA2_SECRET
            )
        )
        
        # Add torrent
        download = aria2.add_magnet(magnet_link)
        
        # Monitor progress
        while not download.is_complete:
            if download.is_failed:
                await status_msg.edit_text("❌ **Torrent failed!**")
                await tasks_db.update_task_status(task_id, 'failed')
                return
            
            # Update progress
            downloaded = download.completed_length
            total = download.total_length
            
            if total > 0:
                percentage = (downloaded / total) * 100
                speed = download.download_speed
                
                system = progress_helper.get_system_stats()
                progress_bar = progress_helper.get_progress_bar(percentage)
                
                progress_text = f"""
**Zonexus M/L Bot 1**
┌ **{Config.BOT_USERNAME}**
└ `/leech1 {task_id}`

▍ **Powered By Zonexus Hub** ❞

1. `{download.name}`
┌ **Task By {user.first_name}**
│ {progress_bar} {percentage:.1f}%
│ **Status** : Download
│ **Total** : {progress_helper.format_size(total)} | **Done** : {progress_helper.format_size(downloaded)}
│ **Speed** : {progress_helper.format_speed(speed)} | **ETA** : {progress_helper.format_eta(download.eta)}
│ **Engine** : Aria2 v1.37.0 | **Mode** : `#Torrent`
> **Stop** : `/c_{task_id}`

⬢ **BOT STATS**
┌ **CPU** : {system['cpu']}% | **RAM** : {system['ram']}%
└ **FREE** : {system['free_disk']}
"""
                
                try:
                    await status_msg.edit_text(progress_text, parse_mode="markdown")
                except:
                    pass
            
            await asyncio.sleep(2)
        
        # Upload completed file
        file_path = download.files[0].path
        
        await status_msg.edit_text("📤 **Uploading to Telegram...**")
        
        success, msg = await uploader.upload_to_telegram(
            client,
            file_path,
            message.chat.id,
            caption=f"🧲 **Torrent:** {download.name}"
        )
        
        if success:
            await status_msg.edit_text(
                f"✅ **Torrent Complete!**\n\n"
                f"📁 **File:** {download.name}\n"
                f"💾 **Size:** {progress_helper.format_size(total)}",
                parse_mode="markdown"
            )
            await tasks_db.update_task_status(task_id, 'completed')
            await users_db.increment_downloads(user.id)
        else:
            await status_msg.edit_text(f"❌ **Upload failed:** {msg}")
            await tasks_db.update_task_status(task_id, 'failed')
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await tasks_db.update_task_status(task_id, 'failed')

@Client.on_message(filters.document & filters.private)
async def handle_torrent_file(client: Client, message: Message):
    """Handle .torrent file upload"""
    if message.document and message.document.file_name.endswith('.torrent'):
        user = message.from_user
        
        status_msg = await message.reply_text("🧲 **Torrent file received, processing...**")
        
        try:
            # Download torrent file
            torrent_path = await message.download()
            
            # Read magnet link from torrent file
            import libtorrent as lt
            info = lt.torrent_info(torrent_path)
            magnet_link = f"magnet:?xt=urn:btih:{info.info_hash()}"
            
            # Process torrent
            await torrent_command(client, message, magnet_link)
            
            # Clean up
            os.remove(torrent_path)
            
        except Exception as e:
            await status_msg.edit_text(f"❌ **Error:** {str(e)}")
