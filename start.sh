#!/bin/bash

# ZxZone-MLB Bot Startup Script
echo "====================================="
echo "  ZxZone-MLB Bot Starting..."
echo "  Powered By Zonexus Hub"
echo "====================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo -e "${YELLOW}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 not found! Installing...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}pip3 not found! Installing...${NC}"
    apt-get install -y python3-pip
fi

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    wget \
    curl \
    git \
    ffmpeg \
    unzip \
    unrar \
    p7zip-full \
    p7zip-rar \
    aria2 \
    rclone

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p downloads encode thumbnails config sessions

# Check .env file
if [ ! -f .env ]; then
    echo -e "${RED}.env file not found!${NC}"
    echo -e "${YELLOW}Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env file with your credentials!${NC}"
    exit 1
fi

# Start aria2
echo -e "${YELLOW}Starting aria2...${NC}"
if command -v aria2c &> /dev/null; then
    aria2c --enable-rpc --rpc-listen-all=false --rpc-allow-origin-all \
        --rpc-listen-port=6800 --rpc-secret=$ARIA2_SECRET \
        --max-connection-per-server=10 --split=10 \
        --daemon=true --dir=/app/downloads
    echo -e "${GREEN}Aria2 started!${NC}"
else
    echo -e "${RED}Aria2 not found!${NC}"
fi

# Start bot
echo -e "${GREEN}Starting ZxZone-MLB Bot...${NC}"
python3 -m bot

# Handle exit
trap 'echo -e "${RED}Bot stopped!${NC}"; exit 0' SIGINT SIGTERM

# Keep script running
wait
