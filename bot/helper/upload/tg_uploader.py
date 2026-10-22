import os
import time
from bot.core.config import Config

async def upload_to_tg(client, file_path, chat_id, progress_callback=None):
    """ডাউনলোড এবং প্রসেস হওয়া ফাইল সরাসরি টেলিগ্রামে আপলোড করবে"""
    if not os.path.exists(file_path):
        return False
        
    file_name = os.path.basename(file_path)
    # ফাইল সাইজ যদি টেলিগ্রাম লিমিটের চেয়ে বড় হয় তাহলে এরর বা স্প্লিট ট্রিগার হবে
    if os.path.getsize(file_path) > Config.MAX_FILE_SIZE:
        raise ValueError("File size exceeds limit. Needs splitting.")

    await client.send_document(
        chat_id=chat_id,
        document=file_path,
        caption=f"`{file_name}` uploaded successfully!",
        progress=progress_callback
    )
    return True
