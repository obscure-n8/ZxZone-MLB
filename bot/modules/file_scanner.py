import os
import hashlib
import asyncio
from typing import Dict, List, Optional
from bot.database.db import db

class FileScanner:
    """File security scanner"""
    
    def __init__(self):
        self.collection = db.scanned_files
        self.suspicious_extensions = [
            '.exe', '.bat', '.cmd', '.sh', '.msi', '.dll',
            '.scr', '.vbs', '.ps1', '.js', '.jar', '.reg'
        ]
        
        self.known_malware_hashes = set()  # Would load from database
        
    async def scan_file(self, file_path: str) -> Dict:
        """Scan file for security threats"""
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            extension = os.path.splitext(file_name)[1].lower()
            
            # Calculate hash
            md5_hash = await self.calculate_md5(file_path)
            
            # Check if known malware
            is_malware = md5_hash in self.known_malware_hashes
            
            # Check suspicious extension
            is_suspicious = extension in self.suspicious_extensions
            
            # Check file size
            is_too_large = file_size > 2 * 1024 * 1024 * 1024
            
            # Check for double extension
            double_extension = False
            if file_name.count('.') > 1:
                double_extension = True
                
            # Calculate risk score
            risk_score = 0
            risks = []
            
            if is_malware:
                risk_score += 100
                risks.append('Known malware detected')
                
            if is_suspicious:
                risk_score += 30
                risks.append('Suspicious file type')
                
            if double_extension:
                risk_score += 20
                risks.append('Double extension detected')
                
            if is_too_large:
                risk_score += 10
                risks.append('File too large')
                
            # Save scan result
            scan_result = {
                'file_name': file_name,
                'file_size': file_size,
                'md5': md5_hash,
                'extension': extension,
                'risk_score': risk_score,
                'is_safe': risk_score < 50,
                'risks': risks,
                'scanned_at': time.time()
            }
            
            await self.collection.insert_one(scan_result)
            
            return scan_result
            
        except Exception as e:
            return {'error': str(e), 'is_safe': False}
            
    async def calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 hash"""
        hash_obj = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
        
    async def scan_text(self, text: str) -> Dict:
        """Scan text for malicious content"""
        # Check for suspicious URLs
        suspicious_urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        
        # Check for phishing patterns
        phishing_patterns = [
            'verify your account',
            'update your information',
            'confirm your password',
            'account suspended',
            'unusual activity',
            'click here to login',
            'secure your account'
        ]
        
        detected_phishing = []
        for pattern in phishing_patterns:
            if pattern in text.lower():
                detected_phishing.append(pattern)
                
        return {
            'suspicious_urls': suspicious_urls,
            'phishing_patterns': detected_phishing,
            'is_safe': len(suspicious_urls) == 0 and len(detected_phishing) == 0
        }
        
    async def get_scan_stats(self) -> Dict:
        """Get scanning statistics"""
        total_scans = await self.collection.count_documents({})
        unsafe_files = await self.collection.count_documents({'is_safe': False})
        
        return {
            'total_scans': total_scans,
            'unsafe_files': unsafe_files,
            'safe_files': total_scans - unsafe_files,
            'timestamp': time.time()
        }

# Create instance
file_scanner = FileScanner()
