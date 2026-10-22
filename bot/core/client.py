from pyrogram import Client
from bot.core.config import Config

bot = Client(
    "mirror_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/modules") # modules ফোল্ডার থেকে কমান্ড অটো লোড হবে
)
