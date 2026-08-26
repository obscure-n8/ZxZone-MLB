import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from bot.database.users import users_db
from bot.database.tasks import tasks_db

class Analytics:
    """Advanced analytics system"""
    
    def __init__(self):
        self.analytics_data = {}
        
    async def get_user_analytics(self, user_id: int) -> Dict:
        """Get comprehensive user analytics"""
        user = await users_db.get_user(user_id)
        tasks = await tasks_db.get_user_tasks(user_id, 1000)
        
        if not user:
            return {}
            
        # Task analytics
        task_types = {}
        task_hours = {}
        success_rate = 0
        
        for task in tasks:
            task_type = task.get('task_type', 'unknown')
            task_types[task_type] = task_types.get(task_type, 0) + 1
            
            created_at = task.get('created_at')
            if created_at:
                hour = created_at.hour if isinstance(created_at, datetime) else 0
                task_hours[hour] = task_hours.get(hour, 0) + 1
                
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t.get('status') == 'completed')
        if total_tasks > 0:
            success_rate = (completed / total_tasks) * 100
            
        return {
            'user_id': user_id,
            'total_tasks': total_tasks,
            'completed_tasks': completed,
            'success_rate': success_rate,
            'task_types': task_types,
            'peak_hours': sorted(task_hours.items(), key=lambda x: x[1], reverse=True)[:5],
            'avg_tasks_per_day': total_tasks / 7 if total_tasks > 0 else 0,
            'is_premium': user.get('is_premium', False),
            'joined_at': user.get('joined_at')
        }
        
    async def get_bot_analytics(self) -> Dict:
        """Get overall bot analytics"""
        total_users = await users_db.get_total_users()
        active_users = await users_db.get_active_today()
        task_stats = await tasks_db.get_task_stats()
        
        # Get task types distribution
        task_distribution = {}
        cursor = tasks_db.collection.find({})
        async for task in cursor:
            task_type = task.get('task_type', 'unknown')
            task_distribution[task_type] = task_distribution.get(task_type, 0) + 1
            
        return {
            'total_users': total_users,
            'active_today': active_users,
            'task_stats': task_stats,
            'task_distribution': task_distribution,
            'timestamp': datetime.now()
        }
        
    async def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Get daily statistics"""
        daily_stats = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0)
            end_of_day = date.replace(hour=23, minute=59, second=59)
            
            # Get tasks for this day
            tasks_count = await tasks_db.collection.count_documents({
                'created_at': {'$gte': start_of_day, '$lte': end_of_day}
            })
            
            # Get new users
            new_users = await users_db.collection.count_documents({
                'joined_at': {'$gte': start_of_day, '$lte': end_of_day}
            })
            
            daily_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'tasks': tasks_count,
                'new_users': new_users
            })
            
        return daily_stats
        
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        from bot.modules.queue import task_queue
        import psutil
        
        queue_status = task_queue.get_queue_status()
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        return {
            'queue': queue_status,
            'cpu_usage': cpu_percent,
            'memory_usage': memory.percent,
            'uptime': time.time() - psutil.boot_time(),
            'active_connections': len(psutil.net_connections())
        }
        
    async def generate_report(self) -> str:
        """Generate comprehensive report"""
        bot_analytics = await self.get_bot_analytics()
        performance = await self.get_performance_metrics()
        daily_stats = await self.get_daily_stats(7)
        
        report = f"""
📊 **ZxZone-MLB Analytics Report**

⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

👥 **User Statistics:**
• Total Users: {bot_analytics['total_users']}
• Active Today: {bot_analytics['active_today']}

📈 **Task Statistics:**
• Total Tasks: {bot_analytics['task_stats']['total']}
• Completed: {bot_analytics['task_stats']['completed']}
• Failed: {bot_analytics['task_stats']['failed']}
• Active: {bot_analytics['task_stats']['active']}

⚡ **Performance:**
• CPU: {performance['cpu_usage']}%
• Memory: {performance['memory_usage']}%
• Queue: {performance['queue']['active']} active, {performance['queue']['waiting']} waiting

📅 **Last 7 Days:**
"""
        
        for day in daily_stats:
            report += f"• {day['date']}: {day['tasks']} tasks, {day['new_users']} new users\n"
            
        return report

# Create instance
analytics = Analytics()
