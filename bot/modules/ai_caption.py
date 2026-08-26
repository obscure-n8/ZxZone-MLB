import os
import re
from typing import Optional, Dict
from bot.helpers.utils import Utils

class AICaptionGenerator:
    """AI-powered caption generator for files"""
    
    def __init__(self):
        self.caption_templates = {
            'video': [
                "🎬 **{filename}**\n\n📺 Quality: {quality}\n⏱ Duration: {duration}\n💾 Size: {size}\n\n📥 Download now!\n\n#Video #{category}",
                "🎥 {filename}\n\n✨ HD Quality\n📦 {size}\n\n⚡️ Fast Download\n\n#{category} #Premium",
                "🍿 {filename}\n\n🎯 {quality} | {size}\n\n🔥 Best Quality Available\n\n#Entertainment"
            ],
            'audio': [
                "🎵 **{filename}**\n\n🎧 High Quality Audio\n💾 {size}\n\n🔊 Listen Now!\n\n#Music #{category}",
                "🎶 {filename}\n\n✨ Premium Audio\n📦 {size}\n\n#Audio #HQ",
                "🎼 {filename}\n\n🎵 Best Quality\n💾 {size}\n\n#Music #Trending"
            ],
            'document': [
                "📄 **{filename}**\n\n📊 Document Type: {category}\n💾 Size: {size}\n\n✅ Verified\n\n#Document",
                "📚 {filename}\n\n📦 {size}\n\n⚡️ Instant Download\n\n#Files #Premium",
                "📑 {filename}\n\n💾 {size}\n\n✅ Safe & Secure\n\n#Document #Trusted"
            ],
            'archive': [
                "📦 **{filename}**\n\n🗜 Compressed File\n💾 Size: {size}\n\n✅ Extract & Use\n\n#Archive",
                "📦 {filename}\n\n💾 {size}\n\n⚡️ High Speed Download\n\n#Zip #Compressed",
                "🗜 {filename}\n\n📦 {size}\n\n✅ Verified Archive\n\n#Archive #Safe"
            ],
            'image': [
                "🖼 **{filename}**\n\n📸 High Resolution\n💾 {size}\n\n✨ Quality Image\n\n#Image",
                "📷 {filename}\n\n💾 {size}\n\n🔥 Premium Quality\n\n#Photo #HD",
                "🖼 {filename}\n\n✨ {size}\n\n✅ Original Quality\n\n#Image #Premium"
            ]
        }
        
        self.category_keywords = {
            'movie': ['movie', 'film', 'bluray', 'webrip', 'web-dl'],
            'music': ['music', 'song', 'album', 'audio', 'mp3', 'flac'],
            'game': ['game', 'pc', 'crack', 'repack'],
            'software': ['software', 'app', 'application', 'setup', 'crack'],
            'ebook': ['book', 'ebook', 'pdf', 'epub', 'novel'],
            'tutorial': ['tutorial', 'course', 'learning', 'education'],
            'anime': ['anime', 'manga', 'japanese', 'cartoon'],
            'series': ['series', 'episode', 'season', 'web series', 'tv'],
        }
        
    async def generate_caption(
        self,
        file_name: str,
        file_size: int,
        file_type: str = 'document',
        quality: str = 'HD',
        duration: str = ''
    ) -> str:
        """Generate AI caption for file"""
        import random
        
        # Clean filename for display
        clean_name = self.clean_filename_for_caption(file_name)
        
        # Detect category
        category = self.detect_category(file_name)
        
        # Get quality info
        quality_info = self.detect_quality(file_name)
        if quality_info:
            quality = quality_info
        
        # Format size
        size_str = Utils.human_readable_size(file_size)
        
        # Get template
        templates = self.caption_templates.get(file_type, self.caption_templates['document'])
        template = random.choice(templates)
        
        # Format caption
        caption = template.format(
            filename=clean_name,
            quality=quality,
            duration=duration or 'N/A',
            size=size_str,
            category=category or 'General'
        )
        
        return caption
        
    def clean_filename_for_caption(self, file_name: str) -> str:
        """Clean filename for caption display"""
        # Remove extension
        name = os.path.splitext(file_name)[0]
        
        # Replace dots and underscores with spaces
        name = name.replace('.', ' ').replace('_', ' ')
        
        # Remove quality tags
        name = re.sub(r'\b(1080p|720p|2160p|4K|8K|HD|SD)\b', '', name, flags=re.IGNORECASE)
        
        # Remove year
        name = re.sub(r'\b(19|20)\d{2}\b', '', name)
        
        # Clean up extra spaces
        name = ' '.join(name.split())
        
        # Truncate if too long
        if len(name) > 80:
            name = name[:77] + '...'
            
        return name
        
    def detect_category(self, file_name: str) -> str:
        """Detect file category from name"""
        file_name_lower = file_name.lower()
        
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in file_name_lower:
                    return category.capitalize()
                    
        return ''
        
    def detect_quality(self, file_name: str) -> str:
        """Detect quality from filename"""
        file_name_lower = file_name.lower()
        
        if '2160p' in file_name_lower or '4k' in file_name_lower:
            return '4K Ultra HD'
        elif '1080p' in file_name_lower or 'full hd' in file_name_lower:
            return '1080p Full HD'
        elif '720p' in file_name_lower:
            return '720p HD'
        elif '480p' in file_name_lower:
            return '480p SD'
        elif 'bluray' in file_name_lower:
            return 'BluRay'
        elif 'web-dl' in file_name_lower:
            return 'WEB-DL'
        elif 'hdr' in file_name_lower:
            return 'HDR'
            
        return ''
        
    async def get_caption_stats(self) -> Dict:
        """Get caption generation statistics"""
        return {
            'total_templates': sum(len(t) for t in self.caption_templates.values()),
            'categories': len(self.category_keywords),
            'file_types': len(self.caption_templates)
        }

# Create instance
ai_caption = AICaptionGenerator()
