import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.database.db import db

class AdminLogger:
    def __init__(self):
        self.collection = db.admin_logs
        
    async def log_action(
        self,
        admin_id: int,
        action: str,
        target_id: int = None,
        details: str = ""
    ):
        """Log admin action"""
        log_data = {
            'admin_id': admin_id,
            'action': action,
            'target_id': target_id,
            'details': details,
            'timestamp': datetime.now()
        }
        
        await self.collection.insert_one(log_data)
        
    async def get_logs(self, limit: int = 50) -> list:
        """Get recent admin logs"""
        logs = []
        cursor = self.collection.find().sort('timestamp', -1).limit(limit)
        async for log in cursor:
            logs.append(log)
        return logs
        
    async def get_user_logs(self, admin_id: int, limit: int = 20) -> list:
        """Get logs for specific admin"""
        logs = []
        cursor = self.collection.find({'admin_id': admin_id}).sort('timestamp', -1).limit(limit)
        async for log in cursor:
            logs.append(log)
        return logs
        
    async def clear_logs(self):
        """Clear all logs"""
        await self.collection.delete_many({})

# Create instance
admin_logger = AdminLogger()

@Client.on_message(filters.command("adminlog") & filters.private)
async def admin_log_command(client: Client, message: Message):
    """View admin logs (sudo/owner only)"""
    user = message.from_user
    
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    logs = await admin_logger.get_logs(20)
    
    if not logs:
        await message.reply_text("📊 **No admin logs found!**")
        return
    
    log_text = "📋 **Recent Admin Actions:**\n\n"
    
    for log in logs:
        log_text += f"👤 Admin: {log['admin_id']}\n"
        log_text += f"🔧 Action: {log['action']}\n"
        if log.get('target_id'):
            log_text += f"🎯 Target: {log['target_id']}\n"
        if log.get('details'):
            log_text += f"📝 Details: {log['details']}\n"
        log_text += f"⏰ Time: {log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    await message.reply_text(log_text, parse_mode="markdown")

@Client.on_message(filters.command("clearlogs") & filters.private)
async def clear_logs_command(client: Client, message: Message):
    """Clear admin logs (owner only)"""
    user = message.from_user
    
    from bot.helpers.permissions import permission_system
    if not await permission_system.is_owner(user.id):
        await message.reply_text("❌ **Only owner can clear logs!**")
        return
    
    await admin_logger.clear_logs()
    await message.reply_text("✅ **Admin logs cleared!**")
