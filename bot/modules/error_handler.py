import os
import sys
import traceback
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Advanced error handling system"""
    
    def __init__(self):
        self.error_log = []
        self.error_count = 0
        self.error_file = os.path.join(Config.BASE_DIR, 'data', 'logs', 'errors.log')
        os.makedirs(os.path.dirname(self.error_file), exist_ok=True)
        
    async def handle_error(
        self,
        error: Exception,
        context: str = "",
        user_id: Optional[int] = None,
        send_to_user: bool = True
    ) -> Dict:
        """Handle error with detailed logging"""
        try:
            self.error_count += 1
            
            # Get traceback
            tb = traceback.format_exc()
            
            # Create error info
            error_info = {
                'error': str(error),
                'type': type(error).__name__,
                'context': context,
                'user_id': user_id,
                'timestamp': datetime.now(),
                'traceback': tb
            }
            
            # Log error
            logger.error(f"Error in {context}: {str(error)}")
            
            # Save to file
            with open(self.error_file, 'a') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Time: {error_info['timestamp']}\n")
                f.write(f"Context: {context}\n")
                f.write(f"User: {user_id}\n")
                f.write(f"Error: {str(error)}\n")
                f.write(f"Traceback:\n{tb}\n")
                
            # Add to list
            self.error_log.append(error_info)
            
            # Get user-friendly message
            friendly_message = self.get_friendly_message(error)
            
            return {
                'success': False,
                'error': str(error),
                'friendly_message': friendly_message,
                'error_info': error_info
            }
            
        except:
            return {'success': False, 'error': str(error)}
            
    def get_friendly_message(self, error: Exception) -> str:
        """Get user-friendly error message"""
        error_messages = {
            'ConnectionError': 'Network connection failed. Please try again.',
            'TimeoutError': 'Request timed out. Please retry.',
            'FileNotFoundError': 'File not found.',
            'PermissionError': 'Permission denied.',
            'ValueError': 'Invalid value provided.',
            'KeyError': 'Missing required data.',
            'TypeError': 'Invalid data type.',
            'aiohttp.ClientError': 'Download failed. Link might be invalid.',
        }
        
        error_type = type(error).__name__
        return error_messages.get(error_type, f'An error occurred: {str(error)}')
        
    async def get_error_stats(self) -> Dict:
        """Get error statistics"""
        return {
            'total_errors': self.error_count,
            'recent_errors': self.error_log[-10:],
            'error_log_file': self.error_file
        }
        
    async def clear_errors(self):
        """Clear error log"""
        self.error_log = []
        self.error_count = 0
        if os.path.exists(self.error_file):
            os.remove(self.error_file)
            
    async def auto_recover(self, error: Exception, retry_func=None, *args, **kwargs):
        """Auto recover from error"""
        try:
            # Log error
            await self.handle_error(error, 'auto_recover', send_to_user=False)
            
            # Retry if function provided
            if retry_func:
                for attempt in range(3):
                    try:
                        return await retry_func(*args, **kwargs)
                    except:
                        await asyncio.sleep(2 ** attempt)
                        
            return None
            
        except:
            return None

# Create instance
error_handler = ErrorHandler()
