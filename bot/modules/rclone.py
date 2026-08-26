import os
import asyncio
from typing import Optional, Callable
from bot.config import Config

class RcloneManager:
    def __init__(self):
        self.config_path = Config.RCLONE_CONFIG
        self.remote = Config.RCLONE_REMOTE
        
    async def check_remote(self) -> bool:
        """Check if rclone remote is configured"""
        if not os.path.exists(self.config_path):
            return False
        if os.path.getsize(self.config_path) == 0:
            return False
        return True
        
    async def list_remotes(self) -> list:
        """List all configured remotes"""
        try:
            process = await asyncio.create_subprocess_shell(
                "rclone listremotes",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return [r.strip() for r in stdout.decode().split('\n') if r.strip()]
        except:
            pass
        return []
        
    async def list_files(self, path: str = "") -> list:
        """List files in remote"""
        try:
            remote_path = f"{self.remote}:{path}" if path else f"{self.remote}:"
            process = await asyncio.create_subprocess_shell(
                f"rclone lsf '{remote_path}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return [f.strip() for f in stdout.decode().split('\n') if f.strip()]
        except:
            pass
        return []
        
    async def upload_file(
        self,
        file_path: str,
        destination: str = "",
        progress_callback: Optional[Callable] = None
    ) -> tuple:
        """Upload file to cloud"""
        try:
            if not await self.check_remote():
                return False, "Rclone not configured!"
                
            dest_path = f"{self.remote}:{destination}" if destination else f"{self.remote}:"
            
            command = f"rclone copy '{file_path}' '{dest_path}' --progress --stats 1s"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor progress
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                    
                line_text = line.decode().strip()
                if '%' in line_text and progress_callback:
                    # Parse progress
                    try:
                        percent_str = line_text.split('%')[0].split(',')[-1].strip()
                        percentage = float(percent_str)
                        await progress_callback(percentage)
                    except:
                        pass
            
            await process.wait()
            
            if process.returncode == 0:
                return True, "Upload successful!"
            else:
                return False, "Upload failed!"
                
        except Exception as e:
            return False, str(e)
            
    async def download_file(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable] = None
    ) -> tuple:
        """Download file from cloud"""
        try:
            if not await self.check_remote():
                return False, "Rclone not configured!"
                
            remote_file = f"{self.remote}:{remote_path}"
            
            command = f"rclone copy '{remote_file}' '{local_path}' --progress --stats 1s"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0:
                return True, "Download successful!"
            else:
                return False, "Download failed!"
                
        except Exception as e:
            return False, str(e)
            
    async def delete_file(self, remote_path: str) -> tuple:
        """Delete file from cloud"""
        try:
            remote_file = f"{self.remote}:{remote_path}"
            process = await asyncio.create_subprocess_shell(
                f"rclone deletefile '{remote_file}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            
            if process.returncode == 0:
                return True, "File deleted!"
            else:
                return False, "Delete failed!"
                
        except Exception as e:
            return False, str(e)
            
    async def mkdir(self, path: str) -> tuple:
        """Create directory in cloud"""
        try:
            remote_path = f"{self.remote}:{path}"
            process = await asyncio.create_subprocess_shell(
                f"rclone mkdir '{remote_path}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            
            if process.returncode == 0:
                return True, "Directory created!"
            else:
                return False, "Failed to create directory!"
                
        except Exception as e:
            return False, str(e)
            
    async def get_file_link(self, remote_path: str) -> str:
        """Get public link for file"""
        try:
            remote_file = f"{self.remote}:{remote_path}"
            process = await asyncio.create_subprocess_shell(
                f"rclone link '{remote_file}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return stdout.decode().strip()
        except:
            pass
        return ""

# Create instance
rclone_manager = RcloneManager()
