import os
import re
import asyncio
from typing import Dict, List, Optional
from bot.config import Config

class AIEnhanced:
    """Enhanced AI features for bot"""
    
    def __init__(self):
        self.file_categories = {
            'movie': ['movie', 'film', 'bluray', 'webrip', 'web-dl', 'hindi', 'english', 'tamil', 'telugu'],
            'series': ['series', 'episode', 'season', 's01', 's02', 'e01', 'e02', 'web series'],
            'anime': ['anime', 'manga', 'japanese', 'cartoon', 'naruto', 'one piece'],
            'music': ['music', 'song', 'album', 'audio', 'mp3', 'flac', 'concerts'],
            'game': ['game', 'pc', 'crack', 'repack', 'fitgirl', 'dodi'],
            'software': ['software', 'app', 'application', 'setup', 'crack', 'patch'],
            'ebook': ['book', 'ebook', 'pdf', 'epub', 'novel', 'magazine'],
            'tutorial': ['tutorial', 'course', 'learning', 'education', 'udemy'],
            'documentary': ['documentary', 'docu', 'bbc', 'national geographic'],
            'sports': ['sports', 'cricket', 'football', 'soccer', 'wwe', 'ufc']
        }
        
        self.quality_detection = {
            '4k': ['2160p', '4k', 'uhd', 'ultra hd'],
            '1080p': ['1080p', 'full hd', 'fhd'],
            '720p': ['720p', 'hd'],
            '480p': ['480p', 'sd'],
            'hdr': ['hdr', 'dolby vision', 'hdr10'],
            'bluray': ['bluray', 'blu-ray', 'bdrip'],
            'webdl': ['web-dl', 'webdl', 'webrip']
        }
        
    async def generate_smart_caption(self, file_name: str, file_size: int) -> str:
        """Generate smart AI caption for file"""
        try:
            clean_name = self.clean_filename(file_name)
            category = await self.detect_category(file_name)
            quality = await self.detect_quality(file_name)
            size_str = self.format_size(file_size)
            
            # Build caption
            caption = f"📁 **{clean_name}**\n\n"
            
            if quality:
                caption += f"🎬 **Quality:** {quality}\n"
                
            if category:
                caption += f"📂 **Category:** {category}\n"
                
            caption += f"💾 **Size:** {size_str}\n"
            caption += f"\n📥 **Download Now!**\n"
            caption += f"\n**Powered By Zonexus Hub** ❞"
            
            return caption
            
        except:
            return f"📁 {file_name}\n\nPowered By Zonexus Hub ❞"
            
    def clean_filename(self, file_name: str) -> str:
        """Clean filename for display"""
        # Remove extension
        name = os.path.splitext(file_name)[0]
        
        # Replace dots and underscores
        name = name.replace('.', ' ').replace('_', ' ')
        
        # Remove quality tags
        for quality, tags in self.quality_detection.items():
            for tag in tags:
                name = re.sub(tag, '', name, flags=re.IGNORECASE)
                
        # Remove year
        name = re.sub(r'\b(19|20)\d{2}\b', '', name)
        
        # Clean up spaces
        name = ' '.join(name.split())
        
        # Truncate
        if len(name) > 80:
            name = name[:77] + '...'
            
        return name.title()
        
    async def detect_category(self, file_name: str) -> str:
        """Detect file category"""
        file_name_lower = file_name.lower()
        
        for category, keywords in self.file_categories.items():
            for keyword in keywords:
                if keyword in file_name_lower:
                    return category.title()
                    
        return ""
        
    async def detect_quality(self, file_name: str) -> str:
        """Detect video quality"""
        file_name_lower = file_name.lower()
        
        for quality, tags in self.quality_detection.items():
            for tag in tags:
                if tag in file_name_lower:
                    return quality.upper()
                    
        return ""
        
    def format_size(self, size: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
        
    async def generate_file_summary(self, file_path: str) -> Dict:
        """Generate file summary"""
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            extension = os.path.splitext(file_name)[1].lower()
            
            summary = {
                'name': file_name,
                'size': file_size,
                'extension': extension,
                'category': await self.detect_category(file_name),
                'quality': await self.detect_quality(file_name),
                'caption': await self.generate_smart_caption(file_name, file_size)
            }
            
            return summary
            
        except:
            return {}

# Create instance
ai_enhanced = AIEnhanced()
