import os
import sys
import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from bot.config import Config

class EnhancedLogging:
    """Enhanced logging system"""
    
    def __init__(self):
        self.log_dir = os.path.join(Config.BASE_DIR, 'data', 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.setup_loggers()
        
    def setup_loggers(self):
        """Setup all loggers"""
        # Main logger
        self.main_logger = self.create_logger('main', 'bot.log')
        
        # Error logger
        self.error_logger = self.create_logger('error', 'error.log')
        
        # Download logger
        self.download_logger = self.create_logger('download', 'download.log')
        
        # Upload logger
        self.upload_logger = self.create_logger('upload', 'upload.log')
        
        # User logger
        self.user_logger = self.create_logger('user', 'user.log')
        
    def create_logger(self, name: str, filename: str) -> logging.Logger:
        """Create logger with rotation"""
        logger = logging.getLogger(f'zxzone_{name}')
        logger.setLevel(logging.INFO)
        
        # File handler with rotation
        file_path = os.path.join(self.log_dir, filename)
        handler = RotatingFileHandler(
            file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    def log_download(self, user_id: int, url: str, status: str, details: str = ""):
        """Log download activity"""
        self.download_logger.info(f"User: {user_id} | URL: {url[:50]} | Status: {status} | {details}")
        
    def log_upload(self, user_id: int, file_name: str, status: str, details: str = ""):
        """Log upload activity"""
        self.upload_logger.info(f"User: {user_id} | File: {file_name} | Status: {status} | {details}")
        
    def log_user_action(self, user_id: int, action: str, details: str = ""):
        """Log user actions"""
        self.user_logger.info(f"User: {user_id} | Action: {action} | {details}")
        
    def log_error(self, error: Exception, context: str = ""):
        """Log error with traceback"""
        self.error_logger.error(f"Context: {context} | Error: {str(error)}")
        self.error_logger.error(traceback.format_exc())
        
    def get_recent_logs(self, log_type: str = 'main', lines: int = 50) -> List[str]:
        """Get recent logs"""
        try:
            log_file = os.path.join(self.log_dir, f'{log_type}.log')
            
            with open(log_file, 'r') as f:
                return f.readlines()[-lines:]
                
        except:
            return []
            
    def clear_logs(self, log_type: str = None):
        """Clear logs"""
        try:
            if log_type:
                log_file = os.path.join(self.log_dir, f'{log_type}.log')
                if os.path.exists(log_file):
                    os.remove(log_file)
            else:
                for file in os.listdir(self.log_dir):
                    os.remove(os.path.join(self.log_dir, file))
                    
        except:
            pass
            
    def get_log_stats(self) -> Dict:
        """Get logging statistics"""
        stats = {}
        
        for file in os.listdir(self.log_dir):
            file_path = os.path.join(self.log_dir, file)
            stats[file] = {
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            }
            
        return stats

# Create instance
enhanced_logging = EnhancedLogging()
