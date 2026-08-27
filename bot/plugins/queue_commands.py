import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.modules.queue import task_queue
from bot.database.users import users_db
from bot.database.tasks import tasks_db

@Client.on_message(filters.command("qbleech") & filters.private)
async def qbleech_command(client: Client, message: Message):
    """Queue batch leech - multiple links"""
    user = message.from_user
    
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /qbleech <url1> <url2> <url3> ...\n\n"
            "Example:\n"
            "/qbleech https://link1.com https://link2.com https://link3.com",
            parse_mode="markdown"
        )
        return
    
    urls = message.command[1:]
    
    if len(urls) > 10:
        await message.reply_text("❌ **Max 10 links at once!**")
        return
    
    status_msg = await message.reply_text(
        f"📥 **Queue Batch Leech Started!**\n\n"
        f"📊 Total Links: {len(urls)}\n"
        f"⏳ Adding to queue..."
    )
    
    task_ids = []
    
    for i, url in enumerate(urls, 1):
        task_id = Utils.generate_task_id()
        task_ids.append(task_id)
        
        await tasks_db.add_task(task_id, user.id, 'leech', url)
        
        await status_msg.edit_text(
            f"📥 **Adding to queue...**\n\n"
            f"✅ Added: {i}/{len(urls)}\n"
            f"🔗 Current: {url[:50]}..."
        )
    
    await status_msg.edit_text(
        f"✅ **All links added to queue!**\n\n"
        f"📊 Total: {len(urls)} tasks\n"
        f"🔖 Task IDs: {', '.join(task_ids[:5])}...\n\n"
        f"⏳ Bot will process them one by one!"
    )

@Client.on_message(filters.command("qbmirror") & filters.private)
async def qbmirror_command(client: Client, message: Message):
    """Queue batch mirror - multiple links"""
    user = message.from_user
    
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /qbmirror <url1> <url2> <url3> ...",
            parse_mode="markdown"
        )
        return
    
    urls = message.command[1:]
    
    status_msg = await message.reply_text(
        f"📥 **Queue Batch Mirror Started!**\n\n"
        f"📊 Total Links: {len(urls)}"
    )
    
    for i, url in enumerate(urls, 1):
        task_id = Utils.generate_task_id()
        await tasks_db.add_task(task_id, user.id, 'mirror', url)
        
        await status_msg.edit_text(
            f"📥 **Adding to mirror queue...**\n\n"
            f"✅ Added: {i}/{len(urls)}"
        )
    
    await status_msg.edit_text(
        f"✅ **All links added to mirror queue!**\n\n"
        f"📊 Total: {len(urls)} tasks"
    )

@Client.on_message(filters.command("cancelalltask") & filters.private)
async def cancel_all_tasks_command(client: Client, message: Message):
    """Cancel all active tasks - admin only"""
    user = message.from_user
    
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **Admin only!**")
        return
    
    status_msg = await message.reply_text("🔄 **Cancelling all tasks...**")
    
    # Cancel all active tasks
    active_tasks = list(task_queue.active_tasks.keys())
    
    for task_id in active_tasks:
        await task_queue.cancel_task(task_id)
        await tasks_db.update_task_status(task_id, 'cancelled')
    
    await status_msg.edit_text(
        f"✅ **All tasks cancelled!**\n\n"
        f"📊 Cancelled: {len(active_tasks)} tasks"
    )
