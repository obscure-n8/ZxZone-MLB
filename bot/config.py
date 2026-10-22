import os

class Config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    API_ID = int(os.environ.get("API_ID", 12345))
    API_HASH = os.environ.get("API_HASH", "")
    DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/usr/src/app/downloads")
    
   # splitting size (Bytes)
    MAX_FILE_SIZE = 2097152000 # 2GB default
