FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    git \
    ffmpeg \
    unzip \
    unrar \
    p7zip-full \
    p7zip-rar \
    procps \
    net-tools \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Aria2
RUN apt-get update && apt-get install -y --no-install-recommends aria2 \
    && rm -rf /var/lib/apt/lists/*

# Install Rclone
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip \
    && unzip rclone-current-linux-amd64.zip \
    && cd rclone-*-linux-amd64 \
    && cp rclone /usr/local/bin/ \
    && chmod 755 /usr/local/bin/rclone \
    && cd .. \
    && rm -rf rclone-*

# Install yt-dlp
RUN pip install --no-cache-dir yt-dlp

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Create necessary directories
RUN mkdir -p /app/downloads /app/encode /app/thumbnails /app/config /app/sessions /app/data/logs /app/data/backups \
    && chmod -R 755 /app

# Copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port for web server
EXPOSE 8080

# Start bot via start.sh
CMD ["/bin/bash", "/app/start.sh"]
