FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    ffmpeg \
    unzip \
    unrar \
    p7zip-full \
    p7zip-rar \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Create necessary directories
RUN mkdir -p downloads encode thumbnails config

# Set permissions
RUN chmod 777 /app

# Expose port for health check
EXPOSE 8080

# Run bot
CMD ["python", "-m", "bot"]
