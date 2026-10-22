import subprocess
from bot.core.config import Config

def start_qbit_download(magnet_or_torrent):
    """qBittorrent-nox এর মাধ্যমে ব্যাকগ্রাউন্ডে টোরেন্ট ডাউনলোড"""
    cmd = ["qbittorrent-nox", f"--save-path={Config.DOWNLOAD_DIR}", magnet_or_torrent]
    return subprocess.Popen(cmd)
