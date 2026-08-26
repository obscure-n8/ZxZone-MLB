import os
import asyncio
import zipfile
import tarfile
from typing import Dict, List
from bot.config import Config

class ArchiveProcessor:
    """Archive file processor"""
    
    def __init__(self):
        self.archive_dir = os.path.join(Config.DOWNLOAD_DIR, 'archive')
        os.makedirs(self.archive_dir, exist_ok=True)
        
    async def create_zip(self, files: List[str], output_name: str = None) -> Dict:
        """Create ZIP archive"""
        try:
            if not output_name:
                output_name = f"archive_{int(time.time())}.zip"
                
            output_path = os.path.join(self.archive_dir, output_name)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in files:
                    zf.write(file_path, os.path.basename(file_path))
                    
            return {
                'success': True,
                'archive': output_path,
                'size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def create_tar(self, files: List[str], output_name: str = None) -> Dict:
        """Create TAR archive"""
        try:
            if not output_name:
                output_name = f"archive_{int(time.time())}.tar"
                
            output_path = os.path.join(self.archive_dir, output_name)
            
            with tarfile.open(output_path, 'w') as tf:
                for file_path in files:
                    tf.add(file_path, arcname=os.path.basename(file_path))
                    
            return {
                'success': True,
                'archive': output_path,
                'size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def extract_archive(self, archive_path: str) -> Dict:
        """Extract archive"""
        try:
            extract_dir = os.path.join(self.archive_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(extract_dir)
            elif archive_path.endswith('.tar'):
                with tarfile.open(archive_path, 'r') as tf:
                    tf.extractall(extract_dir)
                    
            # Get extracted files
            files = []
            for root, dirs, filenames in os.walk(extract_dir):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
                    
            return {
                'success': True,
                'files': files,
                'extract_dir': extract_dir
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
