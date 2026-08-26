import os
import magic
import hashlib
import asyncio
from typing import Dict, Optional
from bot.helpers.utils import Utils

class FileDetective:
    """Intelligent file analysis and detection system"""
    
    def __init__(self):
        self.file_signatures = {
            # Magic bytes for file types
            'pdf': [b'%PDF'],
            'zip': [b'PK\x03\x04'],
            'rar': [b'Rar!'],
            '7z': [b'7z\xbc\xaf\x27\x1c'],
            'mp4': [b'\x00\x00\x00\x18ftypmp4'],
            'mkv': [b'\x1aE\xdf\xa3'],
            'mp3': [b'ID3'],
            'jpg': [b'\xff\xd8\xff'],
            'png': [b'\x89PNG'],
            'gif': [b'GIF8'],
            'exe': [b'MZ'],
            'apk': [b'PK\x03\x04'],
        }
        
    async def detect_file_type(self, file_path: str) -> Dict:
        """Detect actual file type using magic bytes"""
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Read first 1024 bytes
            with open(file_path, 'rb') as f:
                header = f.read(1024)
                
            # Check magic bytes
            detected_type = 'unknown'
            for file_type, signatures in self.file_signatures.items():
                for signature in signatures:
                    if header.startswith(signature):
                        detected_type = file_type
                        break
                if detected_type != 'unknown':
                    break
                    
            # Try python-magic if available
            try:
                mime_type = magic.from_file(file_path, mime=True)
                description = magic.from_file(file_path)
            except:
                mime_type = 'application/octet-stream'
                description = 'Unknown file'
                
            # Calculate hashes
            md5_hash = await self.calculate_hash(file_path, 'md5')
            sha256_hash = await self.calculate_hash(file_path, 'sha256')
            
            return {
                'file_type': detected_type,
                'mime_type': mime_type,
                'description': description,
                'size': file_size,
                'md5': md5_hash,
                'sha256': sha256_hash,
                'extension': os.path.splitext(file_path)[1].lower(),
                'is_valid': detected_type != 'unknown'
            }
            
        except Exception as e:
            return {'error': str(e)}
            
    async def calculate_hash(self, file_path: str, algo: str = 'md5') -> str:
        """Calculate file hash"""
        try:
            if algo == 'md5':
                hash_obj = hashlib.md5()
            elif algo == 'sha256':
                hash_obj = hashlib.sha256()
            else:
                return ''
                
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
                    
            return hash_obj.hexdigest()
            
        except:
            return ''
            
    async def verify_integrity(self, file_path: str, expected_hash: str = None) -> bool:
        """Verify file integrity"""
        if not expected_hash:
            return True
            
        actual_hash = await self.calculate_hash(file_path, 'md5')
        return actual_hash.lower() == expected_hash.lower()
        
    async def analyze_video_quality(self, file_path: str) -> Dict:
        """Analyze video quality"""
        try:
            import subprocess
            command = f"ffprobe -v quiet -print_format json -show_streams '{file_path}'"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                for stream in data.get('streams', []):
                    if stream['codec_type'] == 'video':
                        width = stream.get('width', 0)
                        height = stream.get('height', 0)
                        
                        # Determine quality
                        if height >= 2160:
                            quality = '4K Ultra HD'
                        elif height >= 1080:
                            quality = 'Full HD'
                        elif height >= 720:
                            quality = 'HD'
                        elif height >= 480:
                            quality = 'SD'
                        else:
                            quality = 'Low'
                            
                        return {
                            'width': width,
                            'height': height,
                            'quality': quality,
                            'codec': stream.get('codec_name'),
                            'bitrate': stream.get('bit_rate')
                        }
                        
        except:
            pass
        return {}
        
    async def check_file_health(self, file_path: str) -> Dict:
        """Check file health"""
        try:
            # Get file info
            info = await self.detect_file_type(file_path)
            
            # Check if file is valid
            health_score = 100
            issues = []
            
            if not info.get('is_valid', False):
                health_score -= 50
                issues.append('Unknown file type')
                
            if info.get('size', 0) == 0:
                health_score -= 100
                issues.append('Empty file')
                
            # Check for truncation
            if info.get('file_type') in ['zip', 'rar', '7z']:
                try:
                    import zipfile
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        if zf.testzip() is not None:
                            health_score -= 30
                            issues.append('Corrupted archive')
                except:
                    health_score -= 50
                    issues.append('Invalid archive')
                    
            return {
                'health_score': max(0, health_score),
                'is_healthy': health_score >= 70,
                'issues': issues,
                'file_info': info
            }
            
        except Exception as e:
            return {'error': str(e), 'health_score': 0}

# Create instance
file_detective = FileDetective()
