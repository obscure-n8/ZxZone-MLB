# ZxZone-MLB — The Ultimate Telegram Mirror & Leech Bot

The Most Powerful and Feature-Rich Bot Ever Built

---

## Overview

ZxZone-MLB is not just another mirror bot. It is a complete download management system built with over 180 advanced features. Whether you need to download, upload, search, or manage files, this bot handles everything with speed, security, and intelligence.

---

## Why ZxZone-MLB?

Most bots offer basic downloading. ZxZone-MLB goes far beyond that with AI-powered tools, enterprise-level security, and complete user management. It is built for power users who demand more.

---

## Download System

### Supported Sources:
- Direct HTTP and HTTPS links
- Torrent and Magnet links
- YouTube videos and playlists
- Mega.nz
- Gofile.io
- Pixeldrain
- Google Drive
- MediaFire
- Icc.Tv videos
- Viking files
- M3U8 streams
- Instagram Reels
- TikTok videos
- Facebook videos
- Twitter videos

### Advanced Download Features:
- Batch downloading with multiple links at once
- Smart retry system that automatically resumes failed downloads
- JDownloader integration supporting over 1000 websites
- Password protected file support
- Resume support for interrupted downloads
- Speed control and limiting
- Smart downloader with auto detection

---

## Upload System

### Upload To:
- Telegram as document, video, or audio
- Google Drive
- Team Drive
- Any of 50 plus cloud services via Rclone
- Dump channel

### Advanced Upload Features:
- Custom thumbnail support
- HD thumbnail auto generation (1280x720)
- Custom caption support
- AI-powered caption generation
- Automatic splitting of large files (2GB to 4GB)
- Multiple upload modes
- Link generator for shared downloads
- Automatic upload after download completion

---

## Video Tools

- Video merge system
- Video convert
- Encode
- Multi-resolution
- HardSub
- Watermark
- Aspect ratio change
- Audio extract
- Video compress
- Video and audio merge
- Video and subtitle merge
- Remove audio
- Remove streams
- Strip metadata
- Extract subtitles and audio
- Swap audio

---

## Search System

- Torrent search across multiple engines
- Image search with quality filters
- Multi-source search
- Category filtering
- Seeder and leecher filtering
- Instant download from search results

---

## Security System

- NSFW content detection
- 18+ content filtering
- Spam detection
- Abusive content filtering
- Malware and virus scanning
- File health checking
- Force subscribe system
- Rate limiting
- Permission-based access control

---

## AI-Powered Features

### AI Caption Generator
Automatically creates captions for files by detecting category and quality.

### Smart File Organizer
Organizes files automatically by type and category.

### File Detective
Performs deep file analysis including magic byte detection and hash verification.

### Smart Scheduler
Allows scheduling of tasks at specific times.

### Smart Retry System
Automatically retries failed downloads with exponential backoff.

### Auto Recovery
Automatically recovers from crashes and errors.

---

## User Management

### Premium System
- Weekly, monthly, and yearly plans
- Priority queue for premium users
- Speed boost
- Unlimited task limits
- VIP support

### Session String
- 4GB split size support
- Faster upload speed
- Premium features access

### Admin System
- Complete owner panel
- Sudo user management
- Admin controls
- Permission levels
- Admin activity logs

---

## Settings System

### User Settings (/usetting)
- Leech settings
- General settings
- Private files management

### Bot Settings (/bsetting)
- 15 pages of config variables
- 5 pages of Aria2 settings
- Private files management
- JD account management

---

## Commands
/start - Start the bot
/help - View help menu
/mirror - Mirror files to cloud
/leech - Leech files to Telegram
/qbleech - Queue batch leech
/qbmirror - Queue batch mirror
/ytdlleech - YouTube leech
/yt-dl - YouTube download
/jdmirror - JD mirror
/jdleech - JD leech
/rclone - Rclone operations
/usetting - User settings
/bsetting - Bot settings
/thumb - Set thumbnail
/restart - Restart bot
/cancelalltask - Cancel all tasks
/stats - User statistics
/mysession - Check session status


---

## Deployment

### VPS Deploy

```bash
apt update -y && apt install python3 python3-pip git ffmpeg screen -y
cd /root
git clone https://github.com/obscure-n8/ZxZone-MLB.git
cd ZxZone-MLB
pip3 install -r requirements.txt
cp .env.example .env
nano .env
screen -S bot
python3 -m bot

Heroku Deploy
Click the deploy button or use Heroku CLI:

bash
heroku create your-bot-name
git push heroku main
heroku ps:scale web=1 worker=1

Railway Deploy
Go to Railway

Deploy from GitHub

Select this repo

Add environment variables

Deploy

Docker Deploy
bash
docker build -t zxzone-mlb .
docker run -d --name zxzone-mlb \
  -e BOT_TOKEN=your_token \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e OWNER_ID=your_id \
  -e DATABASE_URL=mongodb_url \
  zxzone-mlb
Environment Variables
Variable	Description	Required
BOT_TOKEN	Telegram Bot Token	Yes
API_ID	Telegram API ID	Yes
API_HASH	Telegram API Hash	Yes
OWNER_ID	Your Telegram ID	Yes
DATABASE_URL	MongoDB URL	Yes
BOT_USERNAME	Bot Username	No
UPDATE_CHANNEL	Update Channel Link	No
REPO_LINK	Repository Link	No
MongoDB Setup
Go to MongoDB Atlas

Create free account

Create free cluster (M0)

Create database user

Allow all IPs (0.0.0.0/0)

Copy connection string

Use in DATABASE_URL

Telegram Info
BOT_TOKEN: @BotFather

API_ID & API_HASH: my.telegram.org

OWNER_ID: @userinfobot

Supported Platforms
Telegram

Google Drive

Mega

Gofile

Pixeldrain

Dropbox

OneDrive

YouTube

Torrents

Direct Links

Icc.Tv

Viking Files

Tech Stack
Python 3.11+

Pyrogram

MongoDB

Redis

Aria2

Qbittorrent

Rclone

YT-DLP

FFmpeg

Docker

Performance
Handles 50 to 70 concurrent tasks

High-speed downloads

Parallel processing

Automatic recovery

VPS full power mode

Heroku optimized mode

Credits
Powered By Zonexus Hub

Channel: https://t.me/zxzoneupdates

Repo: https://github.com/obscure-n8/ZxZone-MLB

License
MIT License

Disclaimer
This bot is for educational purposes only. Use responsibly.
