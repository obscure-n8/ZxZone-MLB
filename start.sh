#!/bin/bash

<<<<<<< HEAD
set -e
python update.py
exec python -m bot
=======
# ZxZone-MLB Start Script for Heroku Web Process
echo "====================================="
echo "ZxZone-MLB Bot Starting..."
echo "Powered By Zonexus Hub"
echo "====================================="

# Set environment
export PYTHONUNBUFFERED=1
export PORT=${PORT:-8080}

# Create necessary directories
mkdir -p /app/downloads /app/encode /app/thumbnails /app/config /app/sessions /app/data/logs

# 1. Start Aria2 in background 
if command -v aria2c &> /dev/null; then
    echo "Starting Aria2..."
    aria2c --enable-rpc \
        --rpc-listen-all=true \
        --rpc-allow-origin-all \
        --rpc-listen-port=6800 \
        --max-connection-per-server=16 \
        --split=16 \
        --dir=/app/downloads \
        --daemon=true \
        > /dev/null 2>&1 &
    echo "Aria2 started!"
else
    echo "Aria2 not found, skipping..."
fi

# 2. Start qBittorrent in background 
if command -v qbittorrent-nox &> /dev/null; then
    echo "Starting qBittorrent-nox..."
    qbittorrent-nox -d > /dev/null 2>&1
    echo "qBittorrent started!"
else
    echo "qBittorrent-nox not found, skipping..."
fi

# Start web server in background
echo "Starting web server..."
python3 web_server.py > /dev/null 2>&1 &
WEB_PID=$!
echo "Web server started on port $PORT"

# Wait for web server to be ready
sleep 3

# 3. Start main bot 
echo "Starting Telegram Bot..."
python3 -m bot.core.client

# If bot exits, keep container alive with web server
echo "Bot exited, keeping web server alive..."
wait $WEB_PID
>>>>>>> dc9f6270dd208eb8a6a5a49f09fd36dc91a1f363
