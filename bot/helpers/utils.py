import os
import re
import time
import string
import random
import asyncio
from typing import Optional, Tuple
from datetime import datetime

class Utils:
    @staticmethod
    def generate_task_id(length: int = 8) -> str:
        """Generate random task ID"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """Clean filename from invalid characters"""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Remove extra spaces
        filename = ' '.join(filename.split())
        # Limit length
        if len(filename) > 150:
            name, ext = os.path.splitext(filename)
            filename = name[:147] + ext
        return filename
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension"""
        return os.path.splitext(filename)[1].lower()
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid"""
        url_pattern = re.compile(
            r'^(?:http|ftp)s?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    @staticmethod
    def is_magnet_link(url: str) -> bool:
        """Check if URL is magnet link"""
        return url.startswith('magnet:')
    
    @staticmethod
    def is_torrent_file(filename: str) -> bool:
        """Check if file is torrent"""
        return filename.lower().endswith('.torrent')
    
    @staticmethod
    def format_time(seconds: int) -> str:
        """Format seconds to human readable time"""
        seconds = int(seconds)
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {secs}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    @staticmethod
    def get_current_time() -> str:
        """Get current time formatted"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    async def run_command(command: str) -> Tuple[int, str, str]:
        """Run shell command and return output"""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode(), stderr.decode()
    
    @staticmethod
    def human_readable_size(size: float) -> str:
        """Convert bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    @staticmethod
    def parse_size(size_str: str) -> int:
        """Parse size string to bytes"""
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        match = re.match(r'(\d+\.?\d*)\s*([A-Za-z]+)', size_str)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            return int(value * units.get(unit, 1))
        return 0
