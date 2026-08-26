import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.jdownloader import jdownloader
from bot.helpers.permissions import permission_system
from bot.database.tasks import tasks_db
from bot.helpers.utils import Utils

@Client.on_message(filters.command("jd") & filters.private)
async def jd_command(client: Client, message: Message):
    """JDownloader main command"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **JDownloader Commands:**\n\n"
            "/jd status - Check status\n"
            "/jd add <url> - Add links\n"
            "/jd start - Start downloads\n"
            "/jd stop - Stop downloads\n"
            "/jd list - Download list\n"
            "/jd speed <limit> - Set speed limit\n"
            "/jd premium - Check premium\n"
            "/jd grab <url> - Grab links from page",
            parse_mode="markdown"
        )
        return
    
    action = message.command[1].lower()
    
    if action == "status":
        # Check connection
        if not jdownloader.connected:
            await jdownloader.connect()
            
        status = await jdownloader.get_status()
        stats = await jdownloader.get_statistics()
        
        status_text = f"""
🔧 **JDownloader Status**

📡 **Connection:** {'✅ Connected' if jdownloader.connected else '❌ Disconnected'}

📊 **Statistics:**
• Total Downloads: {stats.get('total_downloads', 0)}
• Completed: {stats.get('completed', 0)}
• Active: {stats.get('active', 0)}
• Failed: {stats.get('failed', 0)}

⚡ **Speed:**
• Download: {stats.get('download_speed', '0')} KB/s
• Upload: {stats.get('upload_speed', '0')} KB/s
"""
        
        await message.reply_text(status_text, parse_mode="markdown")
        
    elif action == "add":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /jd add <url1> <url2> ...")
            return
            
        links = message.command[2:]
        result = await jdownloader.add_links(links)
        
        if result['success']:
            await message.reply_text(
                f"✅ **Links added!**\n\n"
                f"📊 Count: {len(links)}\n"
                f"📦 Package: ZxZone Downloads",
                parse_mode="markdown"
            )
        else:
            await message.reply_text(f"❌ **Error:** {result.get('error', 'Unknown')}")
            
    elif action == "start":
        if await jdownloader.start_downloads():
            await message.reply_text("✅ **Downloads started!**")
        else:
            await message.reply_text("❌ **Failed to start downloads!**")
            
    elif action == "stop":
        if await jdownloader.stop_downloads():
            await message.reply_text("✅ **Downloads stopped!**")
        else:
            await message.reply_text("❌ **Failed to stop downloads!**")
            
    elif action == "list":
        downloads = await jdownloader.get_download_list()
        
        if not downloads:
            await message.reply_text("📊 **No active downloads!**")
            return
            
        download_text = "📥 **Download List:**\n\n"
        
        for i, download in enumerate(downloads[:10], 1):
            download_text += f"{i}. {download.get('name', 'Unknown')}\n"
            download_text += f"   📊 Progress: {download.get('progress', 0)}%\n"
            download_text += f"   💾 Size: {download.get('size', 'N/A')}\n"
            download_text += f"   ⚡ Speed: {download.get('speed', 'N/A')}\n\n"
            
        await message.reply_text(download_text, parse_mode="markdown")
        
    elif action == "speed":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /jd speed <KB/s> (0 = unlimited)")
            return
            
        speed = int(message.command[2]) * 1024  # Convert to bytes
        await jdownloader.set_speed_limit(speed, speed)
        
        await message.reply_text(
            f"✅ **Speed limit set!**\n\n"
            f"⚡ Speed: {message.command[2]} KB/s",
            parse_mode="markdown"
        )
        
    elif action == "premium":
        premium_status = await jdownloader.check_premium_status()
        
        premium_text = f"""
💎 **Premium Account Status**

"""
        for host, status in premium_status.items():
            premium_text += f"• {host}: {'✅ Active' if status else '❌ Inactive'}\n"
            
        await message.reply_text(premium_text, parse_mode="markdown")
        
    elif action == "grab":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /jd grab <url>")
            return
            
        url = message.command[2]
        links = await jdownloader.grab_links_from_page(url)
        
        if links:
            links_text = f"🔗 **Grabbed Links:** ({len(links)})\n\n"
            for link in links[:20]:
                links_text += f"• {link[:50]}...\n"
                
            await message.reply_text(links_text, parse_mode="markdown")
        else:
            await message.reply_text("❌ **No links found!**")
