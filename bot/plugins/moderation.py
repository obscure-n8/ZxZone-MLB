from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.nsfw_detector import nsfw_detector
from bot.modules.content_filter import content_filter
from bot.modules.file_scanner import file_scanner

@Client.on_message(filters.command("nsfw") & filters.private)
async def nsfw_command(client: Client, message: Message):
    """Check NSFW content (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/nsfw text <content> - Check text\n"
            "/nsfw stats - Get statistics",
            parse_mode="markdown"
        )
        return
    
    action = message.command[1].lower()
    
    if action == "text":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /nsfw text <content>")
            return
            
        content = " ".join(message.command[2:])
        result = await nsfw_detector.detect_text(content)
        
        if result['is_nsfw']:
            await message.reply_text(
                f"🚫 **NSFW Content Detected!**\n\n"
                f"📊 Categories: {', '.join(result['categories'])}\n"
                f"🔍 Keywords: {', '.join(result['keywords'])}\n"
                f"⚡ Confidence: {result['confidence']}%",
                parse_mode="markdown"
            )
        else:
            await message.reply_text("✅ **Content is safe!**")
            
    elif action == "stats":
        stats = await nsfw_detector.get_nsfw_stats()
        
        stats_text = f"""
📊 **NSFW Detection Statistics**

🔢 Total Detections: {stats['total_detections']}

📋 Categories:
"""
        for category, count in stats['categories'].items():
            stats_text += f"• {category}: {count}\n"
            
        await message.reply_text(stats_text, parse_mode="markdown")

@Client.on_message(filters.command("filter") & filters.private)
async def filter_command(client: Client, message: Message):
    """Content filter commands (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/filter check <text> - Check content\n"
            "/filter add <pattern> - Add filter\n"
            "/filter remove <pattern> - Remove filter\n"
            "/filter list - List filters",
            parse_mode="markdown"
        )
        return
    
    action = message.command[1].lower()
    
    if action == "check":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /filter check <text>")
            return
            
        content = " ".join(message.command[2:])
        result = await content_filter.filter_message(content)
        
        if result['is_filtered']:
            await message.reply_text(
                f"⚠️ **Filtered Content Detected!**\n\n"
                f"📊 Reasons: {', '.join(result['reasons'])}\n"
                f"🔍 Spam: {'Yes' if result['spam']['is_spam'] else 'No'}\n"
                f"🔍 Abuse: {'Yes' if result['abuse']['is_abusive'] else 'No'}",
                parse_mode="markdown"
            )
        else:
            await message.reply_text("✅ **Content is clean!**")
            
    elif action == "add":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /filter add <pattern>")
            return
            
        pattern = message.command[2]
        await content_filter.add_custom_filter(pattern)
        await message.reply_text(f"✅ **Filter added:** {pattern}")
        
    elif action == "remove":
        if len(message.command) < 3:
            await message.reply_text("📝 **Usage:** /filter remove <pattern>")
            return
            
        pattern = message.command[2]
        if await content_filter.remove_filter(pattern):
            await message.reply_text(f"✅ **Filter removed:** {pattern}")
        else:
            await message.reply_text(f"❌ **Filter not found!**")
            
    elif action == "list":
        filters = await content_filter.get_filters()
        if not filters:
            await message.reply_text("📊 **No custom filters!**")
            return
            
        filter_text = "📋 **Custom Filters:**\n\n"
        for filter_data in filters:
            filter_text += f"• {filter_data['pattern']} ({filter_data['type']})\n"
            
        await message.reply_text(filter_text, parse_mode="markdown")

@Client.on_message(filters.command("scan") & filters.private)
async def scan_command(client: Client, message: Message):
    """Scan file for security (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("📝 **Usage:** Reply to a file with /scan")
        return
    
    status_msg = await message.reply_text("🔍 **Scanning file...**")
    
    try:
        # Download file
        file_path = await message.reply_to_message.download()
        
        # Scan file
        scan_result = await file_scanner.scan_file(file_path)
        
        # Check NSFW
        nsfw_result = await nsfw_detector.detect_filename(os.path.basename(file_path))
        
        scan_text = f"""
🔍 **File Scan Results**

📁 **File:** {scan_result.get('file_name', 'Unknown')}
💾 **Size:** {scan_result.get('file_size', 0)} bytes
🔐 **MD5:** {scan_result.get('md5', 'N/A')}

⚠️ **Risk Score:** {scan_result.get('risk_score', 0)}/100

"""
        if scan_result.get('risks'):
            scan_text += "🚫 **Risks Detected:**\n"
            for risk in scan_result['risks']:
                scan_text += f"• {risk}\n"
        else:
            scan_text += "✅ **No risks detected!**\n"
            
        if nsfw_result['is_nsfw']:
            scan_text += f"\n🚫 **NSFW Content:** Detected"
        else:
            scan_text += f"\n✅ **NSFW Content:** Safe"
            
        scan_text += f"\n\n**Verdict:** {'❌ Unsafe' if not scan_result.get('is_safe') else '✅ Safe'}"
        
        await status_msg.edit_text(scan_text, parse_mode="markdown")
        
        # Clean up
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.command("moderation_stats") & filters.private)
async def moderation_stats(client: Client, message: Message):
    """Get moderation statistics (admin only)"""
    user = message.from_user
    
    if user.id not in Config.SUDO_USERS:
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    nsfw_stats = await nsfw_detector.get_nsfw_stats()
    scan_stats = await file_scanner.get_scan_stats()
    
    stats_text = f"""
📊 **Moderation Statistics**

🚫 **NSFW Detection:**
• Total: {nsfw_stats['total_detections']}

🔍 **File Scanning:**
• Total Scans: {scan_stats['total_scans']}
• Safe Files: {scan_stats['safe_files']}
• Unsafe Files: {scan_stats['unsafe_files']}

✅ **System:** Active
"""
    
    await message.reply_text(stats_text, parse_mode="markdown")
