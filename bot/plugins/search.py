from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.modules.search import torrent_search
from bot.helpers.utils import Utils
from bot.database.users import users_db

@Client.on_message(filters.command("search") & filters.private)
async def search_command(client: Client, message: Message):
    """Handle /search command"""
    user = message.from_user
    
    # Check if user is banned
    if await users_db.is_banned(user.id):
        await message.reply_text("❌ **You are banned!**")
        return
    
    # Check if search is disabled
    if Config.DISABLE_SEARCH:
        await message.reply_text("❌ **Search is disabled!**")
        return
    
    # Check query
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /search <query>\n\n"
            "Example: /search Ubuntu 22.04 ISO",
            parse_mode="markdown"
        )
        return
    
    query = " ".join(message.command[1:])
    limit = Config.SEARCH_LIMIT if Config.SEARCH_LIMIT > 0 else 10
    
    # Send searching message
    status_msg = await message.reply_text(
        f"🔍 **Searching for:** {query}\n\n"
        f"⏳ Please wait...",
        parse_mode="markdown"
    )
    
    # Search torrents
    results = await torrent_search.search_torrents(query, limit)
    
    if not results:
        await status_msg.edit_text(
            f"❌ **No results found for:** {query}",
            parse_mode="markdown"
        )
        return
    
    # Format results
    search_text = f"🔍 **Search Results for:** {query}\n\n"
    
    for i, result in enumerate(results[:limit], 1):
        search_text += f"**{i}. {result['name'][:100]}**\n"
        search_text += f"   📦 Size: {result.get('size', 'N/A')}\n"
        search_text += f"   ⬆️ Seeders: {result.get('seeders', 0)} | ⬇️ Leechers: {result.get('leechers', 0)}\n\n"
    
    # Create buttons for each result
    keyboard_buttons = []
    for i, result in enumerate(results[:limit], 1):
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"⬇️ Download #{i}",
                callback_data=f"storrent_{i}"
            )
        ])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    # Store results in memory for callback
    from bot.helpers.utils import Utils
    search_id = Utils.generate_task_id()
    # Store in a global dict
    if not hasattr(search_command, 'search_results'):
        search_command.search_results = {}
    search_command.search_results[search_id] = results
    
    await status_msg.edit_text(
        search_text,
        parse_mode="markdown",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^storrent_"))
async def search_download_callback(client: Client, callback_query):
    """Handle torrent download from search"""
    index = int(callback_query.data.split("_")[1]) - 1
    
    # Get results from memory
    if hasattr(search_command, 'search_results'):
        # Find the results
        for search_id, results in search_command.search_results.items():
            if index < len(results):
                result = results[index]
                magnet_link = result.get('magnet', '')
                
                if magnet_link:
                    await callback_query.message.edit_text(
                        f"🧲 **Starting torrent download...**\n\n"
                        f"📝 Name: {result['name'][:100]}\n"
                        f"📦 Size: {result.get('size', 'N/A')}",
                        parse_mode="markdown"
                    )
                    
                    # Process torrent
                    from bot.plugins.torrent import torrent_command
                    await torrent_command(client, callback_query.message, magnet_link)
                    
                else:
                    await callback_query.answer("No magnet link available!")
                break
    
    await callback_query.answer()

@Client.on_message(filters.command("images") & filters.private)
async def image_search_command(client: Client, message: Message):
    """Handle /images command for image search"""
    user = message.from_user
    
    # Check if image search is enabled
    if not Config.USE_IMAGES:
        await message.reply_text("❌ **Image search is disabled!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "📝 **Usage:** /images <query>\n\n"
            "Example: /images nature wallpaper",
            parse_mode="markdown"
        )
        return
    
    query = " ".join(message.command[1:])
    
    status_msg = await message.reply_text(
        f"🖼️ **Searching images for:** {query}",
        parse_mode="markdown"
    )
    
    # This would integrate with image search API
    await status_msg.edit_text(
        f"❌ **Image search not configured!**\n\n"
        f"Set IMG_SEARCH in config to enable.",
        parse_mode="markdown"
    )
