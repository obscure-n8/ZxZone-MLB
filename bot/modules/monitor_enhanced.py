import os
import time
import json
import asyncio
import psutil
from typing import Dict, Optional
from datetime import datetime
from bot.config import Config

class EnhancedMonitor:
    """Enhanced system monitoring"""
    
    def __init__(self):
        self.monitoring_data = {}
        self.alert_thresholds = {
            'cpu': 90,
            'ram': 85,
            'disk': 90
        }
        
    async def get_full_status(self) -> Dict:
        """Get full system status"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'cores': psutil.cpu_count(),
                    'frequency': psutil.cpu_freq().current if psutil.cpu_freq() else 0
                },
                'memory': {
                    'total': memory.total,
                    'used': memory.used,
                    'available': memory.available,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'network': {
                    'sent': network.bytes_sent,
                    'received': network.bytes_recv
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except:
            return {}
            
    async def check_alerts(self) -> list:
        """Check system alerts"""
        try:
            status = await self.get_full_status()
            alerts = []
            
            if status.get('cpu', {}).get('percent', 0) > self.alert_thresholds['cpu']:
                alerts.append(f"High CPU: {status['cpu']['percent']}%")
                
            if status.get('memory', {}).get('percent', 0) > self.alert_thresholds['ram']:
                alerts.append(f"High RAM: {status['memory']['percent']}%")
                
            if status.get('disk', {}).get('percent', 0) > self.alert_thresholds['disk']:
                alerts.append(f"High Disk: {status['disk']['percent']}%")
                
            return alerts
            
        except:
            return []
            
    async def generate_report(self) -> Dict:
        """Generate full monitoring report"""
        status = await self.get_full_status()
        alerts = await self.check_alerts()
        
        return {
            'status': status,
            'alerts': alerts,
            'uptime': time.time() - psutil.boot_time(),
            'python_version': os.sys.version,
            'bot_username': Config.BOT_USERNAME,
            'generated_at': datetime.now().isoformat()
        }

# Create instance
enhanced_monitor = EnhancedMonitor()
