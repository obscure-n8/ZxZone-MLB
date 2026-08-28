import os
import time
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    """Home page for keep alive"""
    return jsonify({
        'status': 'alive',
        'bot': os.getenv('BOT_USERNAME', 'ZxZone-MLB'),
        'timestamp': time.time(),
        'message': 'Bot is running!'
    })

@app.route('/health')
def health():
    """Health check endpoint - Railway uses this"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

@app.route('/ping')
def ping():
    """Ping endpoint"""
    return jsonify({
        'status': 'ok',
        'pong': True,
        'timestamp': time.time()
    })

def start_web_server():
    """Start web server for keep alive"""
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    start_web_server()
