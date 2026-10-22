import subprocess
from bot.core.config import Config

def start_ytdlp_download(url):
    """yt-dlp ব্যবহার করে ভিডিও ডাউনলোড ইঞ্জিন"""
    cmd = ["yt-dlp", "-P", Config.DOWNLOAD_DIR, url]
    return subprocess.Popen(cmd)
