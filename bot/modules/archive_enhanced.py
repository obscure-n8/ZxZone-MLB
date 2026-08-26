import os
import asyncio
import zipfile
import tarfile
import rarfile
import py7zr
import shutil
from typing import Dict, List, Optional
from bot.config import Config

class AdvancedArchive:
    """Advanced archive system"""
    
    def __init__(self):
        self.archive_dir = os.path.join(Config.DOWNLOAD_DIR, 'archive')
        os.makedirs(self.archive_dir, exist_ok=True)
        
    async def create_archive(
        self,
        files: List[str],
        format: str = 'zip',
        compression: str = 'normal',
        password: str = None
    ) -> Dict:
        """Create archive with advanced options"""
        try:
            archive_name = f"archive_{int(time.time())}"
            
            compression_levels = {
                'fast': zipfile.ZIP_DEFLATED,
                'normal': zipfile.ZIP_DEFLATED,
                'maximum': zipfile.ZIP_BZIP2
            }
            
            if format == 'zip':
                archive_path = os.path.join(self.archive_dir, f"{archive_name}.zip")
                
                with zipfile.ZipFile(archive_path, 'w', compression_levels.get(compression, zipfile.ZIP_DEFLATED)) as zf:
                    if password:
                        zf.setpassword(password.encode())
                    for file_path in files:
                        zf.write(file_path, os.path.basename(file_path))
                        
            elif format == 'tar':
                archive_path = os.path.join(self.archive_dir, f"{archive_name}.tar")
                with tarfile.open(archive_path, 'w') as tf:
                    for file_path in files:
                        tf.add(file_path, arcname=os.path.basename(file_path))
                        
            elif format == '7z':
                archive_path = os.path.join(self.archive_dir, f"{archive_name}.7z")
                with py7zr.SevenZipFile(archive_path, 'w', password=password) as szf:
                    for file_path in files:
                        szf.write(file_path, os.path.basename(file_path))
                        
            elif format == 'rar':
                archive_path = os.path.join(self.archive_dir, f"{archive_name}.rar")
                # RAR creation requires external tool
                command = f"rar a '{archive_path}' {' '.join(files)}"
                process = await asyncio.create_subprocess_shell(command)
                await process.wait()
                
            if os.path.exists(archive_path):
                return {
                    'success': True,
                    'archive': archive_path,
                    'size': os.path.getsize(archive_path),
                    'format': format
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def extract_archive(
        self,
        archive_path: str,
        extract_dir: str = None,
        password: str = None
    ) -> Dict:
        """Extract archive with password support"""
        try:
            if not extract_dir:
                extract_dir = os.path.join(self.archive_dir, 'extracted')
                
            os.makedirs(extract_dir, exist_ok=True)
            
            extension = os.path.splitext(archive_path)[1].lower()
            
            if extension == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    if password:
                        zf.setpassword(password.encode())
                    zf.extractall(extract_dir)
                    
            elif extension == '.tar':
                with tarfile.open(archive_path, 'r') as tf:
                    tf.extractall(extract_dir)
                    
            elif extension == '.7z':
                with py7zr.SevenZipFile(archive_path, 'r', password=password) as szf:
                    szf.extractall(extract_dir)
                    
            elif extension == '.rar':
                with rarfile.RarFile(archive_path, 'r') as rf:
                    if password:
                        rf.setpassword(password)
                    rf.extractall(extract_dir)
                    
            # Get extracted files
            files = []
            for root, dirs, filenames in os.walk(extract_dir):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
                    
            return {
                'success': True,
                'files': files,
                'extract_dir': extract_dir,
                'file_count': len(files)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def split_archive(
        self,
        file_path: str,
        split_size: int = 500 * 1024 * 1024  # 500MB default
    ) -> Dict:
        """Split archive into multiple parts"""
        try:
            parts = []
            part_num = 1
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(split_size)
                    if not chunk:
                        break
                        
                    part_path = f"{file_path}.part{part_num:03d}"
                    with open(part_path, 'wb') as part_file:
                        part_file.write(chunk)
                        
                    parts.append(part_path)
                    part_num += 1
                    
            return {
                'success': True,
                'parts': parts,
                'part_count': len(parts),
                'split_size': split_size
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def verify_archive(self, archive_path: str) -> Dict:
        """Verify archive integrity"""
        try:
            extension = os.path.splitext(archive_path)[1].lower()
            
            if extension == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    bad_file = zf.testzip()
                    if bad_file:
                        return {'success': False, 'error': f'Corrupted: {bad_file}'}
                    return {'success': True, 'files': len(zf.namelist())}
                    
            elif extension == '.rar':
                with rarfile.RarFile(archive_path, 'r') as rf:
                    rf.testrar()
                    return {'success': True, 'files': len(rf.namelist())}
                    
            elif extension == '.7z':
                with py7zr.SevenZipFile(archive_path, 'r') as szf:
                    szf.testzip()
                    return {'success': True}
                    
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def repair_archive(self, archive_path: str) -> Dict:
        """Attempt to repair corrupted archive"""
        try:
            extension = os.path.splitext(archive_path)[1].lower()
            
            if extension == '.zip':
                # Use zip -F for repair
                command = f"zip -F '{archive_path}' --out '{archive_path}.repaired'"
                process = await asyncio.create_subprocess_shell(command)
                await process.wait()
                
                if os.path.exists(f"{archive_path}.repaired"):
                    return {'success': True, 'repaired': f"{archive_path}.repaired"}
                    
            return {'success': False, 'error': 'Cannot repair this format'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Create instance
advanced_archive = AdvancedArchive()
