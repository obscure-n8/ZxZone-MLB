from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec, gather
from os import environ
from pyrogram import Client

from bot import (
    bot_dict,
    bot_lock,
    aria2,
    aria2_options,
    config_dict,
    user_data,
    task_dict,
    images,
    Intervals,
    kwargs,
    LOGGER,
    GLOBAL_EXTENSION_FILTER,
    DEFAULT_SPLIT_SIZE,
    DRIVES_IDS,
    DRIVES_NAMES,
    INDEX_URLS,
    SHORTENER_APIS,
    SHORTENERES,
)
from bot.helper.ext_utils.bot_utils import setInterval, sync_to_async
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.stream_utils.web_services import start_server, server
from bot.helper.telegram_helper.message_utils import update_status_message
from bot.modules.rss import addJob
from bot.modules.torrent_search import initiate_search_tools


default_values = {
    "AUTO_DELETE_MESSAGE_DURATION": 30,
    "AUTO_DELETE_UPLOAD_MESSAGE_DURATION": 60,
    "INCOMPLETE_TASK_NOTIFIER": False,
    "INCOMPLETE_AUTO_RESUME": True,
    "STICKER_DELETE_DURATION": 0,
    "DOWNLOAD_DIR": "/usr/src/app/downloads/",
    "DISABLE_MIRROR_LEECH": "",
    "USER_SESSION_STRING": "",
    "LEECH_SPLIT_SIZE": DEFAULT_SPLIT_SIZE,
    "STATUS_UPDATE_INTERVAL": 10,
    "SEARCH_LIMIT": 0,
    "STATUS_LIMIT": 10,
    "RSS_DELAY": 900,
    "CLOUD_LINK_FILTERS": "",
    "UPSTREAM_BRANCH": "main",
    "FSUB_BUTTON_NAME": "Join Channel",
    "CHANNEL_USERNAME": "zonexusmlgroup4gb",
    "AUTHOR_NAME": "ZxZone",
    "AUTHOR_URL": "https://t.me/zonexusmlgroup4gb",
    "DRIVE_SEARCH_TITLE": "Drive Search",
    "GD_INFO": "By ZxZone",
    "RCLONE_TFSIMULATION": 4,
    "SESSION_TIMEOUT": 0,
    "PROG_FINISH": "⬢",
    "PROG_UNFINISH": "⬡",
    "SOURCE_LINK_TITLE": "Source Link",
    "TIME_ZONE": "Asia/Dhaka",
    "TIME_ZONE_TITLE": "UTC+6",
    "NONPREMIUM_LIMIT": 5,
    "DAILY_LIMIT_SIZE": 50,
    "TSEARCH_TITLE": "Torrent Search",
    "DISABLE_VIDTOOLS": "Nope",
    "COMPRESS_BANNER": "Re-Encoded by ZxZone",
    "LIB264_PRESET": "superfast",
    "LIB265_PRESET": "faster",
    "HARDSUB_FONT_NAME": "ZxZone",
    "HARDSUB_FONT_SIZE": "",
    "DISABLE_MULTI_VIDTOOLS": "compress rmstream extract trim watermark convert",
    "BOT_PM": True,
    "IMAGE_ARIA": "",
    "IMAGE_AUTH": "",
    "IMAGE_BOLD": "",
    "IMAGE_BYE": "",
    "IMAGE_CANCEL": "",
    "IMAGE_CAPTION": "",
    "IMAGE_COMMONS_CHECK": "",
    "IMAGE_COMPLETE": "",
    "IMAGE_CONEDIT": "",
    "IMAGE_CONPRIVATE": "",
    "IMAGE_CONSET": "",
    "IMAGE_CONVIEW": "",
    "IMAGE_DUMP": "",
    "IMAGE_EXTENSION": "",
    "IMAGE_GD": "",
    "IMAGE_HELP": "",
    "IMAGE_HTML": "",
    "IMAGE_IMDB": "",
    "IMAGE_INFO": "",
    "IMAGE_ITALIC": "",
    "IMAGE_JD": "",
    "IMAGE_LOGS": "",
    "IMAGE_MDL": "",
    "IMAGE_MEDINFO": "",
    "IMAGE_METADATA": "",
    "IMAGE_MONO": "",
    "IMAGE_NORMAL": "",
    "IMAGE_OWNER": "",
    "IMAGE_PAUSE": "",
    "IMAGE_PRENAME": "",
    "IMAGE_QBIT": "",
    "IMAGE_RCLONE": "",
    "IMAGE_REMNAME": "",
    "IMAGE_RSS": "",
    "IMAGE_SEARCH": "",
    "IMAGE_STATS": "",
    "IMAGE_STATUS": "",
    "IMAGE_SUFNAME": "",
    "IMAGE_TMDB": "",
    "IMAGE_TXT": "",
    "IMAGE_UNAUTH": "",
    "IMAGE_UNKNOW": "",
    "IMAGE_USER": "",
    "IMAGE_USETIINGS": "",
    "IMAGE_VIDTOOLS": "",
    "IMAGE_WEL": "",
    "IMAGE_WIBU": "",
    "IMAGE_YT": "",
    "IMAGE_ZIP": "",
}


async def load_config():
    # ============================ REQUIRED ================================
    BOT_TOKEN = environ.get("BOT_TOKEN", "") or config_dict["BOT_TOKEN"]

    TELEGRAM_API = environ.get("TELEGRAM_API", "")
    TELEGRAM_API = int(TELEGRAM_API) if TELEGRAM_API else config_dict["TELEGRAM_API"]

    TELEGRAM_HASH = environ.get("TELEGRAM_HASH", "") or config_dict["TELEGRAM_HASH"]

    OWNER_ID = environ.get("OWNER_ID", "")
    OWNER_ID = int(OWNER_ID) if OWNER_ID else config_dict["OWNER_ID"]

    DOWNLOAD_DIR = environ.get("DOWNLOAD_DIR", "/usr/src/app/downloads/")
    if not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR += "/"

    GDRIVE_ID = environ.get("GDRIVE_ID", "")
    CLOUD_LINK_FILTERS = environ.get("CLOUD_LINK_FILTERS", "mypikpak.com")
    RCLONE_PATH = environ.get("RCLONE_PATH", "")
    RCLONE_FLAGS = environ.get("RCLONE_FLAGS", "")

    DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
    if DEFAULT_UPLOAD != "rc":
        DEFAULT_UPLOAD = "gd"
    # ======================================================================

    # =========================== OPTIONALS ===============================
    if AUTHORIZED_CHATS := environ.get("AUTHORIZED_CHATS", ""):
        aid = AUTHORIZED_CHATS.split()
        for id_ in aid:
            user_data.setdefault(int(id_.strip()), {})["is_auth"] = True

    if SUDO_USERS := environ.get("SUDO_USERS", ""):
        aid = SUDO_USERS.split()
        for id_ in aid:
            user_data.setdefault(int(id_.strip()), {})["is_sudo"] = True

    if EXTENSION_FILTER := environ.get("EXTENSION_FILTER", ""):
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.extend(["aria2", "!qB"])
        fx = EXTENSION_FILTER.split()
        for x in fx:
            if x.strip().startswith("."):
                x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

    DATABASE_URL = environ.get("DATABASE_URL", "")
    downloads = aria2.get_downloads()
    if TORRENT_TIMEOUT := environ.get("TORRENT_TIMEOUT", ""):
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": TORRENT_TIMEOUT},
                    )
                except Exception as e:
                    LOGGER.error(e)
        aria2_options["bt-stop-timeout"] = TORRENT_TIMEOUT
        if DATABASE_URL:
            await DbManager().update_aria2("bt-stop-timeout", TORRENT_TIMEOUT)
        TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)
    else:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": "0"},
                    )
                except Exception as e:
                    LOGGER.error(e)
        aria2_options["bt-stop-timeout"] = "0"
        if DATABASE_URL:
            await DbManager().update_aria2("bt-stop-timeout", "0")
        TORRENT_TIMEOUT = ""

    QUEUE_ALL = environ.get("QUEUE_ALL", "")
    QUEUE_ALL = int(QUEUE_ALL) if QUEUE_ALL else ""

    QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "5")
    QUEUE_DOWNLOAD = int(QUEUE_DOWNLOAD) if QUEUE_DOWNLOAD else ""

    QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
    QUEUE_UPLOAD = int(QUEUE_UPLOAD) if QUEUE_UPLOAD else ""

    QUEUE_COMPLETE = environ.get("QUEUE_COMPLETE", "False").lower() == "true"

    ENABLE_STREAM_LINK = environ.get("ENABLE_STREAM_LINK", "False").lower() == "true"
    STREAM_BASE_URL = environ.get("STREAM_BASE_URL", "").rstrip("/")
    STREAM_PORT = environ.get("STREAM_PORT", "")

    DISABLE_MIRROR_LEECH = environ.get("DISABLE_MIRROR_LEECH", "")
    INDEX_URL = environ.get("INDEX_URL", "").rstrip("/")
    USE_SERVICE_ACCOUNTS = (
        environ.get("USE_SERVICE_ACCOUNTS", "False").lower() == "true"
    )
    CMD_SUFFIX = environ.get("CMD_SUFFIX", "")
    AUTO_THUMBNAIL = environ.get("AUTO_THUMBNAIL", "False").lower()
    if AUTO_THUMBNAIL == "true":
        AUTO_THUMBNAIL = "poster"
    elif AUTO_THUMBNAIL == "false":
        AUTO_THUMBNAIL = "disabled"
    PREMIUM_MODE = environ.get("PREMIUM_MODE", "False").lower() == "true"
    SESSION_TIMEOUT = int(environ.get("SESSION_TIMEOUT", 0))
    DAILY_MODE = environ.get("DAILY_MODE", "False").lower() == "true"
    MEDIA_GROUP = environ.get("MEDIA_GROUP", "False").lower() == "true"
    STOP_DUPLICATE = environ.get("STOP_DUPLICATE", "False").lower() == "true"
    IS_TEAM_DRIVE = environ.get("IS_TEAM_DRIVE", "False").lower() == "true"
    MULTI_TIMEGAP = int(environ.get("MULTI_TIMEGAP", 5))
    AS_DOCUMENT = environ.get("AS_DOCUMENT", "False").lower() == "true"
    SAVE_MESSAGE = environ.get("SAVE_MESSAGE", "False").lower() == "true"
    LEECH_FILENAME_PREFIX = environ.get("LEECH_FILENAME_PREFIX", "")
    LEECH_INFO_PIN = environ.get("LEECH_INFO_PIN", "False").lower() == "true"
    USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
    SAVE_SESSION_STRING = environ.get("SAVE_SESSION_STRING", "")
    USERBOT_LEECH = environ.get("USERBOT_LEECH", "False").lower() == "true"
    BOT_PM = environ.get("BOT_PM", "True").lower() == "true"
    AUTO_DELETE_MESSAGE_DURATION = int(environ.get("AUTO_DELETE_MESSAGE_DURATION", 30))
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = int(
        environ.get("AUTO_DELETE_UPLOAD_MESSAGE_DURATION", 60)
    )
    YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
    DAILY_LIMIT_SIZE = int(environ.get("DAILY_LIMIT_SIZE", 2))
    VIDTOOLS_FAST_MODE = environ.get("VIDTOOLS_FAST_MODE", "False").lower() == "true"
    COMPRESS_BANNER = environ.get("COMPRESS_BANNER", "Re-Encoded by ZxZone")
    LIB264_PRESET = environ.get("LIB264_PRESET", "superfast")
    LIB265_PRESET = environ.get("LIB265_PRESET", "faster")
    HARDSUB_FONT_SIZE = environ.get("HARDSUB_FONT_SIZE", "20")
    HARDSUB_FONT_NAME = environ.get("HARDSUB_FONT_NAME", "ZxZone")
    DISABLE_VIDTOOLS = environ.get("DISABLE_VIDTOOLS", "compress convert watermark")
    DISABLE_MULTI_VIDTOOLS = environ.get(
        "DISABLE_MULTI_VIDTOOLS", "compress rmstream extract trim watermark convert"
    )
    START_MESSAGE = environ.get("START_MESSAGE", "")
    STATUS_UPDATE_INTERVAL = int(environ.get("STATUS_UPDATE_INTERVAL", 5))
    if len(task_dict) != 0 and (st := Intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            Intervals["status"][key] = setInterval(
                STATUS_UPDATE_INTERVAL, update_status_message, key
            )

    INCOMPLETE_TASK_NOTIFIER = (
        environ.get("INCOMPLETE_TASK_NOTIFIER", "False").lower() == "true"
    )
    if not INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        await DbManager().trunc_table("tasks")
    INCOMPLETE_AUTO_RESUME = (
        environ.get("INCOMPLETE_AUTO_RESUME", "True").lower() == "true"
    )
    # ======================================================================

    # ============================= RCLONE =================================
    ENABLE_FASTDL = environ.get("ENABLE_FASTDL", "False").lower() == "true"
    RCLONE_SERVE_URL = environ.get("RCLONE_SERVE_URL", "")
    RCLONE_SERVE_PORT = environ.get("RCLONE_SERVE_PORT", "")
    RCLONE_SERVE_USER = environ.get("RCLONE_SERVE_USER", "")
    RCLONE_SERVE_PASS = environ.get("RCLONE_SERVE_PASS", "")
    RCLONE_TFSIMULATION = int(environ.get("RCLONE_TFSIMULATION", "4"))
    # ======================================================================

    # ============================== LOGS ==================================
    ONCOMPLETE_LEECH_LOG = environ.get("ONCOMPLETE_LEECH_LOG", "True").lower() == "true"
    LEECH_LOG = environ.get("LEECH_LOG", "")
    LEECH_LOG = (
        int(LEECH_LOG)
        if LEECH_LOG.isdigit() or LEECH_LOG.startswith("-")
        else LEECH_LOG
    )

    MIRROR_LOG = environ.get("MIRROR_LOG", "")
    MIRROR_LOG = (
        int(MIRROR_LOG)
        if MIRROR_LOG.isdigit() or MIRROR_LOG.startswith("-")
        else MIRROR_LOG
    )

    OTHER_LOG = environ.get("OTHER_LOG", "")
    OTHER_LOG = (
        int(OTHER_LOG)
        if OTHER_LOG.isdigit() or OTHER_LOG.startswith("-")
        else OTHER_LOG
    )

    LINK_LOG = environ.get("LINK_LOG", "")
    LINK_LOG = (
        int(LINK_LOG) if LINK_LOG.isdigit() or LINK_LOG.startswith("-") else LINK_LOG
    )
    # ======================================================================

    # ============================= LIMITS =================================
    EQUAL_SPLITS = environ.get("EQUAL_SPLITS", "False").lower() == "true"

    CLONE_LIMIT = environ.get("CLONE_LIMIT", "")
    CLONE_LIMIT = float(CLONE_LIMIT) if CLONE_LIMIT else ""

    LEECH_LIMIT = environ.get("LEECH_LIMIT", "")
    LEECH_LIMIT = float(LEECH_LIMIT) if LEECH_LIMIT else ""

    LEECH_SPLIT_SIZE = environ.get("LEECH_SPLIT_SIZE", "")
    LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE) if LEECH_SPLIT_SIZE else ""

    MEGA_LIMIT = environ.get("MEGA_LIMIT", "")
    MEGA_LIMIT = float(MEGA_LIMIT) if MEGA_LIMIT else ""

    NONPREMIUM_LIMIT = environ.get("NONPREMIUM_LIMIT", "5")
    NONPREMIUM_LIMIT = float(NONPREMIUM_LIMIT) if NONPREMIUM_LIMIT else ""

    STATUS_LIMIT = environ.get("STATUS_LIMIT", "")
    STATUS_LIMIT = int(STATUS_LIMIT) if STATUS_LIMIT else 10

    TORRENT_DIRECT_LIMIT = environ.get("TORRENT_DIRECT_LIMIT", "")
    TORRENT_DIRECT_LIMIT = float(TORRENT_DIRECT_LIMIT) if TORRENT_DIRECT_LIMIT else ""

    TOTAL_TASKS_LIMIT = environ.get("TOTAL_TASKS_LIMIT", "")
    TOTAL_TASKS_LIMIT = int(TOTAL_TASKS_LIMIT) if TOTAL_TASKS_LIMIT else ""

    USER_TASKS_LIMIT = environ.get("USER_TASKS_LIMIT", "")
    USER_TASKS_LIMIT = int(USER_TASKS_LIMIT) if USER_TASKS_LIMIT else ""

    ZIP_UNZIP_LIMIT = environ.get("ZIP_UNZIP_LIMIT", "")
    ZIP_UNZIP_LIMIT = float(ZIP_UNZIP_LIMIT) if ZIP_UNZIP_LIMIT else ""

    STORAGE_THRESHOLD = environ.get("STORAGE_THRESHOLD", "")
    STORAGE_THRESHOLD = float(STORAGE_THRESHOLD) if STORAGE_THRESHOLD else ""

    MAX_YTPLAYLIST = environ.get("MAX_YTPLAYLIST", "")
    MAX_YTPLAYLIST = int(MAX_YTPLAYLIST) if MAX_YTPLAYLIST else ""
    # ======================================================================

    # ============================= GOFILE =================================
    GOFILE = environ.get("GOFILE", "False").lower() == "true"
    GOFILETOKEN = environ.get("GOFILETOKEN", "")
    GOFILEBASEFOLDER = environ.get("GOFILEBASEFOLDER", "")
    if not GOFILETOKEN or not GOFILEBASEFOLDER:
        GOFILE = False
    # ======================================================================

    # ============================= FORCE =================================
    # Auto Mute
    FORCE_SHORTEN = environ.get("FORCE_SHORTEN", "False").lower() == "true"
    AUTO_MUTE = environ.get("AUTO_MUTE", "False").lower() == "true"
    MUTE_CHAT_ID = int(environ.get("MUTE_CHAT_ID", -1004319932089))
    AUTO_MUTE_DURATION = int(environ.get("AUTO_MUTE_DURATION", 30))
    # Username
    FUSERNAME = environ.get("FUSERNAME", "False").lower() == "true"
    # Subscribe
    FSUB = environ.get("FSUB", "False").lower() == "true"
    FSUB_CHANNEL_ID = int(environ.get("FSUB_CHANNEL_ID", -1004319932089))
    FSUB_BUTTON_NAME = environ.get("FSUB_BUTTON_NAME", "Join Channel")
    CHANNEL_USERNAME = environ.get("CHANNEL_USERNAME", "zonexusmlgroup4gb")
    # ======================================================================

    # ============================ STICKERS ================================
    STICKERID_COUNT = environ.get("STICKERID_COUNT", "")
    STICKERID_ERROR = environ.get("STICKERID_ERROR", "")
    STICKERID_LEECH = environ.get("STICKERID_LEECH", "")
    STICKERID_MIRROR = environ.get("STICKERID_MIRROR", "")
    STICKER_DELETE_DURATION = int(environ.get("STICKER_DELETE_DURATION", 0))
    # ======================================================================

    # ============================= IMAGES =================================
    ENABLE_IMAGE_MODE = False
    IMAGE_ARIA = ""
    IMAGE_AUTH = ""
    IMAGE_BOLD = ""
    IMAGE_BYE = ""
    IMAGE_CANCEL = ""
    IMAGE_CAPTION = ""
    IMAGE_COMMONS_CHECK = ""
    IMAGE_COMPLETE = ""
    IMAGE_CONEDIT = ""
    IMAGE_CONPRIVATE = ""
    IMAGE_CONSET = ""
    IMAGE_CONVIEW = ""
    IMAGE_DUMP = ""
    IMAGE_EXTENSION = ""
    IMAGE_GD = ""
    IMAGE_HELP = ""
    IMAGE_HTML = ""
    IMAGE_IMDB = ""
    IMAGE_INFO = ""
    IMAGE_ITALIC = ""
    IMAGE_JD = ""
    IMAGE_LOGS = ""
    IMAGE_MDL = ""
    IMAGE_MEDINFO = ""
    IMAGE_METADATA = ""
    IMAGE_MONO = ""
    IMAGE_NORMAL = ""
    IMAGE_OWNER = ""
    IMAGE_PAUSE = ""
    IMAGE_PRENAME = ""
    IMAGE_QBIT = ""
    IMAGE_RCLONE = ""
    IMAGE_REMNAME = ""
    IMAGE_RSS = ""
    IMAGE_SEARCH = ""
    IMAGE_STATS = ""
    IMAGE_STATUS = ""
    IMAGE_SUFNAME = ""
    IMAGE_TMDB = ""
    IMAGE_TXT = ""
    IMAGE_UNAUTH = ""
    IMAGE_UNKNOW = ""
    IMAGE_USER = ""
    IMAGE_USETIINGS = ""
    IMAGE_VIDTOOLS = ""
    IMAGE_WEL = ""
    IMAGE_WIBU = ""
    IMAGE_YT = ""
    IMAGE_ZIP = ""
    # ======================================================================

    # =========================== ACCOUNTS =================================
    # JDownloader
    JD_EMAIL = environ.get("JD_EMAIL", "")
    JD_PASS = environ.get("JD_PASS", "")
    # Uptobox
    UPTOBOX_TOKEN = environ.get("UPTOBOX_TOKEN", "")
    # GDTot
    CRYPT_GDTOT = environ.get("CRYPT_GDTOT", "")
    # FileLion
    FILELION_API = environ.get("FILELION_API", "")
    # StreamWish
    STREAMWISH_API = environ.get("STREAMWISH_API", "")
    # SharerPw
    SHARERPW_LARAVEL_SESSION = environ.get("SHARERPW_LARAVEL_SESSION", "")
    SHARERPW_XSRF_TOKEN = environ.get("SHARERPW_XSRF_TOKEN", "")
    # ======================================================================

    # =========================== UPSTREAM =================================
    UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
    UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "main")
    UPDATE_EVERYTHING = environ.get("UPDATE_EVERYTHING", "False").lower() == "true"
    # ======================================================================

    # ============================== UI ====================================
    AUTHOR_NAME = environ.get("AUTHOR_NAME", "ZxZone")
    AUTHOR_URL = environ.get("AUTHOR_URL", "https://t.me/zonexusmlgroup4gb")
    DRIVE_SEARCH_TITLE = environ.get("DRIVE_SEARCH_TITLE", "Drive Search")
    GD_INFO = environ.get("GD_INFO", "By ZxZone")
    PROG_FINISH = environ.get("PROG_FINISH", "⬢")
    PROG_UNFINISH = environ.get("PROG_UNFINISH", "⬡")
    SOURCE_LINK_TITLE = environ.get("SOURCE_LINK_TITLE", "Source Link")
    TIME_ZONE = environ.get("TIME_ZONE", "Asia/Dhaka")
    TIME_ZONE_TITLE = environ.get("TIME_ZONE_TITLE", "UTC+6")
    TSEARCH_TITLE = environ.get("TSEARCH_TITLE", "Torrent Search")
    # ======================================================================

    # =========================== BUTTONS =================================
    SOURCE_LINK = environ.get("SOURCE_LINK", "False").lower() == "true"
    VIEW_LINK = environ.get("VIEW_LINK", "False").lower() == "true"
    BUTTON_FIVE_NAME = environ.get("BUTTON_FIVE_NAME", "")
    BUTTON_FIVE_URL = environ.get("BUTTON_FIVE_URL", "")
    BUTTON_FOUR_NAME = environ.get("BUTTON_FOUR_NAME", "")
    BUTTON_FOUR_URL = environ.get("BUTTON_FOUR_URL", "")
    BUTTON_SIX_NAME = environ.get("BUTTON_SIX_NAME", "")
    BUTTON_SIX_URL = environ.get("BUTTON_SIX_URL", "")
    # ======================================================================

    # =========================== SERVER ==============================
    port_value = environ.get("PORT")
    PORT = int(port_value) if port_value else 80
    if not 1 <= PORT <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    BASE_URL = environ.get("BASE_URL", "").rstrip("/")
    if BASE_URL == STREAM_BASE_URL:
        STREAM_PORT = PORT
    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    if BASE_URL and BASE_URL != STREAM_BASE_URL:
        await create_subprocess_exec(
            "gunicorn",
            "web.wserver:app",
            "--bind",
            f"0.0.0.0:{PORT}",
            "--worker-class",
            "gevent",
        )

    WEB_PINCODE = environ.get("WEB_PINCODE", "False").lower() == "true"
    # ======================================================================

    # =============================== RSS ==================================
    RSS_CHAT = environ.get("RSS_CHAT", "")
    RSS_CHAT = (
        int(RSS_CHAT) if RSS_CHAT.isdigit() or RSS_CHAT.startswith("-") else RSS_CHAT
    )
    RSS_DELAY = environ.get("RSS_DELAY", "")
    RSS_DELAY = int(RSS_DELAY) if RSS_DELAY else 900
    # ======================================================================

    # ============================ TORSEARCH ===============================
    SEARCH_LIMIT = int(environ.get("SEARCH_LIMIT", 20))
    SEARCH_API_LINK = environ.get("SEARCH_API_LINK", "").rstrip("/")
    SEARCH_PLUGINS = environ.get("SEARCH_PLUGINS", "")
    # ======================================================================

    # ============================= HEROKU =================================
    HEROKU_API_KEY = environ.get("HEROKU_API_KEY", "")
    HEROKU_APP_NAME = environ.get("HEROKU_APP_NAME", "")
    # ======================================================================

    DRIVES_IDS.clear()
    DRIVES_NAMES.clear()
    INDEX_URLS.clear()

    if GDRIVE_ID:
        DRIVES_NAMES.append("Main")
        DRIVES_IDS.append(GDRIVE_ID)
        INDEX_URLS.append(INDEX_URL)

    if await aiopath.exists("list_drives.txt"):
        async with aiopen("list_drives.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                DRIVES_IDS.append(temp[1])
                DRIVES_NAMES.append(temp[0].replace("_", " "))
                if len(temp) > 2:
                    INDEX_URLS.append(temp[2])
                else:
                    INDEX_URLS.append("")

    SHORTENERES.clear()
    SHORTENER_APIS.clear()
    if await aiopath.exists("shorteners.txt"):
        with open("shorteners.txt", "r+") as f:
            lines = f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    SHORTENERES.append(temp[0])
                    SHORTENER_APIS.append(temp[1])

    config_dict.update(
        {
            "BOT_TOKEN": BOT_TOKEN,
            "TELEGRAM_API": TELEGRAM_API,
            "TELEGRAM_HASH": TELEGRAM_HASH,
            "OWNER_ID": OWNER_ID,
            "DATABASE_URL": DATABASE_URL,
            "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
            "DOWNLOAD_DIR": DOWNLOAD_DIR,
            "GDRIVE_ID": GDRIVE_ID,
            "RCLONE_PATH": RCLONE_PATH,
            "RCLONE_FLAGS": RCLONE_FLAGS,
            "CLOUD_LINK_FILTERS": CLOUD_LINK_FILTERS,
            # OPTIONALS
            "START_MESSAGE": START_MESSAGE,
            "COMPRESS_BANNER": COMPRESS_BANNER,
            "LIB264_PRESET": LIB264_PRESET,
            "LIB265_PRESET": LIB265_PRESET,
            "HARDSUB_FONT_NAME": HARDSUB_FONT_NAME,
            "HARDSUB_FONT_SIZE": HARDSUB_FONT_SIZE,
            "VIDTOOLS_FAST_MODE": VIDTOOLS_FAST_MODE,
            "DISABLE_VIDTOOLS": DISABLE_VIDTOOLS,
            "DISABLE_MULTI_VIDTOOLS": DISABLE_MULTI_VIDTOOLS,
            "ENABLE_STREAM_LINK": ENABLE_STREAM_LINK,
            "STREAM_BASE_URL": STREAM_BASE_URL,
            "STREAM_PORT": STREAM_PORT,
            "DISABLE_MIRROR_LEECH": DISABLE_MIRROR_LEECH,
            "AUTHORIZED_CHATS": AUTHORIZED_CHATS,
            "SUDO_USERS": SUDO_USERS,
            "EXTENSION_FILTER": EXTENSION_FILTER,
            "INDEX_URL": INDEX_URL,
            "TORRENT_TIMEOUT": TORRENT_TIMEOUT,
            "INCOMPLETE_TASK_NOTIFIER": INCOMPLETE_TASK_NOTIFIER,
            "INCOMPLETE_AUTO_RESUME": INCOMPLETE_AUTO_RESUME,
            "USE_SERVICE_ACCOUNTS": USE_SERVICE_ACCOUNTS,
            "CMD_SUFFIX": CMD_SUFFIX,
            "STOP_DUPLICATE": STOP_DUPLICATE,
            "IS_TEAM_DRIVE": IS_TEAM_DRIVE,
            "MULTI_TIMEGAP": MULTI_TIMEGAP,
            "AS_DOCUMENT": AS_DOCUMENT,
            "SAVE_MESSAGE": SAVE_MESSAGE,
            "LEECH_FILENAME_PREFIX": LEECH_FILENAME_PREFIX,
            "LEECH_INFO_PIN": LEECH_INFO_PIN,
            "USER_SESSION_STRING": USER_SESSION_STRING,
            "SAVE_SESSION_STRING": SAVE_SESSION_STRING,
            "USERBOT_LEECH": USERBOT_LEECH,
            "BOT_PM": BOT_PM,
            "AUTO_DELETE_MESSAGE_DURATION": AUTO_DELETE_MESSAGE_DURATION,
            "AUTO_DELETE_UPLOAD_MESSAGE_DURATION": AUTO_DELETE_UPLOAD_MESSAGE_DURATION,
            "STATUS_UPDATE_INTERVAL": STATUS_UPDATE_INTERVAL,
            "YT_DLP_OPTIONS": YT_DLP_OPTIONS,
            "AUTO_THUMBNAIL": AUTO_THUMBNAIL,
            "PREMIUM_MODE": PREMIUM_MODE,
            "DAILY_MODE": DAILY_MODE,
            "SESSION_TIMEOUT": SESSION_TIMEOUT,
            "MEDIA_GROUP": MEDIA_GROUP,
            "QUEUE_ALL": QUEUE_ALL,
            "QUEUE_DOWNLOAD": QUEUE_DOWNLOAD,
            "QUEUE_UPLOAD": QUEUE_UPLOAD,
            "QUEUE_COMPLETE": QUEUE_COMPLETE,
            # RCLONE
            "ENABLE_FASTDL": ENABLE_FASTDL,
            "RCLONE_SERVE_URL": RCLONE_SERVE_URL,
            "RCLONE_SERVE_PORT": RCLONE_SERVE_PORT,
            "RCLONE_SERVE_USER": RCLONE_SERVE_USER,
            "RCLONE_SERVE_PASS": RCLONE_SERVE_PASS,
            "RCLONE_TFSIMULATION": RCLONE_TFSIMULATION,
            # LOGS
            "ONCOMPLETE_LEECH_LOG": ONCOMPLETE_LEECH_LOG,
            "LEECH_LOG": LEECH_LOG,
            "MIRROR_LOG": MIRROR_LOG,
            "OTHER_LOG": OTHER_LOG,
            "LINK_LOG": LINK_LOG,
            # LIMITS
            "EQUAL_SPLITS": EQUAL_SPLITS,
            "DAILY_LIMIT_SIZE": DAILY_LIMIT_SIZE,
            "CLONE_LIMIT": CLONE_LIMIT,
            "LEECH_LIMIT": LEECH_LIMIT,
            "LEECH_SPLIT_SIZE": LEECH_SPLIT_SIZE,
            "MEGA_LIMIT": MEGA_LIMIT,
            "NONPREMIUM_LIMIT": NONPREMIUM_LIMIT,
            "STATUS_LIMIT": STATUS_LIMIT,
            "TORRENT_DIRECT_LIMIT": TORRENT_DIRECT_LIMIT,
            "TOTAL_TASKS_LIMIT": TOTAL_TASKS_LIMIT,
            "USER_TASKS_LIMIT": USER_TASKS_LIMIT,
            "ZIP_UNZIP_LIMIT": ZIP_UNZIP_LIMIT,
            "STORAGE_THRESHOLD": STORAGE_THRESHOLD,
            "MAX_YTPLAYLIST": MAX_YTPLAYLIST,
            # GOFILE
            "GOFILE": GOFILE,
            "GOFILETOKEN": GOFILETOKEN,
            "GOFILEBASEFOLDER": GOFILEBASEFOLDER,
            # FMODE
            "FORCE_SHORTEN": FORCE_SHORTEN,
            "AUTO_MUTE": AUTO_MUTE,
            "MUTE_CHAT_ID": MUTE_CHAT_ID,
            "AUTO_MUTE_DURATION": AUTO_MUTE_DURATION,
            "FUSERNAME": FUSERNAME,
            "FSUB": FSUB,
            "FSUB_CHANNEL_ID": FSUB_CHANNEL_ID,
            "FSUB_BUTTON_NAME": FSUB_BUTTON_NAME,
            "CHANNEL_USERNAME": CHANNEL_USERNAME,
            # STICKERS
            "STICKERID_COUNT": STICKERID_COUNT,
            "STICKERID_ERROR": STICKERID_ERROR,
            "STICKERID_LEECH": STICKERID_LEECH,
            "STICKERID_MIRROR": STICKERID_MIRROR,
            "STICKER_DELETE_DURATION": STICKER_DELETE_DURATION,
            # IMAGES
            "ENABLE_IMAGE_MODE": False,
            "IMAGE_ARIA": "",
            "IMAGE_AUTH": "",
            "IMAGE_BOLD": "",
            "IMAGE_BYE": "",
            "IMAGE_CANCEL": "",
            "IMAGE_CAPTION": "",
            "IMAGE_COMPLETE": "",
            "IMAGE_CONEDIT": "",
            "IMAGE_CONPRIVATE": "",
            "IMAGE_CONSET": "",
            "IMAGE_CONVIEW": "",
            "IMAGE_DUMP": "",
            "IMAGE_COMMONS_CHECK": "",
            "IMAGE_EXTENSION": "",
            "IMAGE_GD": "",
            "IMAGE_HELP": "",
            "IMAGE_HTML": "",
            "IMAGE_IMDB": "",
            "IMAGE_INFO": "",
            "IMAGE_ITALIC": "",
            "IMAGE_JD": "",
            "IMAGE_LOGS": "",
            "IMAGE_MDL": "",
            "IMAGE_MEDINFO": "",
            "IMAGE_METADATA": "",
            "IMAGE_MONO": "",
            "IMAGE_NORMAL": "",
            "IMAGE_OWNER": "",
            "IMAGE_PAUSE": "",
            "IMAGE_PRENAME": "",
            "IMAGE_QBIT": "",
            "IMAGE_RCLONE": "",
            "IMAGE_REMNAME": "",
            "IMAGE_RSS": "",
            "IMAGE_SEARCH": "",
            "IMAGE_STATS": "",
            "IMAGE_STATUS": "",
            "IMAGE_SUFNAME": "",
            "IMAGE_TMDB": "",
            "IMAGE_TXT": "",
            "IMAGE_UNAUTH": "",
            "IMAGE_UNKNOW": "",
            "IMAGE_USER": "",
            "IMAGE_USETIINGS": "",
            "IMAGE_VIDTOOLS": "",
            "IMAGE_WEL": "",
            "IMAGE_WIBU": "",
            "IMAGE_YT": "",
            "IMAGE_ZIP": "",
            # ACCOUNTS
            "JD_EMAIL": JD_EMAIL,
            "JD_PASS": JD_PASS,
            "UPTOBOX_TOKEN": UPTOBOX_TOKEN,
            "CRYPT_GDTOT": CRYPT_GDTOT,
            "FILELION_API": FILELION_API,
            "STREAMWISH_API": STREAMWISH_API,
            "SHARERPW_LARAVEL_SESSION": SHARERPW_LARAVEL_SESSION,
            "SHARERPW_XSRF_TOKEN": SHARERPW_XSRF_TOKEN,
            # UPSTREAM
            "UPSTREAM_REPO": UPSTREAM_REPO,
            "UPSTREAM_BRANCH": UPSTREAM_BRANCH,
            "UPDATE_EVERYTHING": UPDATE_EVERYTHING,
            # UI
            "AUTHOR_NAME": AUTHOR_NAME,
            "AUTHOR_URL": AUTHOR_URL,
            "DRIVE_SEARCH_TITLE": DRIVE_SEARCH_TITLE,
            "GD_INFO": GD_INFO,
            "PROG_FINISH": PROG_FINISH,
            "PROG_UNFINISH": PROG_UNFINISH,
            "SOURCE_LINK_TITLE": SOURCE_LINK_TITLE,
            "TIME_ZONE": TIME_ZONE,
            "TIME_ZONE_TITLE": TIME_ZONE_TITLE,
            "TSEARCH_TITLE": TSEARCH_TITLE,
            # BUTTONS
            "SOURCE_LINK": SOURCE_LINK,
            "VIEW_LINK": VIEW_LINK,
            "BUTTON_FIVE_NAME": BUTTON_FIVE_NAME,
            "BUTTON_FIVE_URL": BUTTON_FIVE_URL,
            "BUTTON_FOUR_NAME": BUTTON_FOUR_NAME,
            "BUTTON_FOUR_URL": BUTTON_FOUR_URL,
            "BUTTON_SIX_NAME": BUTTON_SIX_NAME,
            "BUTTON_SIX_URL": BUTTON_SIX_URL,
            # QBITTORRENT
            "BASE_URL": BASE_URL,
            "WEB_PINCODE": WEB_PINCODE,
            # RSS
            "RSS_CHAT": RSS_CHAT,
            "RSS_DELAY": RSS_DELAY,
            # TORSEARCH
            "SEARCH_API_LINK": SEARCH_API_LINK,
            "SEARCH_PLUGINS": SEARCH_PLUGINS,
            "SEARCH_LIMIT": SEARCH_LIMIT,
            # HEROKU
            "HEROKU_API_KEY": HEROKU_API_KEY,
            "HEROKU_APP_NAME": HEROKU_APP_NAME,
        }
    )
    LOGGER.info("Config loaded!")
    if DATABASE_URL:
        await DbManager().update_config(config_dict)
        LOGGER.info("Config update in database!!")
    await gather(
        server.cleanup(),
        intialize_userbot(),
        initiate_search_tools(),
        start_from_queued(),
        rclone_serve_booter(),
    )
    await start_server()
    addJob()


async def intialize_userbot(check=True):
    async with bot_lock:
        if check:
            userbot: Client = bot_dict["USERBOT"]
            if userbot and userbot.is_connected:
                await userbot.stop()
                LOGGER.info("Userbot stopped.")
        bot_dict.update(
            {"IS_PREMIUM": False, "USERBOT": None, "MAX_SPLIT_SIZE": DEFAULT_SPLIT_SIZE}
        )
        if USER_SESSION_STRING := config_dict["USER_SESSION_STRING"]:
            try:
                await gather(
                    clean_target("user.session"), clean_target("user.session-journal")
                )
                userbot = await Client(
                    "user",
                    config_dict["TELEGRAM_API"],
                    config_dict["TELEGRAM_HASH"],
                    session_string=USER_SESSION_STRING,
                    no_updates=True,
                    **kwargs,
                ).start()
                bot_dict["IS_PREMIUM"] = userbot.me.is_premium
                if bot_dict["IS_PREMIUM"]:
                    bot_dict["USERBOT"] = userbot
                    LOGGER.info("Premium detected, 4GB leech enabled.")
                    if not config_dict["LEECH_LOG"]:
                        LOGGER.warning("Premium Leech required Leech Log!")
                    bot_dict["MAX_SPLIT_SIZE"] = 4194304000
                else:
                    await userbot.stop()
                    LOGGER.info(
                        "Not detected premium from session string, using default client!"
                    )
            except Exception as e:
                LOGGER.error(e)
    LEECH_SPLIT_SIZE, MAX_SPLIT_SIZE = (
        config_dict["LEECH_SPLIT_SIZE"],
        bot_dict["MAX_SPLIT_SIZE"],
    )
    if (
        not LEECH_SPLIT_SIZE
        or LEECH_SPLIT_SIZE > MAX_SPLIT_SIZE
        or LEECH_SPLIT_SIZE == DEFAULT_SPLIT_SIZE
    ):
        config_dict["LEECH_SPLIT_SIZE"] = MAX_SPLIT_SIZE
        if config_dict["DATABASE_URL"]:
            await DbManager().update_config({"LEECH_SPLIT_SIZE": MAX_SPLIT_SIZE})
    LOGGER.info("Leech Split Size: %s.", config_dict["LEECH_SPLIT_SIZE"])


async def intialize_savebot(session_string=None, check=True, user_id=None):
    async with bot_lock:
        if session_string == config_dict["USER_SESSION_STRING"] and (
            userbot := bot_dict.get("USERBOT")
        ):
            bot_dict["SAVEBOT"] = userbot
            return
        if (
            user_id
            and session_string == user_data.get(user_id, {}).get("session_string", "")
            and (savebot := bot_dict.get(user_id, {}).get("SAVEBOT"))
        ):
            bot_dict.setdefault(user_id, {})
            bot_dict[user_id]["SAVEBOT"] = savebot
            return
        if check:
            savebot: Client = (
                bot_dict.get(user_id, {}).get("SAVEBOT")
                if user_id
                else bot_dict["SAVEBOT"]
            )
            if savebot and savebot.is_connected:
                await savebot.stop()
                LOGGER.info("Savebot stopped.")
        if user_id:
            bot_dict.setdefault(user_id, {})
            bot_dict[user_id]["SAVEBOT"] = None
        else:
            bot_dict["SAVEBOT"] = None
        if session_string:
            try:
                id_ = str(user_id) if user_id else "savebot"
                await gather(
                    clean_target(f"{id_}.session"),
                    clean_target(f"{id_}.session-journal"),
                )
                savebot = await Client(
                    id_,
                    config_dict["TELEGRAM_API"],
                    config_dict["TELEGRAM_HASH"],
                    session_string=session_string,
                    no_updates=True,
                    **kwargs,
                ).start()
                if user_id:
                    bot_dict[user_id]["SAVEBOT"] = savebot
                else:
                    bot_dict["SAVEBOT"] = savebot
                LOGGER.info("Save content mode enabled!")
            except Exception as e:
                LOGGER.error(e)
