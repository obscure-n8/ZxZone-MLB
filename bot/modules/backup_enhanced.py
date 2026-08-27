import os
import time
import json
import shutil
import asyncio
from typing import Dict, Optional
from datetime import datetime
from bot.config import Config

class EnhancedBackup:
    """Enhanced backup system"""
    
    def __init__(self):
        self.backup_dir = os.path.join(Config.BASE_DIR, 'data', 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        self.max_backups = 10
        
    async def create_full_backup(self) -> Dict:
        """Create full backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup config
            await self.backup_config(backup_path)
            
            # Backup database
            await self.backup_database(backup_path)
            
            # Create archive
            archive_path = f"{backup_path}.zip"
            shutil.make_archive(backup_path, 'zip', backup_path)
            
            # Clean up temp
            shutil.rmtree(backup_path)
            
            # Clean old backups
            await self.cleanup_old_backups()
            
            return {
                'success': True,
                'backup': archive_path,
                'size': os.path.getsize(archive_path)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def backup_config(self, backup_path: str):
        """Backup config files"""
        config_files = [
            '.env',
            'config/rclone.conf',
            'config/cookies.txt',
            'config/token.pickle'
        ]
        
        for file_path in config_files:
            full_path = os.path.join(Config.BASE_DIR, file_path)
            if os.path.exists(full_path):
                dest_path = os.path.join(backup_path, file_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(full_path, dest_path)
                
    async def backup_database(self, backup_path: str):
        """Backup database collections"""
        try:
            from bot.database.db import db
            
            collections = ['users', 'tasks', 'settings', 'logs']
            
            for collection_name in collections:
                collection = db.db[collection_name]
                data = []
                
                async for doc in collection.find():
                    doc['_id'] = str(doc['_id'])
                    data.append(doc)
                    
                file_path = os.path.join(backup_path, f"{collection_name}.json")
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                    
        except:
            pass
            
    async def cleanup_old_backups(self):
        """Clean up old backups"""
        try:
            backups = []
            
            for file in os.listdir(self.backup_dir):
                if file.endswith('.zip'):
                    file_path = os.path.join(self.backup_dir, file)
                    backups.append((file_path, os.path.getmtime(file_path)))
                    
            backups.sort(key=lambda x: x[1], reverse=True)
            
            for backup_path, _ in backups[self.max_backups:]:
                os.remove(backup_path)
                
        except:
            pass
            
    async def list_backups(self) -> list:
        """List all backups"""
        backups = []
        
        for file in os.listdir(self.backup_dir):
            if file.endswith('.zip'):
                file_path = os.path.join(self.backup_dir, file)
                backups.append({
                    'name': file,
                    'size': os.path.getsize(file_path),
                    'created': datetime.fromtimestamp(os.path.getmtime(file_path))
                })
                
        return sorted(backups, key=lambda x: x['created'], reverse=True)

# Create instance
enhanced_backup = EnhancedBackup()
