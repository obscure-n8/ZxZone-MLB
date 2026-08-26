import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.file_detective import file_detective
from bot.modules.scheduler import smart_scheduler
from bot.modules.analytics import analytics
from bot.modules.ai_caption import ai_caption
from bot.helpers.progress import Progress

progress_helper = Progress()

@Client.on_message(filters.command("analyze") & filters.private)
async def analyze_command(client: Client, message: Message):
    """Analyze file (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("📝 **Usage:** Reply to a file with /analyze")
        return
    
    status_msg = await message.reply_text("🔍 **Analyzing file...**")
    
    try:
        # Download file
        file_path = await message.reply_to_message.download()
        
        # Analyze file
        file_info = await file_detective.detect_file_type(file_path)
        health = await file_detective.check_file_health(file_path)
        
        # Generate caption
        caption = await ai_caption.generate_caption(
            os.path.basename(file_path),
            os.path.getsize(file_path),
            file_info.get('file_type', 'document')
        )
        
        analysis_text = f"""
🔍 **File Analysis Report**

📁 **File Info:**
• Name: {os.path.basename(file_path)}
• Size: {progress_helper.format_size(file_info.get('size', 0))}
• Type: {file_info.get('file_type', 'unknown').upper()}
• MIME: {file_info.get('mime_type', 'unknown')}
• Description: {file_info.get('description', 'N/A')}

🔐 **Hashes:**
• MD5: `{file_info.get('md5', 'N/A')}`
• SHA256: `{file_info.get('sha256', 'N/A')}`

💊 **Health Check:**
• Score: {health.get('health_score', 0)}/100
• Status: {'✅ Healthy' if health.get('is_healthy') else '❌ Issues Found'}

🤖 **AI Caption Generated:**
{caption}
"""
        
        await status_msg.edit_text(analysis_text, parse_mode="markdown")
        
        # Clean up
        os.remove(file_path)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.command("schedule") & filters.private)
async def schedule_command(client: Client, message: Message):
    """Schedule task (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/schedule backup <minutes>\n"
            "/schedule cleanup <days>\n"
            "/schedule list\n"
            "/schedule cancel <id>",
            parse_mode="markdown"
        )
        return
    
    action = message.command[1].lower()
    
    if action == "backup":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /schedule backup <minutes>")
            return
            
        minutes = int(message.command[2])
        schedule_id = await smart_scheduler.schedule_task(
            'backup',
            {},
            interval=minutes * 60,
            repeat=True
        )
        
        await message.reply_text(
            f"✅ **Backup scheduled!**\n\n"
            f"🆔 Schedule ID: {schedule_id}\n"
            f"⏰ Every: {minutes} minutes",
            parse_mode="markdown"
        )
        
    elif action == "cleanup":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /schedule cleanup <days>")
            return
            
        days = int(message.command[2])
        schedule_id = await smart_scheduler.schedule_task(
            'cleanup',
            {'days': days},
            interval=86400,
            repeat=True
        )
        
        await message.reply_text(
            f"✅ **Cleanup scheduled!**\n\n"
            f"🆔 Schedule ID: {schedule_id}\n"
            f"⏰ Every: 24 hours",
            parse_mode="markdown"
        )
        
    elif action == "list":
        schedules = await smart_scheduler.get_schedules()
        if not schedules:
            await message.reply_text("📊 **No schedules found!**")
            return
            
        schedule_text = "📅 **Active Schedules:**\n\n"
        for schedule in schedules:
            schedule_text += f"• {schedule['schedule_id']} - {schedule['task_type']}\n"
            
        await message.reply_text(schedule_text, parse_mode="markdown")
        
    elif action == "cancel":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /schedule cancel <id>")
            return
            
        schedule_id = message.command[2]
        if await smart_scheduler.cancel_schedule(schedule_id):
            await message.reply_text(f"✅ **Schedule cancelled!**")
        else:
            await message.reply_text(f"❌ **Schedule not found!**")

@Client.on_message(filters.command("report") & filters.private)
async def report_command(client: Client, message: Message):
    """Generate analytics report (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    status_msg = await message.reply_text("📊 **Generating report...**")
    
    # Generate report
    report = await analytics.generate_report()
    
    await status_msg.edit_text(report, parse_mode="markdown")

@Client.on_message(filters.command("health") & filters.private)
async def health_command(client: Client, message: Message):
    """Check bot health"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    # Get metrics
    metrics = await analytics.get_performance_metrics()
    
    health_text = f"""
💊 **Bot Health Check**

⚡ **Performance:**
• CPU: {metrics['cpu_usage']}%
• Memory: {metrics['memory_usage']}%
• Uptime: {progress_helper.format_eta(metrics['uptime'])}

📊 **Queue:**
• Active: {metrics['queue']['active']}
• Waiting: {metrics['queue']['waiting']}
• Max: {metrics['queue']['max']}

🔌 **Connections:** {metrics['active_connections']}

✅ **Status:** All systems operational!
"""
    
    await message.reply_text(health_text, parse_mode="markdown")
