import os
from pyrogram import Client
from typing import Optional
from bot.config import Config

class NotificationSystem:
    """User notification system"""
    
    def __init__(self):
        self.processing_messages = {}
        
    async def send_processing_message(self, client: Client, user_id: int, task_type: str, file_count: int = 1):
        """Send processing message to user DM"""
        try:
            message_text = f"""
🔄 **Your Files Processing Going On!**

📥 **Task Type:** {task_type}
📊 **Files:** {file_count}
⏳ **Status:** Processing...

**Powered By Zonexus Hub** ❞
"""
            
            msg = await client.send_message(user_id, message_text, parse_mode="markdown")
            self.processing_messages[user_id] = msg.id
            
            return msg.id
            
        except:
            return None
            
    async def send_completion_message(
        self,
        client: Client,
        user_id: int,
        username: str,
        files_sent: int,
        files_failed: int,
        task_type: str
    ):
        """Send completion message to user"""
        try:
            mention = f"@{username}" if username else f"User {user_id}"
            
            message_text = f"""
✅ **Files Sent in Your DM!**

👤 **User:** {mention}

📊 **Results:**
• ✅ Sent: {files_sent} files
• ❌ Failed: {files_failed} files
• 📥 Task Type: {task_type}

**Powered By Zonexus Hub** ❞
"""
            
            await client.send_message(user_id, message_text, parse_mode="markdown")
            
            # Also send to dump channel if configured
            if Config.LEECH_DUMP_CHAT:
                dump_text = f"""
📦 **Task Completed**

👤 **User:** {mention}
✅ Sent: {files_sent}
❌ Failed: {files_failed}
📥 Type: {task_type}
"""
                await client.send_message(int(Config.LEECH_DUMP_CHAT), dump_text)
                
        except:
            pass
            
    async def send_error_message(self, client: Client, user_id: int, error: str):
        """Send error message to user"""
        try:
            message_text = f"""
❌ **Error Occurred!**

⚠️ **Error:** {error}

Please try again or contact support.

**Powered By Zonexus Hub** ❞
"""
            
            await client.send_message(user_id, message_text, parse_mode="markdown")
            
        except:
            pass
            
    async def update_processing_message(self, client: Client, user_id: int, progress_text: str):
        """Update processing message"""
        try:
            if user_id in self.processing_messages:
                msg_id = self.processing_messages[user_id]
                await client.edit_message_text(user_id, msg_id, progress_text)
        except:
            pass
            
    async def clear_processing_message(self, client: Client, user_id: int):
        """Clear processing message"""
        try:
            if user_id in self.processing_messages:
                msg_id = self.processing_messages[user_id]
                await client.delete_messages(user_id, msg_id)
                del self.processing_messages[user_id]
        except:
            pass

# Create instance
notification_system = NotificationSystem()
