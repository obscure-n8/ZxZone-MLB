import time
import os
import re
import asyncio
from typing import Dict, Optional, List
from bot.database.db import db

class NSFDetector:
    """NSFW content detection system"""
    
    def __init__(self):
        self.collection = db.nsfw_logs
        self.nsfw_keywords = {
            'explicit': [
                'porn', 'xxx', 'sex', 'nude', 'naked', 'adult', '18+',
                'nsfw', 'hentai', 'onlyfans', 'escort', 'milf', 'bdsm',
                'fetish', 'orgy', 'strip', 'lingerie', 'bikini'
            ],
            'violence': [
                'gore', 'blood', 'murder', 'kill', 'torture', 'brutal',
                'weapon', 'gun', 'knife', 'dead', 'death', 'violent'
            ],
            'drugs': [
                'drug', 'cocaine', 'heroin', 'marijuana', 'weed',
                'meth', 'lsd', 'ecstasy', 'opium', 'narcotic'
            ],
            'gambling': [
                'casino', 'gambling', 'bet', 'poker', 'slot machine',
                'lottery', 'jackpot', 'roulette'
            ],
            'hate': [
                'racist', 'hate', 'discriminat', 'terrorist', 'extremist',
                'offensive', 'abusive', 'harassment'
            ]
        }
        
        self.nsfw_extensions = [
            '.xxx', '.porn', '.adult', '.nsfw'
        ]
        
    async def detect_text(self, text: str) -> Dict:
        """Detect NSFW content in text"""
        try:
            text_lower = text.lower()
            detected_categories = []
            detected_keywords = []
            
            for category, keywords in self.nsfw_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        detected_categories.append(category)
                        detected_keywords.append(keyword)
                        
            is_nsfw = len(detected_categories) > 0
            
            return {
                'is_nsfw': is_nsfw,
                'categories': list(set(detected_categories)),
                'keywords': list(set(detected_keywords)),
                'confidence': min(100, len(detected_keywords) * 25),
                'safe': not is_nsfw
            }
            
        except Exception as e:
            return {'error': str(e), 'is_nsfw': False, 'safe': True}
            
    async def detect_filename(self, file_name: str) -> Dict:
        """Detect NSFW content in filename"""
        try:
            file_name_lower = file_name.lower()
            
            # Check extension
            extension = os.path.splitext(file_name_lower)[1]
            if extension in self.nsfw_extensions:
                return {
                    'is_nsfw': True,
                    'categories': ['explicit'],
                    'keywords': [extension],
                    'confidence': 100,
                    'safe': False
                }
                
            # Check keywords in filename
            return await self.detect_text(file_name_lower)
            
        except Exception as e:
            return {'error': str(e), 'is_nsfw': False, 'safe': True}
            
    async def detect_file_content(self, file_path: str) -> Dict:
        """Detect NSFW content in file"""
        try:
            # Check if it's a text file
            text_extensions = ['.txt', '.md', '.log', '.csv', '.json']
            extension = os.path.splitext(file_path)[1].lower()
            
            if extension in text_extensions:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1024 * 1024)  # Read first 1MB
                    return await self.detect_text(content)
                    
            # For images/videos, we would use image recognition
            # For now, check filename
            return await self.detect_filename(os.path.basename(file_path))
            
        except Exception as e:
            return {'error': str(e), 'is_nsfw': False, 'safe': True}
            
    async def log_nsfw(self, user_id: int, chat_id: int, content_type: str, result: Dict):
        """Log NSFW detection"""
        log_data = {
            'user_id': user_id,
            'chat_id': chat_id,
            'content_type': content_type,
            'categories': result.get('categories', []),
            'keywords': result.get('keywords', []),
            'confidence': result.get('confidence', 0),
            'timestamp': time.time()
        }
        
        await self.collection.insert_one(log_data)
        
    async def get_nsfw_stats(self) -> Dict:
        """Get NSFW detection statistics"""
        total = await self.collection.count_documents({})
        
        # Get category stats
        categories = {}
        cursor = self.collection.find({})
        async for log in cursor:
            for category in log.get('categories', []):
                categories[category] = categories.get(category, 0) + 1
                
        return {
            'total_detections': total,
            'categories': categories,
            'timestamp': time.time()
        }
        
    async def is_safe_content(self, content: str, file_name: str = "") -> bool:
        """Check if content is safe"""
        if content:
            text_result = await self.detect_text(content)
            if text_result['is_nsfw']:
                return False
                
        if file_name:
            file_result = await self.detect_filename(file_name)
            if file_result['is_nsfw']:
                return False
                
        return True

# Create instance
nsfw_detector = NSFDetector()
