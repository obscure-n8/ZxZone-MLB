import os
import time
import shutil
import asyncio
from typing import Optional, Dict
from datetime import datetime
from bot.config import Config

class BackupManager:
    def __init__(self):
        self.backup_dir = os.path.join(Config.BASE_DIR, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.max_backups = 10
        
    async def create_backup(
        self,
        include_database: bool = True,
        include_config: bool = True,
        include_files: bool = False
    ) -> Optional[str]:
        """Create system backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup database
            if include_database:
                await self.backup_database(backup_path)
                
            # Backup config
            if include_config:
                await self.backup_config(backup_path)
                
            # Backup files
            if include_files:
                await self.backup_files(backup_path)
                
            # Create zip
            zip_path = f"{backup_path}.zip"
            shutil.make_archive(backup_path, 'zip', backup_path)
            
            # Remove temp directory
            shutil.rmtree(backup_path)
            
            # Clean old backups
            await self.cleanup_old_backups()
            
            return zip_path
            
        except Exception as e:
            print(f"Backup error: {e}")
            return None
            
    async def backup_database(self, backup_path: str):
        """Backup database"""
        try:
            # MongoDB backup
            import subprocess
            db_path = os.path.join(backup_path, "database")
            os.makedirs(db_path, exist_ok=True)
            
            command = f"mongodump --uri='{Config.DATABASE_URL}' --out='{db_path}'"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            
        except:
            pass
            
    async def backup_config(self, backup_path: str):
        """Backup configuration files"""
        try:
            config_backup = os.path.join(backup_path, "config")
            os.makedirs(config_backup, exist_ok=True)
            
            # Copy .env
            env_file = os.path.join(Config.BASE_DIR, ".env")
            if os.path.exists(env_file):
                shutil.copy2(env_file, config_backup)
                
            # Copy rclone config
            if os.path.exists(Config.RCLONE_CONFIG):
                shutil.copy2(Config.RCLONE_CONFIG, config_backup)
                
            # Copy cookies
            cookies_file = os.path.join(Config.CONFIG_DIR, "cookies.txt")
            if os.path.exists(cookies_file):
                shutil.copy2(cookies_file, config_backup)
                
        except:
            pass
            
    async def backup_files(self, backup_path: str):
        """Backup important files"""
        try:
            files_backup = os.path.join(backup_path, "files")
            os.makedirs(files_backup, exist_ok=True)
            
            # Copy thumbnails
            if os.path.exists(Config.THUMB_DIR):
                shutil.copytree(Config.THUMB_DIR, os.path.join(files_backup, "thumbnails"))
                
        except:
            pass
            
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup"""
        try:
            if not os.path.exists(backup_path):
                return False
                
            # Extract backup
            extract_dir = backup_path.replace('.zip', '')
            shutil.unpack_archive(backup_path, extract_dir)
            
            # Restore database
            db_backup = os.path.join(extract_dir, "database")
            if os.path.exists(db_backup):
                import subprocess
                command = f"mongorestore --uri='{Config.DATABASE_URL}' '{db_backup}'"
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                
            # Restore config
            config_backup = os.path.join(extract_dir, "config")
            if os.path.exists(config_backup):
                # Restore .env
                env_file = os.path.join(config_backup, ".env")
                if os.path.exists(env_file):
                    shutil.copy2(env_file, Config.BASE_DIR)
                    
                # Restore rclone config
                rclone_file = os.path.join(config_backup, os.path.basename(Config.RCLONE_CONFIG))
                if os.path.exists(rclone_file):
                    shutil.copy2(rclone_file, Config.RCLONE_CONFIG)
                    
            # Clean up
            shutil.rmtree(extract_dir)
            
            return True
            
        except Exception as e:
            print(f"Restore error: {e}")
            return False
            
    async def cleanup_old_backups(self):
        """Remove old backups"""
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.endswith('.zip'):
                    file_path = os.path.join(self.backup_dir, file)
                    backups.append((file_path, os.path.getmtime(file_path)))
                    
            # Sort by modification time
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old backups
            for backup_path, _ in backups[self.max_backups:]:
                os.remove(backup_path)
                
        except:
            pass
            
    async def list_backups(self) -> list:
        """List available backups"""
        backups = []
        try:
            for file in os.listdir(self.backup_dir):
                if file.endswith('.zip'):
                    file_path = os.path.join(self.backup_dir, file)
                    backups.append({
                        'name': file,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'created': datetime.fromtimestamp(os.path.getmtime(file_path))
                    })
        except:
            pass
        return backups

# Create instance
backup_manager = BackupManager()
