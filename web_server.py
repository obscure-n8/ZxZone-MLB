import os
import json
from flask import Flask, request, jsonify, render_template_string
from bot.config import Config
from bot.database.users import users_db
from bot.database.tasks import tasks_db
from bot.modules.queue import task_queue
from bot.helpers.progress import Progress

app = Flask(__name__)
progress_helper = Progress()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ZxZone-MLB Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        .stat-card h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .stat-card p {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .tasks-table {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #667eea;
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .status {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        .active { background: #4CAF50; color: white; }
        .queued { background: #FF9800; color: white; }
        .completed { background: #2196F3; color: white; }
        .failed { background: #f44336; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ZxZone-MLB Dashboard</h1>
            <p>Powered By Zonexus Hub ❞</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>👥 Total Users</h3>
                <p>{{ total_users }}</p>
            </div>
            <div class="stat-card">
                <h3>📊 Total Tasks</h3>
                <p>{{ total_tasks }}</p>
            </div>
            <div class="stat-card">
                <h3>🔄 Active Tasks</h3>
                <p>{{ active_tasks }}</p>
            </div>
            <div class="stat-card">
                <h3>✅ Completed</h3>
                <p>{{ completed_tasks }}</p>
            </div>
        </div>
        
        <div class="tasks-table">
            <h2>📋 Recent Tasks</h2>
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
    </div>
</body>
</html>
"""

@app.route('/')
async def dashboard():
    """Main dashboard"""
    # Get statistics
    total_users = await users_db.get_total_users()
    task_stats = await tasks_db.get_task_stats()
    queue_status = task_queue.get_queue_status()
    
    # Get recent tasks
    recent_tasks = []
    cursor = tasks_db.collection.find().sort('created_at', -1).limit(10)
    async for task in cursor:
        recent_tasks.append(task)
    
    return render_template_string(
        HTML_TEMPLATE,
        total_users=total_users,
        total_tasks=task_stats['total'],
        active_tasks=queue_status['active'],
        completed_tasks=task_stats['completed'],
        recent_tasks=recent_tasks
    )

@app.route('/api/stats')
async def api_stats():
    """API endpoint for stats"""
    total_users = await users_db.get_total_users()
    task_stats = await tasks_db.get_task_stats()
    queue_status = task_queue.get_queue_status()
    
    return jsonify({
        'users': total_users,
        'tasks': task_stats,
        'queue': queue_status,
        'timestamp': time.time()
    })

@app.route('/api/tasks')
async def api_tasks():
    """API endpoint for tasks"""
    tasks = await tasks_db.get_active_tasks()
    return jsonify(tasks)

@app.route('/api/users')
async def api_users():
    """API endpoint for users"""
    users = await users_db.get_all_users()
    return jsonify(users)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'bot': Config.BOT_USERNAME,
        'timestamp': time.time()
    })

def start_web_server():
    """Start web server"""
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    start_web_server()
