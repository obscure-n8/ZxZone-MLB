import time
import psutil
import asyncio
from typing import Dict, Optional
from datetime import datetime
from bot.config import Config

class SystemMonitor:
    def __init__(self):
        self.monitoring = False
        self.monitor_task = None
        self.stats_history = []
        self.alert_thresholds = {
            'cpu': 90,      # Alert if CPU > 90%
            'ram': 85,      # Alert if RAM > 85%
            'disk': 90,     # Alert if Disk > 90%
            'temp': 80      # Alert if Temp > 80°C
        }
        
    async def start_monitoring(self, interval: int = 60):
        """Start system monitoring"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval))
        
    async def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            
    async def _monitor_loop(self, interval: int):
        """Monitor loop"""
        while self.monitoring:
            stats = await self.get_system_stats()
            self.stats_history.append(stats)
            
            # Keep last 100 records
            if len(self.stats_history) > 100:
                self.stats_history.pop(0)
                
            # Check alerts
            await self.check_alerts(stats)
            
            await asyncio.sleep(interval)
            
    async def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()
        disk_usage = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Get process info
        process = psutil.Process()
        process_info = {
            'pid': process.pid,
            'name': process.name(),
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'threads': process.num_threads(),
            'open_files': len(process.open_files()),
        }
        
        return {
            'timestamp': datetime.now(),
            'cpu': {
                'percent': cpu_percent,
                'cores': psutil.cpu_count(),
                'frequency': cpu_freq.current if cpu_freq else 0,
            },
            'memory': {
                'total': virtual_memory.total,
                'available': virtual_memory.available,
                'percent': virtual_memory.percent,
                'used': virtual_memory.used,
            },
            'swap': {
                'total': swap_memory.total,
                'used': swap_memory.used,
                'percent': swap_memory.percent,
            },
            'disk': {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': disk_usage.percent,
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv,
            },
            'process': process_info,
        }
        
    async def check_alerts(self, stats: Dict):
        """Check for system alerts"""
        alerts = []
        
        # CPU alert
        if stats['cpu']['percent'] > self.alert_thresholds['cpu']:
            alerts.append(f"⚠️ High CPU usage: {stats['cpu']['percent']}%")
            
        # RAM alert
        if stats['memory']['percent'] > self.alert_thresholds['ram']:
            alerts.append(f"⚠️ High RAM usage: {stats['memory']['percent']}%")
            
        # Disk alert
        if stats['disk']['percent'] > self.alert_thresholds['disk']:
            alerts.append(f"⚠️ Low disk space: {stats['disk']['percent']}% used")
            
        # Temperature check (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > self.alert_thresholds['temp']:
                            alerts.append(f"⚠️ High temperature: {name} - {entry.current}°C")
        except:
            pass
            
        return alerts
        
    async def get_uptime(self) -> Dict:
        """Get system uptime"""
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        return {
            'boot_time': datetime.fromtimestamp(boot_time),
            'uptime_seconds': int(uptime_seconds),
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'formatted': f"{days}d {hours}h {minutes}m"
        }
        
    async def get_network_stats(self) -> Dict:
        """Get network statistics"""
        network = psutil.net_io_counters()
        connections = psutil.net_connections()
        
        return {
            'bytes_sent': network.bytes_sent,
            'bytes_recv': network.bytes_recv,
            'packets_sent': network.packets_sent,
            'packets_recv': network.packets_recv,
            'error_in': network.errin,
            'error_out': network.errout,
            'drop_in': network.dropin,
            'drop_out': network.dropout,
            'active_connections': len(connections),
        }
        
    async def get_disk_io(self) -> Dict:
        """Get disk I/O statistics"""
        disk_io = psutil.disk_io_counters()
        
        return {
            'read_count': disk_io.read_count,
            'write_count': disk_io.write_count,
            'read_bytes': disk_io.read_bytes,
            'write_bytes': disk_io.write_bytes,
            'read_time': disk_io.read_time,
            'write_time': disk_io.write_time,
        }

# Create instance
system_monitor = SystemMonitor()
