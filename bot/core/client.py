from pyrogram import Client
from bot.core.config import Config

bot = Client(
    "mirror_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/modules")
)

# বট চালু করার জন্য এই লাইনটি একদম নিচে যোগ করুন
if __name__ == "__main__":
    bot.run()
