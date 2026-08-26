import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # ============ REQUIRED CONFIG ============
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    # ============ BOT INFO ============
    BOT_USERNAME = os.getenv("BOT_USERNAME", "ZxZoneMLB_Bot")
    AUTHOR_NAME = os.getenv("AUTHOR_NAME", "ZxZone Hub")
    AUTHOR_URL = os.getenv("AUTHOR_URL", "https://t.me/zxzoneupdates")
    
    # ============ CHANNELS & LINKS ============
    UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "https://t.me/zxzoneupdates")
    REPO_LINK = os.getenv("REPO_LINK", "https://github.com/obscure-n8/ZxZone-MLB")
    
    # ============ OPTIONAL CONFIG ============
    DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")
    CMD_SUFFIX = os.getenv("CMD_SUFFIX", "")
    AUTHORIZED_CHATS = os.getenv("AUTHORIZED_CHATS", "")
    SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split() if x]
    SUDO_USERS.append(OWNER_ID)
    
    # ============ TASK LIMITS ============
    STATUS_LIMIT = int(os.getenv("STATUS_LIMIT", "10"))
    STATUS_UPDATE_INTERVAL = int(os.getenv("STATUS_UPDATE_INTERVAL", "15"))
    BOT_MAX_TASKS = int(os.getenv("BOT_MAX_TASKS", "0"))
    USER_MAX_TASKS = int(os.getenv("USER_MAX_TASKS", "0"))
    USER_TIME_INTERVAL = int(os.getenv("USER_TIME_INTERVAL", "0"))
    
    # Task Type Limits
    DIRECT_LIMIT = int(os.getenv("DIRECT_LIMIT", "0"))
    MEGA_LIMIT = int(os.getenv("MEGA_LIMIT", "0"))
    TORRENT_LIMIT = int(os.getenv("TORRENT_LIMIT", "0"))
    GD_DL_LIMIT = int(os.getenv("GD_DL_LIMIT", "0"))
    RC_DL_LIMIT = int(os.getenv("RC_DL_LIMIT", "0"))
    CLONE_LIMIT = int(os.getenv("CLONE_LIMIT", "0"))
    JD_LIMIT = int(os.getenv("JD_LIMIT", "0"))
    NZB_LIMIT = int(os.getenv("NZB_LIMIT", "0"))
    YTDLP_LIMIT = int(os.getenv("YTDLP_LIMIT", "0"))
    PLAYLIST_LIMIT = int(os.getenv("PLAYLIST_LIMIT", "0"))
    LEECH_LIMIT = int(os.getenv("LEECH_LIMIT", "0"))
    EXTRACT_LIMIT = int(os.getenv("EXTRACT_LIMIT", "0"))
    ARCHIVE_LIMIT = int(os.getenv("ARCHIVE_LIMIT", "0"))
    STORAGE_LIMIT = int(os.getenv("STORAGE_LIMIT", "0"))
    
    # ============ UPLOAD SETTINGS ============
    DEFAULT_UPLOAD = os.getenv("DEFAULT_UPLOAD", "rc")
    AS_DOCUMENT = os.getenv("AS_DOCUMENT", "False").lower() == "true"
    EQUAL_SPLITS = os.getenv("EQUAL_SPLITS", "False").lower() == "true"
    MEDIA_GROUP = os.getenv("MEDIA_GROUP", "False").lower() == "true"
    LEECH_SPLIT_SIZE = int(os.getenv("LEECH_SPLIT_SIZE", "0"))
    LEECH_PREFIX = os.getenv("LEECH_PREFIX", "")
    LEECH_SUFFIX = os.getenv("LEECH_SUFFIX", "")
    LEECH_FONT = os.getenv("LEECH_FONT", "")
    LEECH_CAPTION = os.getenv("LEECH_CAPTION", "")
    THUMBNAIL_LAYOUT = os.getenv("THUMBNAIL_LAYOUT", "")
    
    # ============ DISABLE OPTIONS ============
    DISABLE_TORRENTS = os.getenv("DISABLE_TORRENTS", "False").lower() == "true"
    DISABLE_LEECH = os.getenv("DISABLE_LEECH", "False").lower() == "true"
    DISABLE_MIRROR = os.getenv("DISABLE_MIRROR", "False").lower() == "true"
    DISABLE_BULK = os.getenv("DISABLE_BULK", "False").lower() == "true"
    DISABLE_MULTI = os.getenv("DISABLE_MULTI", "False").lower() == "true"
    DISABLE_SEED = os.getenv("DISABLE_SEED", "False").lower() == "true"
    DISABLE_FF_MODE = os.getenv("DISABLE_FF_MODE", "False").lower() == "true"
    DISABLE_JD = os.getenv("DISABLE_JD", "False").lower() == "true"
    DISABLE_NZB = os.getenv("DISABLE_NZB", "False").lower() == "true"
    DISABLE_RSS = os.getenv("DISABLE_RSS", "False").lower() == "true"
    DISABLE_SEARCH = os.getenv("DISABLE_SEARCH", "False").lower() == "true"
    DISABLE_STREAM = os.getenv("DISABLE_STREAM", "False").lower() == "true"
    DISABLE_YTDLP = os.getenv("DISABLE_YTDLP", "False").lower() == "true"
    DISABLE_MEGA = os.getenv("DISABLE_MEGA", "False").lower() == "true"
    
    # ============ API KEYS ============
    FILELION_API = os.getenv("FILELION_API", "")
    STREAMWISH_API = os.getenv("STREAMWISH_API", "")
    ALLDEBRID_API_KEY = os.getenv("ALLDEBRID_API_KEY", "")
    INSTADL_API = os.getenv("INSTADL_API", "")
    HYDRA_IP = os.getenv("HYDRA_IP", "")
    HYDRA_API_KEY = os.getenv("HYDRA_API_KEY", "")
    
    # ============ MEGA ============
    MEGA_EMAIL = os.getenv("MEGA_EMAIL", "")
    MEGA_PASSWORD = os.getenv("MEGA_PASSWORD", "")
    
    # ============ PATHS ============
    BASE_DIR = Path(__file__).parent.parent
    DOWNLOAD_DIR = str(BASE_DIR / "downloads")
    ENCODE_DIR = str(BASE_DIR / "encode")
    THUMB_DIR = str(BASE_DIR / "thumbnails")
    CONFIG_DIR = str(BASE_DIR / "config")
    SESSION_DIR = str(BASE_DIR / "sessions")
    
    # ============ GD TOOLS ============
    GDRIVE_ID = os.getenv("GDRIVE_ID", "")
    GD_DESP = os.getenv("GD_DESP", "Uploaded with ZxZone Bot")
    IS_TEAM_DRIVE = os.getenv("IS_TEAM_DRIVE", "False").lower() == "true"
    STOP_DUPLICATE = os.getenv("STOP_DUPLICATE", "False").lower() == "true"
    INDEX_URL = os.getenv("INDEX_URL", "")
    USE_SERVICE_ACCOUNTS = os.getenv("USE_SERVICE_ACCOUNTS", "False").lower() == "true"
    
    # ============ RCLONE ============
    RCLONE_PATH = os.getenv("RCLONE_PATH", "")
    RCLONE_FLAGS = os.getenv("RCLONE_FLAGS", "")
    RCLONE_SERVE_URL = os.getenv("RCLONE_SERVE_URL", "")
    SHOW_CLOUD_LINK = os.getenv("SHOW_CLOUD_LINK", "True").lower() == "true"
    RCLONE_SERVE_PORT = int(os.getenv("RCLONE_SERVE_PORT", "0"))
    RCLONE_SERVE_USER = os.getenv("RCLONE_SERVE_USER", "")
    RCLONE_SERVE_PASS = os.getenv("RCLONE_SERVE_PASS", "")
    
    # ============ QUEUE SYSTEM ============
    QUEUE_ALL = int(os.getenv("QUEUE_ALL", "0"))
    QUEUE_DOWNLOAD = int(os.getenv("QUEUE_DOWNLOAD", "0"))
    QUEUE_UPLOAD = int(os.getenv("QUEUE_UPLOAD", "0"))
    
    # ============ TORRENT ============
    TORRENT_TIMEOUT = int(os.getenv("TORRENT_TIMEOUT", "0"))
    BASE_URL = os.getenv("BASE_URL", "")
    WEB_PINCODE = os.getenv("WEB_PINCODE", "True").lower() == "true"
    
    # ============ RSS ============
    RSS_DELAY = int(os.getenv("RSS_DELAY", "600"))
    RSS_CHAT = os.getenv("RSS_CHAT", "")
    RSS_SIZE_LIMIT = int(os.getenv("RSS_SIZE_LIMIT", "0"))
    
    # ============ SEARCH ============
    SEARCH_API_LINK = os.getenv("SEARCH_API_LINK", "")
    SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", "0"))
    USE_IMAGES = os.getenv("USE_IMAGES", "False").lower() == "true"
    IMG_SEARCH = os.getenv("IMG_SEARCH", "")
    IMG_PAGE = int(os.getenv("IMG_PAGE", "1"))
    
    # ============ YT TOOLS ============
    YT_DESP = os.getenv("YT_DESP", "Uploaded to YouTube by ZxZone bot")
    YT_CATEGORY_ID = int(os.getenv("YT_CATEGORY_ID", "22"))
    YT_PRIVACY_STATUS = os.getenv("YT_PRIVACY_STATUS", "unlisted")
    
    # ============ BOT SETTINGS ============
    BOT_PM = os.getenv("BOT_PM", "False").lower() == "true"
    SET_COMMANDS = os.getenv("SET_COMMANDS", "True").lower() == "true"
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Dhaka")
    FORCE_SUB_IDS = os.getenv("FORCE_SUB_IDS", "")
    MEDIA_STORE = os.getenv("MEDIA_STORE", "True").lower() == "true"
    DELETE_LINKS = os.getenv("DELETE_LINKS", "False").lower() == "true"
    VERIFY_TIMEOUT = int(os.getenv("VERIFY_TIMEOUT", "0"))
    LOGIN_PASS = os.getenv("LOGIN_PASS", "")
    
    # ============ LOG CHANNELS ============
    LEECH_DUMP_CHAT = os.getenv("LEECH_DUMP_CHAT", "")
    LINKS_LOG_ID = os.getenv("LINKS_LOG_ID", "")
    MIRROR_LOG_ID = os.getenv("MIRROR_LOG_ID", "")
    
    # ============ UPDATES ============
    UPSTREAM_REPO = os.getenv("UPSTREAM_REPO", "")
    UPSTREAM_BRANCH = os.getenv("UPSTREAM_BRANCH", "main")
    
    # ============ JDOWNLOADER ============
    JD_EMAIL = os.getenv("JD_EMAIL", "")
    JD_PASS = os.getenv("JD_PASS", "")
    
    # ============ TELEMETRY ============
    ENABLE_TELEMETRY = os.getenv("ENABLE_TELEMETRY", "True").lower() == "true"
    
    # ============ PROXY ============
    TG_PROXY = os.getenv("TG_PROXY", "")
    
    # ============ USER SESSION ============
    USER_SESSION_STRING = os.getenv("USER_SESSION_STRING", "")
    
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
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is missing!")
        if not cls.API_ID or cls.API_ID == 0:
            errors.append("API_ID is missing!")
        if not cls.API_HASH:
            errors.append("API_HASH is missing!")
        if not cls.OWNER_ID or cls.OWNER_ID == 0:
            errors.append("OWNER_ID is missing!")
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is missing!")
        if errors:
            raise ValueError("\n".join(errors))
        return True
