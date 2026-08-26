import os
import asyncio
import shutil
import hashlib
from typing import Dict, List, Optional
from bot.config import Config

class EnhancedFileOps:
    """Enhanced file operations system"""
    
    def __init__(self):
        self.ops_dir = os.path.join(Config.DOWNLOAD_DIR, 'ops')
        os.makedirs(self.ops_dir, exist_ok=True)
        
    async def batch_operations(self, files: List[str], operation: str) -> Dict:
        """Perform batch operations on multiple files"""
        results = []
        
        for file_path in files:
            if operation == 'hash':
                result = await self.get_file_hash(file_path)
            elif operation == 'size':
                result = {'file': file_path, 'size': os.path.getsize(file_path)}
            elif operation == 'type':
                result = await self.detect_file_type(file_path)
            else:
                result = {'file': file_path, 'error': 'Unknown operation'}
                
            results.append(result)
            
        return {
            'success': True,
            'operation': operation,
            'results': results,
            'total': len(results)
        }
        
    async def get_file_hash(self, file_path: str, algo: str = 'md5') -> Dict:
        """Get file hash"""
        try:
            if algo == 'md5':
                hash_obj = hashlib.md5()
            elif algo == 'sha256':
                hash_obj = hashlib.sha256()
            elif algo == 'sha1':
                hash_obj = hashlib.sha1()
            else:
                return {'success': False, 'error': 'Unknown algorithm'}
                
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
                    
            return {
                'success': True,
                'file': file_path,
                'hash': hash_obj.hexdigest(),
                'algorithm': algo
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def detect_file_type(self, file_path: str) -> Dict:
        """Detect actual file type"""
        try:
            import magic
            mime_type = magic.from_file(file_path, mime=True)
            description = magic.from_file(file_path)
            
            return {
                'success': True,
                'file': file_path,
                'mime_type': mime_type,
                'description': description
            }
            
        except:
            # Fallback to extension
            extension = os.path.splitext(file_path)[1].lower()
            return {
                'success': True,
                'file': file_path,
                'extension': extension
            }
            
    async def compress_files(self, files: List[str], output_path: str) -> Dict:
        """Compress multiple files"""
        try:
            import zipfile
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in files:
                    zf.write(file_path, os.path.basename(file_path))
                    
            return {
                'success': True,
                'archive': output_path,
                'size': os.path.getsize(output_path),
                'files_compressed': len(files)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def split_by_parts(self, file_path: str, num_parts: int) -> Dict:
        """Split file into specific number of parts"""
        try:
            file_size = os.path.getsize(file_path)
            part_size = file_size // num_parts
            
            parts = []
            with open(file_path, 'rb') as f:
                for i in range(num_parts):
                    part_path = f"{file_path}.part{i+1:03d}"
                    remaining = part_size if i < num_parts - 1 else file_size - (i * part_size)
                    
                    with open(part_path, 'wb') as part_file:
                        while remaining > 0:
                            chunk = f.read(min(1024 * 1024, remaining))
                            if not chunk:
                                break
                            part_file.write(chunk)
                            remaining -= len(chunk)
                            
                    parts.append(part_path)
                    
            return {
                'success': True,
                'parts': parts,
                'part_count': num_parts,
                'part_size': part_size
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def verify_integrity(self, file_path: str, expected_hash: str, algo: str = 'md5') -> bool:
        """Verify file integrity"""
        result = await self.get_file_hash(file_path, algo)
        
        if result['success']:
            return result['hash'] == expected_hash.lower()
            
        return False
        
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> Dict:
        """Clean up temporary files"""
        try:
            current_time = time.time()
            cleaned = 0
            
            for root, dirs, files in os.walk(Config.DOWNLOAD_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > (max_age_hours * 3600):
                        try:
                            os.remove(file_path)
                            cleaned += 1
                        except:
                            pass
                            
            return {
                'success': True,
                'cleaned': cleaned,
                'max_age_hours': max_age_hours
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Create instance
enhanced_file_ops = EnhancedFileOps()
