import os
import time
import json
import asyncio
from flask import Flask, render_template_string, jsonify, request
from bot.config import Config
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.modules.queue import task_queue

app = Flask(__name__)

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZxZone-MLB Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 30px;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.8; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(10px);
            transition: transform 0.3s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-card h3 { margin-bottom: 15px; opacity: 0.8; }
        .stat-card .value { font-size: 2.5em; font-weight: bold; }
        .tasks-table {
            background: rgba(255,255,255,0.1);
            padding: 25px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            overflow-x: auto;
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { background: rgba(255,255,255,0.1); }
        .status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        .active { background: #4CAF50; color: white; }
        .queued { background: #FF9800; color: white; }
        .completed { background: #2196F3; color: white; }
        .failed { background: #f44336; color: white; }
        .auto-refresh { text-align: center; margin-top: 20px; opacity: 0.6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ZxZone-MLB Dashboard</h1>
            <p>Powered By Zonexus Hub</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Users</h3>
                <div class="value">{{ total_users }}</div>
            </div>
            <div class="stat-card">
                <h3>Total Tasks</h3>
                <div class="value">{{ total_tasks }}</div>
            </div>
            <div class="stat-card">
                <h3>Active Tasks</h3>
                <div class="value">{{ active_tasks }}</div>
            </div>
            <div class="stat-card">
                <h3>Completed</h3>
                <div class="value">{{ completed_tasks }}</div>
            </div>
        </div>
        
        <div class="tasks-table">
            <h2>Recent Tasks</h2>
            <table>
                <thead>
                    <tr>
                        <th>Task ID</th>
                        <th>User</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Progress</th>
                    </tr>
                </thead>
                <tbody>
                    {% for task in recent_tasks %}
                    <tr>
                        <td>{{ task.task_id }}</td>
                        <td>{{ task.user_id }}</td>
                        <td>{{ task.task_type }}</td>
                        <td><span class="status {{ task.status }}">{{ task.status }}</span></td>
                        <td>{{ task.progress }}%</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="auto-refresh">
            Auto-refresh in 30 seconds
        </div>
    </div>
    
    <script>
        setTimeout(function() {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
async def dashboard():
    """Main dashboard"""
    total_users = await users_db.get_total_users()
    task_stats = await tasks_db.get_task_stats()
    queue_status = task_queue.get_queue_status()
    
    recent_tasks = []
    cursor = tasks_db.collection.find().sort('created_at', -1).limit(10)
    async for task in cursor:
        recent_tasks.append(task)
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        total_users=total_users,
        total_tasks=task_stats['total'],
        active_tasks=queue_status['active'],
        completed_tasks=task_stats['completed'],
        recent_tasks=recent_tasks
    )

@app.route('/api/stats')
async def api_stats():
    """API stats endpoint"""
    total_users = await users_db.get_total_users()
    task_stats = await tasks_db.get_task_stats()
    queue_status = task_queue.get_queue_status()
    
    return jsonify({
        'users': total_users,
        'tasks': task_stats,
        'queue': queue_status,
        'timestamp': time.time()
    })

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'bot': Config.BOT_USERNAME,
        'timestamp': time.time()
    })
