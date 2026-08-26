import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.helpers.progress import Progress
from bot.modules.uploader import uploader
from bot.database.users import users_db
from bot.database.tasks import tasks_db

progress_helper = Progress()

@Client.on_message(filters.command("gofile") & filters.private)
async def gofile_command(client: Client, message: Message):
    """Handle /gofile command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /gofile <gofile_link>\n\n"
            "Download from Gofile.io",
            parse_mode="markdown"
        )
        return
    
    gofile_link = message.command[1]
    
    if 'gofile.io' not in gofile_link:
        await message.reply_text("❌ **Invalid Gofile link!**")
        return
    
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text(
        f"📁 **Gofile Download Started**\n\n"
        f"🔖 **Task ID:** `{task_id}`\n"
        f"📊 **Status:** Fetching file info...",
        parse_mode="markdown"
    )
    
    await tasks_db.add_task(task_id, user.id, 'gofile', gofile_link)
    
    try:
        # Gofile API
        api_url = "https://api.gofile.io/getServer"
        response = requests.get(api_url)
        server = response.json()['data']['server']
        
        # Get file info
        file_id = gofile_link.split('/')[-1]
        info_url = f"https://{server}.gofile.io/getContent?contentId={file_id}"
        response = requests.get(info_url)
        file_data = response.json()['data']
        
        if 'children' in file_data:
            files = file_data['children']
            for file_id, file_info in files.items():
                file_name = file_info['name']
                file_size = file_info['size']
                download_link = file_info['link']
                
                await status_msg.edit_text(
                    f"📁 **Downloading:** {file_name}\n"
                    f"💾 **Size:** {progress_helper.format_size(file_size)}",
                    parse_mode="markdown"
                )
                
                # Download file
                file_path = os.path.join(Config.DOWNLOAD_DIR, file_name)
                
                response = requests.get(download_link, stream=True)
                total = int(response.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        if total > 0 and time.time() - progress_helper.last_update_time > 2:
                            progress_helper.last_update_time = time.time()
                            percentage = (downloaded / total) * 100
                            speed = downloaded / (time.time() - start_time)
                            
                            system = progress_helper.get_system_stats()
                            progress_bar = progress_helper.get_progress_bar(percentage)
                            
                            progress_text = f"""
**Zonexus M/L Bot 1**
┌ **{Config.BOT_USERNAME}**
└ `/leech1 {task_id}`

▍ **Powered By Zonexus Hub** ❞

1. `{file_name}`
┌ **Task By {user.first_name}**
│ {progress_bar} {percentage:.1f}%
│ **Status** : Download
│ **Total** : {progress_helper.format_size(total)} | **Done** : {progress_helper.format_size(downloaded)}
│ **Speed** : {progress_helper.format_speed(speed)} | **ETA** : {progress_helper.format_eta((total-downloaded)/speed if speed > 0 else 0)}
│ **Engine** : Gofile | **Mode** : `#Gofile`
> **Stop** : `/c_{task_id}`

⬢ **BOT STATS**
┌ **CPU** : {system['cpu']}% | **RAM** : {system['ram']}%
└ **FREE** : {system['free_disk']}
"""
                            
                            try:
                                await status_msg.edit_text(progress_text, parse_mode="markdown")
                            except:
                                pass
                
                # Upload to Telegram
                await status_msg.edit_text("📤 **Uploading to Telegram...**")
                
                success, msg = await uploader.upload_to_telegram(
                    client,
                    file_path,
                    message.chat.id,
                    caption=f"📁 **Gofile:** {file_name}"
                )
                
                if success:
                    await status_msg.edit_text(
                        f"✅ **Download Complete!**\n\n"
                        f"📁 **File:** {file_name}",
                        parse_mode="markdown"
                    )
                    await tasks_db.update_task_status(task_id, 'completed')
                    await users_db.increment_downloads(user.id)
                    
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                break  # Only first file
                
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        await tasks_db.update_task_status(task_id, 'failed')
