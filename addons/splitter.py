import os
import asyncio
from typing import Dict, List
from bot.config import Config

class FileSplitter:
    """Advanced file splitter"""
    
    def __init__(self):
        self.split_dir = os.path.join(Config.DOWNLOAD_DIR, 'split')
        os.makedirs(self.split_dir, exist_ok=True)
        
    async def split_file(self, file_path: str, split_size: int = None) -> Dict:
        """Split file into parts"""
        try:
            file_size = os.path.getsize(file_path)
            
            if not split_size:
                # Auto detect split size
                if 'DYNO' in os.environ:
                    split_size = 500 * 1024 * 1024  # 500MB for Heroku
                else:
                    split_size = 1900 * 1024 * 1024  # 1.9GB for VPS
                    
            # Calculate parts
            num_parts = (file_size + split_size - 1) // split_size
            
            parts = []
            with open(file_path, 'rb') as f:
                for i in range(num_parts):
                    part_path = os.path.join(self.split_dir, f"{os.path.basename(file_path)}.part{i+1:03d}")
                    
                    with open(part_path, 'wb') as part_file:
                        remaining = min(split_size, file_size - (i * split_size))
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
                'num_parts': num_parts,
                'split_size': split_size
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    async def merge_files(self, parts: List[str], output_path: str) -> Dict:
        """Merge split files"""
        try:
            with open(output_path, 'wb') as outfile:
                for part_path in parts:
                    with open(part_path, 'rb') as infile:
                        while True:
                            chunk = infile.read(1024 * 1024)
                            if not chunk:
                                break
                            outfile.write(chunk)
                            
            return {
                'success': True,
                'file': output_path,
                'size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
