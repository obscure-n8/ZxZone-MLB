from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.modules.jdownloader import jdownloader
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.helpers.utils import Utils

@Client.on_message(filters.command("jdmirror") & filters.private)
async def jdmirror_command(client: Client, message: Message):
    """JD Mirror - Download via JDownloader and upload to cloud"""
    user = message.from_user
    
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if Config.DISABLE_JD:
        await message.reply_text("❌ **JD Downloader is disabled!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /jdmirror <url>\n\n"
            "Download via JDownloader and mirror to cloud",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text(
        f"📥 **JD Mirror Started**\n\n"
        f"🔖 Task ID: `{task_id}`\n"
        f"🔗 URL: {url[:50]}...\n"
        f"⏳ Connecting to JDownloader..."
    )
    
    await tasks_db.add_task(task_id, user.id, 'jdmirror', url)
    
    # Add to JDownloader
    result = await jdownloader.add_links([url])
    
    if result['success']:
        await status_msg.edit_text(
            f"✅ **Link added to JDownloader!**\n\n"
            f"🔖 Task ID: `{task_id}`\n"
            f"⏳ JDownloader will process..."
        )
    else:
        await status_msg.edit_text(f"❌ **Failed:** {result.get('error', 'Unknown')}")

@Client.on_message(filters.command("jdleech") & filters.private)
async def jdleech_command(client: Client, message: Message):
    """JD Leech - Download via JDownloader and upload to Telegram"""
    user = message.from_user
    
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if Config.DISABLE_JD:
        await message.reply_text("❌ **JD Downloader is disabled!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /jdleech <url>",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    task_id = Utils.generate_task_id()
    
    status_msg = await message.reply_text(
        f"📥 **JD Leech Started**\n\n"
        f"🔖 Task ID: `{task_id}`\n"
        f"⏳ Connecting..."
    )
    
    await tasks_db.add_task(task_id, user.id, 'jdleech', url)
    
    result = await jdownloader.add_links([url])
    
    if result['success']:
        await status_msg.edit_text("✅ **Link added! JD will download...**")
    else:
        await status_msg.edit_text(f"❌ **Failed:** {result.get('error', '')}")
