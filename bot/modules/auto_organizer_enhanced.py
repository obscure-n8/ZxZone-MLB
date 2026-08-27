import os
import shutil
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from bot.config import Config

class AutoOrganizerEnhanced:
    """Enhanced auto organizer system"""
    
    def __init__(self):
        self.organize_folders = {
            'Movies': ['.mp4', '.mkv', '.avi', '.mov', '.webm'],
            'Music': ['.mp3', '.m4a', '.wav', '.flac', '.ogg'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.ppt', '.xls'],
            'Images': ['.jpg', '.jpeg', '.png', '.webp', '.gif'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'Software': ['.exe', '.msi', '.apk', '.dmg', '.deb']
        }
        
    async def organize_file(self, file_path: str) -> Dict:
        """Organize single file"""
        try:
            extension = os.path.splitext(file_path)[1].lower()
            
            for folder, extensions in self.organize_folders.items():
                if extension in extensions:
                    dest_dir = os.path.join(Config.DOWNLOAD_DIR, folder)
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    dest_path = os.path.join(dest_dir, os.path.basename(file_path))
                    shutil.move(file_path, dest_path)
                    
                    return {
                        'success': True,
                        'folder': folder,
                        'new_path': dest_path
                    }
                    
            return {'success': False, 'error': 'Unknown file type'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def organize_directory(self, directory: str) -> Dict:
        """Organize entire directory"""
        try:
            organized = 0
            skipped = 0
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    result = await self.organize_file(file_path)
                    
                    if result['success']:
                        organized += 1
                    else:
                        skipped += 1
                        
            return {
                'success': True,
                'organized': organized,
                'skipped': skipped
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def generate_report(self) -> Dict:
        """Generate organization report"""
        try:
            report = {}
            
            for folder in self.organize_folders:
                folder_path = os.path.join(Config.DOWNLOAD_DIR, folder)
                if os.path.exists(folder_path):
                    files = os.listdir(folder_path)
                    total_size = sum(
                        os.path.getsize(os.path.join(folder_path, f))
                        for f in files if os.path.isfile(os.path.join(folder_path, f))
                    )
                    report[folder] = {
                        'files': len(files),
                        'size': total_size
                    }
                    
            return {'success': True, 'report': report}
            
        except:
            return {'success': False}

# Create instance
auto_organizer_enhanced = AutoOrganizerEnhanced()
