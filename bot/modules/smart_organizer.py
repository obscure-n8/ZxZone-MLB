import os
import shutil
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from bot.config import Config

class SmartFileOrganizer:
    """Smart file organization system"""
    
    def __init__(self):
        self.organize_rules = {
            'videos': {
                'extensions': ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv'],
                'folder': 'Videos',
                'sub_folders': {
                    'movies': ['movie', 'film', 'bluray', 'webrip'],
                    'series': ['series', 'episode', 'season', 's01', 's02'],
                    'anime': ['anime', 'manga', 'japanese'],
                    'tutorials': ['tutorial', 'course', 'learning']
                }
            },
            'music': {
                'extensions': ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac'],
                'folder': 'Music',
                'sub_folders': {
                    'songs': ['song', 'music', 'audio'],
                    'albums': ['album', 'discography'],
                    'podcasts': ['podcast', 'episode']
                }
            },
            'documents': {
                'extensions': ['.pdf', '.doc', '.docx', '.txt', '.ppt', '.xls'],
                'folder': 'Documents',
                'sub_folders': {
                    'ebooks': ['book', 'ebook', 'novel'],
                    'notes': ['notes', 'study'],
                    'reports': ['report', 'project']
                }
            },
            'images': {
                'extensions': ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'],
                'folder': 'Images',
                'sub_folders': {
                    'wallpapers': ['wallpaper', 'background'],
                    'screenshots': ['screenshot', 'capture'],
                    'photos': ['photo', 'picture', 'image']
                }
            },
            'archives': {
                'extensions': ['.zip', '.rar', '.7z', '.tar', '.gz'],
                'folder': 'Archives',
                'sub_folders': {}
            },
            'software': {
                'extensions': ['.exe', '.msi', '.apk', '.dmg', '.deb'],
                'folder': 'Software',
                'sub_folders': {
                    'windows': ['windows', 'win', 'exe'],
                    'android': ['android', 'apk'],
                    'mac': ['mac', 'dmg']
                }
            }
        }
        
        self.stats = {
            'total_organized': 0,
            'organized_today': 0,
            'last_organize_time': None
        }
        
    async def organize_file(self, file_path: str) -> Dict:
        """Organize single file"""
        try:
            file_name = os.path.basename(file_path)
            extension = os.path.splitext(file_name)[1].lower()
            
            # Find category
            category = self.get_category(extension)
            if not category:
                return {'success': False, 'reason': 'Unknown file type'}
                
            # Find sub-folder
            sub_folder = self.get_sub_folder(file_name, category)
            
            # Create destination
            dest_dir = os.path.join(Config.DOWNLOAD_DIR, category['folder'])
            if sub_folder:
                dest_dir = os.path.join(dest_dir, sub_folder)
                
            os.makedirs(dest_dir, exist_ok=True)
            
            # Move file
            dest_path = os.path.join(dest_dir, file_name)
            
            # Handle duplicate names
            if os.path.exists(dest_path):
                dest_path = self.get_unique_path(dest_path)
                
            shutil.move(file_path, dest_path)
            
            # Update stats
            self.stats['total_organized'] += 1
            self.stats['organized_today'] += 1
            self.stats['last_organize_time'] = datetime.now()
            
            return {
                'success': True,
                'original_path': file_path,
                'new_path': dest_path,
                'category': category['folder'],
                'sub_folder': sub_folder
            }
            
        except Exception as e:
            return {'success': False, 'reason': str(e)}
            
    def get_category(self, extension: str) -> Optional[Dict]:
        """Get category for file extension"""
        for category, rules in self.organize_rules.items():
            if extension in rules['extensions']:
                return rules
        return None
        
    def get_sub_folder(self, file_name: str, category: Dict) -> str:
        """Get sub-folder based on file name"""
        file_name_lower = file_name.lower()
        
        for sub_folder, keywords in category['sub_folders'].items():
            for keyword in keywords:
                if keyword in file_name_lower:
                    return sub_folder.capitalize()
                    
        return ''
        
    def get_unique_path(self, file_path: str) -> str:
        """Get unique path for duplicate files"""
        directory = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        name, extension = os.path.splitext(file_name)
        
        counter = 1
        while os.path.exists(file_path):
            new_name = f"{name}_{counter}{extension}"
            file_path = os.path.join(directory, new_name)
            counter += 1
            
        return file_path
        
    async def organize_directory(self, directory: str) -> Dict:
        """Organize all files in directory"""
        results = {
            'total': 0,
            'organized': 0,
            'failed': 0,
            'skipped': 0,
            'files': []
        }
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    results['total'] += 1
                    
                    # Skip temp files
                    if file.startswith('.'):
                        results['skipped'] += 1
                        continue
                        
                    # Organize file
                    result = await self.organize_file(file_path)
                    
                    if result['success']:
                        results['organized'] += 1
                        results['files'].append(result)
                    else:
                        results['failed'] += 1
                        
        except Exception as e:
            pass
            
        return results
        
    async def get_stats(self) -> Dict:
        """Get organizer statistics"""
        return self.stats
        
    async def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_organized': 0,
            'organized_today': 0,
            'last_organize_time': None
        }

# Create instance
smart_organizer = SmartFileOrganizer()
