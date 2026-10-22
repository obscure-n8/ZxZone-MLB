import subprocess
import os
from bot.core.config import Config

def start_aria2_download(url, task_id):
    """Aria2c দিয়ে ব্যাকগ্রাউন্ডে ডাউনলোড শুরু করার মেথড"""
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    cmd = [
        "aria2c",
        "--dir", Config.DOWNLOAD_DIR,
        "--max-connection-per-server=16",
        "--split=16",
        url
    ]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
