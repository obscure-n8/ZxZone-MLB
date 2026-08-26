import os
import asyncio
import shutil
from typing import List, Optional
from bot.helpers.utils import Utils

class FileOperations:
    def __init__(self):
        self.temp_dir = "downloads/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
    async def split_file(
        self,
        file_path: str,
        chunk_size: int = 1024 * 1024 * 1024,  # 1GB chunks
        progress_callback=None
    ) -> List[str]:
        """Split large file into smaller parts"""
        try:
            file_size = os.path.getsize(file_path)
            if file_size <= chunk_size:
                return [file_path]
                
            parts = []
            part_num = 1
            downloaded = 0
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                        
                    part_path = f"{file_path}.part{part_num:03d}"
                    with open(part_path, 'wb') as part_file:
                        part_file.write(chunk)
                        
                    parts.append(part_path)
                    downloaded += len(chunk)
                    part_num += 1
                    
                    if progress_callback:
                        await progress_callback(downloaded, file_size)
                        
            return parts
            
        except Exception as e:
            return []
            
    async def merge_files(
        self,
        file_paths: List[str],
        output_path: str,
        progress_callback=None
    ) -> bool:
        """Merge multiple files into one"""
        try:
            total_size = sum(os.path.getsize(f) for f in file_paths)
            merged = 0
            
            with open(output_path, 'wb') as outfile:
                for file_path in file_paths:
                    with open(file_path, 'rb') as infile:
                        while True:
                            chunk = infile.read(1024 * 1024)
                            if not chunk:
                                break
                            outfile.write(chunk)
                            merged += len(chunk)
                            
                            if progress_callback:
                                await progress_callback(merged, total_size)
                                
            return True
            
        except:
            return False
            
    async def convert_video(
        self,
        input_path: str,
        output_format: str = 'mp4',
        quality: str = 'medium',
        progress_callback=None
    ) -> Optional[str]:
        """Convert video to different format"""
        try:
            output_path = f"{os.path.splitext(input_path)[0]}.{output_format}"
            
            # Quality settings
            quality_settings = {
                'low': '-crf 28 -preset fast',
                'medium': '-crf 23 -preset medium',
                'high': '-crf 18 -preset slow'
            }
            
            command = f"ffmpeg -i '{input_path}' {quality_settings.get(quality, quality_settings['medium'])} '{output_path}'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
                
        except:
            pass
        return None
        
    async def extract_audio(
        self,
        video_path: str,
        output_format: str = 'mp3',
        bitrate: str = '192k'
    ) -> Optional[str]:
        """Extract audio from video"""
        try:
            output_path = f"{os.path.splitext(video_path)[0]}.{output_format}"
            
            command = f"ffmpeg -i '{video_path}' -b:a {bitrate} -vn '{output_path}'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
                
        except:
            pass
        return None
        
    async def compress_video(
        self,
        input_path: str,
        target_size: int = 50 * 1024 * 1024,  # 50MB
        progress_callback=None
    ) -> Optional[str]:
        """Compress video to target size"""
        try:
            output_path = f"{os.path.splitext(input_path)[0]}_compressed.mp4"
            
            # Get video duration
            process = await asyncio.create_subprocess_shell(
                f"ffprobe -v quiet -print_format json -show_format '{input_path}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            import json
            data = json.loads(stdout.decode())
            duration = float(data['format']['duration'])
            
            # Calculate bitrate
            target_bitrate = int((target_size * 8) / duration)
            
            command = f"ffmpeg -i '{input_path}' -b:v {target_bitrate} -b:a 128k '{output_path}'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
                
        except:
            pass
        return None
        
    async def add_watermark(
        self,
        video_path: str,
        watermark_text: str,
        position: str = 'bottom-right'
    ) -> Optional[str]:
        """Add watermark to video"""
        try:
            output_path = f"{os.path.splitext(video_path)[0]}_watermarked.mp4"
            
            # Position settings
            positions = {
                'top-left': 'x=10:y=10',
                'top-right': 'x=w-tw-10:y=10',
                'bottom-left': 'x=10:y=h-th-10',
                'bottom-right': 'x=w-tw-10:y=h-th-10',
                'center': 'x=(w-tw)/2:y=(h-th)/2'
            }
            
            pos = positions.get(position, positions['bottom-right'])
            
            command = f"ffmpeg -i '{video_path}' -vf \"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white:{pos}\" '{output_path}'"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
                
        except:
            pass
        return None

# Create instance
file_ops = FileOperations()
