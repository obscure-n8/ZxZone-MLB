from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.permissions import permission_system
from bot.modules.jdownloader import jdownloader

class LinkGrabber:
    def __init__(self):
        self.file_hosts = {
            'mega': r'mega\.nz',
            'gofile': r'gofile\.io',
            'mediafire': r'mediafire\.com',
            'zippyshare': r'zippyshare\.com',
            'drive': r'drive\.google\.com',
            'dropbox': r'dropbox\.com',
            'onedrive': r'onedrive\.live\.com',
            'uptobox': r'uptobox\.com',
            '1fichier': r'1fichier\.com',
            'solidfiles': r'solidfiles\.com',
            'file.io': r'file\.io',
            'pixeldrain': r'pixeldrain\.com',
            'wetransfer': r'wetransfer\.com',
            'sendspace': r'sendspace\.com',
        }
        
    async def grab_links_from_text(self, text: str) -> list:
        """Extract links from text"""
        # Find all URLs
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        
        # Filter file host links
        file_links = []
        for url in urls:
            for host, pattern in self.file_hosts.items():
                if re.search(pattern, url, re.IGNORECASE):
                    file_links.append({
                        'url': url,
                        'host': host
                    })
                    break
                    
        return file_links
        
    async def grab_links_from_page(self, url: str) -> list:
        """Grab links from webpage"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        links = await self.grab_links_from_text(html)
                        return links
        except:
            pass
        return []
        
    async def download_from_host(self, url: str, host: str) -> bool:
        """Download from specific host"""
        try:
            if host == 'mega':
                from bot.plugins.mega import mega_command
                return True
            elif host == 'gofile':
                from bot.plugins.gofile import gofile_command
                return True
            elif host == 'drive':
                return True
            else:
                # Use JDownloader for other hosts
                await jdownloader.add_links([url])
                return True
        except:
            return False

# Create instance
link_grabber = LinkGrabber()

@Client.on_message(filters.command("grab") & filters.private)
async def grab_command(client: Client, message: Message):
    """Grab links from text/page"""
    user = message.from_user
    
    if not await permission_system.is_admin(user.id):
        await message.reply_text("❌ **You are not authorized!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:**\n"
            "/grab <url> - Grab links from page\n"
            "Or send me text with links",
            parse_mode="markdown"
        )
        return
    
    url = message.command[1]
    
    status_msg = await message.reply_text("🔗 **Grabbing links...**")
    
    # Check if URL or text
    if url.startswith('http'):
        links = await link_grabber.grab_links_from_page(url)
    else:
        text = " ".join(message.command[1:])
        links = await link_grabber.grab_links_from_text(text)
        
    if links:
        links_text = f"🔗 **Grabbed Links:** ({len(links)})\n\n"
        
        keyboard_buttons = []
        for i, link in enumerate(links[:10], 1):
            links_text += f"{i}. [{link['host'].upper()}] {link['url'][:50]}...\n"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"⬇️ Download #{i}",
                    callback_data=f"grab_{i}"
                )
            ])
            
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        # Store links
        if not hasattr(grab_command, 'grab_links'):
            grab_command.grab_links = {}
        grab_command.grab_links[message.id] = links
        
        await status_msg.edit_text(
            links_text,
            reply_markup=keyboard,
            parse_mode="markdown"
        )
    else:
        await status_msg.edit_text("❌ **No links found!**")
