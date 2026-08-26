import time
import re
import asyncio
from typing import Dict, List, Optional
from bot.database.db import db

class ContentFilter:
    """Advanced content filtering system"""
    
    def __init__(self):
        self.collection = db.filters
        self.spam_patterns = [
            r'buy now',
            r'click here',
            r'free money',
            r'winner',
            r'lottery',
            r'casino',
            r'betting',
            r'crypto',
            r'bitcoin',
            r'investment',
            r'earn money',
            r'make money',
            r'work from home',
            r'discount',
            r'offer',
            r'limited time',
            r'act now',
            r'don\'t miss',
            r'exclusive',
            r'guaranteed',
            r'risk-free',
            r'no obligation',
            r'free trial',
            r'cheap',
            r'cheapest',
            r'best price',
            r'lowest price',
            r'special deal',
            r'coupon',
            r'voucher',
            r'reward',
            r'bonus',
            r'cash',
            r'prize',
            r'gift card',
            r'giftcard',
            r'paypal',
            r'wire transfer',
            r'western union',
            r'money gram',
        ]
        
        self.abusive_words = [
            'stupid', 'idiot', 'dumb', 'fool', 'bastard',
            'moron', 'loser', 'shut up', 'shutup', 'hate you',
            'kill yourself', 'go die', 'worthless', 'trash'
        ]
        
    async def detect_spam(self, text: str) -> Dict:
        """Detect spam content"""
        text_lower = text.lower()
        detected_patterns = []
        
        for pattern in self.spam_patterns:
            if re.search(pattern, text_lower):
                detected_patterns.append(pattern)
                
        is_spam = len(detected_patterns) > 2  # More than 2 patterns = spam
        
        # Check for repeated characters
        repeated = re.findall(r'(.)\1{4,}', text_lower)
        if repeated:
            is_spam = True
            detected_patterns.append('repeated_characters')
            
        # Check for excessive caps
        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.7:
                is_spam = True
                detected_patterns.append('excessive_caps')
                
        return {
            'is_spam': is_spam,
            'patterns': detected_patterns,
            'confidence': min(100, len(detected_patterns) * 30),
            'safe': not is_spam
        }
        
    async def detect_abuse(self, text: str) -> Dict:
        """Detect abusive content"""
        text_lower = text.lower()
        detected_words = []
        
        for word in self.abusive_words:
            if word in text_lower:
                detected_words.append(word)
                
        is_abusive = len(detected_words) > 0
        
        return {
            'is_abusive': is_abusive,
            'words': detected_words,
            'confidence': min(100, len(detected_words) * 40),
            'safe': not is_abusive
        }
        
    async def filter_message(self, text: str) -> Dict:
        """Filter message content"""
        spam_result = await self.detect_spam(text)
        abuse_result = await self.detect_abuse(text)
        
        is_filtered = spam_result['is_spam'] or abuse_result['is_abusive']
        
        return {
            'is_filtered': is_filtered,
            'spam': spam_result,
            'abuse': abuse_result,
            'safe': not is_filtered,
            'reasons': (
                (['spam'] if spam_result['is_spam'] else []) +
                (['abuse'] if abuse_result['is_abusive'] else [])
            )
        }
        
    async def add_custom_filter(self, pattern: str, filter_type: str = 'spam') -> bool:
        """Add custom filter pattern"""
        await self.collection.insert_one({
            'pattern': pattern,
            'type': filter_type,
            'created_at': time.time()
        })
        return True
        
    async def remove_filter(self, pattern: str) -> bool:
        """Remove filter pattern"""
        result = await self.collection.delete_one({'pattern': pattern})
        return result.deleted_count > 0
        
    async def get_filters(self) -> List[Dict]:
        """Get all custom filters"""
        filters = []
        cursor = self.collection.find({})
        async for filter_data in cursor:
            filters.append(filter_data)
        return filters
        
    async def cleanup_content(self, text: str) -> str:
        """Clean filtered content"""
        # Remove spam patterns
        cleaned = text
        for pattern in self.spam_patterns:
            cleaned = re.sub(pattern, '[FILTERED]', cleaned, flags=re.IGNORECASE)
            
        # Remove abusive words
        for word in self.abusive_words:
            cleaned = re.sub(word, '[REMOVED]', cleaned, flags=re.IGNORECASE)
            
        return cleaned

# Create instance
content_filter = ContentFilter()
