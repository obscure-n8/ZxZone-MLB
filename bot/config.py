import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def safe_get_env(key: str, default: str = "") -> str:
    """Safely get environment variable"""
    value = os.getenv(key, default)
    if value is None:
        return default
    return value.strip()

def safe_get_int(key: str, default: int = 0) -> int:
    """Safely get integer environment variable"""
    try:
        value = safe_get_env(key, str(default))
        return int(value)
    except (ValueError, TypeError):
        return default

class Config:
    # ============ REQUIRED CONFIG ============
    # Support multiple naming conventions
    BOT_TOKEN = safe_get_env("BOT_TOKEN", safe_get_env("TG_BOT_TOKEN", ""))
    API_ID = safe_get_int("API_ID", safe_get_int("TELEGRAM_API", 0))
    API_HASH = safe_get_env("API_HASH", safe_get_env("TELEGRAM_HASH", ""))
    OWNER_ID = safe_get_int("OWNER_ID", 0)
    DATABASE_URL = safe_get_env("DATABASE_URL", "")
    
    # ============ BOT INFO ============
    BOT_USERNAME = safe_get_env("BOT_USERNAME", "ZxZoneMLB_Bot")
    AUTHOR_NAME = safe_get_env("AUTHOR_NAME", "ZxZone Hub")
    AUTHOR_URL = safe_get_env("AUTHOR_URL", "https://t.me/zxzoneupdates")
    
    # ============ CHANNELS & LINKS ============
    UPDATE_CHANNEL = safe_get_env("UPDATE_CHANNEL", "https://t.me/zxzoneupdates")
    REPO_LINK = safe_get_env("REPO_LINK", "https://github.com/obscure-n8/ZxZone-MLB")
    
    # ============ PATHS ============
    BASE_DIR = Path(__file__).parent.parent
    DOWNLOAD_DIR = str(BASE_DIR / "downloads")
    ENCODE_DIR = str(BASE_DIR / "encode")
    THUMB_DIR = str(BASE_DIR / "thumbnails")
    CONFIG_DIR = str(BASE_DIR / "config")
    SESSION_DIR = str(BASE_DIR / "sessions")
    
    # ============ LIMITS ============
    BOT_MAX_TASKS = safe_get_int("BOT_MAX_TASKS", 50)
    USER_MAX_TASKS = safe_get_int("USER_MAX_TASKS", 3)
    QUEUE_LIMIT = safe_get_int("QUEUE_LIMIT", 20)
    
    # ============ ARIA2 ============
    ARIA2_HOST = safe_get_env("ARIA2_HOST", "http://localhost")
    ARIA2_PORT = safe_get_int("ARIA2_PORT", 6800)
    ARIA2_SECRET = safe_get_env("ARIA2_SECRET", "")
    
    # ============ RCLONE ============
    RCLONE_CONFIG = safe_get_env("RCLONE_CONFIG_PATH", str(BASE_DIR / "config" / "rclone.conf"))
    RCLONE_REMOTE = safe_get_env("RCLONE_REMOTE", "gdrive")
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN/TG_BOT_TOKEN is missing!")
        if not cls.API_ID or cls.API_ID == 0:
            errors.append("API_ID/TELEGRAM_API is missing!")
        if not cls.API_HASH:
            errors.append("API_HASH/TELEGRAM_HASH is missing!")
        if not cls.OWNER_ID or cls.OWNER_ID == 0:
            errors.append("OWNER_ID is missing!")
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is missing!")
            
        if errors:
            error_msg = "\n".join(errors)
            print(f"Configuration Error:\n{error_msg}")
            # Don't raise error, just warn
            # Bot will show error message instead of crashing
            return False
            
        return True
    
    @classmethod
    def ensure_dirs(cls):
        """Create necessary directories"""
        dirs = [
            cls.DOWNLOAD_DIR,
            cls.ENCODE_DIR,
            cls.THUMB_DIR,
            cls.CONFIG_DIR,
            cls.SESSION_DIR,
            os.path.join(cls.DOWNLOAD_DIR, "temp"),
            os.path.join(cls.DOWNLOAD_DIR, "queue"),
            os.path.join(cls.DOWNLOAD_DIR, "completed"),
            os.path.join(cls.THUMB_DIR, "users"),
            os.path.join(cls.THUMB_DIR, "watermarks"),
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
