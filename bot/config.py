import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram API
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "ZxZoneMLB_Bot")
    
    # Owner & Admins
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split() if x]
    SUDO_USERS.append(OWNER_ID)
    
    # Channels & Links
    UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "https://t.me/ZonexusHub")
    REPO_LINK = os.getenv("REPO_LINK", "https://github.com/obscure-n8/ZxZone-MLB")
    SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/ZonexusSupport")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DOWNLOAD_DIR = str(BASE_DIR / "downloads")
    ENCODE_DIR = str(BASE_DIR / "encode")
    THUMB_DIR = str(BASE_DIR / "thumbnails")
    CONFIG_DIR = str(BASE_DIR / "config")
    
    # Limits
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    MAX_TASKS_PER_USER = int(os.getenv("MAX_TASKS_PER_USER", "3"))
    MAX_TOTAL_TASKS = int(os.getenv("MAX_TOTAL_TASKS", "50"))
    QUEUE_LIMIT = int(os.getenv("QUEUE_LIMIT", "20"))
    
    # Bot Settings
    DEFAULT_UPLOAD_MODE = os.getenv("DEFAULT_UPLOAD_MODE", "document")
    ALLOW_PRIVATE_FILES = os.getenv("ALLOW_PRIVATE_FILES", "True").lower() == "true"
    FORCE_SUBSCRIBE = os.getenv("FORCE_SUBSCRIBE", "True").lower() == "true"
    
    # Aria2
    ARIA2_HOST = os.getenv("ARIA2_HOST", "http://localhost")
    ARIA2_PORT = int(os.getenv("ARIA2_PORT", "6800"))
    ARIA2_SECRET = os.getenv("ARIA2_SECRET", "")
    
    # Rclone
    RCLONE_CONFIG = os.getenv("RCLONE_CONFIG_PATH", str(BASE_DIR / "config" / "rclone.conf"))
    RCLONE_REMOTE = os.getenv("RCLONE_REMOTE", "gdrive")
    
    # YT-DLP
    YTDLP_OPTIONS = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        'merge_output_format': 'mkv',
        'writethumbnail': True,
        'cookiefile': str(BASE_DIR / "config" / "cookies.txt"),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    # Bot Messages
    START_MESSAGE = """
**Zonexus M/L Bot** 🔥

**Powered By Zonexus Hub** ❞

👋 Welcome {user}!

I'm **{bot}** - Powerful Mirror/Leech Bot

**Features:**
• Direct Link Download
• Torrent/Magnet Support
• YouTube/YT-DLP
• Google Drive/Mega
• Rclone Support
• File Operations

**Commands:**
/leech - Leech to Telegram
/mirror - Mirror to Cloud
/ytdl - YouTube Download
/settings - Bot Settings
/status - Check Status
"""
    
    PROGRESS_TEMPLATE = """
**Zonexus M/L Bot 1**
┌ **{bot_name}**
└ `/leech1 {task_id}`

▍ **Powered By Zonexus Hub** ❞

{file_count}. `{file_name}`
┌ **Task By {user}**
│ {progress_bar} {percentage:.1f}%
│ **Status** : {status}
│ **Total** : {total} | **Done** : {done}
│ **Speed** : {speed}/s | **ETA** : {eta}
│ **Engine** : Aria2 v1.37.0 | **Mode** : `#{mode}`
> **Stop** : `/c_{task_id}`

⬢ **BOT STATS**
┌ **CPU** : {cpu}% | **RAM** : {ram}%
└ **FREE** : {free_disk}
"""
    
    @classmethod
    def ensure_dirs(cls):
        """Create necessary directories"""
        dirs = [
            cls.DOWNLOAD_DIR,
            cls.ENCODE_DIR,
            cls.THUMB_DIR,
            cls.CONFIG_DIR,
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
