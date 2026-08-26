import os
import zipfile
import rarfile
import py7zr
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.helpers.utils import Utils
from bot.modules.uploader import uploader

@Client.on_message(filters.command("zip") & filters.private)
async def zip_command(client: Client, message: Message):
    """Handle /zip command"""
    user = message.from_user
    
    if not message.reply_to_message:
        await message.reply_text("📝 **Usage:** Reply to a file with /zip")
        return
    
    replied = message.reply_to_message
    
    if not replied.document:
        await message.reply_text("❌ **Reply to a document!**")
        return
    
    status_msg = await message.reply_text("📦 **Creating zip...**")
    
    try:
        # Download file
        file_path = await replied.download()
        
        # Create zip
        zip_path = file_path + ".zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, os.path.basename(file_path))
        
        # Upload zip
        await uploader.upload_to_telegram(
            client,
            zip_path,
            message.chat.id,
            caption=f"📦 **Zipped:** {os.path.basename(file_path)}"
        )
        
        await status_msg.edit_text("✅ **Zip created and uploaded!**")
        
        # Clean up
        os.remove(file_path)
        os.remove(zip_path)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.command("unzip") & filters.private)
async def unzip_command(client: Client, message: Message):
    """Handle /unzip command"""
    user = message.from_user
    
    if not message.reply_to_message:
        await message.reply_text("📝 **Usage:** Reply to a zip file with /unzip")
        return
    
    replied = message.reply_to_message
    
    if not replied.document:
        await message.reply_text("❌ **Reply to a document!**")
        return
    
    status_msg = await message.reply_text("📦 **Extracting...**")
    
    try:
        # Download file
        file_path = await replied.download()
        
        # Extract based on extension
        extract_dir = file_path + "_extracted"
        os.makedirs(extract_dir, exist_ok=True)
        
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.extractall(extract_dir)
        elif file_path.endswith('.rar'):
            with rarfile.RarFile(file_path, 'r') as rf:
                rf.extractall(extract_dir)
        elif file_path.endswith('.7z'):
            with py7zr.SevenZipFile(file_path, 'r') as szf:
                szf.extractall(extract_dir)
        else:
            await status_msg.edit_text("❌ **Unsupported format!**")
            return
        
        # Upload extracted files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                await uploader.upload_to_telegram(
                    client,
                    file_path,
                    message.chat.id
                )
        
        await status_msg.edit_text("✅ **Extraction complete!**")
        
        # Clean up
        os.remove(file_path)
        import shutil
        shutil.rmtree(extract_dir)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

@Client.on_message(filters.command("rename") & filters.private)
async def rename_command(client: Client, message: Message):
    """Handle /rename command"""
    user = message.from_user
    
    if not message.reply_to_message:
        await message.reply_text("📝 **Usage:** Reply to file with /rename new_name")
        return
    
    if len(message.command) < 2:
        await message.reply_text("📝 **Usage:** /rename new_name")
        return
    
    replied = message.reply_to_message
    
    if not replied.document and not replied.video:
        await message.reply_text("❌ **Reply to a file!**")
        return
    
    new_name = " ".join(message.command[1:])
    new_name = Utils.clean_filename(new_name)
    
    status_msg = await message.reply_text(f"📝 **Renaming to:** {new_name}")
    
    try:
        # Download file
        file_path = await replied.download()
        
        # Rename
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        os.rename(file_path, new_path)
        
        # Upload renamed file
        await uploader.upload_to_telegram(
            client,
            new_path,
            message.chat.id,
            caption=f"📝 **Renamed:** {new_name}"
        )
        
        await status_msg.edit_text("✅ **File renamed and uploaded!**")
        
        # Clean up
        os.remove(new_path)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")
