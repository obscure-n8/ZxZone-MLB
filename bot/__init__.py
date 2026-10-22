from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aria2p import API as ariaAPI, Client as ariaClient
from asyncio import Lock, new_event_loop, set_event_loop
from base64 import b64decode
from dotenv import load_dotenv, dotenv_values
from logging import (
    getLogger,
    FileHandler,
    StreamHandler,
    basicConfig,
    INFO,
    ERROR,
    warning as log_warning,
)
from os import chmod, environ, getcwd, path as ospath, remove as osremove, walk
from pymongo import MongoClient
from pyrogram import Client as tgClient, __version__
from requests import get as rget
from pyrogram.enums import ParseMode
from qbittorrentapi import Client as qbClient
from re import sub as resub
from shutil import copyfile
from socket import setdefaulttimeout
from subprocess import Popen, run as srun
from sys import exit
from time import sleep, time
from tzlocal import get_localzone
from uvloop import install
from zipfile import BadZipFile, ZipFile
from pyrogram import utils as pyroutils

pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999


install()
bot_loop = new_event_loop()
set_event_loop(bot_loop)
setdefaulttimeout(600)

botStartTime = time()

getLogger("qbittorrentapi").setLevel(INFO)
getLogger("requests").setLevel(INFO)
getLogger("urllib3").setLevel(INFO)
getLogger("pyrogram").setLevel(ERROR)
getLogger("googleapiclient.discovery").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)

basicConfig(
    format="%(asctime)s: [%(levelname)s: %(filename)s - %(lineno)d] ~ %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    datefmt="%d-%b-%y %I:%M:%S %p",
    level=INFO,
)


LOGGER = getLogger(__name__)

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

load_dotenv("config.env", override=True)

Intervals = {"status": {}, "qb": "", "jd": ""}
QbTorrents = {}
jd_downloads = {}
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []
SHORTENERES = []
SHORTENER_APIS = []
GLOBAL_EXTENSION_FILTER = ["aria2", "!qB"]
user_data = {}
aria2_options = {}
qbit_options = {}
queued_dl = {}
queued_up = {}
non_queued_dl = set()
non_queued_up = set()
multi_tags = set()

task_dict_lock = Lock()
queue_dict_lock = Lock()
qb_listener_lock = Lock()
jd_lock = Lock()
cpu_eater_lock = Lock()
subprocess_lock = Lock()
bot_lock = Lock()
status_dict = {}
task_dict = {}
rss_dict = {}
bot_dict = {}

DEFAULT_SPLIT_SIZE = 2097151000
ARIA_NAME = environ.get("ARIA_NAME", "wz2c")
QBIT_NAME = environ.get("QBIT_NAME", "wznox")
FFMPEG_NAME = environ.get("FFMPEG_NAME", "wzeg")

# ============================ REQUIRED ================================
if not (BOT_TOKEN := environ.get("BOT_TOKEN", "")):
    LOGGER.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = BOT_TOKEN.split(":", 1)[0]

if DATABASE_URL := environ.get("DATABASE_URL", ""):
    if not DATABASE_URL.startswith("mongodb"):
        try:
            DATABASE_URL = b64decode(
                resub("ini|adalah|pesan|yang|sangat|rahasia", "", DATABASE_URL)
            ).decode("utf-8")
        except Exception:
            pass
    try:
        conn = MongoClient(DATABASE_URL)
        db = conn.mltb
        current_config = dict(dotenv_values("config.env"))
        old_config = db.settings.deployConfig.find_one({"_id": bot_id})
        if old_config is None:
            db.settings.deployConfig.replace_one(
                {"_id": bot_id}, current_config, upsert=True
            )
        else:
            del old_config["_id"]
        if old_config and old_config != current_config:
            db.settings.deployConfig.replace_one(
                {"_id": bot_id}, current_config, upsert=True
            )
        elif config_dict := db.settings.config.find_one({"_id": bot_id}):
            del config_dict["_id"]
            for key, value in config_dict.items():
                environ[key] = str(value)
        if pf_dict := db.settings.files.find_one({"_id": bot_id}):
            del pf_dict["_id"]
            for key, value in pf_dict.items():
                if value:
                    file_ = key.replace("__", ".")
                    LOGGER.info("%s has been imported from database.", file_)
                    with open(file_, "wb+") as f:
                        f.write(value)
                    if file_ == "cfg.zip":
                        srun(["rm", "-rf", "/JDownloader/cfg"])
                        srun(["7z", "x", "cfg.zip", "-o/JDownloader"])
                        osremove("cfg.zip")
        if a2c_options := db.settings.aria2c.find_one({"_id": bot_id}):
            del a2c_options["_id"]
            aria2_options = a2c_options
            LOGGER.info("Aria2c settings imported from database.")
        if qbit_opt := db.settings.qbittorrent.find_one({"_id": bot_id}):
            del qbit_opt["_id"]
            qbit_options = qbit_opt
            LOGGER.info("QBittorrent settings imported from database.")
        conn.close()
        BOT_TOKEN = environ.get("BOT_TOKEN", "")
        bot_id = BOT_TOKEN.split(":", 1)[0]
        if DATABASE_URL := environ.get("DATABASE_URL", ""):
            if not DATABASE_URL.startswith("mongodb"):
                try:
                    DATABASE_URL = b64decode(
                        resub("ini|adalah|pesan|yang|sangat|rahasia", "", DATABASE_URL)
                    ).decode("utf-8")
                except Exception:
                    pass
    except Exception as e:
        LOGGER.error("Database ERROR: %s", e)
else:
    config_dict = {}

if OWNER_ID := environ.get("OWNER_ID"):
    try:
        OWNER_ID = int(OWNER_ID)
    except ValueError:
        LOGGER.error("OWNER_ID must be an integer. Exiting now")
        exit(1)
else:
    LOGGER.error("OWNER_ID variable is missing! Exiting now")
    exit(1)

if TELEGRAM_API := environ.get("TELEGRAM_API", "24324274"):
    TELEGRAM_API = int(TELEGRAM_API)
else:
    LOGGER.error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)

if not (
    TELEGRAM_HASH := environ.get("TELEGRAM_HASH", "9702205c640fbca462e5e583298cce74")
):
    LOGGER.error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)

DOWNLOAD_DIR = environ.get("DOWNLOAD_DIR", "/usr/src/app/downloads/")
if not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR += "/"

GDRIVE_ID = environ.get("GDRIVE_ID", "0AOIjN1u1lhaiUk9PVA")
CLOUD_LINK_FILTERS = environ.get("CLOUD_LINK_FILTERS", "mypikpak.com")
RCLONE_PATH = environ.get("RCLONE_PATH", "MAIN:DL")
RCLONE_FLAGS = environ.get("RCLONE_FLAGS", "")

DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "rc")
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
    fx = EXTENSION_FILTER.split()
    for x in fx:
        x = x.lstrip(".")
        GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

TORRENT_TIMEOUT = environ.get("TORRENT_TIMEOUT", "")
TORRENT_TIMEOUT = int(TORRENT_TIMEOUT) if TORRENT_TIMEOUT else ""

QUEUE_ALL = environ.get("QUEUE_ALL", "")
QUEUE_ALL = int(QUEUE_ALL) if QUEUE_ALL else ""

QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "5")
QUEUE_DOWNLOAD = int(QUEUE_DOWNLOAD) if QUEUE_DOWNLOAD else ""

QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
QUEUE_UPLOAD = int(QUEUE_UPLOAD) if QUEUE_UPLOAD else ""

ARGO_TOKEN = environ.get("ARGO_TOKEN", "")
PING_URL = environ.get("PING_URL", "")
ENABLE_STREAM_LINK = environ.get("ENABLE_STREAM_LINK", "False").lower() == "true"
STREAM_BASE_URL = environ.get("STREAM_BASE_URL", "").rstrip("/")
STREAM_PORT = environ.get("STREAM_PORT", "")
QUEUE_COMPLETE = environ.get("QUEUE_COMPLETE", "True").lower() == "true"
DISABLE_MIRROR_LEECH = environ.get("DISABLE_MIRROR_LEECH", "")
INDEX_URL = environ.get("INDEX_URL", "").rstrip("/")
INCOMPLETE_TASK_NOTIFIER = (
    environ.get("INCOMPLETE_TASK_NOTIFIER", "False").lower() == "true"
)
INCOMPLETE_AUTO_RESUME = environ.get("INCOMPLETE_AUTO_RESUME", "True").lower() == "true"
USE_SERVICE_ACCOUNTS = environ.get("USE_SERVICE_ACCOUNTS", "False").lower() == "true"
CMD_SUFFIX = environ.get("CMD_SUFFIX", "")
DATABASE_URL = environ.get("DATABASE_URL", "")
AUTO_THUMBNAIL = environ.get("AUTO_THUMBNAIL", "True").lower()
if AUTO_THUMBNAIL == "true":
    AUTO_THUMBNAIL = "poster"
elif AUTO_THUMBNAIL == "false":
    AUTO_THUMBNAIL = "disabled"
HD_THUMBNAIL = environ.get("HD_THUMBNAIL", "False").lower() == "true"
PREMIUM_MODE = environ.get("PREMIUM_MODE", "False").lower() == "true"
SESSION_TIMEOUT = int(environ.get("SESSION_TIMEOUT", 0))
DAILY_MODE = environ.get("DAILY_MODE", "False").lower() == "true"
MEDIA_GROUP = environ.get("MEDIA_GROUP", "False").lower() == "true"
STOP_DUPLICATE = environ.get("STOP_DUPLICATE", "True").lower() == "true"
IS_TEAM_DRIVE = environ.get("IS_TEAM_DRIVE", "True").lower() == "true"
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
STATUS_UPDATE_INTERVAL = int(environ.get("STATUS_UPDATE_INTERVAL", 5))
YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
DAILY_LIMIT_SIZE = int(environ.get("DAILY_LIMIT_SIZE", 50))
COMPRESS_BANNER = environ.get("COMPRESS_BANNER", "Re-Encoded by ZxZone")
LIB264_PRESET = environ.get("LIB264_PRESET", "superfast")
LIB265_PRESET = environ.get("LIB265_PRESET", "faster")
HARDSUB_FONT_SIZE = environ.get("HARDSUB_FONT_SIZE", "20")
HARDSUB_FONT_NAME = environ.get("HARDSUB_FONT_NAME", "ZxZone")
VIDTOOLS_FAST_MODE = environ.get("VIDTOOLS_FAST_MODE", "False").lower() == "true"
DISABLE_VIDTOOLS = environ.get("DISABLE_VIDTOOLS", "None")
DISABLE_MULTI_VIDTOOLS = environ.get("DISABLE_MULTI_VIDTOOLS", "None")
START_MESSAGE = environ.get("START_MESSAGE", "")
# ======================================================================


# ============================= RCLONE =================================
ENABLE_FASTDL = environ.get("ENABLE_FASTDL", "False").lower() == "true"
RCLONE_SERVE_URL = environ.get("RCLONE_SERVE_URL", "").rstrip("/")
RCLONE_SERVE_PORT = environ.get("RCLONE_SERVE_PORT", "")
RCLONE_SERVE_USER = environ.get("RCLONE_SERVE_USER", "")
RCLONE_SERVE_PASS = environ.get("RCLONE_SERVE_PASS", "")
RCLONE_TFSIMULATION = int(environ.get("RCLONE_TFSIMULATION", "8"))
# ======================================================================


# ============================== LOGS ==================================
ONCOMPLETE_LEECH_LOG = environ.get("ONCOMPLETE_LEECH_LOG", "True").lower() == "true"
LEECH_LOG = environ.get("LEECH_LOG", "")
if LEECH_LOG:
    if LEECH_LOG.isdigit() or LEECH_LOG.startswith("-"):
        LEECH_LOG = int(LEECH_LOG)
else:
    ENABLE_STREAM_LINK = False

MIRROR_LOG = environ.get("MIRROR_LOG", "")
MIRROR_LOG = (
    int(MIRROR_LOG)
    if MIRROR_LOG.isdigit() or MIRROR_LOG.startswith("-")
    else MIRROR_LOG
)

OTHER_LOG = environ.get("OTHER_LOG", "")
OTHER_LOG = (
    int(OTHER_LOG) if OTHER_LOG.isdigit() or OTHER_LOG.startswith("-") else OTHER_LOG
)

LINK_LOG = environ.get("LINK_LOG", "")
LINK_LOG = int(LINK_LOG) if LINK_LOG.isdigit() or LINK_LOG.startswith("-") else LINK_LOG
# ======================================================================


# ============================= LIMITS =================================
EQUAL_SPLITS = environ.get("EQUAL_SPLITS", "False").lower() == "true"

CLONE_LIMIT = ""

LEECH_LIMIT = environ.get("LEECH_LIMIT", "")
LEECH_LIMIT = float(LEECH_LIMIT) if LEECH_LIMIT else ""

LEECH_SPLIT_SIZE = environ.get("LEECH_SPLIT_SIZE", "")
LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE) if LEECH_SPLIT_SIZE else ""

MEGA_LIMIT = environ.get("MEGA_LIMIT", "")
MEGA_LIMIT = float(MEGA_LIMIT) if MEGA_LIMIT else ""

NONPREMIUM_LIMIT = environ.get("NONPREMIUM_LIMIT", "5")
NONPREMIUM_LIMIT = float(NONPREMIUM_LIMIT) if NONPREMIUM_LIMIT else ""

STATUS_LIMIT = environ.get("STATUS_LIMIT", "")
STATUS_LIMIT = int(STATUS_LIMIT) if STATUS_LIMIT else 5

TORRENT_DIRECT_LIMIT = environ.get("TORRENT_DIRECT_LIMIT", "")
TORRENT_DIRECT_LIMIT = float(TORRENT_DIRECT_LIMIT) if TORRENT_DIRECT_LIMIT else ""

TOTAL_TASKS_LIMIT = environ.get("TOTAL_TASKS_LIMIT", "")
TOTAL_TASKS_LIMIT = int(TOTAL_TASKS_LIMIT) if TOTAL_TASKS_LIMIT else ""

MEGA_EMAIL = environ.get("MEGA_EMAIL", "")
MEGA_PASSWORD = environ.get("MEGA_PASSWORD", "")
if len(MEGA_EMAIL) == 0 or len(MEGA_PASSWORD) == 0:
    log_warning("MEGA Credentials not provided!")
    MEGA_EMAIL = ""
    MEGA_PASSWORD = ""

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
if GOFILE:
    LOGGER.info("GoFile feature has been enabled!")
# ======================================================================


# ============================= FORCE =================================
# Auto Mute
FORCE_SHORTEN = environ.get("FORCE_SHORTEN", "False").lower() == "true"
AUTO_MUTE = environ.get("AUTO_MUTE", "False").lower() == "true"

mute_id = environ.get("MUTE_CHAT_ID", "").strip()
MUTE_CHAT_ID = int(mute_id) if mute_id.replace("-", "").isdigit() else -1004319932089

AUTO_MUTE_DURATION = int(environ.get("AUTO_MUTE_DURATION", "30") or 30)

# Username
FUSERNAME = environ.get("FUSERNAME", "False").lower() == "true"

# Subscribe
FSUB = environ.get("FSUB", "False").lower() == "true"

fsub_id = environ.get("FSUB_CHANNEL_ID", "").strip()
FSUB_CHANNEL_ID = int(fsub_id) if fsub_id.replace("-", "").isdigit() else -1004319932089

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
# SharerPW
SHARERPW_LARAVEL_SESSION = environ.get("SHARERPW_LARAVEL_SESSION", "")
SHARERPW_XSRF_TOKEN = environ.get("SHARERPW_XSRF_TOKEN", "")
# ======================================================================


# =========================== UPSTREAM =================================
UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "main")
UPDATE_EVERYTHING = environ.get("UPDATE_EVERYTHING", "False").lower() == "true"
# ======================================================================

# ============================= BOT PM =================================
BOT_PM = environ.get("BOT_PM", "True").lower() == "true"
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


# =========================== QBITTORRENT ==============================
BASE_URL_PORT = environ.get("BASE_URL_PORT", "")
BASE_URL_PORT = 80 if len(BASE_URL_PORT) == 0 else int(BASE_URL_PORT)

BASE_URL = environ.get("BASE_URL", "").rstrip("/")
if len(BASE_URL) == 0:
    BASE_URL = ""

PORT = environ.get("PORT", "")
PORT = 80 if len(PORT) == 0 else int(PORT)


TORRENT_PORT = environ.get("TORRENT_PORT", "5000")
WEB_PINCODE = environ.get("WEB_PINCODE", "False").lower() == "true"
# ======================================================================


# =============================== RSS ==================================
RSS_CHAT = environ.get("RSS_CHAT", "")
RSS_CHAT = int(RSS_CHAT) if RSS_CHAT.isdigit() or RSS_CHAT.startswith("-") else RSS_CHAT

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

IS_PREMIUM = None

config_dict = {
    "BOT_TOKEN": BOT_TOKEN,
    "BASE_URL": BASE_URL,
    "BASE_URL_PORT": BASE_URL_PORT,
    "TELEGRAM_API": TELEGRAM_API,
    "TELEGRAM_HASH": TELEGRAM_HASH,
    "OWNER_ID": OWNER_ID,
    "DATABASE_URL": DATABASE_URL,
    "DOWNLOAD_DIR": DOWNLOAD_DIR,
    "GDRIVE_ID": GDRIVE_ID,
    "CLOUD_LINK_FILTERS": CLOUD_LINK_FILTERS,
    "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
    # OPTIONALS
    "ARGO_TOKEN": ARGO_TOKEN,
    "PING_URL": PING_URL,
    "TORRENT_PORT": TORRENT_PORT,
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
    "MEGA_EMAIL": MEGA_EMAIL,
    "MEGA_PASSWORD": MEGA_PASSWORD,
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
    "SESSION_TIMEOUT": SESSION_TIMEOUT,
    "DAILY_MODE": DAILY_MODE,
    "MEDIA_GROUP": MEDIA_GROUP,
    "QUEUE_ALL": QUEUE_ALL,
    "QUEUE_DOWNLOAD": QUEUE_DOWNLOAD,
    "QUEUE_UPLOAD": QUEUE_UPLOAD,
    "QUEUE_COMPLETE": QUEUE_COMPLETE,
    # RCLONE
    "ENABLE_FASTDL": ENABLE_FASTDL,
    "RCLONE_FLAGS": RCLONE_FLAGS,
    "RCLONE_PATH": RCLONE_PATH,
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
    "STICKER_DELETE_DURATION": STICKER_DELETE_DURATION,
    "STICKERID_COUNT": STICKERID_COUNT,
    "STICKERID_ERROR": STICKERID_ERROR,
    "STICKERID_LEECH": STICKERID_LEECH,
    "STICKERID_MIRROR": STICKERID_MIRROR,
   
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

if GDRIVE_ID:
    DRIVES_NAMES.append("Main")
    DRIVES_IDS.append(GDRIVE_ID)
    INDEX_URLS.append(INDEX_URL)

if ospath.exists("list_drives.txt"):
    with open("list_drives.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVES_IDS.append(temp[1])
            DRIVES_NAMES.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                INDEX_URLS.append(temp[2])
            else:
                INDEX_URLS.append("")

if ospath.exists("shorteners.txt"):
    with open("shorteners.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(temp) == 2:
                SHORTENERES.append(temp[0])
                SHORTENER_APIS.append(temp[1])


if not config_dict["ARGO_TOKEN"]:
    config_dict["TORRENT_PORT"] = PORT

port_value = environ.get("PORT")
PORT = int(port_value) if port_value else PORT
if not 1 <= PORT <= 65535:
    raise ValueError("PORT must be between 1 and 65535")
Popen(
    [
        "gunicorn",
        "web.wserver:app",
        "--bind",
        f"0.0.0.0:{PORT}",
        "--worker-class",
        "gevent",
    ]
)

srun([QBIT_NAME, "-d", f"--profile={getcwd()}"], check=True)
if not ospath.exists(".netrc"):
    with open(".netrc", "w"):
        pass
chmod(".netrc", 0o600)
copyfile(".netrc", "/root/.netrc")
tracker_sources = (
    "https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/all.txt",
    "https://ngosang.github.io/trackerslist/trackers_all_http.txt",
    "https://newtrackon.com/api/all",
    "https://raw.githubusercontent.com/hezhijie0327/Trackerslist/main/trackerslist_tracker.txt",
)
trackers = []
for tracker_source in tracker_sources:
    try:
        response = rget(tracker_source, timeout=15)
        response.raise_for_status()
        trackers.extend(
            line.strip()
            for line in response.text.splitlines()
            if line.strip()
            and line.strip().startswith(
                ("http://", "https://", "udp://", "ws://", "wss://")
            )
            and not any(char in line for char in "[]\r\n")
        )
    except Exception as e:
        LOGGER.warning("Unable to fetch tracker list %s: %s", tracker_source, e)
trackers = ",".join(trackers)
with open("a2c.conf", "r+") as a:
    lines = [
        line
        for line in a.read().splitlines()
        if not line.startswith(("bt-stop-timeout=", "bt-tracker="))
    ]
    if TORRENT_TIMEOUT:
        lines.append(f"bt-stop-timeout={TORRENT_TIMEOUT}")
    lines.append(f"bt-tracker=[{trackers}]")
    a.seek(0)
    a.write("\n".join(lines) + "\n")
    a.truncate()
srun([ARIA_NAME, f"--conf-path={ospath.join(getcwd(), 'a2c.conf')}"], check=True)
alive = Popen(["python3", "alive.py"])
sleep(0.5)
if ospath.exists("accounts.zip"):
    if ospath.exists("accounts"):
        srun(["rm", "-rf", "accounts"], check=True)
    try:
        with ZipFile("accounts.zip") as archive:
            accounts_root = ospath.realpath("accounts")
            for member in archive.infolist():
                member_name = member.filename
                if not (
                    member_name.startswith("accounts/")
                    and member_name.endswith(".json")
                ):
                    continue
                member_path = ospath.realpath(ospath.join(".", member_name))
                if ospath.commonpath((accounts_root, member_path)) != accounts_root:
                    LOGGER.warning("Skipping unsafe archive member: %s", member_name)
                    continue
                archive.extract(member, ".")
        for dirpath, dirnames, filenames in walk("accounts"):
            chmod(dirpath, 0o700)
            for filename in filenames:
                chmod(ospath.join(dirpath, filename), 0o600)
    except (BadZipFile, OSError) as e:
        LOGGER.error("Failed to import accounts.zip: %s", e)
    osremove("accounts.zip")
if not ospath.exists("accounts"):
    config_dict["USE_SERVICE_ACCOUNTS"] = False


def get_client():
    return qbClient(
        host="localhost",
        port=8090,
        VERIFY_WEBUI_CERTIFICATE=False,
        REQUESTS_ARGS={"timeout": (30, 60)},
    )


aria2c_global = [
    "bt-max-open-files",
    "download-result",
    "keep-unfinished-download-result",
    "log",
    "log-level",
    "max-concurrent-downloads",
    "max-download-result",
    "max-overall-download-limit",
    "save-session",
    "max-overall-upload-limit",
    "optimize-concurrent-downloads",
    "save-cookies",
    "server-stat-of",
]

qb_client = get_client()
if not qbit_options:
    qbit_options = dict(qb_client.app_preferences())
    del qbit_options["listen_port"]
    for k in list(qbit_options.keys()):
        if k.startswith("rss"):
            del qbit_options[k]
else:
    qb_opt = {**qbit_options}
    for k, v in list(qb_opt.items()):
        if v in ["", "*"]:
            del qb_opt[k]
    qb_client.app_set_preferences(qb_opt)

LOGGER.info("Creating client Pyrofork V%s...", __version__)
kwargs = {"workers": 1000, "parse_mode": ParseMode.HTML}
if int(__version__.replace(".", "")[:3]) > 221:
    kwargs.update({"max_concurrent_transmissions": 1000})
bot: tgClient = tgClient(
    "bot", TELEGRAM_API, TELEGRAM_HASH, bot_token=BOT_TOKEN, **kwargs
)


async def _start_bot():
    await bot.start()


bot_loop.run_until_complete(_start_bot())
bot_name = bot.me.username
scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)

if not aria2_options:
    aria2_options = aria2.client.get_global_option()
else:
    a2c_glo = {op: aria2_options[op] for op in aria2c_global if op in aria2_options}
    aria2.set_global_options(a2c_glo)
